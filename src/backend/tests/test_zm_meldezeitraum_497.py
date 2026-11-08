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
    GutschriftVerrechnenRequest, ZahlungKorrigieren, create_gutschrift, create_rechnung, ersatzrechnung_erstellen,
    finalisiere_rechnung, forderungsausfall_buchen, gutschrift_verrechnen, storno_rechnung, zahlung_bar_erstellen,
    zahlung_korrigieren,
)
from api.schemas import JournalEintragCreate, StornoRequest
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


def _zahlung(db, rechnung_id, datum, betrag=None, skonto=None):
    zahlung_bar_erstellen(rechnung_id, BarZahlungCreate(
        datum=datum, zahlungsart="Bank", betrag=Decimal(betrag) if betrag else None,
        skonto_betrag=Decimal(skonto) if skonto else None,
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


@pytest.mark.parametrize("dokument_typ", ["Proforma", "Angebot", "Auftrag", "Lieferschein"])
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
    assert posten[0].beschreibung == "Rechnung vom 10.03.2025 (Meldezeitraum nach §18a Abs. 8 UStG)"
    assert ustva_posten(zeitraum="2025-03", kz="41", db=db) == []
    assert jahresumsatzsteuer(jahr=2025, db=db).kz_41 == T


def test_zm_und_ustva_aus_derselben_quelle(db):
    _rechnung(db, "L", date(2025, 1, 15))
    _rechnung(db, "S", date(2025, 2, 10), leistung_bis=date(2025, 1, 31))
    kz, _ = _berechne_kz(date(2025, 1, 1), date(2025, 3, 31), db)
    zm = zm_berechnen("2025-Q1", db=db)
    assert zm.gesamt == kz["kz_41"] + kz["kz_21"] == Decimal("2000.00")


# ---------------------------------------------------------------------------
# Korrekturen nach §17 UStG (X18-X30, X34, X37)
#
# storno_rechnung(), create_gutschrift() und zahlung_korrigieren() datieren auf "heute" - das
# Ereignisdatum wird über date in api.rechnungen gesetzt.
# ---------------------------------------------------------------------------

class _Datum(date):
    heute = None

    @classmethod
    def today(cls):
        return cls.heute or date.today()


@pytest.fixture
def heute(monkeypatch):
    monkeypatch.setattr(rechnungen_api, "date", _Datum)

    def setze(d):
        _Datum.heute = d
    yield setze
    _Datum.heute = None


def _storno(db, rechnung_id):
    storno_rechnung(rechnung_id, StornoRequest(grund="Fehler"), db)


def _gutschrift(db, rechnung_id, netto="200.00", finalisieren=True) -> int:
    gid = create_gutschrift(rechnung_id, db).id
    gs = db.get(Rechnung, gid)
    betrag = -Decimal(netto)
    pos = gs.positionen[0]
    pos.netto = Decimal(netto)
    pos.brutto = betrag
    gs.netto_gesamt = gs.brutto_gesamt = betrag
    db.commit()
    if finalisieren:
        finalisiere_rechnung(gid, db)
    return gid


def _texte(db, jahr, monat, nr):
    _, posten = _berechne_kz(*_monat(jahr, monat), db)
    return sorted((p["beschreibung"], p["betrag"]) for p in posten[nr])


NULL = Decimal("0.00")


def test_x18_storno_in_spaeterem_monat(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15), leistung_bis=date(2025, 1, 10))
    heute(date(2025, 3, 10))
    _storno(db, rid)
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _kz(db, 2025, 3, "kz_41") == -T
    assert _zm(db, "2025-01") == [(UID, "L", T)]
    assert _zm(db, "2025-03") == [(UID, "L", -T)]
    assert _zm(db, "2025-Q1") == []
    assert _texte(db, 2025, 3, "kz_41") == [("Storno der Rechnung (§17 UStG)", -T)]


def test_x19_storno_im_selben_monat(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    heute(date(2025, 1, 25))
    _storno(db, rid)
    assert _kz(db, 2025, 1, "kz_41") == NULL
    assert _zm(db, "2025-01") == []


def test_x20_storno_einer_bezahlten_rechnung(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    _zahlung(db, rid, date(2025, 2, 1))
    heute(date(2025, 3, 10))
    _storno(db, rid)  # Gegenbuchung auf dem Zahlungsdatum (#320) - zählt nicht
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _kz(db, 2025, 2, "kz_41") == NULL
    assert _kz(db, 2025, 3, "kz_41") == -T
    assert _zm(db, "2025-02") == []
    assert _zm(db, "2025-Q1") == []


def test_x20_storno_nach_skonto_steht_auf_null(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    _zahlung(db, rid, date(2025, 2, 5), "980.00", skonto="20.00")
    heute(date(2025, 3, 10))
    _storno(db, rid)
    assert _kz(db, 2025, 2, "kz_41") == Decimal("-20.00")
    assert _kz(db, 2025, 3, "kz_41") == Decimal("-980.00")
    assert _zm(db, "2025-Q1") == []


def test_x21_storno_vor_dem_meldemonat(db, heute):
    rid = _rechnung(db, "S", date(2025, 1, 15), leistung_bis=date(2025, 4, 30))
    heute(date(2025, 2, 10))
    _storno(db, rid)
    for monat in (1, 2, 4):
        assert _kz(db, 2025, monat, "kz_21") == NULL
    assert _zm(db, "2025-Q1") == []
    assert _zm(db, "2025-Q2") == []


def test_x22_ersatzrechnung_nach_storno(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15), leistung_bis=date(2025, 1, 10))
    heute(date(2025, 3, 10))
    _storno(db, rid)
    eid = ersatzrechnung_erstellen(rid, db).id
    finalisiere_rechnung(eid, db)
    ersatz = db.get(Rechnung, eid)
    assert ersatz.datum == date(2025, 3, 10)
    assert ersatz.ist_eu_lieferung
    # Lieferung im Januar, aber die Ersatzrechnung meldet nicht vor dem Storno des Originals:
    # Februar bleibt unverändert, im März heben sich Storno und Ersatz auf
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _kz(db, 2025, 2, "kz_41") == NULL
    assert _kz(db, 2025, 3, "kz_41") == NULL
    assert _zm(db, "2025-02") == []
    assert _zm(db, "2025-03") == []
    assert _zm(db, "2025-Q1") == [(UID, "L", T)]
    assert _texte(db, 2025, 3, "kz_41") == [
        ("Rechnung vom 10.03.2025 (Ersatzrechnung, gemeldet im Monat des Stornos der Originalrechnung)", T),
        ("Storno der Rechnung (§17 UStG)", -T),
    ]


def test_x22_ersatzrechnung_fuer_alte_rechnung_ohne_sperre(db, heute):
    rid = _rechnung(db, "L", date(2024, 12, 15), leistung_bis=date(2024, 12, 10))
    _zahlung(db, rid, date(2024, 12, 20))
    heute(date(2025, 2, 10))
    _storno(db, rid)  # alt: Gegenbuchung auf dem Zahlungsdatum (#320), wie bisher
    heute(date(2025, 3, 10))
    eid = ersatzrechnung_erstellen(rid, db).id
    finalisiere_rechnung(eid, db)
    # Original nach altem Verfahren (Dezember gemeldet und dort storniert) - keine Sperre bis
    # zum Storno; der Ersatz meldet nach eigener Regel im ersten Monat ab dem Stichtag (X16)
    assert _kz(db, 2024, 12, "kz_41") == NULL
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _zm(db, "2025-01") == [(UID, "L", T)]


@pytest.mark.parametrize("art, feld", [
    ("L", "ist_eu_lieferung"), ("S", "ist_reverse_charge"),
    ("ausfuhr", "ist_ausfuhrlieferung"), ("drittland", "ist_drittland_leistung"),
])
def test_ersatzrechnung_uebernimmt_steuerkennzeichen(db, heute, art, feld):
    rid = _rechnung(db, art, date(2025, 1, 15))
    heute(date(2025, 3, 10))
    _storno(db, rid)
    ersatz = db.get(Rechnung, ersatzrechnung_erstellen(rid, db).id)
    flags = ("ist_eu_lieferung", "ist_reverse_charge", "ist_ausfuhrlieferung", "ist_drittland_leistung")
    assert {f: bool(getattr(ersatz, f)) for f in flags} == {f: f == feld for f in flags}


def test_x23_storno_alter_rechnung_wie_bisher(db, heute):
    rid = _rechnung(db, "L", date(2024, 12, 15))
    _zahlung(db, rid, date(2024, 12, 20))
    heute(date(2025, 2, 10))
    _storno(db, rid)
    kz, posten = _berechne_kz(*_monat(2024, 12), db)
    assert kz["kz_41"] == NULL
    assert sorted((p["quelle"], p["betrag"]) for p in posten["kz_41"]) == [("journal", -T), ("journal", T)]
    assert _kz(db, 2025, 2, "kz_41") == NULL
    assert _zm(db, "2025-Q1") == []


def test_x24_gutschrift_meldet_minus_am_gutschriftsdatum(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    heute(date(2025, 5, 12))
    gid = _gutschrift(db, rid)
    heute(date(2025, 5, 20))
    _zahlung(db, gid, date(2025, 5, 20))  # Auszahlung zählt nicht
    assert db.get(Rechnung, gid).netto_gesamt == Decimal("-200.00")
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _kz(db, 2025, 5, "kz_41") == Decimal("-200.00")
    assert _zm(db, "2025-05") == [(UID, "L", Decimal("-200.00"))]
    assert _zm(db, "2025-Q2") == [(UID, "L", Decimal("-200.00"))]
    posten = ustva_posten(zeitraum="2025-05", kz="41", db=db)
    assert [(p.quelle, p.rechnung_id, p.beschreibung) for p in posten] == [
        ("rechnung", gid, "Gutschrift (§17 UStG)")]


def test_x24_verrechnung_einer_gutschrift_zaehlt_nicht(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    zweite = _rechnung(db, "L", date(2025, 2, 15))
    heute(date(2025, 5, 12))
    gid = _gutschrift(db, rid)
    gutschrift_verrechnen(gid, GutschriftVerrechnenRequest(rechnung_id=zweite), db)
    assert db.query(Journaleintrag).filter(Journaleintrag.zahlungsart == "Verrechnung").count() == 2
    assert _kz(db, 2025, 2, "kz_41") == T
    assert _texte(db, 2025, 5, "kz_41") == [("Gutschrift (§17 UStG)", Decimal("-200.00"))]
    assert _zm(db, "2025-Q2") == [(UID, "L", Decimal("-200.00"))]


def test_x25_gutschrift_zu_alter_rechnung_wie_bisher(db, heute):
    rid = _rechnung(db, "L", date(2024, 12, 15))
    _zahlung(db, rid, date(2024, 12, 20))
    heute(date(2025, 2, 10))
    gid = _gutschrift(db, rid)
    assert _kz(db, 2025, 2, "kz_41") == NULL  # noch nicht ausgezahlt: wie bisher nichts
    _zahlung(db, gid, date(2025, 2, 10))
    kz, posten = _berechne_kz(*_monat(2025, 2), db)
    assert kz["kz_41"] == Decimal("-200.00")
    assert [p["quelle"] for p in posten["kz_41"]] == ["journal"]
    assert _zm(db, "2025-Q1") == [(UID, "L", Decimal("-200.00"))]


def test_x26_gutschrift_entwurf_meldet_nichts(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    heute(date(2025, 5, 12))
    _gutschrift(db, rid, finalisieren=False)
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _kz(db, 2025, 5, "kz_41") == NULL
    assert _zm(db, "2025-Q2") == []


def test_x27_storno_der_gutschrift_meldet_plus(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    heute(date(2025, 5, 12))
    gid = _gutschrift(db, rid)
    heute(date(2025, 6, 10))
    _storno(db, gid)
    assert _kz(db, 2025, 5, "kz_41") == Decimal("-200.00")
    assert _kz(db, 2025, 6, "kz_41") == Decimal("200.00")
    assert _zm(db, "2025-06") == [(UID, "L", Decimal("200.00"))]
    assert _zm(db, "2025-Q2") == []


def test_x28_skonto_meldet_minus_am_skontodatum(db):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    _zahlung(db, rid, date(2025, 2, 5), "980.00", skonto="20.00")
    assert _kz(db, 2025, 1, "kz_41") == T
    assert _kz(db, 2025, 2, "kz_41") == Decimal("-20.00")
    assert _zm(db, "2025-02") == [(UID, "L", Decimal("-20.00"))]
    assert _zm(db, "2025-Q1") == [(UID, "L", Decimal("980.00"))]
    assert _texte(db, 2025, 2, "kz_41") == [("Skonto (§17 UStG)", Decimal("-20.00"))]


def test_x29_skonto_alter_rechnung_wie_bisher(db):
    rid = _rechnung(db, "L", date(2024, 12, 15))
    _zahlung(db, rid, date(2025, 2, 5), "980.00", skonto="20.00")
    assert _kz(db, 2024, 12, "kz_41") == NULL
    assert _kz(db, 2025, 2, "kz_41") == Decimal("980.00")
    assert _zm(db, "2025-Q1") == [(UID, "L", Decimal("980.00"))]


def test_x30_korrektur_der_skontobuchung(db, heute):
    rid = _rechnung(db, "S", date(2025, 1, 15))
    _zahlung(db, rid, date(2025, 2, 5), "980.00", skonto="20.00")
    skonto_id = db.query(Journaleintrag.id).filter(
        Journaleintrag.rechnung_id == rid, Journaleintrag.zahlungsart == "Skonto").scalar()
    heute(date(2025, 3, 10))
    zahlung_korrigieren(rid, skonto_id, ZahlungKorrigieren(
        neues_datum=date(2025, 3, 10), neuer_betrag=Decimal("15.00")), db)
    # Seit PR #494 steht der Storno einer korrigierten Zahlung auf dem Datum der Originalbuchung:
    # der Februar wird berichtigt (−20 + 20), die korrigierte Skontobuchung zählt im März
    assert _texte(db, 2025, 2, "kz_21") == [
        ("Skonto (§17 UStG)", Decimal("-20.00")), ("Skonto (§17 UStG)", Decimal("20.00"))]
    assert _kz(db, 2025, 2, "kz_21") == Decimal("0.00")
    assert _texte(db, 2025, 3, "kz_21") == [("Skonto (§17 UStG)", Decimal("-15.00"))]
    assert _kz(db, 2025, 3, "kz_21") == Decimal("-15.00")
    assert _zm(db, "2025-Q1") == [(UID, "S", Decimal("985.00"))]


def test_x34_forderungsausfall_alter_rechnung_meldet_nichts(db):
    rid = _rechnung(db, "L", date(2024, 11, 15))
    forderungsausfall_buchen(rid, db)
    for jahr, monat in [(2024, 11), (2024, 12), (2025, 1)]:
        assert _kz(db, jahr, monat, "kz_41") == NULL
    assert _zm(db, "2024-Q4") == []
    assert _zm(db, "2025-Q1") == []


def test_x37_storno_der_schlussrechnung(db, heute):
    aid = _abschlag(db, date(2025, 2, 15))
    _zahlung(db, aid, date(2025, 2, 20))
    sid = _schlussrechnung(db, date(2025, 5, 15), aid, leistung_bis=date(2025, 4, 30))
    heute(date(2025, 7, 10))
    _storno(db, sid)
    assert db.get(Rechnung, aid).verrechnet_in_rechnung_id is None
    assert _kz(db, 2025, 2, "kz_41") == NULL
    assert _kz(db, 2025, 5, "kz_41") == Decimal("1500.00")
    assert _kz(db, 2025, 7, "kz_41") == Decimal("-1500.00")
    assert _zm(db, "2025-07") == [(UID, "L", Decimal("-1500.00"))]
    assert _zm(db, "2025-Q1") == []


def test_x27_storno_der_gutschrift_nach_storno_der_rechnung(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    heute(date(2025, 5, 12))
    gid = _gutschrift(db, rid)
    heute(date(2025, 6, 10))
    _storno(db, rid)
    heute(date(2025, 7, 10))
    _storno(db, gid)
    # nach dem Storno steht die Rechnung auf 0 - das spätere Storno der Gutschrift meldet nichts
    assert _kz(db, 2025, 5, "kz_41") == Decimal("-200.00")
    assert _kz(db, 2025, 6, "kz_41") == Decimal("-800.00")
    assert _kz(db, 2025, 7, "kz_41") == NULL
    assert _zm(db, "2025-06") == [(UID, "L", Decimal("-800.00"))]
    assert _zm(db, "2025-07") == []
    assert sum(_kz(db, 2025, m, "kz_41") for m in range(1, 13)) == NULL


def test_gutschrift_nach_storno_der_rechnung_meldet_nichts(db, heute):
    rid = _rechnung(db, "L", date(2025, 1, 15))
    heute(date(2025, 5, 12))
    gid = _gutschrift(db, rid, finalisieren=False)
    heute(date(2025, 6, 10))
    _storno(db, rid)
    # Entwurf vor dem Storno angelegt, mit späterem Datum erst danach finalisiert
    heute(date(2025, 7, 10))
    db.get(Rechnung, gid).datum = date(2025, 7, 10)
    db.commit()
    finalisiere_rechnung(gid, db)
    assert _kz(db, 2025, 6, "kz_41") == -T
    assert _kz(db, 2025, 7, "kz_41") == NULL
    assert _zm(db, "2025-07") == []
    assert sum(_kz(db, 2025, m, "kz_41") for m in range(1, 13)) == NULL


# ---------------------------------------------------------------------------
# Alte und neue Rechnungen nebeneinander (Stichtag-Übergang)
# ---------------------------------------------------------------------------

def test_alte_und_neue_rechnung_im_selben_quartal(db):
    alt = _rechnung(db, "L", date(2024, 12, 15))
    _zahlung(db, alt, date(2025, 2, 10))      # alt: meldet bei Zahlung (Februar)
    neu = _rechnung(db, "L", date(2025, 1, 15), netto="300.00")
    _zahlung(db, neu, date(2025, 2, 10))      # neu: Zahlung zählt nicht
    s_alt = _rechnung(db, "S", date(2024, 12, 20), netto="50.00")
    _zahlung(db, s_alt, date(2025, 3, 5))
    _rechnung(db, "S", date(2025, 3, 20), leistung_bis=date(2025, 3, 15), netto="70.00")
    assert _kz(db, 2025, 1, "kz_41") == Decimal("300.00")
    assert _kz(db, 2025, 2, "kz_41") == T
    assert _kz(db, 2025, 3, "kz_21") == Decimal("120.00")
    assert _zm(db, "2025-Q1") == [(UID, "L", Decimal("1300.00")), (UID, "S", Decimal("120.00"))]
    kz, _ = _berechne_kz(date(2025, 1, 1), date(2025, 3, 31), db)
    assert zm_berechnen("2025-Q1", db=db).gesamt == kz["kz_41"] + kz["kz_21"]


def test_storno_alter_und_neuer_rechnung_im_selben_monat(db, heute):
    alt = _rechnung(db, "L", date(2024, 12, 15))
    _zahlung(db, alt, date(2025, 1, 10))
    neu = _rechnung(db, "L", date(2025, 1, 20), netto="400.00")
    heute(date(2025, 3, 10))
    _storno(db, alt)  # alt: Gegenbuchung auf dem Zahlungsdatum (#320), Januar steht auf 0
    _storno(db, neu)  # neu: Minus im März
    assert _kz(db, 2025, 1, "kz_41") == Decimal("400.00")
    assert _kz(db, 2025, 3, "kz_41") == Decimal("-400.00")
    assert _zm(db, "2025-Q1") == []
