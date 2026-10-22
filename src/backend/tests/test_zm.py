"""
Issue #456: Zusammenfassende Meldung (§18a UStG).

EU-B2B-Dienstleistungen (Ausgangsrechnung mit ist_reverse_charge, §3a Abs. 2 UStG) fehlten in
der ZM, weil sie über ust_sonderfall='13b_abs1' gesucht wurden - den bekommen sie seit #372
nicht mehr. Stattdessen erschien die Storno-Gegenbuchung eines §13b-EINKAUFS (art kehrt sich
um → Einnahme + 13b_abs1) als Position mit USt-IdNr. „unbekannt". Fix: Erkennung wie UStVA
KZ 21 über die rechnung_id, Kennzeichen „S" wie bei ELSTER.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.journal import create_eintrag, storno_eintrag
from api.rechnungen import create_rechnung, finalisiere_rechnung, storno_rechnung, zahlung_bar_erstellen
from api.schemas import JournalEintragCreate, StornoRequest
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate
from api.ustva import _berechne_kz
from api.zm import _hat_ig_eintraege_gesamt, zm_berechnen
from database.connection import Base
from database.models import Kategorie, Kunde, Unternehmen


@pytest.fixture
def db(monkeypatch):
    import api.rechnungen as rechnungen_api
    import api.ustva as ustva_api
    monkeypatch.setattr(rechnungen_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    monkeypatch.setattr(ustva_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345",
                            ort="Testort", ist_kleinunternehmer=False))
    session.add(Kunde(firmenname="EU-Kunde SARL", land="FR", ust_idnr="FR40303265045"))
    session.commit()
    yield session
    session.close()


def _eu_dienstleistung(db, netto="1000.00") -> int:
    kunde = db.query(Kunde).first()
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 6, 1), kunde_id=kunde.id, ist_reverse_charge=True,
        positionen=[RechnungspositionCreate(beschreibung="Beratung", netto=Decimal(netto), ust_satz=Decimal("0"))],
    ), db)
    finalisiere_rechnung(resp.id, db)
    zahlung_bar_erstellen(resp.id, BarZahlungCreate(datum=date(2026, 6, 15), zahlungsart="Bank"), db)
    return resp.id


def _stornierter_13b_einkauf(db):
    kat = Kategorie(name="EU-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
                    konto_skr03="3123", konto_skr04="5923", vorsteuer_prozent=100, ust_satz_standard=19)
    db.add(kat)
    db.commit()
    eintrag = create_eintrag(JournalEintragCreate(
        datum=date(2026, 6, 5), beschreibung="EU-Software-Abo", kategorie_id=kat.id, art="Ausgabe",
        brutto_betrag=Decimal("200.00"), ust_satz=Decimal("19"), vorsteuerabzug=True,
        ust_sonderfall="13b_abs1", zahlungsart="Bank",
    ), db)
    storno_eintrag(eintrag.id, StornoRequest(grund="Testkorrektur"), db)


def test_eu_dienstleistung_erscheint_als_sonstige_leistung(db):
    _eu_dienstleistung(db)
    ergebnis = zm_berechnen("2026-Q2", db=db)
    assert [(p.ust_idnr, p.land, p.kennzeichen, p.betrag) for p in ergebnis.positionen] == [
        ("FR40303265045", "FR", "S", Decimal("1000.00")),
    ]
    assert _hat_ig_eintraege_gesamt(db)


def test_zm_summe_entspricht_ustva_kz21(db):
    _eu_dienstleistung(db)
    kz, _ = _berechne_kz(date(2026, 4, 1), date(2026, 6, 30), db)
    assert zm_berechnen("2026-Q2", db=db).gesamt == kz["kz_21"]


def test_stornierter_13b_einkauf_ist_keine_zm_position(db):
    _stornierter_13b_einkauf(db)
    assert zm_berechnen("2026-Q2", db=db).positionen == []
    assert not _hat_ig_eintraege_gesamt(db)


def test_szenario_aus_issue(db):
    _eu_dienstleistung(db)
    _stornierter_13b_einkauf(db)
    positionen = zm_berechnen("2026-Q2", db=db).positionen
    assert len(positionen) == 1
    assert positionen[0].ust_idnr == "FR40303265045"
    assert positionen[0].kennzeichen == "S"


# ---------------------------------------------------------------------------
# Issue #458: ig. Lieferungen aus Rechnungen fehlten in UStVA KZ 41
# ---------------------------------------------------------------------------

def _ig_lieferung(db, mit_kategorie: bool, netto="2000.00") -> int:
    kat_id = None
    if mit_kategorie:
        kat = Kategorie(name="Innergemeinschaftliche Lieferungen", kontenart="Erlös",
                        konto_skr03="8125", konto_skr04="3125", ust_satz_standard=0)
        db.add(kat)
        db.commit()
        kat_id = kat.id
    kunde = db.query(Kunde).first()
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 8, 1), kunde_id=kunde.id, ist_eu_lieferung=True,
        positionen=[RechnungspositionCreate(beschreibung="Ware", netto=Decimal(netto), ust_satz=Decimal("0"),
                                            kategorie_id=kat_id)],
    ), db)
    finalisiere_rechnung(resp.id, db)
    zahlung_bar_erstellen(resp.id, BarZahlungCreate(datum=date(2026, 8, 20), zahlungsart="Bank"), db)
    return resp.id


@pytest.mark.parametrize("mit_kategorie", [True, False])
def test_ig_lieferung_aus_rechnung_in_kz41_und_zm(db, mit_kategorie):
    _ig_lieferung(db, mit_kategorie)
    kz, posten = _berechne_kz(date(2026, 7, 1), date(2026, 9, 30), db)
    assert kz["kz_41"] == Decimal("2000.00")
    assert kz["kz_81"] == Decimal("0.00")
    assert len(posten["kz_41"]) == 1
    zm = zm_berechnen("2026-Q3", db=db)
    assert [(p.ust_idnr, p.kennzeichen, p.betrag) for p in zm.positionen] == [
        ("FR40303265045", "L", Decimal("2000.00")),
    ]
    assert zm.gesamt == kz["kz_41"]


@pytest.mark.parametrize("mit_kategorie", [True, False])
def test_storno_ig_lieferung_hebt_kz41_und_zm_auf(db, mit_kategorie):
    rechnung_id = _ig_lieferung(db, mit_kategorie)
    storno_rechnung(rechnung_id, StornoRequest(grund="Testkorrektur"), db)
    kz, _ = _berechne_kz(date(2026, 7, 1), date(2026, 9, 30), db)
    assert kz["kz_41"] == Decimal("0.00")
    assert zm_berechnen("2026-Q3", db=db).positionen == []


def test_stornierte_eu_dienstleistung_hebt_sich_auf(db):
    rechnung_id = _eu_dienstleistung(db)
    storno_rechnung(rechnung_id, StornoRequest(grund="Testkorrektur"), db)
    assert zm_berechnen("2026-Q2", db=db).positionen == []


def test_zm_csv_export_mit_sonstiger_leistung(db):
    """Issue #456 + #360: Kennzeichen S aus zm_berechnen() muss im ELSTER-CSV ankommen."""
    from api.zm import zm_csv
    _eu_dienstleistung(db)
    antwort = zm_csv("2026-Q2", db=db)
    import asyncio
    async def _lesen():
        return b"".join([c async for c in antwort.body_iterator])
    inhalt = asyncio.run(_lesen()).decode("utf-8")
    assert "FR40303265045,1000,S" in inhalt.splitlines()


