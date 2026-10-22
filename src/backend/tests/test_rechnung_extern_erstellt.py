"""
Tests für extern erstellte Ausgangsrechnungen (Datenübernahme, manuelle Erfassung).

Altrechnungen, die außerhalb von RechnungsFee geschrieben und verschickt wurden (z. B. beim
Umstieg mit Teilzahlungen/Berichtigungen, die der CSV-Import nicht abbildet), bekommen
import_quelle='extern' und damit dieselbe Sperre wie CSV-importierte Rechnungen: kein eigenes
PDF/ZUGFeRD, kein Versand, keine Mahnung. Die Sperre hängt allein an der Kennzeichnung,
nicht an einem angehängten Beleg.
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_rechnung, markiere_ausgegeben, rechnung_als_pdf, rechnung_als_zugferd
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Kunde, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        ist_kleinunternehmer=False, datenmigration_aktiv=True,
    ))
    session.add(Kunde(firmenname="Beispiel Kunde", kundennummer="K-00010"))
    session.commit()
    yield session
    session.close()


def _daten(db, **extra) -> RechnungCreate:
    kunde = db.query(Kunde).first()
    werte = dict(
        typ="ausgang",
        extern_erstellt=True,
        rechnungsnummer="ALT-2026-004",
        datum=date(2026, 3, 10),
        kunde_id=kunde.id,
        ist_entwurf=False,
        positionen=[RechnungspositionCreate(beschreibung="Leistung", netto=Decimal("1000"), ust_satz=Decimal("19"))],
    )
    werte.update(extra)
    return RechnungCreate(**werte)


def test_extern_erstellt_setzt_import_quelle_und_behaelt_originalnummer(db):
    antwort = create_rechnung(_daten(db), db=db)
    rechnung = db.query(Rechnung).filter(Rechnung.id == antwort.id).one()
    assert rechnung.import_quelle == "extern"
    assert rechnung.rechnungsnummer == "ALT-2026-004"
    assert rechnung.datum == date(2026, 3, 10)
    assert rechnung.brutto_gesamt == Decimal("1190.00")


def test_ohne_option_bleibt_rechnung_normal(db):
    antwort = create_rechnung(_daten(db, extern_erstellt=False, rechnungsnummer="RE-260001"), db=db)
    assert db.query(Rechnung).filter(Rechnung.id == antwort.id).one().import_quelle is None


def test_extern_erstellt_sperrt_pdf_zugferd_ausgabe_ohne_angehaengten_beleg(db):
    antwort = create_rechnung(_daten(db), db=db)
    rechnung = db.query(Rechnung).filter(Rechnung.id == antwort.id).one()
    assert rechnung.beleg_id is None  # Sperre wirkt unabhängig von einem Anhang
    for aufruf in (
        lambda: rechnung_als_pdf(rechnung.id, db=db),
        lambda: rechnung_als_zugferd(rechnung.id, db=db),
        lambda: markiere_ausgegeben(rechnung.id, db=db),
    ):
        with pytest.raises(HTTPException) as exc:
            aufruf()
        assert exc.value.status_code == 409


def test_extern_erstellt_sperrt_mailversand_und_mahnung(db):
    from api.mail import _pdf_bytes_fuer
    from api.mahnwesen import _berechne_mahnung

    antwort = create_rechnung(_daten(db), db=db)
    with pytest.raises(HTTPException) as exc:
        _pdf_bytes_fuer(antwort.id, db)
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        _berechne_mahnung(db, [antwort.id], None, SimpleNamespace())
    assert exc.value.status_code == 409


@pytest.mark.parametrize("extra", [
    {"typ": "eingang", "kunde_id": None, "partner_freitext": "Lieferant"},
    {"dokument_typ": "Angebot"},
])
def test_extern_erstellt_nur_fuer_ausgangsrechnungen(db, extra):
    with pytest.raises(HTTPException) as exc:
        create_rechnung(_daten(db, **extra), db=db)
    assert exc.value.status_code == 422
    assert db.query(Rechnung).count() == 0


def test_kennzeichnung_nachtraeglich_setzen_und_entfernen(db):
    from api.rechnungen import ExternErstelltRequest, setze_extern_erstellt

    antwort = create_rechnung(_daten(db, extern_erstellt=False), db=db)
    assert setze_extern_erstellt(antwort.id, ExternErstelltRequest(extern_erstellt=True), db=db).import_quelle == "extern"
    with pytest.raises(HTTPException):
        rechnung_als_pdf(antwort.id, db=db)
    assert setze_extern_erstellt(antwort.id, ExternErstelltRequest(extern_erstellt=False), db=db).import_quelle is None


@pytest.mark.parametrize("feld,wert", [
    ("ausgegeben", True),
    ("original_pdf_pfad", "rechnungen/original.pdf"),
    ("storniert", True),
])
def test_kennzeichnung_nach_ausgabe_oder_storno_gesperrt(db, feld, wert):
    from api.rechnungen import ExternErstelltRequest, setze_extern_erstellt

    antwort = create_rechnung(_daten(db, extern_erstellt=False), db=db)
    rechnung = db.query(Rechnung).filter(Rechnung.id == antwort.id).one()
    setattr(rechnung, feld, wert)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        setze_extern_erstellt(rechnung.id, ExternErstelltRequest(extern_erstellt=True), db=db)
    assert exc.value.status_code == 409
    assert db.query(Rechnung).filter(Rechnung.id == antwort.id).one().import_quelle is None


def test_csv_import_kennzeichnung_bleibt_unveraenderlich(db):
    from api.rechnungen import ExternErstelltRequest, setze_extern_erstellt

    antwort = create_rechnung(_daten(db, extern_erstellt=False), db=db)
    rechnung = db.query(Rechnung).filter(Rechnung.id == antwort.id).one()
    rechnung.import_quelle = "papierkram"
    db.commit()
    with pytest.raises(HTTPException) as exc:
        setze_extern_erstellt(rechnung.id, ExternErstelltRequest(extern_erstellt=False), db=db)
    assert exc.value.status_code == 409


def test_extern_erstellt_nur_mit_aktiver_datenuebernahme(db):
    db.query(Unternehmen).first().datenmigration_aktiv = False
    db.commit()
    with pytest.raises(HTTPException) as exc:
        create_rechnung(_daten(db), db=db)
    assert exc.value.status_code == 422
    assert "Datenübernahme" in exc.value.detail
    assert db.query(Rechnung).count() == 0


# ---------------------------------------------------------------------------
# Issue #464: Steuerfall der letzten Kundenrechnung wird übernommen
# ---------------------------------------------------------------------------

def test_letzter_steuerfall_des_kunden(db):
    from api.rechnungen import letzter_steuerfall
    kunde = db.query(Kunde).first()
    assert letzter_steuerfall(kunde.id, db=db).ist_reverse_charge is False  # noch keine Rechnung
    create_rechnung(_daten(db, extern_erstellt=False, rechnungsnummer="RE-1", datum=date(2026, 3, 1),
                           ist_reverse_charge=True), db=db)
    create_rechnung(_daten(db, extern_erstellt=False, rechnungsnummer="AN-1", datum=date(2026, 4, 1),
                           dokument_typ="Angebot"), db=db)  # Angebote zählen nicht
    ergebnis = letzter_steuerfall(kunde.id, db=db)
    assert ergebnis.ist_reverse_charge is True
    assert ergebnis.ist_eu_lieferung is False
    create_rechnung(_daten(db, extern_erstellt=False, rechnungsnummer="RE-2", datum=date(2026, 5, 1)), db=db)
    assert letzter_steuerfall(kunde.id, db=db).ist_reverse_charge is False  # neueste Rechnung zählt
