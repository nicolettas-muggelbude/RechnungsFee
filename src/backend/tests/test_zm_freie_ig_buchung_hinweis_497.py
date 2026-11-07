"""
Issue #497: Hinweis beim Buchen einer freien ig. Lieferung ohne Rechnungsbezug.

Eine Einnahme auf 8125/4125 ohne rechnung_id zählt weiter nach Buchungsdatum (keine Sperre -
manche schreiben ihre Rechnungen in einem anderen Programm). Ab zm_meldezeitraum.CUTOVER_DATUM
meldet eine Rechnung in RechnungsFee aber selbst, die Zahlung dazu als freie Buchung stünde
doppelt in KZ 41 und der ZM. Deshalb ab dem Stichtag ein Hinweis in der Antwort jedes Wegs, der
eine solche Buchung anlegt: Journal (einzeln, Korrektur, Split), Bank-Import mit Kategorie
(manuell und auto-buchen), Buchungsvorlage. Mit Rechnungsbezug, vor dem Stichtag, auf anderen
Konten und bei Ausgaben kein Hinweis.

Läuft gegen den echten Stichtag (kein Patch): Journal-, Bank- und Vorlagenbuchungen dürfen in der
Zukunft liegen.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import BuchungsRequest, auto_buchen, buche_transaktion
from api.buchungsvorlagen import BuchenRequest, buche_vorlage
from api.journal import create_eintrag, create_split_buchung, update_eintrag
from api.rechnungen import create_rechnung, finalisiere_rechnung
from api.schemas import JournalEintragCreate, SplitBuchungCreate, SplitPosition
from api.schemas_rechnungen import RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import (
    BankImport, BankTemplate, BankTransaktion, Buchungsvorlage, Journaleintrag, Kategorie, Konto, Kunde,
    Rechnung, Unternehmen,
)
from utils import zm_meldezeitraum

VORHER = zm_meldezeitraum.CUTOVER_DATUM - timedelta(days=1)
AB = zm_meldezeitraum.CUTOVER_DATUM
HINWEIS = zm_meldezeitraum.HINWEIS_FREIE_IG_BUCHUNG


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345",
                            ort="Testort", ist_kleinunternehmer=False))
    session.add(Kunde(firmenname="EU-Kunde SARL", land="FR", ust_idnr="FR40303265045"))
    session.add(Kategorie(name="Innergemeinschaftliche Lieferungen", kontenart="Erlös",
                          konto_skr03="8125", konto_skr04="4125", vorsteuer_prozent=0, ust_satz_standard=0))
    session.add(Kategorie(name="Nicht steuerbare Auslandsumsätze (Drittland)", kontenart="Erlös",
                          konto_skr03="8338", konto_skr04="4338", vorsteuer_prozent=0, ust_satz_standard=0))
    session.commit()
    yield session
    session.close()


def _kat(db, skr03) -> int:
    return db.query(Kategorie.id).filter(Kategorie.konto_skr03 == skr03).scalar()


def _journal(db, datum, skr03="8125", art="Einnahme"):
    return create_eintrag(JournalEintragCreate(
        datum=datum, beschreibung="Lieferung FR", kategorie_id=_kat(db, skr03),
        art=art, brutto_betrag=Decimal("1000.00"), zahlungsart="Bank",
    ), db)


# --- Journal: einzeln -------------------------------------------------------------------------

def test_journal_ab_stichtag_mit_hinweis(db):
    assert _journal(db, AB).hinweis == HINWEIS


def test_journal_vor_stichtag_ohne_hinweis(db):
    assert _journal(db, VORHER).hinweis is None


def test_journal_anderes_konto_ohne_hinweis(db):
    assert _journal(db, AB, skr03="8338").hinweis is None


def test_journal_ausgabe_ohne_hinweis(db):
    assert _journal(db, AB, art="Ausgabe").hinweis is None


def test_journal_buchung_bleibt_erlaubt_und_unveraendert(db):
    resp = _journal(db, AB)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == resp.id).one()
    assert (e.datum, e.konto_skr03, e.netto_betrag, e.rechnung_id) == (AB, "8125", Decimal("1000.00"), None)
    assert e.steuerbefreiung_grund == "§4 Nr. 1b UStG"


def test_skr04_konto_allein_reicht():
    e = Journaleintrag(datum=AB, art="Einnahme", konto_skr03=None, konto_skr04="4125", rechnung_id=None)
    assert zm_meldezeitraum.hinweis_freie_ig_buchung(e) == HINWEIS


def test_mit_rechnungsbezug_ohne_hinweis():
    e = Journaleintrag(datum=AB, art="Einnahme", konto_skr03="8125", konto_skr04="4125", rechnung_id=7)
    assert zm_meldezeitraum.hinweis_freie_ig_buchung(e) is None


# --- Journal: Korrektur -----------------------------------------------------------------------

def _korrektur(db, alt_datum, neu_datum, neu_skr03="8125", nach_frist=False):
    alt = _journal(db, alt_datum, skr03="8338")
    if nach_frist:
        e = db.query(Journaleintrag).filter(Journaleintrag.id == alt.id).one()
        e.erstellt_am = datetime.utcnow() - timedelta(hours=1)
        db.commit()
    return update_eintrag(alt.id, JournalEintragCreate(
        datum=neu_datum, beschreibung="Lieferung FR", kategorie_id=_kat(db, neu_skr03),
        art="Einnahme", brutto_betrag=Decimal("1000.00"), zahlungsart="Bank",
    ), db)


@pytest.mark.parametrize("nach_frist", [False, True])
def test_korrektur_auf_ig_lieferung_ab_stichtag_mit_hinweis(db, nach_frist):
    resp = _korrektur(db, AB, AB, nach_frist=nach_frist)
    assert resp.hinweis == HINWEIS
    if nach_frist:
        assert db.query(Journaleintrag).count() == 3  # Original, Storno, Neubuchung


@pytest.mark.parametrize("nach_frist", [False, True])
def test_korrektur_vor_stichtag_ohne_hinweis(db, nach_frist):
    assert _korrektur(db, VORHER, VORHER, nach_frist=nach_frist).hinweis is None


@pytest.mark.parametrize("nach_frist", [False, True])
def test_korrektur_auf_anderes_konto_ohne_hinweis(db, nach_frist):
    assert _korrektur(db, AB, AB, neu_skr03="8338", nach_frist=nach_frist).hinweis is None


# --- Journal: Split ---------------------------------------------------------------------------

def _split(db, datum):
    return create_split_buchung(SplitBuchungCreate(
        datum=datum, art="Einnahme", zahlungsart="Bank", positionen=[
            SplitPosition(beschreibung="Lieferung FR", kategorie_id=_kat(db, "8125"), brutto_betrag=Decimal("600.00")),
            SplitPosition(beschreibung="Leistung CH", kategorie_id=_kat(db, "8338"), brutto_betrag=Decimal("400.00")),
        ],
    ), db)


def test_split_ab_stichtag_hinweis_nur_an_ig_position(db):
    assert [p.hinweis for p in _split(db, AB)] == [HINWEIS, None]


def test_split_vor_stichtag_ohne_hinweis(db):
    assert [p.hinweis for p in _split(db, VORHER)] == [None, None]


# --- Bank-Import ------------------------------------------------------------------------------

def _tx(db, datum, skr03="8125", betrag="1000.00") -> BankTransaktion:
    k = Konto(name="Testkonto", anbieter="Testbank")
    db.add(k)
    db.flush()
    tmpl = BankTemplate(id=f"t-{k.id}", name="Test", bank="Testbank", format="Standard", column_mapping="{}")
    db.add(tmpl)
    db.flush()
    imp = BankImport(konto_id=k.id, template_id=tmpl.id, dateiname="test.csv")
    db.add(imp)
    db.flush()
    tx = BankTransaktion(konto_id=k.id, import_id=imp.id, datum=datum, betrag=Decimal(betrag),
                         partner_name="Client SARL", verwendungszweck="Lieferung",
                         kategorie_id=_kat(db, skr03) if skr03 else None)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@pytest.mark.parametrize("datum, skr03, betrag, erwartet", [
    (AB, "8125", "1000.00", HINWEIS),
    (VORHER, "8125", "1000.00", None),
    (AB, "8338", "1000.00", None),
    (AB, "8125", "-1000.00", None),   # Ausgabe (Rückzahlung)
])
def test_bank_manuell_mit_kategorie(db, datum, skr03, betrag, erwartet):
    tx = _tx(db, datum, skr03, betrag)
    resp = buche_transaktion(tx.id, BuchungsRequest(), db)
    assert resp.journal_id is not None
    assert resp.hinweis == erwartet


@pytest.mark.parametrize("datum, skr03, erwartet", [
    (AB, "8125", HINWEIS),
    (VORHER, "8125", None),
    (AB, "8338", None),
])
def test_bank_auto_buchen_mit_kategorie(db, datum, skr03, erwartet):
    tx = _tx(db, datum, skr03)
    ergebnis = auto_buchen(tx.konto_id, import_id=tx.import_id, db=db)
    assert ergebnis.gebucht == 1
    assert ergebnis.hinweis == erwartet


def test_bank_auto_buchen_rollback_verwirft_hinweis(db, monkeypatch):
    # Faellt eine spaetere Transaktion, verwirft db.rollback() auch die zuvor gebuchte
    # ig. Lieferung - der Hinweis dazu darf dann nicht in der Antwort stehen.
    import api.bank_import as bank_import
    tx1 = _tx(db, AB)
    tx2 = BankTransaktion(konto_id=tx1.konto_id, import_id=tx1.import_id, datum=AB + timedelta(days=1),
                          betrag=Decimal("500.00"), partner_name="Client SARL", verwendungszweck="Lieferung",
                          kategorie_id=_kat(db, "8338"))
    db.add(tx2)
    db.commit()
    original = bank_import._buche_pfad_b

    def pfad_b(db_, tx):
        if tx.id == tx2.id:
            raise RuntimeError("Testfehler")
        return original(db_, tx)

    monkeypatch.setattr(bank_import, "_buche_pfad_b", pfad_b)
    ergebnis = auto_buchen(tx1.konto_id, import_id=tx1.import_id, db=db)
    assert ergebnis.fehler == 1
    assert db.query(Journaleintrag).filter(Journaleintrag.konto_skr03 == "8125").count() == 0
    assert ergebnis.hinweis is None


def _ig_rechnung(db) -> int:
    kunde = db.query(Kunde).first()
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date.today(), kunde_id=kunde.id, ist_eu_lieferung=True,
        positionen=[RechnungspositionCreate(beschreibung="Lieferung", netto=Decimal("1000.00"),
                                            ust_satz=Decimal("0"), kategorie_id=_kat(db, "8125"))],
    ), db)
    finalisiere_rechnung(resp.id, db)
    return resp.id


def test_bank_manuell_an_rechnung_ohne_hinweis(db):
    rid = _ig_rechnung(db)
    tx = _tx(db, AB)
    resp = buche_transaktion(tx.id, BuchungsRequest(rechnung_id=rid), db)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == resp.journal_id).one()
    assert e.rechnung_id == rid and e.konto_skr03 == "8125"
    assert resp.hinweis is None


def test_bank_auto_buchen_an_rechnung_ohne_hinweis(db):
    # Pfad A: eindeutiger Treffer (Betrag, Nummer, Name) geht vor die Kategorie der Transaktion.
    rid = _ig_rechnung(db)
    tx = _tx(db, AB)
    tx.verwendungszweck = db.get(Rechnung, rid).rechnungsnummer
    tx.partner_name = "EU-Kunde SARL"
    db.commit()
    ergebnis = auto_buchen(tx.konto_id, import_id=tx.import_id, db=db)
    db.refresh(tx)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == tx.journal_id).one()
    assert ergebnis.gebucht == 1 and e.rechnung_id == rid and e.konto_skr03 == "8125"
    assert ergebnis.hinweis is None


# --- Buchungsvorlage --------------------------------------------------------------------------

@pytest.mark.parametrize("datum, skr03, art, erwartet", [
    (AB, "8125", "Einnahme", HINWEIS),
    (VORHER, "8125", "Einnahme", None),
    (AB, "8338", "Einnahme", None),
    (AB, "8125", "Ausgabe", None),
])
def test_buchungsvorlage(db, datum, skr03, art, erwartet):
    v = Buchungsvorlage(
        bezeichnung="Lieferung FR", betrag=Decimal("1000.00"), ist_brutto=True, ust_satz=Decimal("0"),
        intervall="monatlich", naechstes_datum=datum, modus="direkt", art=art, kategorie_id=_kat(db, skr03),
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    assert buche_vorlage(v.id, data=BuchenRequest(), db=db).hinweis == erwartet
