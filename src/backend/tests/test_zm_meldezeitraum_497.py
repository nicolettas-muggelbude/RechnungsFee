"""
Issue #497: Meldezeitraum für ZM und UStVA KZ 41/21 nach Rechnung statt Zahlung.

§18a Abs. 8 / §18b Satz 1 Nr. 1/2 UStG: L (KZ 41) im Monat der Rechnung, spätestens im Monat nach
der Lieferung; S (KZ 21) im Monat der Leistung (leistung_bis → leistung_von → Rechnungsdatum).
Quelle ist die Rechnung (Netto), nicht die Zahlung - ZM und UStVA aus derselben Quelle
(utils/zm_meldezeitraum.ig_umsaetze). Rechnungen vor dem Stichtag bleiben beim Zahlungsdatum.

Der echte Stichtag liegt in der Zukunft; finalisiere_rechnung() lässt aber kein Rechnungsdatum in
der Zukunft zu. CUTOVER_DATUM wird deshalb auf STICHTAG (01.01.2025) gepatcht - alle Daten sind
gegenüber dem Stichtag 01.01.2027 um genau zwei Jahre vorverlegt.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.rechnungen as rechnungen_api
import api.ustva as ustva_api
from api.journal import create_eintrag
from api.rechnungen import (
    ZahlungKorrigieren, create_rechnung, finalisiere_rechnung, zahlung_bar_erstellen, zahlung_korrigieren,
)
from api.schemas import JournalEintragCreate
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate
from api.ustva import _berechne_kz, _berechne_kz_fuer, jahresumsatzsteuer, ustva_posten
from api.zm import _hat_ig_eintraege_gesamt, zm_berechnen
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Kunde, Rechnung, Unternehmen
from utils import zm_meldezeitraum

STICHTAG = date(2025, 1, 1)
UID = "FR40303265045"


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(rechnungen_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    monkeypatch.setattr(ustva_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    monkeypatch.setattr(zm_meldezeitraum, "CUTOVER_DATUM", STICHTAG)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345",
                            ort="Testort", ist_kleinunternehmer=False))
    session.add(Kunde(firmenname="EU-Kunde SARL", land="FR", ust_idnr=UID))
    session.commit()
    yield session
    session.close()


_FLAG = {
    "L": {"ist_eu_lieferung": True},
    "S": {"ist_reverse_charge": True},
    "ausfuhr": {"ist_ausfuhrlieferung": True},
    "drittland": {"ist_drittland_leistung": True},
}


def _rechnung(db, art, datum, leistung_von=None, leistung_bis=None, netto="1000.00",
              dokument_typ="Rechnung", positionen=None) -> int:
    kunde = db.query(Kunde).first()
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", datum=datum, kunde_id=kunde.id, dokument_typ=dokument_typ,
        leistung_von=leistung_von, leistung_bis=leistung_bis, **_FLAG[art],
        positionen=positionen or [
            RechnungspositionCreate(beschreibung="Leistung", netto=Decimal(netto), ust_satz=Decimal("0")),
        ],
    ), db)
    finalisiere_rechnung(resp.id, db)
    return resp.id


def _zahlung(db, rechnung_id, datum, betrag=None):
    zahlung_bar_erstellen(rechnung_id, BarZahlungCreate(
        datum=datum, zahlungsart="Bank", betrag=Decimal(betrag) if betrag else None,
    ), db)


def _monat(jahr, monat):
    von, bis, _ = ustva_api._zeitraum_grenzen(f"{jahr}-{monat:02d}")
    return von, bis


def _kz(db, jahr, monat, nr):
    kz, _ = _berechne_kz(*_monat(jahr, monat), db)
    return kz[nr]


def _zm(db, zeitraum):
    return [(p.ust_idnr, p.kennzeichen, p.betrag) for p in zm_berechnen(zeitraum, db=db).positionen]


T = Decimal("1000.00")


# ---------------------------------------------------------------------------
# L / KZ 41 - Monat der Rechnung, spätestens Monat nach der Lieferung (X1-X8)
# ---------------------------------------------------------------------------

def test_x1_unbezahlte_ig_lieferung_im_rechnungsmonat(db):
    _rechnung(db, "L", date(2025, 1, 15), leistung_bis=date(2025, 1, 10))
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _zm(db, "2025-01") == [(UID, "L", T)]
    assert _zm(db, "2025-Q1") == [(UID, "L", T)]


def test_x2_spaetere_zahlung_verschiebt_nichts(db):
    rid = _rechnung(db, "L", date(2025, 1, 15), leistung_bis=date(2025, 1, 10))
    _zahlung(db, rid, date(2025, 4, 10))
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _kz(db, 2025, 4, "kz_41") == Decimal("0.00")
    assert _zm(db, "2025-Q2") == []


def test_x3_spaete_rechnung_meldet_im_monat_nach_lieferung(db):
    _rechnung(db, "L", date(2025, 3, 10), leistung_bis=date(2025, 1, 20))
    assert _kz(db, 2025, 2, "kz_41") == T
    assert _kz(db, 2025, 3, "kz_41") == Decimal("0.00")
    assert _zm(db, "2025-02") == [(UID, "L", T)]


def test_x4_rechnung_im_monat_nach_lieferung(db):
    _rechnung(db, "L", date(2025, 3, 31), leistung_bis=date(2025, 2, 20))
    assert _kz(db, 2025, 3, "kz_41") == T
    assert _zm(db, "2025-03") == [(UID, "L", T)]


def test_x5_ohne_leistungsdatum_gilt_rechnungsdatum(db):
    _rechnung(db, "L", date(2025, 2, 15))
    assert _kz(db, 2025, 2, "kz_41") == T
    assert _zm(db, "2025-02") == [(UID, "L", T)]


def test_x6_leistungszeitraum_endet_mit_leistung_bis(db):
    _rechnung(db, "L", date(2025, 4, 10), leistung_von=date(2025, 1, 5), leistung_bis=date(2025, 2, 25))
    assert _kz(db, 2025, 3, "kz_41") == T
    assert _zm(db, "2025-03") == [(UID, "L", T)]


def test_x7_jahreswechsel(db):
    _rechnung(db, "L", date(2026, 2, 15), leistung_bis=date(2025, 12, 20))
    assert _kz(db, 2026, 1, "kz_41") == T
    assert _kz(db, 2025, 12, "kz_41") == Decimal("0.00")
    assert _zm(db, "2026-Q1") == [(UID, "L", T)]


def test_x8_rechnung_vor_lieferung_meldet_im_rechnungsmonat(db):
    _rechnung(db, "L", date(2025, 1, 10), leistung_bis=date(2025, 3, 20))
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _zm(db, "2025-01") == [(UID, "L", T)]


# ---------------------------------------------------------------------------
# S / KZ 21 - Monat der Leistung (X9-X12)
# ---------------------------------------------------------------------------

def test_x9_sonstige_leistung_nach_leistung_bis(db):
    _rechnung(db, "S", date(2025, 3, 10), leistung_bis=date(2025, 2, 28))
    assert _kz(db, 2025, 2, "kz_21") == T
    assert _kz(db, 2025, 3, "kz_21") == Decimal("0.00")
    assert _zm(db, "2025-02") == [(UID, "S", T)]


def test_x10_nur_leistung_von(db):
    _rechnung(db, "S", date(2025, 3, 5), leistung_von=date(2025, 1, 15))
    assert _kz(db, 2025, 1, "kz_21") == T
    assert _zm(db, "2025-01") == [(UID, "S", T)]


def test_x11_ohne_leistungsdatum_spaetere_zahlung(db):
    rid = _rechnung(db, "S", date(2025, 1, 15))
    _zahlung(db, rid, date(2025, 4, 10))
    assert _kz(db, 2025, 1, "kz_21") == T
    assert _kz(db, 2025, 4, "kz_21") == Decimal("0.00")
    assert _zm(db, "2025-01") == [(UID, "S", T)]
    assert _zm(db, "2025-04") == []


def test_x12_leistung_nach_rechnung(db):
    _rechnung(db, "S", date(2025, 1, 15), leistung_bis=date(2025, 4, 30))
    assert _kz(db, 2025, 1, "kz_21") == Decimal("0.00")
    assert _kz(db, 2025, 4, "kz_21") == T
    assert _zm(db, "2025-Q2") == [(UID, "S", T)]


# ---------------------------------------------------------------------------
# Stichtag (X13-X17)
# ---------------------------------------------------------------------------

def test_x13_alte_rechnung_bleibt_beim_zahlungsdatum(db):
    rid = _rechnung(db, "L", date(2024, 12, 15))
    _zahlung(db, rid, date(2025, 2, 10))
    assert _kz(db, 2024, 12, "kz_41") == Decimal("0.00")
    assert _kz(db, 2025, 2, "kz_41") == T
    assert _zm(db, "2025-Q1") == [(UID, "L", T)]


def test_x14_alte_unbezahlte_rechnung_wie_bisher_nirgends(db):
    _rechnung(db, "L", date(2024, 11, 15))
    for jahr, monat in [(2024, 11), (2024, 12), (2025, 1)]:
        assert _kz(db, jahr, monat, "kz_41") == Decimal("0.00")
    assert _zm(db, "2024-Q4") == []
    assert _zm(db, "2025-Q1") == []


def test_x15_alte_sonstige_leistung_bleibt_beim_zahlungsdatum(db):
    rid = _rechnung(db, "S", date(2024, 12, 20), leistung_bis=date(2025, 1, 31))
    _zahlung(db, rid, date(2025, 1, 15))
    assert _kz(db, 2024, 12, "kz_21") == Decimal("0.00")
    kz, posten = _berechne_kz(*_monat(2025, 1), db)
    assert kz["kz_21"] == T
    assert [p["quelle"] for p in posten["kz_21"]] == ["journal"]


def test_x16_lieferung_vor_stichtag_meldet_nicht_rueckwirkend(db):
    # Entscheidung: nie vor dem Stichtag - Lieferung im November, Rechnung im Januar → Januar,
    # nicht Dezember (Zeitraum nach altem Verfahren schon abgegeben)
    _rechnung(db, "L", date(2025, 1, 15), leistung_bis=date(2024, 11, 10))
    assert _kz(db, 2024, 12, "kz_41") == Decimal("0.00")
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _zm(db, "2024-Q4") == []
    assert _zm(db, "2025-01") == [(UID, "L", T)]


def test_x17_leistung_vor_stichtag_meldet_nicht_rueckwirkend(db):
    _rechnung(db, "S", date(2025, 1, 10), leistung_bis=date(2024, 12, 15))
    assert _kz(db, 2024, 12, "kz_21") == Decimal("0.00")
    assert _kz(db, 2025, 1, "kz_21") == T
    assert _zm(db, "2024-12") == []
    assert _zm(db, "2025-01") == [(UID, "S", T)]


# ---------------------------------------------------------------------------
# Abschlags- und Schlussrechnungen, Issue #419 (X35, X36, X38)
# ---------------------------------------------------------------------------

def _abschlag(db, datum, netto="500.00") -> int:
    return _rechnung(db, "L", datum, netto=netto, dokument_typ="Abschlagsrechnung")


def _schlussrechnung(db, datum, abschlag_id, leistung_bis=None, gesamt="1500.00", abzug="500.00") -> int:
    return _rechnung(db, "L", datum, leistung_bis=leistung_bis, positionen=[
        RechnungspositionCreate(beschreibung="Gesamtleistung", netto=Decimal(gesamt), ust_satz=Decimal("0")),
        RechnungspositionCreate(beschreibung="Abzgl. Abschlag", menge=Decimal("-1"), netto=Decimal(abzug),
                                ust_satz=Decimal("0"), abschlag_rechnung_id=abschlag_id),
    ])


def test_x35_schlussrechnung_meldet_gesamtleistung_abschlag_nichts(db):
    aid = _abschlag(db, date(2025, 2, 15))
    _zahlung(db, aid, date(2025, 2, 20))
    sid = _schlussrechnung(db, date(2025, 5, 15), aid, leistung_bis=date(2025, 4, 30))
    assert db.get(Rechnung, sid).netto_gesamt == Decimal("1000.00")
    assert _kz(db, 2025, 2, "kz_41") == Decimal("0.00")
    assert _kz(db, 2025, 5, "kz_41") == Decimal("1500.00")
    assert _zm(db, "2025-Q1") == []
    assert _zm(db, "2025-05") == [(UID, "L", Decimal("1500.00"))]


def test_x36_abschlag_ohne_schlussrechnung(db):
    aid = _abschlag(db, date(2025, 2, 15))
    _zahlung(db, aid, date(2025, 2, 20))
    assert _kz(db, 2025, 2, "kz_41") == Decimal("0.00")
    assert _zm(db, "2025-Q1") == []


def test_x38_alter_abschlag_neue_schlussrechnung_nicht_doppelt(db):
    aid = _abschlag(db, date(2024, 12, 15))
    _zahlung(db, aid, date(2024, 12, 20))
    _schlussrechnung(db, date(2025, 1, 15), aid, leistung_bis=date(2025, 1, 10))
    assert _kz(db, 2024, 12, "kz_41") == Decimal("500.00")
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _zm(db, "2024-12") == [(UID, "L", Decimal("500.00"))]
    assert _zm(db, "2025-01") == [(UID, "L", T)]


# ---------------------------------------------------------------------------
# Zahlungen, freie Buchungen, andere Dokumenttypen und Kennzahlen (X39-X45)
# ---------------------------------------------------------------------------

def test_x39_teil_und_ueberzahlung_aendern_nichts(db):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    _zahlung(db, rid, date(2025, 2, 5), "400.00")
    _zahlung(db, rid, date(2025, 3, 5), "700.00")
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _kz(db, 2025, 2, "kz_41") == Decimal("0.00")
    assert _kz(db, 2025, 3, "kz_41") == Decimal("0.00")
    assert _zm(db, "2025-Q1") == [(UID, "L", T)]


def test_x40_zahlungskorrektur_aendert_nichts(db):
    rid = _rechnung(db, "S", date(2025, 1, 15))
    _zahlung(db, rid, date(2025, 2, 5))
    journal_id = db.query(Journaleintrag.id).filter(Journaleintrag.rechnung_id == rid).scalar()
    zahlung_korrigieren(rid, journal_id, ZahlungKorrigieren(neues_datum=date(2025, 3, 5)), db)
    assert _kz(db, 2025, 1, "kz_21") == T
    assert _kz(db, 2025, 2, "kz_21") == Decimal("0.00")
    assert _kz(db, 2025, 3, "kz_21") == Decimal("0.00")
    assert _zm(db, "2025-Q1") == [(UID, "S", T)]


def test_x41_freie_buchung_ohne_rechnung_bleibt_beim_buchungsdatum(db):
    kat = Kategorie(name="Innergemeinschaftliche Lieferungen", kontenart="Erlös",
                    konto_skr03="8125", konto_skr04="4125", vorsteuer_prozent=0, ust_satz_standard=0)
    db.add(kat)
    db.commit()
    create_eintrag(JournalEintragCreate(
        datum=date(2025, 3, 10), beschreibung="ig. Lieferung ohne Rechnung", kategorie_id=kat.id,
        art="Einnahme", brutto_betrag=T, zahlungsart="Bank",
    ), db)
    assert _kz(db, 2025, 3, "kz_41") == T
    assert _zm(db, "2025-03") == [("unbekannt", "L", T)]


@pytest.mark.parametrize("dokument_typ", ["Proforma", "Angebot"])
def test_x42_andere_dokumenttypen_melden_nichts(db, dokument_typ):
    _rechnung(db, "L", date(2025, 1, 15), dokument_typ=dokument_typ)
    assert _kz(db, 2025, 1, "kz_41") == Decimal("0.00")
    assert _zm(db, "2025-Q1") == []


@pytest.mark.parametrize("art, nr", [("ausfuhr", "kz_43"), ("drittland", "kz_45")])
def test_x43_x44_kz43_kz45_bleiben_beim_zahlungsdatum(db, art, nr):
    rid = _rechnung(db, art, date(2025, 1, 15))
    _zahlung(db, rid, date(2025, 4, 10))
    assert _kz(db, 2025, 1, nr) == Decimal("0.00")
    assert _kz(db, 2025, 4, nr) == T


def test_x45_kleinunternehmer(db):
    unt = db.query(Unternehmen).first()
    unt.ist_kleinunternehmer = True
    db.commit()
    _rechnung(db, "L", date(2025, 1, 15))
    kz, posten = _berechne_kz_fuer(unt, *_monat(2025, 1), db)
    assert kz["kz_41"] == Decimal("0.00")
    assert posten["kz_41"] == []
    with pytest.raises(HTTPException) as exc:
        zm_berechnen("2025-Q1", db=db)
    assert exc.value.status_code == 422


# ---------------------------------------------------------------------------
# Menüpunkt ZM, Posten-Aufschlüsselung, Jahreserklärung (X46, X47)
# ---------------------------------------------------------------------------

def test_x46_menue_zeigt_zm_fuer_unbezahlte_neue_rechnung(db):
    _rechnung(db, "L", date(2024, 11, 15))  # alt, unbezahlt: wie bisher unsichtbar
    assert not _hat_ig_eintraege_gesamt(db)
    _rechnung(db, "L", date(2025, 1, 15))
    assert _hat_ig_eintraege_gesamt(db)


def test_x47_posten_und_jahreserklaerung(db):
    rid = _rechnung(db, "L", date(2025, 3, 10), leistung_bis=date(2025, 1, 20))
    _zahlung(db, rid, date(2025, 3, 20))
    posten = ustva_posten(zeitraum="2025-02", kz="41", db=db)
    assert len(posten) == 1
    assert posten[0].quelle == "rechnung"
    assert posten[0].rechnung_id == rid
    assert posten[0].datum == date(2025, 2, 28)
    assert posten[0].betrag == T
    assert ustva_posten(zeitraum="2025-03", kz="41", db=db) == []
    assert jahresumsatzsteuer(jahr=2025, db=db).kz_41 == T


def test_zm_und_ustva_aus_derselben_quelle(db):
    _rechnung(db, "L", date(2025, 1, 15))
    _rechnung(db, "S", date(2025, 2, 10), leistung_bis=date(2025, 1, 31))
    kz, _ = _berechne_kz(date(2025, 1, 1), date(2025, 3, 31), db)
    zm = zm_berechnen("2025-Q1", db=db)
    assert zm.gesamt == kz["kz_41"] + kz["kz_21"] == Decimal("2000.00")
