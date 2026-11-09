"""
Issue #495 (Gerti): Angebot, Auftrag, Proforma und Lieferschein gehen an einen Standort des
Kunden (z. B. ein Einkaufszentrum), die Rechnung an die Zentrale (Betreiber). Bisher stand im
Adressfeld immer der Kunde – Gerti musste das Angebot an einen frei eingetippten Empfänger
schreiben und den Kunden nachträglich austauschen.

Jetzt: rechnungen.empfaenger_adresse_id – eine Lieferadresse des Kunden als Empfänger im
Adressfeld. Wandert beim Umwandeln mit; am Lieferschein ist der Standort zugleich Lieferort.
Die Rechnung bleibt beim Kunden.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from fastapi import HTTPException
from pypdf import PdfReader
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from api.kunden import delete_lieferadresse
from api.rechnungen import (
    auftrag_aus_angebot, auftrag_erstellen, create_rechnung, lieferschein_aus_angebot,
    lieferschein_aus_auftrag, proforma_aus_angebot, rechnung_aus_lieferschein, update_rechnung,
)
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Kunde, KundeLieferadresse, Nummernkreis, Rechnung, Unternehmen
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1

UNT = {
    "firmenname": "Test GmbH", "vorname": "", "nachname": "", "strasse": "Teststr.", "hausnummer": "1",
    "plz": "12345", "ort": "Testort", "land": "DE", "ust_idnr": "", "steuernummer": "", "iban": "",
    "bic": "", "telefon": "", "email": "", "webseite": "", "ist_kleinunternehmer": False,
}


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _fk(conn, _):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O",
                            angebote_aktiv=True, auftraege_aktiv=True, lieferschein_aktiv=True,
                            proforma_aktiv=True))
    for typ, fmt in [("rechnung_ausgang", "RE-YY####"), ("lieferschein", "LS-YY####"),
                     ("auftrag", "AU-YY####"), ("angebot", "ANG-YY####"), ("proforma", "PRF-YY####")]:
        session.add(Nummernkreis(bezeichnung=typ, typ=typ, format=fmt, naechste_nr=1, reset_jaehrlich=True, aktiv=True))
    betreiber = Kunde(firmenname="FDF Management GmbH", strasse="Alster Weg", hausnummer="1", plz="22529", ort="Hamburg")
    fremd = Kunde(firmenname="Andere AG")
    session.add_all([betreiber, fremd])
    session.flush()
    session.add_all([
        KundeLieferadresse(kunde_id=betreiber.id, bezeichnung="Lager", strasse="A-Str.", plz="10000", ort="A", ist_standard=True),
        KundeLieferadresse(kunde_id=betreiber.id, bezeichnung="Ostwestfalen Center", z_hd="Center Management",
                           strasse="Lipper Str.", hausnummer="100", plz="33609", ort="Bielefeld"),
        KundeLieferadresse(kunde_id=fremd.id, bezeichnung="Fremd", strasse="C-Str.", plz="30000", ort="C"),
    ])
    session.commit()
    yield session
    session.close()


def _kunde(db) -> Kunde:
    return db.query(Kunde).filter(Kunde.firmenname == "FDF Management GmbH").one()


def _adresse(db, bezeichnung) -> KundeLieferadresse:
    return db.query(KundeLieferadresse).filter(KundeLieferadresse.bezeichnung == bezeichnung).one()


def _daten(db, dokument_typ: str, empfaenger: str | None = "Ostwestfalen Center") -> RechnungCreate:
    return RechnungCreate(
        typ="ausgang", dokument_typ=dokument_typ, datum=date(2026, 11, 9), kunde_id=_kunde(db).id,
        ist_entwurf=False, gueltig_bis=date(2026, 12, 9),
        empfaenger_adresse_id=_adresse(db, empfaenger).id if empfaenger else None,
        positionen=[RechnungspositionCreate(beschreibung="Wartung", menge=Decimal("1"), einheit="Stk.",
                                            netto=Decimal("100.00"), ust_satz=Decimal("19"))],
    )


def _obj(db, id_) -> Rechnung:
    db.expire_all()
    return db.query(Rechnung).filter(Rechnung.id == id_).one()


def _pdf_text(r: Rechnung, generate=generate_rechnung_pdf) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(BytesIO(generate(r, UNT))).pages)


# ── Speichern ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("dokument_typ", ["Angebot", "Proforma", "Lieferschein"])
def test_empfaenger_wird_gespeichert(db, dokument_typ):
    r = create_rechnung(_daten(db, dokument_typ), db)
    assert _obj(db, r.id).empfaenger_adresse_id == _adresse(db, "Ostwestfalen Center").id


def test_auftrag_mit_empfaenger(db):
    au = auftrag_erstellen(_daten(db, "Auftrag"), db)
    assert _obj(db, au.id).empfaenger_adresse_id == _adresse(db, "Ostwestfalen Center").id


def test_rechnung_ignoriert_empfaenger(db):
    """Die Rechnung muss an den Leistungsempfänger (Kunde) gehen."""
    r = create_rechnung(_daten(db, "Rechnung"), db)
    assert _obj(db, r.id).empfaenger_adresse_id is None


def test_adresse_eines_anderen_kunden_abgewiesen(db):
    with pytest.raises(HTTPException) as exc:
        create_rechnung(_daten(db, "Angebot", empfaenger="Fremd"), db)
    assert exc.value.status_code == 422


def test_empfaenger_aendern_und_entfernen(db):
    r = create_rechnung(_daten(db, "Angebot", empfaenger=None), db)
    update_rechnung(r.id, RechnungUpdate(empfaenger_adresse_id=_adresse(db, "Ostwestfalen Center").id), db)
    assert _obj(db, r.id).empfaenger_adresse_id == _adresse(db, "Ostwestfalen Center").id

    update_rechnung(r.id, RechnungUpdate(notizen="nur Notiz"), db)  # Teil-Update lässt ihn stehen
    assert _obj(db, r.id).empfaenger_adresse_id == _adresse(db, "Ostwestfalen Center").id

    update_rechnung(r.id, RechnungUpdate(empfaenger_adresse_id=None), db)
    assert _obj(db, r.id).empfaenger_adresse_id is None


def test_kundenwechsel_entfernt_empfaenger(db):
    r = create_rechnung(_daten(db, "Angebot"), db)
    fremd = db.query(Kunde).filter(Kunde.firmenname == "Andere AG").one()
    update_rechnung(r.id, RechnungUpdate(kunde_id=fremd.id), db)
    assert _obj(db, r.id).empfaenger_adresse_id is None


# ── Umwandeln ─────────────────────────────────────────────────────────────────

def test_kette_angebot_auftrag_lieferschein_rechnung(db):
    standort = _adresse(db, "Ostwestfalen Center").id
    ang = create_rechnung(_daten(db, "Angebot"), db)
    au = auftrag_aus_angebot(ang.id, db)
    assert _obj(db, au.id).empfaenger_adresse_id == standort

    ls = lieferschein_aus_auftrag(au.id, db)
    ls_obj = _obj(db, ls.id)
    assert ls_obj.empfaenger_adresse_id == standort
    assert ls_obj.lieferadresse_id == standort  # Lieferung geht an den Standort, nicht ans Lager

    re = rechnung_aus_lieferschein(ls.id, db)
    assert _obj(db, re.id).empfaenger_adresse_id is None  # Rechnung an die Zentrale


def test_angebot_zu_proforma_und_lieferschein(db):
    standort = _adresse(db, "Ostwestfalen Center").id
    ang = create_rechnung(_daten(db, "Angebot"), db)
    assert _obj(db, proforma_aus_angebot(ang.id, db).id).empfaenger_adresse_id == standort
    ang2 = create_rechnung(_daten(db, "Angebot"), db)
    assert _obj(db, lieferschein_aus_angebot(ang2.id, db).id).lieferadresse_id == standort


def test_ohne_empfaenger_bleibt_standard_lieferadresse(db):
    ang = create_rechnung(_daten(db, "Angebot", empfaenger=None), db)
    ls = _obj(db, lieferschein_aus_angebot(ang.id, db).id)
    assert ls.empfaenger_adresse_id is None
    assert ls.lieferadresse_id == _adresse(db, "Lager").id


# ── PDF ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("generate", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
def test_pdf_adressfeld_zeigt_standort(db, generate):
    r = _obj(db, create_rechnung(_daten(db, "Angebot"), db).id)
    text = _pdf_text(r, generate)
    assert "Ostwestfalen Center" in text
    assert "z.Hd. Center Management" in text
    assert "Lipper Str. 100" in text and "33609 Bielefeld" in text
    assert "Alster Weg" not in text  # Anschrift der Zentrale nicht im Adressfeld


def test_pdf_ohne_empfaenger_unveraendert(db):
    r = _obj(db, create_rechnung(_daten(db, "Angebot", empfaenger=None), db).id)
    text = _pdf_text(r)
    assert "FDF Management GmbH" in text and "Alster Weg 1" in text
    assert "Ostwestfalen" not in text


def test_pdf_rechnung_bleibt_beim_kunden(db):
    r = _obj(db, create_rechnung(_daten(db, "Rechnung"), db).id)
    r.empfaenger_adresse_id = _adresse(db, "Ostwestfalen Center").id  # auch wenn gesetzt
    db.commit()
    text = _pdf_text(_obj(db, r.id))
    assert "Alster Weg 1" in text and "Lipper Str." not in text


# ── Löschen einer genutzten Adresse ───────────────────────────────────────────

def test_genutzte_adresse_nicht_loeschbar(db):
    r = create_rechnung(_daten(db, "Angebot"), db)
    la = _adresse(db, "Ostwestfalen Center")
    with pytest.raises(HTTPException) as exc:
        delete_lieferadresse(_kunde(db).id, la.id, db)
    assert exc.value.status_code == 409
    assert _obj(db, r.id).rechnungsnummer in exc.value.detail


def test_ungenutzte_adresse_loeschbar(db):
    la = _adresse(db, "Ostwestfalen Center")
    delete_lieferadresse(_kunde(db).id, la.id, db)
    assert db.query(KundeLieferadresse).filter(KundeLieferadresse.id == la.id).first() is None