# ---------------------------------------------------------------------------
# Issue #457: Ausfuhrlieferungen in KZ 43 (nicht KZ 87)
# ---------------------------------------------------------------------------

def _ausfuhr(db, netto="1500.00") -> int:
    resp = create_rechnung(RechnungCreate(
        typ="ausgang", datum=date(2026, 8, 1), partner_freitext="Kunde AG, Schweiz", ist_ausfuhrlieferung=True,
        positionen=[RechnungspositionCreate(beschreibung="Ware", netto=Decimal(netto), ust_satz=Decimal("0"))],
    ), db)
    finalisiere_rechnung(resp.id, db)
    zahlung_bar_erstellen(resp.id, BarZahlungCreate(datum=date(2026, 8, 20), zahlungsart="Bank"), db)
    return resp.id


def test_ausfuhrlieferung_in_kz43(db):
    _ausfuhr(db)
    kz, posten = _berechne_kz(date(2026, 7, 1), date(2026, 9, 30), db)
    assert kz["kz_43"] == Decimal("1500.00")
    assert kz["kz_87"] == Decimal("0.00")
    assert kz["kz_41"] == Decimal("0.00")
    assert kz["kz_81"] == Decimal("0.00")
    assert len(posten["kz_43"]) == 1
    assert zm_berechnen("2026-Q3", db=db).positionen == []  # Drittland gehört nicht in die ZM


def test_storno_ausfuhrlieferung_hebt_kz43_auf(db):
    rechnung_id = _ausfuhr(db)
    storno_rechnung(rechnung_id, StornoRequest(grund="Testkorrektur"), db)
    kz, _ = _berechne_kz(date(2026, 7, 1), date(2026, 9, 30), db)
    assert kz["kz_43"] == Decimal("0.00")


def test_kz43_im_elster_xml_und_kz87_als_null_prozent():
    from api.ustva import KZ_META
    from utils.elster import KZ_BEMESSUNGSGRUNDLAGE
    meta = {nr: (bez, auto) for _, nr, bez, _, auto in KZ_META}
    assert "Ausfuhr" in meta["43"][0] and meta["43"][1] is True
    assert "0 %" in meta["87"][0] and "Ausfuhr" not in meta["87"][0] and meta["87"][1] is False
    assert "43" in KZ_BEMESSUNGSGRUNDLAGE
