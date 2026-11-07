"""
Issue #502: Privater Anteil im Bank-Abgleich.

1. Abbuchung größer als die Eingangsrechnung (Mischkonto-Beleg, private Artikel auf dem Bon):
   der Rest kann statt als Lieferantenguthaben als Privatentnahme gebucht werden - mit Datum
   und Bankkonto der Transaktion, damit sie im DATEV-Export erscheint.
2. Ausbuchen eines Lieferantenguthabens mit einer Privat-Kategorie übernimmt Datum und
   Bankkonto der ursprünglichen Zahlung. Das bisherige Ausbuchen (Forderungsausfall auf eine
   Aufwand-Kategorie, Guthaben ohne Bank-Zahlung, Kundenguthaben) bleibt unverändert - dafür
   gab es bislang keine Tests, sie halten das bestehende Verhalten hier ausdrücklich fest.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import BuchungsRequest, buche_transaktion
from api.datev import _gegenkonto, _sachkonto
from api.forderungen import AusbuchenRequest, ForderungCreate, create_forderung, forderung_ausbuchen
from database.connection import Base
from database.models import (
    BankImport, BankTemplate, BankTransaktion, Forderung, Journaleintrag, Kategorie, Konto,
    Rechnung, Rechnungsposition, Unternehmen,
)

HEUTE = date.today()
TX_DATUM = date(2026, 3, 5)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(
        firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        kontenrahmen="SKR03", ist_kleinunternehmer=False,
    ))
    konto = Konto(name="Geschäftskonto", anbieter="Testbank", datev_kontonummer="1210")
    session.add(konto)
    session.flush()
    tmpl = BankTemplate(id="test-tmpl", name="Test", bank="Testbank", format="Standard", column_mapping="{}")
    session.add(tmpl)
    session.flush()
    imp = BankImport(konto_id=konto.id, template_id=tmpl.id, dateiname="test.csv")
    session.add(imp)
    session.add_all([
        Kategorie(name="Bürobedarf", kontenart="Aufwand", konto_skr03="4930", konto_skr04="6815",
                  vorsteuer_prozent=100, ust_satz_standard=19, euer_zeile=60),
        Kategorie(name="Forderungsverluste", kontenart="Aufwand", konto_skr03="2400", konto_skr04="6930",
                  vorsteuer_prozent=0, ust_satz_standard=0, euer_zeile=60),
        Kategorie(name="Privatentnahme", kontenart="Privat", konto_skr03="1800", konto_skr04="2100",
                  vorsteuer_prozent=0, ust_satz_standard=0, euer_zeile=106),
        Kategorie(name="Privateinlage", kontenart="Privat", konto_skr03="1890", konto_skr04="2180",
                  vorsteuer_prozent=0, ust_satz_standard=0, euer_zeile=107),
    ])
    session.commit()
    session.konto_id = konto.id
    session.import_id = imp.id
    yield session
    session.close()


def _kat(db, name: str) -> Kategorie:
    return db.query(Kategorie).filter(Kategorie.name == name).one()


def _tx(db, betrag: str, datum=TX_DATUM) -> BankTransaktion:
    tx = BankTransaktion(
        konto_id=db.konto_id, import_id=db.import_id, datum=datum, betrag=Decimal(betrag),
        partner_name="Telekom", verwendungszweck="Internet",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def _eingangsrechnung(db, brutto: str = "8.99", typ: str = "eingang") -> Rechnung:
    brutto_d = Decimal(brutto)
    netto = (brutto_d / Decimal("1.19")).quantize(Decimal("0.01"))
    kat = _kat(db, "Bürobedarf")
    rechnung = Rechnung(
        typ=typ, rechnungsnummer=f"{'ER' if typ == 'eingang' else 'RE'}-2026-{db.query(Rechnung).count() + 1}",
        datum=date(2026, 3, 1), brutto_gesamt=brutto_d, netto_gesamt=netto, ust_gesamt=brutto_d - netto,
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
        kategorie_id=kat.id if typ == "eingang" else None,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Internet betrieblich 20 %", menge=Decimal("1"),
        einheit="Stk.", netto=netto, ust_satz=Decimal("19"), ust_betrag=brutto_d - netto, brutto=brutto_d,
        kategorie_id=kat.id if typ == "eingang" else None,
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def _privat_eintraege(db) -> list[Journaleintrag]:
    kat_ids = [k.id for k in db.query(Kategorie).filter(Kategorie.kontenart == "Privat")]
    return db.query(Journaleintrag).filter(Journaleintrag.kategorie_id.in_(kat_ids)).all()


# ---------------------------------------------------------------------------
# 1. Bank-Abgleich: Rest als Guthaben (bisher) oder privater Anteil (neu)
# ---------------------------------------------------------------------------

def test_abgleich_ohne_wahl_legt_wie_bisher_lieferantenguthaben_an(db):
    rechnung = _eingangsrechnung(db)
    tx = _tx(db, "-44.93")
    buche_transaktion(tx.id, BuchungsRequest(rechnung_id=rechnung.id), db)

    f = db.query(Forderung).one()
    assert f.typ == "lieferantenguthaben"
    assert f.betrag == Decimal("35.94")
    assert f.status == "offen"
    assert _privat_eintraege(db) == []


def test_abgleich_rest_privat_bucht_privatentnahme_statt_guthaben(db):
    rechnung = _eingangsrechnung(db)
    tx = _tx(db, "-44.93")
    buche_transaktion(tx.id, BuchungsRequest(rechnung_id=rechnung.id, rest_privat=True), db)

    assert db.query(Forderung).count() == 0
    [entnahme] = _privat_eintraege(db)
    assert entnahme.kategorie_id == _kat(db, "Privatentnahme").id
    assert entnahme.brutto_betrag == Decimal("35.94")
    assert entnahme.art == "Ausgabe"
    assert entnahme.datum == TX_DATUM
    assert entnahme.zahlungsart == "Bank"
    assert entnahme.konto_id == db.konto_id
    assert entnahme.ust_betrag == Decimal("0.00")
    assert entnahme.vorsteuer_betrag == Decimal("0.00")
    assert entnahme.rechnung_id is None  # sonst zählte sie als Zahlung auf die Rechnung
    assert entnahme.signatur

    db.refresh(rechnung)
    assert rechnung.zahlungsstatus == "bezahlt"
    assert rechnung.bezahlt_betrag == Decimal("8.99")

    # Zahlung + Entnahme ergeben zusammen genau die Abbuchung
    summe = sum(j.brutto_betrag for j in db.query(Journaleintrag).filter(Journaleintrag.art == "Ausgabe"))
    assert summe == Decimal("44.93")


def test_privatentnahme_erscheint_im_datev_export_gegen_bankkonto(db):
    rechnung = _eingangsrechnung(db, "16.20")
    tx = _tx(db, "-20.48")
    buche_transaktion(tx.id, BuchungsRequest(rechnung_id=rechnung.id, rest_privat=True), db)

    [entnahme] = _privat_eintraege(db)
    unt = db.query(Unternehmen).one()
    assert entnahme.brutto_betrag == Decimal("4.28")
    assert _gegenkonto(entnahme, unt, db) == "1210"
    assert _sachkonto(entnahme, "SKR03", db) == "1800"


def test_abgleich_rest_privat_ohne_rest_bucht_keine_entnahme(db):
    rechnung = _eingangsrechnung(db)
    tx = _tx(db, "-8.99")
    buche_transaktion(tx.id, BuchungsRequest(rechnung_id=rechnung.id, rest_privat=True), db)
    assert _privat_eintraege(db) == []
    assert db.query(Forderung).count() == 0


def test_abgleich_rest_privat_bei_ausgangsrechnung_abgewiesen(db):
    rechnung = _eingangsrechnung(db, "100.00", typ="ausgang")
    tx = _tx(db, "-150.00")
    with pytest.raises(HTTPException) as exc:
        buche_transaktion(tx.id, BuchungsRequest(rechnung_id=rechnung.id, rest_privat=True), db)
    assert exc.value.status_code == 422
    db.rollback()
    assert db.query(Journaleintrag).count() == 0


def test_abgleich_rest_privat_bei_gutschrift_eingang_abgewiesen(db):
    rechnung = _eingangsrechnung(db)
    tx = _tx(db, "44.93")  # Eingang auf dem Konto, kein privater Anteil denkbar
    with pytest.raises(HTTPException) as exc:
        buche_transaktion(tx.id, BuchungsRequest(rechnung_id=rechnung.id, rest_privat=True), db)
    assert exc.value.status_code == 422


def test_abgleich_rest_privat_ohne_privatkategorie_bucht_nichts(db):
    for k in db.query(Kategorie).filter(Kategorie.kontenart == "Privat"):
        db.delete(k)
    db.commit()
    rechnung = _eingangsrechnung(db)
    tx = _tx(db, "-44.93")
    with pytest.raises(HTTPException) as exc:
        buche_transaktion(tx.id, BuchungsRequest(rechnung_id=rechnung.id, rest_privat=True), db)
    assert exc.value.status_code == 422
    db.rollback()
    assert db.query(Journaleintrag).count() == 0
    db.refresh(tx)
    assert tx.journal_id is None


# ---------------------------------------------------------------------------
# 2. Ausbuchen eines Guthabens - bestehendes Verhalten
# ---------------------------------------------------------------------------

def _guthaben_aus_bank(db, rechnung_brutto="8.99", tx_betrag="-44.93", tx_datum=TX_DATUM) -> Forderung:
    rechnung = _eingangsrechnung(db, rechnung_brutto)
    tx = _tx(db, tx_betrag, tx_datum)
    buche_transaktion(tx.id, BuchungsRequest(rechnung_id=rechnung.id), db)
    return db.query(Forderung).filter(Forderung.rechnung_id == rechnung.id).one()


def test_ausbuchen_auf_aufwand_bleibt_heute_und_ohne_zahlungsart(db):
    f = _guthaben_aus_bank(db)
    forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Forderungsverluste").id), db)

    db.refresh(f)
    assert f.status == "ausgebucht"
    e = db.query(Journaleintrag).filter(Journaleintrag.id == f.ausgleich_journal_id).one()
    assert e.datum == HEUTE
    assert e.zahlungsart == "Keine"
    assert e.konto_id is None
    assert e.art == "Ausgabe"
    assert e.brutto_betrag == Decimal("35.94")
    assert e.beschreibung == f"Forderungsausfall Lieferantenguthaben #{f.id}"
    assert _gegenkonto(e, db.query(Unternehmen).one(), db) is None


def test_ausbuchen_notiz_wird_beschreibung_und_notiz(db):
    f = _guthaben_aus_bank(db)
    forderung_ausbuchen(
        f.id, AusbuchenRequest(kategorie_id=_kat(db, "Forderungsverluste").id, notiz="Lieferant insolvent"), db,
    )
    db.refresh(f)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == f.ausgleich_journal_id).one()
    assert e.beschreibung == "Lieferant insolvent"
    assert f.notiz == "Lieferant insolvent"


def test_ausbuchen_nicht_offen_404_und_unbekannte_kategorie(db):
    f = _guthaben_aus_bank(db)
    with pytest.raises(HTTPException) as exc:
        forderung_ausbuchen(9999, AusbuchenRequest(kategorie_id=_kat(db, "Forderungsverluste").id), db)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=9999), db)
    assert exc.value.status_code == 404
    forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Forderungsverluste").id), db)
    with pytest.raises(HTTPException) as exc:
        forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Forderungsverluste").id), db)
    assert exc.value.status_code == 409


def test_ausbuchen_kundenguthaben_auf_aufwand_unveraendert(db):
    f = create_forderung(ForderungCreate(typ="kundenguthaben", betrag=Decimal("12.00"), partner_typ="kunde"), db)
    forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Forderungsverluste").id), db)
    db.refresh(f)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == f.ausgleich_journal_id).one()
    assert (e.datum, e.zahlungsart, e.konto_id) == (HEUTE, "Keine", None)


# ---------------------------------------------------------------------------
# 2. Ausbuchen als privater Anteil - neu
# ---------------------------------------------------------------------------

def test_ausbuchen_als_privatentnahme_uebernimmt_datum_und_bankkonto(db):
    f = _guthaben_aus_bank(db, "16.20", "-20.48")
    forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Privatentnahme").id), db)

    db.refresh(f)
    assert f.status == "ausgebucht"
    e = db.query(Journaleintrag).filter(Journaleintrag.id == f.ausgleich_journal_id).one()
    assert e.datum == TX_DATUM
    assert e.zahlungsart == "Bank"
    assert e.konto_id == db.konto_id
    assert e.brutto_betrag == Decimal("4.28")
    assert e.ust_betrag == Decimal("0.00")
    assert e.vorsteuer_betrag == Decimal("0.00")
    assert e.steuerbefreiung_grund == "Privatbuchung"
    assert e.beschreibung == f"Privater Anteil Lieferantenguthaben #{f.id}"
    unt = db.query(Unternehmen).one()
    assert _gegenkonto(e, unt, db) == "1210"
    assert _sachkonto(e, "SKR03", db) == "1800"


def test_ausbuchen_als_privatentnahme_im_vorjahr_bleibt_im_vorjahr(db):
    f = _guthaben_aus_bank(db, tx_datum=date(2025, 12, 20))
    forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Privatentnahme").id), db)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == f.ausgleich_journal_id).one()
    assert e.datum == date(2025, 12, 20)
    assert e.belegnr


def test_ausbuchen_privat_ohne_verknuepfte_zahlung_wie_bisher(db):
    f = create_forderung(ForderungCreate(typ="lieferantenguthaben", betrag=Decimal("5.00")), db)
    forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Privatentnahme").id), db)
    db.refresh(f)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == f.ausgleich_journal_id).one()
    assert (e.datum, e.zahlungsart, e.konto_id) == (HEUTE, "Keine", None)


def test_ausbuchen_privat_bei_barzahlung_wie_bisher(db):
    """Bar: keine Rückdatierung in einen womöglich abgeschlossenen Tagesabschluss."""
    bar = Journaleintrag(
        datum=date(2026, 2, 2), belegnr="J-1", beschreibung="Zahlung bar", zahlungsart="Bar",
        art="Ausgabe", netto_betrag=Decimal("10.00"), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
        vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal("10.00"),
    )
    db.add(bar)
    db.commit()
    f = create_forderung(ForderungCreate(typ="lieferantenguthaben", betrag=Decimal("2.00"), journal_id=bar.id), db)
    forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Privatentnahme").id), db)
    db.refresh(f)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == f.ausgleich_journal_id).one()
    assert (e.datum, e.zahlungsart, e.konto_id) == (HEUTE, "Keine", None)


def test_ausbuchen_als_privateinlage_abgewiesen(db):
    f = _guthaben_aus_bank(db)
    with pytest.raises(HTTPException) as exc:
        forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Privateinlage").id), db)
    assert exc.value.status_code == 422
    db.rollback()
    db.refresh(f)
    assert f.status == "offen"
    assert f.ausgleich_journal_id is None


def test_ausbuchen_kundenguthaben_als_privat_abgewiesen(db):
    f = create_forderung(ForderungCreate(typ="kundenguthaben", betrag=Decimal("12.00"), partner_typ="kunde"), db)
    with pytest.raises(HTTPException) as exc:
        forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Privatentnahme").id), db)
    assert exc.value.status_code == 422
    db.rollback()
    db.refresh(f)
    assert f.status == "offen"


def test_ausbuchen_privat_kleinunternehmer(db):
    unt = db.query(Unternehmen).one()
    unt.ist_kleinunternehmer = True
    db.commit()
    f = _guthaben_aus_bank(db)
    forderung_ausbuchen(f.id, AusbuchenRequest(kategorie_id=_kat(db, "Privatentnahme").id), db)
    e = db.query(Journaleintrag).filter(Journaleintrag.id == f.ausgleich_journal_id).one()
    assert (e.datum, e.zahlungsart) == (TX_DATUM, "Bank")
    assert e.vorsteuer_betrag == Decimal("0.00")
