"""
Issue #606: Schlussrechnung zeigte die verrechneten Abschlagsrechnungen nur im Entwurf im
Summenblock (Issue #600). Ursache: das Formular übernahm beim Bearbeiten des Entwurfs die
Markierung abschlag_rechnung_id nicht - beim Speichern wurden die Abzugszeilen zu normalen
Minus-Positionen und die Abschläge wieder freigegeben. Migration 204 repariert Bestandsdaten.
"""
from datetime import date
from decimal import Decimal

import pymupdf
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    AbschlagAusDokumentRequest,
    abschlag_aus_dokument,
    auftrag_erstellen,
    finalisiere_rechnung,
    rechnung_als_pdf,
    rechnung_aus_auftrag,
    update_rechnung,
)
from api.schemas_rechnungen import RechnungCreate, RechnungUpdate, RechnungspositionCreate
from database.connection import Base
from database.models import Forderung, Kunde, Rechnung, Unternehmen
from main import _repariere_abschlag_verknuepfung_606


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    import api.rechnungen as modul
    monkeypatch.setattr(modul, "APP_DATA_DIR", tmp_path)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Testfirma", strasse="Str.", hausnummer="1", plz="12345",
                            ort="Ort", abschlagsrechnungen_aktiv=True, ust_idnr="DE123456789",
                            iban="DE64500105175407399649"))
    kunde = Kunde(vorname="Mathilde", nachname="Musterfrau")
    session.add(kunde)
    session.commit()
    yield engine, session, kunde.id
    session.close()


def _text(resp) -> str:
    return "".join(p.get_text() for p in pymupdf.open(stream=resp.body, filetype="pdf"))


def _schlussrechnung(s, k, anzahl=3) -> tuple[Rechnung, list[Rechnung]]:
    auftrag = s.get(Rechnung, auftrag_erstellen(RechnungCreate(
        typ="ausgang", dokument_typ="Auftrag", datum=date(2026, 11, 28), ist_entwurf=False,
        kunde_id=k, eingabemodus="brutto",
        positionen=[RechnungspositionCreate(beschreibung="Führung", menge=Decimal("1"),
                                            netto=Decimal("120.00"), ust_satz=Decimal("19"))],
    ), s).id)
    abschlaege = []
    for _ in range(anzahl):
        a = s.get(Rechnung, abschlag_aus_dokument(auftrag.id, AbschlagAusDokumentRequest(betrag=Decimal("30")), s).id)
        finalisiere_rechnung(a.id, s)
        s.refresh(a)
        a.bezahlt_betrag = a.brutto_gesamt
        a.zahlungsstatus = "bezahlt"
        s.commit()
        abschlaege.append(a)
    return s.get(Rechnung, rechnung_aus_auftrag(auftrag.id, s).id), abschlaege


def _formular_speichern(s, r: Rechnung):
    """Speichert den Entwurf so, wie das Formular es nach dem Fix tut (Markierung bleibt)."""
    positionen = [RechnungspositionCreate(
        beschreibung=p.beschreibung, menge=p.menge, einheit=p.einheit, netto=abs(p.netto),
        ust_satz=p.ust_satz, abschlag_rechnung_id=p.abschlag_rechnung_id,
    ) for p in sorted(r.positionen, key=lambda p: p.position_nr or 0)]
    update_rechnung(r.id, RechnungUpdate(positionen=positionen), s)


def test_finalisiert_zeigt_abzug_im_summenblock(umgebung):
    _, s, k = umgebung
    schluss, _ = _schlussrechnung(s, k)
    finalisiere_rechnung(schluss.id, s)
    s.expire_all()
    final = _text(rechnung_als_pdf(schluss.id, db=s))
    assert "Gesamtbetrag der Leistung" in final
    assert "Abzgl. Abschlagsrechnung" not in final  # nicht als Position in der Tabelle


def test_entwurf_bearbeiten_behaelt_verrechnung(umgebung):
    _, s, k = umgebung
    schluss, abschlaege = _schlussrechnung(s, k)
    _formular_speichern(s, schluss)
    finalisiere_rechnung(schluss.id, s)
    s.expire_all()
    assert sum(1 for p in s.get(Rechnung, schluss.id).positionen if p.abschlag_rechnung_id) == 3
    assert all(s.get(Rechnung, a.id).verrechnet_in_rechnung_id == schluss.id for a in abschlaege)
    assert "Gesamtbetrag der Leistung" in _text(rechnung_als_pdf(schluss.id, db=s))


def _kaputt_machen(s, schluss: Rechnung, abschlaege: list[Rechnung]):
    """Zustand wie vor dem Fix nach dem Speichern im Formular."""
    for p in schluss.positionen:
        p.abschlag_rechnung_id = None
    for a in abschlaege:
        a.verrechnet_in_rechnung_id = None
    s.commit()


def test_datenfix_stellt_verrechnung_wieder_her(umgebung):
    engine, s, k = umgebung
    schluss, abschlaege = _schlussrechnung(s, k)
    finalisiere_rechnung(schluss.id, s)
    s.add(Forderung(typ="kundenguthaben", status="offen", betrag=Decimal("5.00"),
                    partner_typ="kunde", partner_id=k, rechnung_id=abschlaege[0].id))
    _kaputt_machen(s, schluss, abschlaege)

    with engine.connect() as conn:
        assert _repariere_abschlag_verknuepfung_606(conn) == 3
        conn.commit()
        assert _repariere_abschlag_verknuepfung_606(conn) == 0  # zweiter Lauf ändert nichts
        protokoll = conn.execute(text(
            "SELECT tabelle, feld FROM aenderungsprotokoll WHERE migration_version = 204")).fetchall()
    s.expire_all()
    assert all(s.get(Rechnung, a.id).verrechnet_in_rechnung_id == schluss.id for a in abschlaege)
    assert {p.abschlag_rechnung_id for p in s.get(Rechnung, schluss.id).positionen} - {None} == {a.id for a in abschlaege}
    assert s.query(Forderung).one().status == "ausgeglichen"
    assert sorted(protokoll) == sorted(
        [("rechnungspositionen", "abschlag_rechnung_id")] * 3
        + [("rechnungen", "verrechnet_in_rechnung_id")] * 3
        + [("forderungen", "status")]
    )
    assert "Gesamtbetrag der Leistung" in _text(rechnung_als_pdf(schluss.id, db=s))


def test_datenfix_laesst_bereits_wieder_verrechneten_abschlag(umgebung):
    """Wurde der freigegebene Abschlag inzwischen anderswo verrechnet, bleibt alles unverändert."""
    engine, s, k = umgebung
    schluss, abschlaege = _schlussrechnung(s, k, anzahl=1)
    _kaputt_machen(s, schluss, abschlaege)
    abschlaege[0].verrechnet_in_rechnung_id = schluss.id + 1000
    s.commit()
    with engine.connect() as conn:
        assert _repariere_abschlag_verknuepfung_606(conn) == 0
