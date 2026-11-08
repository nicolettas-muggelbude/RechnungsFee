"""
Issue #495: Lieferscheine aus Angebot oder Auftrag entstehen als Entwurf, damit vor dem
Finalisieren noch die Lieferadresse (Standort eines Filialkunden) gewählt werden kann.

Lager: Diese Lieferscheine wurden bisher sofort final und ohne Lagerabgang angelegt, der Abgang
läuft über die Rechnung. Das muss so bleiben - finalisiert man den Entwurf, darf er nicht
zusätzlich abbuchen. Direkt angelegte Lieferscheine behalten ihr bisheriges Verhalten.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    auftrag_erstellen, create_rechnung, delete_rechnung, finalisiere_rechnung, lieferschein_aus_angebot,
    lieferschein_aus_auftrag, rechnung_aus_lieferschein, update_rechnung,
)
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate, RechnungUpdate
from database.connection import Base
from database.models import Artikel, Kunde, KundeLieferadresse, Nummernkreis, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O",
                            lagerführung_aktiv=True, angebote_aktiv=True, auftraege_aktiv=True,
                            lieferschein_aktiv=True))
    for typ, fmt in [("rechnung_ausgang", "RE-YY####"), ("lieferschein", "LS-YY####"),
                     ("auftrag", "AU-YY####"), ("angebot", "ANG-YY####")]:
        session.add(Nummernkreis(bezeichnung=typ, typ=typ, format=fmt, naechste_nr=1, reset_jaehrlich=True, aktiv=True))
    betreiber = Kunde(firmenname="Betreiber GmbH")
    fremd = Kunde(firmenname="Andere AG")
    session.add_all([betreiber, fremd])
    session.flush()
    session.add_all([
        KundeLieferadresse(kunde_id=betreiber.id, bezeichnung="Standort 1", strasse="A-Str.", plz="10000", ort="A", ist_standard=True),
        KundeLieferadresse(kunde_id=betreiber.id, bezeichnung="Standort 47", strasse="B-Str.", plz="20000", ort="B"),
        KundeLieferadresse(kunde_id=fremd.id, bezeichnung="Fremd", strasse="C-Str.", plz="30000", ort="C"),
        Artikel(artikelnummer="ART-1", bezeichnung="Ersatzteil", typ="artikel", einheit="Stk.",
                vk_netto=Decimal("10"), vk_brutto=Decimal("11.90"), steuersatz=Decimal("19"),
                lager_aktiv=True, bestand_aktuell=Decimal("10"), minusbestand_erlaubt=True),
    ])
    session.commit()
    yield session
    session.close()


def _kunde(db, name="Betreiber GmbH") -> Kunde:
    return db.query(Kunde).filter(Kunde.firmenname == name).one()


def _adresse(db, bezeichnung) -> KundeLieferadresse:
    return db.query(KundeLieferadresse).filter(KundeLieferadresse.bezeichnung == bezeichnung).one()


def _artikel(db) -> Artikel:
    a = db.query(Artikel).one()
    db.refresh(a)
    return a


def _daten(db, dokument_typ: str, ist_entwurf: bool = False) -> RechnungCreate:
    return RechnungCreate(
        typ="ausgang", dokument_typ=dokument_typ, datum=date(2026, 11, 7), kunde_id=_kunde(db).id,
        ist_entwurf=ist_entwurf,
        positionen=[RechnungspositionCreate(beschreibung="Ersatzteil", menge=Decimal("2"), einheit="Stk.",
                                            netto=Decimal("10.00"), ust_satz=Decimal("19"), artikel_id=_artikel(db).id)],
    )


def _angebot(db):
    return create_rechnung(_daten(db, "Angebot"), db)


def _auftrag(db):
    return auftrag_erstellen(_daten(db, "Auftrag"), db)


@pytest.mark.parametrize("quelle", ["angebot", "auftrag"])
def test_lieferschein_entsteht_als_entwurf_mit_standardadresse(db, quelle):
    if quelle == "angebot":
        ls = lieferschein_aus_angebot(_angebot(db).id, db)
    else:
        ls = lieferschein_aus_auftrag(_auftrag(db).id, db)
    obj = db.query(Rechnung).filter(Rechnung.id == ls.id).one()
    assert obj.ist_entwurf is True
    assert obj.lieferadresse_id == _adresse(db, "Standort 1").id
    assert obj.absender_snapshot is None  # wird erst beim Finalisieren eingefroren


def test_lieferadresse_im_entwurf_aendern_und_entfernen(db):
    ls = lieferschein_aus_angebot(_angebot(db).id, db)
    update_rechnung(ls.id, RechnungUpdate(lieferadresse_id=_adresse(db, "Standort 47").id), db)
    assert db.query(Rechnung).filter(Rechnung.id == ls.id).one().lieferadresse_id == _adresse(db, "Standort 47").id

    update_rechnung(ls.id, RechnungUpdate(lieferadresse_id=None), db)
    assert db.query(Rechnung).filter(Rechnung.id == ls.id).one().lieferadresse_id is None


def test_lieferadresse_eines_anderen_kunden_abgewiesen(db):
    ls = lieferschein_aus_angebot(_angebot(db).id, db)
    with pytest.raises(HTTPException) as exc:
        update_rechnung(ls.id, RechnungUpdate(lieferadresse_id=_adresse(db, "Fremd").id), db)
    assert exc.value.status_code == 422


def test_update_ohne_lieferadresse_laesst_sie_stehen(db):
    """Teil-Updates ohne das Feld (z. B. nur Notizen) dürfen die Adresse nicht entfernen."""
    ls = lieferschein_aus_angebot(_angebot(db).id, db)
    update_rechnung(ls.id, RechnungUpdate(notizen="Tor 3"), db)
    assert db.query(Rechnung).filter(Rechnung.id == ls.id).one().lieferadresse_id == _adresse(db, "Standort 1").id


@pytest.mark.parametrize("quelle", ["angebot", "auftrag"])
def test_kein_doppelter_lagerabgang(db, quelle):
    # Bestand nach dem Anlegen der Quelle als Basis - ob schon das Angebot selbst abbucht, ist
    # eine eigene Frage (Lager-Issue), hier geht es nur um Lieferschein und Rechnung
    quelle_doc = _angebot(db) if quelle == "angebot" else _auftrag(db)
    basis = _artikel(db).bestand_aktuell
    if quelle == "angebot":
        ls = lieferschein_aus_angebot(quelle_doc.id, db)
    else:
        ls = lieferschein_aus_auftrag(quelle_doc.id, db)
    assert _artikel(db).bestand_aktuell == basis

    finalisiere_rechnung(ls.id, db)
    assert _artikel(db).bestand_aktuell == basis  # wie bisher: kein Abgang am Lieferschein
    assert db.query(Rechnung).filter(Rechnung.id == ls.id).one().absender_snapshot

    r = rechnung_aus_lieferschein(ls.id, db)
    finalisiere_rechnung(r.id, db)
    assert _artikel(db).bestand_aktuell == basis - 2  # genau einmal, über die Rechnung


def test_direkter_lieferschein_entwurf_bucht_wie_bisher(db):
    ls = create_rechnung(_daten(db, "Lieferschein", ist_entwurf=True), db)
    finalisiere_rechnung(ls.id, db)
    assert _artikel(db).bestand_aktuell == Decimal("8")


def test_entwurf_loeschen_gibt_angebot_wieder_frei(db):
    angebot = _angebot(db)
    ls = lieferschein_aus_angebot(angebot.id, db)
    delete_rechnung(ls.id, db)
    assert db.query(Rechnung).filter(Rechnung.id == angebot.id).one().lieferschein_zu_angebot_id is None
    # Angebot kann erneut umgewandelt werden
    assert lieferschein_aus_angebot(angebot.id, db).ist_entwurf is True


def test_entwurf_loeschen_setzt_auftrag_zurueck(db):
    auftrag = _auftrag(db)
    ls = lieferschein_aus_auftrag(auftrag.id, db)
    assert db.query(Rechnung).filter(Rechnung.id == auftrag.id).one().auftrag_status == "in_bearbeitung"
    delete_rechnung(ls.id, db)
    au = db.query(Rechnung).filter(Rechnung.id == auftrag.id).one()
    assert au.lieferschein_zu_auftrag_id is None
    assert au.auftrag_status == "offen"
