"""
Issue #597: Abschlagsrechnung aus Angebot/Auftrag erstellen, Schlussrechnung aus dem Dokument
zieht die bezahlten Abschläge automatisch ab.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    AbschlagAusDokumentRequest,
    abschlag_aus_dokument,
    auftrag_erstellen,
    create_rechnung,
    finalisiere_rechnung,
    rechnung_aus_angebot,
    rechnung_aus_auftrag,
)
from api.schemas_rechnungen import RechnungCreate, RechnungResponse, RechnungspositionCreate
from database.connection import Base
from database.models import Kunde, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Testfirma", strasse="Str.", hausnummer="1", plz="12345",
                            ort="Ort", abschlagsrechnungen_aktiv=True))
    kunde = Kunde(firmenname="Kunde GmbH")
    session.add(kunde)
    session.commit()
    yield session, kunde.id
    session.close()


def _pos(netto, satz="19", menge="1"):
    return RechnungspositionCreate(beschreibung="Leistung", menge=Decimal(menge), netto=Decimal(netto),
                                   ust_satz=Decimal(satz))


def _auftrag(db, kunde_id, positionen=None, **kw):
    resp = auftrag_erstellen(RechnungCreate(
        typ="ausgang", dokument_typ="Auftrag", datum=date(2026, 11, 1), ist_entwurf=False, kunde_id=kunde_id,
        positionen=positionen or [_pos("10000.00")], **kw,
    ), db)
    return db.get(Rechnung, resp.id)


def _angebot(db, kunde_id):
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Angebot", datum=date(2026, 11, 1), ist_entwurf=False, kunde_id=kunde_id,
        positionen=[_pos("5000.00")],
    ), db)
    return db.get(Rechnung, resp.id)


def _abschlag(db, dok, **kw) -> Rechnung:
    resp = abschlag_aus_dokument(dok.id, AbschlagAusDokumentRequest(**kw), db)
    return db.get(Rechnung, resp.id)


def _bezahlt(db, abschlag: Rechnung) -> Rechnung:
    finalisiere_rechnung(abschlag.id, db)
    db.refresh(abschlag)
    abschlag.bezahlt_betrag = abschlag.brutto_gesamt
    abschlag.zahlungsstatus = "bezahlt"
    db.commit()
    return abschlag


def test_abschlag_prozent_aus_auftrag(db):
    s, k = db
    auftrag = _auftrag(s, k)
    a = _abschlag(s, auftrag, prozent=Decimal("30"))
    assert a.dokument_typ == "Abschlagsrechnung" and a.ist_entwurf
    assert a.abschlag_zu_dokument_id == auftrag.id and a.kunde_id == k
    assert a.netto_gesamt == Decimal("3000.00") and a.brutto_gesamt == Decimal("3570.00")
    assert len(a.positionen) == 1
    assert a.positionen[0].beschreibung == f"Abschlag 30 % auf Auftrag {auftrag.rechnungsnummer}"
    # Auftrag bleibt offen, damit die Schlussrechnung möglich bleibt
    s.refresh(auftrag)
    assert auftrag.auftrag_status == "offen"


def test_abschlag_betrag_mehrere_steuersaetze(db):
    s, k = db
    auftrag = _auftrag(s, k, positionen=[_pos("1000.00", "19"), _pos("1000.00", "7")])  # 1190 + 1070
    a = _abschlag(s, auftrag, betrag=Decimal("1130.00"))  # genau 50 %
    assert {p.ust_satz for p in a.positionen} == {Decimal("19"), Decimal("7")}
    assert a.netto_gesamt == Decimal("1000.00")
    assert a.brutto_gesamt == Decimal("1130.00")
    assert all("Anteil" in p.beschreibung for p in a.positionen)


def test_abschlag_beruecksichtigt_rechnungsrabatt(db):
    s, k = db
    auftrag = _auftrag(s, k, rabatt_prozent=Decimal("10"))  # 9000 netto
    a = _abschlag(s, auftrag, prozent=Decimal("50"))
    assert a.netto_gesamt == Decimal("4500.00")


def test_abschlag_nicht_ueber_restbetrag(db):
    s, k = db
    auftrag = _auftrag(s, k)
    _abschlag(s, auftrag, prozent=Decimal("60"))
    with pytest.raises(HTTPException) as e:
        _abschlag(s, auftrag, prozent=Decimal("50"))
    assert e.value.status_code == 422
    _abschlag(s, auftrag, prozent=Decimal("40"))  # genau der Rest geht


@pytest.mark.parametrize("kw", [{}, {"prozent": Decimal("10"), "betrag": Decimal("5")},
                                {"prozent": Decimal("0")}, {"prozent": Decimal("101")},
                                {"betrag": Decimal("-1")}])
def test_eingabe_ungueltig(db, kw):
    s, k = db
    auftrag = _auftrag(s, k)
    with pytest.raises(HTTPException) as e:
        _abschlag(s, auftrag, **kw)
    assert e.value.status_code == 422


def test_schalter_aus_gesperrt(db):
    s, k = db
    s.query(Unternehmen).first().abschlagsrechnungen_aktiv = False
    s.commit()
    with pytest.raises(HTTPException) as e:
        _abschlag(s, _auftrag(s, k), prozent=Decimal("30"))
    assert e.value.status_code == 409


def test_schlussrechnung_aus_auftrag_zieht_bezahlte_ab(db):
    s, k = db
    auftrag = _auftrag(s, k)
    bezahlt = _bezahlt(s, _abschlag(s, auftrag, prozent=Decimal("30")))
    unbezahlt = _abschlag(s, auftrag, prozent=Decimal("20"))
    finalisiere_rechnung(unbezahlt.id, s)

    resp = rechnung_aus_auftrag(auftrag.id, s)
    schluss = s.get(Rechnung, resp.id)
    abzug = [p for p in schluss.positionen if p.abschlag_rechnung_id]
    assert [p.abschlag_rechnung_id for p in abzug] == [bezahlt.id]
    assert abzug[0].menge == Decimal("-1")
    assert schluss.netto_gesamt == Decimal("7000.00")
    assert schluss.brutto_gesamt == Decimal("8330.00")
    s.refresh(bezahlt)
    s.refresh(unbezahlt)
    assert bezahlt.verrechnet_in_rechnung_id == schluss.id
    assert unbezahlt.verrechnet_in_rechnung_id is None


def test_kein_abschlag_nach_schlussrechnung(db):
    s, k = db
    auftrag = _auftrag(s, k)
    rechnung_aus_auftrag(auftrag.id, s)
    with pytest.raises(HTTPException) as e:
        _abschlag(s, auftrag, prozent=Decimal("10"))
    assert e.value.status_code == 409


def test_angebot_abschlag_und_schlussrechnung(db):
    s, k = db
    angebot = _angebot(s, k)
    a = _bezahlt(s, _abschlag(s, angebot, betrag=Decimal("1190.00")))
    assert a.netto_gesamt == Decimal("1000.00")
    resp = rechnung_aus_angebot(angebot.id, s)
    schluss = s.get(Rechnung, resp.id)
    assert schluss.netto_gesamt == Decimal("4000.00")


def test_response_listet_abschlaege_und_herkunft(db):
    s, k = db
    auftrag = _auftrag(s, k)
    a = _abschlag(s, auftrag, prozent=Decimal("25"))
    s.refresh(auftrag)
    r = RechnungResponse.from_orm_extended(auftrag)
    assert [x.id for x in r.abschlaege] == [a.id]
    ra = RechnungResponse.from_orm_extended(a)
    assert ra.abschlag_zu_dokument_id == auftrag.id
    assert ra.abschlag_zu_dokument_typ == "Auftrag"
    assert ra.abschlag_zu_dokument_nr == auftrag.rechnungsnummer


def test_migration_202(tmp_path, monkeypatch):
    import main
    from sqlalchemy import text
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE rechnungen (id INTEGER PRIMARY KEY, rechnungsnummer TEXT)"))
        conn.execute(text("PRAGMA user_version = 201"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        spalten = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)"))}
        assert "abschlag_zu_dokument_id" in spalten
        assert conn.execute(text("PRAGMA user_version")).scalar() == 202
        conn.execute(text("PRAGMA user_version = 201"))
    main._run_migrations()  # zweiter Lauf ändert nichts


# ── Rechnungsrabatt gilt nicht für Abzugszeilen ──────────────────────────────

def test_schlussrechnung_mit_rabatt_zieht_vollen_abschlag_ab(db):
    s, k = db
    auftrag = _auftrag(s, k, rabatt_prozent=Decimal("10"))  # 9000 netto
    a = _bezahlt(s, _abschlag(s, auftrag, prozent=Decimal("30")))  # 2700 netto
    schluss = s.get(Rechnung, rechnung_aus_auftrag(auftrag.id, s).id)
    assert schluss.netto_gesamt == Decimal("6300.00")  # vorher 6570,00
    assert schluss.brutto_gesamt == auftrag.brutto_gesamt - a.brutto_gesamt


@pytest.mark.parametrize("modus", ["netto", "brutto"])
def test_berechnung_rabatt_ohne_abzug_unveraendert(modus):
    from types import SimpleNamespace as P
    from api.rechnungen import _berechne_rechnung
    leistung = P(netto=Decimal("1000"), menge=Decimal("1"), ust_satz=Decimal("19"))
    abzug = P(netto=Decimal("300") if modus == "netto" else Decimal("357"), menge=Decimal("-1"),
              ust_satz=Decimal("19"), abschlag_rechnung_id=1)
    ohne = _berechne_rechnung([leistung], modus, Decimal("10"), None, False, False)
    mit = _berechne_rechnung([leistung, abzug], modus, Decimal("10"), None, False, False)
    assert mit.netto_gesamt == ohne.netto_gesamt - Decimal("300.00")
    assert mit.brutto_gesamt == ohne.brutto_gesamt - Decimal("357.00")


def test_berechnung_festbetrag_rabatt_bezieht_sich_nur_auf_leistung():
    from types import SimpleNamespace as P
    from api.rechnungen import _berechne_rechnung
    leistung = P(netto=Decimal("1000"), menge=Decimal("1"), ust_satz=Decimal("19"))
    abzug = P(netto=Decimal("300"), menge=Decimal("-1"), ust_satz=Decimal("19"), abschlag_rechnung_id=1)
    erg = _berechne_rechnung([leistung, abzug], "netto", Decimal("0"), Decimal("119"), False, False)
    # 1190 brutto - 119 Rabatt = 1071, minus 357 Abschlag = 714
    assert erg.brutto_gesamt == Decimal("714.00")
