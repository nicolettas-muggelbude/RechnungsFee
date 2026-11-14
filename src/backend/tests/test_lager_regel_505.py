"""
Issue #505: einheitliche Lagerregel je Dokumenttyp.

Artikel mit Bestand 10, je 2 Stück – alle Wege aus der Issue-Tabelle plus Storno, Vorkasse
(Rechnung → Lieferschein) und Altdokumente (vor dem Stichtag, ohne Bewegungsprotokoll).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import (
    auftrag_erstellen, create_rechnung, finalisiere_rechnung, lieferschein_aus_angebot,
    lieferschein_aus_auftrag, lieferschein_aus_rechnung, rechnung_aus_angebot, rechnung_aus_lieferschein,
    storno_rechnung,
)
from api.schemas import StornoRequest
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Artikel, Kunde, Lagerbewegung, Nummernkreis, Rechnung, Rechnungsposition, Unternehmen

HEUTE = date.today()


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O",
                            lagerführung_aktiv=True, angebote_aktiv=True, auftraege_aktiv=True,
                            lieferschein_aktiv=True, proforma_aktiv=True, abschlagsrechnungen_aktiv=True))
    for typ, fmt in [("rechnung_ausgang", "RE-YY####"), ("lieferschein", "LS-YY####"), ("auftrag", "AU-YY####"),
                     ("angebot", "ANG-YY####"), ("proforma", "PRF-YY####"), ("abschlagsrechnung", "AB-YY####"),
                     ("gutschrift", "GS-YY####"), ("stornorechnung", "STORNO-YY####")]:
        session.add(Nummernkreis(bezeichnung=typ, typ=typ, format=fmt, naechste_nr=1, reset_jaehrlich=True, aktiv=True))
    session.add(Kunde(firmenname="Kunde GmbH"))
    session.add(Artikel(artikelnummer="ART-1", bezeichnung="Ersatzteil", typ="artikel", einheit="Stk.",
                        vk_netto=Decimal("10"), vk_brutto=Decimal("11.90"), steuersatz=Decimal("19"),
                        lager_aktiv=True, bestand_aktuell=Decimal("10"), minusbestand_erlaubt=True))
    session.commit()
    yield session
    session.close()


def _bestand(db) -> Decimal:
    a = db.query(Artikel).one()
    db.refresh(a)
    return a.bestand_aktuell


def _daten(db, dokument_typ, ist_entwurf=False, menge="2") -> RechnungCreate:
    return RechnungCreate(
        typ="ausgang", dokument_typ=dokument_typ, datum=HEUTE, kunde_id=db.query(Kunde).one().id,
        ist_entwurf=ist_entwurf,
        positionen=[RechnungspositionCreate(beschreibung="Ersatzteil", menge=Decimal(menge), einheit="Stk.",
                                            netto=Decimal("10.00"), ust_satz=Decimal("19"),
                                            artikel_id=db.query(Artikel).one().id)],
    )


def _final(db, dok):
    obj = db.get(Rechnung, dok.id)
    if obj.ist_entwurf:
        finalisiere_rechnung(obj.id, db)
    return db.get(Rechnung, dok.id)


# ── Tabelle aus dem Issue ─────────────────────────────────────────────────────

def test_rechnung_direkt(db):
    create_rechnung(_daten(db, "Rechnung"), db)
    assert _bestand(db) == 8


@pytest.mark.parametrize("typ", ["Angebot", "Proforma", "Abschlagsrechnung"])
def test_kein_abgang_direkt_final(db, typ):
    create_rechnung(_daten(db, typ), db)
    assert _bestand(db) == 10


@pytest.mark.parametrize("typ", ["Angebot", "Proforma", "Abschlagsrechnung"])
def test_kein_abgang_entwurf_finalisiert(db, typ):
    _final(db, create_rechnung(_daten(db, typ, ist_entwurf=True), db))
    assert _bestand(db) == 10


def test_auftrag(db):
    auftrag_erstellen(_daten(db, "Auftrag"), db)
    assert _bestand(db) == 10


def test_lieferschein_direkt_dann_rechnung(db):
    ls = _final(db, create_rechnung(_daten(db, "Lieferschein", ist_entwurf=True), db))
    assert _bestand(db) == 8
    _final(db, rechnung_aus_lieferschein(ls.id, db))
    assert _bestand(db) == 8


def test_angebot_dann_rechnung(db):
    angebot = create_rechnung(_daten(db, "Angebot"), db)
    _final(db, rechnung_aus_angebot(angebot.id, db))
    assert _bestand(db) == 8


@pytest.mark.parametrize("quelle", ["angebot", "auftrag"])
def test_ueber_lieferschein_zur_rechnung(db, quelle):
    if quelle == "angebot":
        ls = lieferschein_aus_angebot(create_rechnung(_daten(db, "Angebot"), db).id, db)
    else:
        ls = lieferschein_aus_auftrag(auftrag_erstellen(_daten(db, "Auftrag"), db).id, db)
    _final(db, ls)
    assert _bestand(db) == 8
    _final(db, rechnung_aus_lieferschein(ls.id, db))
    assert _bestand(db) == 8


# ── weitere Wege ──────────────────────────────────────────────────────────────

def test_vorkasse_rechnung_dann_lieferschein(db):
    r = create_rechnung(_daten(db, "Rechnung"), db)
    assert _bestand(db) == 8
    lieferschein_aus_rechnung(r.id, db)
    assert _bestand(db) == 8


def test_lieferschein_entwurf_in_rechnung_dann_lieferschein_finalisiert(db):
    """Reihenfolge umgekehrt: Rechnung wird vor dem Lieferschein final – trotzdem nur einmal."""
    ls = create_rechnung(_daten(db, "Lieferschein", ist_entwurf=True), db)
    _final(db, rechnung_aus_lieferschein(ls.id, db))
    assert _bestand(db) == 8
    finalisiere_rechnung(ls.id, db)
    assert _bestand(db) == 8


def test_rechnung_mit_mehr_als_lieferschein_bucht_differenz(db):
    ls = _final(db, create_rechnung(_daten(db, "Lieferschein", ist_entwurf=True, menge="2"), db))
    r = rechnung_aus_lieferschein(ls.id, db)
    pos = db.query(Rechnungsposition).filter(Rechnungsposition.rechnung_id == r.id).one()
    pos.menge = Decimal("3")  # eine Zusatzmenge erst auf der Rechnung
    db.commit()
    _final(db, r)
    assert _bestand(db) == 7


def test_gutschrift_bucht_zugang(db):
    create_rechnung(_daten(db, "Gutschrift", menge="-1"), db)
    assert _bestand(db) == 11


# ── Storno ────────────────────────────────────────────────────────────────────

def test_storno_rechnung_bucht_zurueck(db):
    r = create_rechnung(_daten(db, "Rechnung"), db)
    storno_rechnung(r.id, StornoRequest(grund="Test"), db)
    assert _bestand(db) == 10
    arten = [b.art for b in db.query(Lagerbewegung).order_by(Lagerbewegung.id).all()]
    assert arten == ["abgang", "storno"]


def test_storno_rechnung_aus_lieferschein_laesst_ware_beim_kunden(db):
    """Die Rechnung selbst hat nichts abgebucht (das war der Lieferschein) – also nichts zurück."""
    ls = _final(db, create_rechnung(_daten(db, "Lieferschein", ist_entwurf=True), db))
    r = _final(db, rechnung_aus_lieferschein(ls.id, db))
    storno_rechnung(r.id, StornoRequest(grund="Falsche Adresse"), db)
    assert _bestand(db) == 8
    # neue Rechnung zum selben Lieferschein bucht ebenfalls nicht erneut ab
    _final(db, rechnung_aus_lieferschein(ls.id, db))
    assert _bestand(db) == 8


def test_storno_angebot_ohne_bewegung(db):
    angebot = create_rechnung(_daten(db, "Abschlagsrechnung"), db)
    storno_rechnung(angebot.id, StornoRequest(grund="Test"), db)
    assert _bestand(db) == 10


# ── Altdokumente (Stichtag) ───────────────────────────────────────────────────

def _altdokument(db, typ, **felder):
    """Finalisiertes Dokument wie vor #505: kein lager_erfasst, keine Bewegungen."""
    dok = create_rechnung(_daten(db, typ, ist_entwurf=True), db)
    obj = db.get(Rechnung, dok.id)
    obj.ist_entwurf = False
    for k, v in felder.items():
        setattr(obj, k, v)
    db.commit()
    return obj


def test_alt_rechnung_storno_wie_bisher(db):
    alt = _altdokument(db, "Rechnung")
    a = db.query(Artikel).one()
    a.bestand_aktuell = Decimal("8")  # damals abgebucht
    db.commit()
    storno_rechnung(alt.id, StornoRequest(grund="Test"), db)
    assert _bestand(db) == 10


def test_lieferschein_zu_alt_rechnung_bucht_nicht_erneut(db):
    alt = _altdokument(db, "Rechnung")
    a = db.query(Artikel).one()
    a.bestand_aktuell = Decimal("8")
    db.commit()
    lieferschein_aus_rechnung(alt.id, db)
    assert _bestand(db) == 8


def test_alt_lieferschein_gilt_als_nicht_abgebucht(db):
    alt_ls = _altdokument(db, "Lieferschein")
    _final(db, rechnung_aus_lieferschein(alt_ls.id, db))
    assert _bestand(db) == 8
