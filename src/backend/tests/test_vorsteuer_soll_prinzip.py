"""
Vorsteuerabzug nach Soll-Prinzip (§15 UStG, Issue #338).

Vorsteuer ist rechtlich bereits mit Rechnungseingang (Leistungsbezug + ordnungsgemäße Rechnung)
abzugsfähig, unabhängig vom Zahlungsdatum. Vor diesem Feature wurde Vorsteuer ausschließlich beim
Bezahlen einer Eingangsrechnung gebucht (journal.vorsteuer_betrag, Zahlungsdatum) - eine
unbezahlte Eingangsrechnung hatte damit nirgendwo einen Vorsteuerbetrag.

Diese Tests prüfen die neue, unabhängige Quelle (vorsteuer_ansprueche, Rechnungsdatum) für
Eingangsrechnungen mit datum >= CUTOVER_DATUM - insbesondere, dass die Vorsteuer NIE doppelt
gezählt wird (weder bei Zahlung, noch bei Storno), und dass Rechnungen vor dem Cutover
unverändert auf dem alten Zahlungsdatum-Pfad bleiben.

CUTOVER_DATUM_VORSTEUER wird in allen Tests auf ein Datum in der Vergangenheit gepatcht (statt
des echten, in der Zukunft liegenden Konstanten-Werts), damit Testrechnungen mit für
finalisiere_rechnung() zulässigem Datum (nicht in der Zukunft) trotzdem als "post-Cutover"
gelten.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.rechnungen as rechnungen_api
import api.ustva as ustva_api
from api.rechnungen import finalisiere_rechnung, storno_rechnung, zahlung_bar_erstellen
from api.schemas_rechnungen import BarZahlungCreate
from api.schemas import StornoRequest
from database.connection import Base
from database.models import Kategorie, Rechnung, Rechnungsposition, Unternehmen, VorsteuerAnspruch

PAST_CUTOVER = date(2020, 1, 1)  # "Cutover" während der Tests - liegt sicher vor allen Testdaten


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(rechnungen_api, "CUTOVER_DATUM_VORSTEUER", PAST_CUTOVER)
    monkeypatch.setattr(ustva_api, "CUTOVER_DATUM_VORSTEUER", PAST_CUTOVER)
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _kategorie(db, name="Bürobedarf", skr03="4930", skr04="6815", vorsteuer_prozent=100) -> Kategorie:
    kat = Kategorie(
        name=name, kontenart="Aufwand", konto_skr03=skr03, konto_skr04=skr04,
        vorsteuer_prozent=vorsteuer_prozent, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    db.refresh(kat)
    return kat


def _eingangsrechnung_entwurf(db, datum: date, kategorie_id=None, satz=Decimal("19")) -> Rechnung:
    faktor = Decimal("1") + satz / 100
    netto = Decimal("100.00")
    ust = (netto * satz / 100).quantize(Decimal("0.01"))
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-1", datum=datum,
        brutto_gesamt=netto + ust, netto_gesamt=netto, ust_gesamt=ust,
        ist_entwurf=True, kategorie_id=kategorie_id,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung",
        menge=Decimal("1"), netto=netto, ust_satz=satz, ust_betrag=ust, brutto=netto + ust,
        kategorie_id=kategorie_id,
    ))
    db.commit()
    db.refresh(rechnung)
    return rechnung


# ---------------------------------------------------------------------------
# Kategorie-Pflicht ab Cutover
# ---------------------------------------------------------------------------

def test_finalisierung_ohne_kategorie_ab_cutover_wird_verweigert(db):
    rechnung = _eingangsrechnung_entwurf(db, date(2020, 1, 5))  # nach PAST_CUTOVER, keine Kategorie
    with pytest.raises(Exception) as exc_info:
        finalisiere_rechnung(rechnung.id, db)
    assert "422" in str(exc_info.value) or "Kategorie" in str(exc_info.value)


def test_finalisierung_vor_cutover_braucht_keine_kategorie(db):
    rechnung = _eingangsrechnung_entwurf(db, date(2019, 1, 5))  # vor PAST_CUTOVER
    finalisiere_rechnung(rechnung.id, db)  # darf nicht werfen
    db.refresh(rechnung)
    assert rechnung.ist_entwurf is False
    assert db.query(VorsteuerAnspruch).filter(VorsteuerAnspruch.rechnung_id == rechnung.id).count() == 0


# ---------------------------------------------------------------------------
# vorsteuer_ansprueche wird korrekt erzeugt
# ---------------------------------------------------------------------------

def test_finalisierung_erzeugt_vorsteuer_anspruch(db):
    kat = _kategorie(db)
    rechnung = _eingangsrechnung_entwurf(db, date(2020, 3, 15), kategorie_id=kat.id)
    finalisiere_rechnung(rechnung.id, db)

    ansprueche = db.query(VorsteuerAnspruch).filter(VorsteuerAnspruch.rechnung_id == rechnung.id).all()
    assert len(ansprueche) == 1
    va = ansprueche[0]
    assert va.datum == date(2020, 3, 15)
    assert va.typ == "anspruch"
    assert va.netto_betrag == Decimal("100.00")
    assert va.ust_betrag == Decimal("19.00")
    assert va.vorsteuer_betrag == Decimal("19.00")
    assert va.ust_sonderfall is None


def test_reduzierte_vorsteuerquote_wird_beruecksichtigt(db):
    kat = _kategorie(db, name="Bewirtungskosten", vorsteuer_prozent=70)
    rechnung = _eingangsrechnung_entwurf(db, date(2020, 3, 15), kategorie_id=kat.id)
    finalisiere_rechnung(rechnung.id, db)

    va = db.query(VorsteuerAnspruch).filter(VorsteuerAnspruch.rechnung_id == rechnung.id).first()
    assert va.ust_betrag == Decimal("19.00")
    assert va.vorsteuer_betrag == Decimal("13.30")  # 19.00 * 70%


def test_13b_kategorie_setzt_sonderfall_auf_anspruch(db):
    kat = _kategorie(db, name="EU-Dienstleistungen (§13b Abs. 1)", skr03="3123", skr04="5923")
    rechnung = _eingangsrechnung_entwurf(db, date(2020, 3, 15), kategorie_id=kat.id)
    finalisiere_rechnung(rechnung.id, db)

    va = db.query(VorsteuerAnspruch).filter(VorsteuerAnspruch.rechnung_id == rechnung.id).first()
    assert va.ust_sonderfall == "13b_abs1"
    assert va.konto_ust_skr03 == "1787"


# ---------------------------------------------------------------------------
# Kernänderung: Vorsteuer sichtbar auch ohne Zahlung
# ---------------------------------------------------------------------------

def test_unbezahlte_rechnung_erscheint_in_ustva(db):
    kat = _kategorie(db)
    rechnung = _eingangsrechnung_entwurf(db, date(2020, 3, 15), kategorie_id=kat.id)
    finalisiere_rechnung(rechnung.id, db)
    # bewusst NICHT bezahlt

    kz = ustva_api._berechne_kz(date(2020, 3, 1), date(2020, 3, 31), db)
    assert kz["kz_66"] == Decimal("19.00")


# ---------------------------------------------------------------------------
# Wichtigster Regressionstest: keine Doppelzählung bei späterer Zahlung
# ---------------------------------------------------------------------------

def test_keine_doppelzaehlung_bei_zahlung_in_spaeterer_periode(db):
    kat = _kategorie(db)
    rechnung = _eingangsrechnung_entwurf(db, date(2020, 3, 15), kategorie_id=kat.id)
    finalisiere_rechnung(rechnung.id, db)

    zahlung_bar_erstellen(
        rechnung.id,
        BarZahlungCreate(datum=date(2020, 5, 20), zahlungsart="Bank", kategorie_id=kat.id),
        db,
    )

    kz_maerz = ustva_api._berechne_kz(date(2020, 3, 1), date(2020, 3, 31), db)
    kz_mai = ustva_api._berechne_kz(date(2020, 5, 1), date(2020, 5, 31), db)

    assert kz_maerz["kz_66"] == Decimal("19.00"), "Vorsteuer muss in der Rechnungsdatum-Periode stehen"
    assert kz_mai["kz_66"] == Decimal("0.00"), "Vorsteuer darf in der Zahlungsperiode NICHT nochmal auftauchen"


def test_rechnung_vor_cutover_bleibt_auf_zahlungsdatum_pfad(db):
    kat = _kategorie(db)
    rechnung = _eingangsrechnung_entwurf(db, date(2019, 3, 15), kategorie_id=kat.id)
    finalisiere_rechnung(rechnung.id, db)  # vor Cutover, keine vorsteuer_ansprueche-Zeile

    zahlung_bar_erstellen(
        rechnung.id,
        BarZahlungCreate(datum=date(2020, 5, 20), zahlungsart="Bank", kategorie_id=kat.id),
        db,
    )

    kz_maerz = ustva_api._berechne_kz(date(2019, 3, 1), date(2019, 3, 31), db)
    kz_mai = ustva_api._berechne_kz(date(2020, 5, 1), date(2020, 5, 31), db)

    assert kz_maerz["kz_66"] == Decimal("0.00"), "vor Cutover: keine Vorsteuer zum Rechnungsdatum"
    assert kz_mai["kz_66"] == Decimal("19.00"), "vor Cutover: Vorsteuer weiterhin zum Zahlungsdatum"


# ---------------------------------------------------------------------------
# Storno: Korrektur in der aktuellen Periode, nicht rückwirkend
# ---------------------------------------------------------------------------

def test_storno_unbezahlter_rechnung_korrigiert_in_aktueller_periode(db, monkeypatch):
    kat = _kategorie(db)
    rechnung = _eingangsrechnung_entwurf(db, date(2020, 3, 15), kategorie_id=kat.id)
    finalisiere_rechnung(rechnung.id, db)

    storno_rechnung(rechnung.id, StornoRequest(grund="Testkorrektur"), db)

    korrekturen = db.query(VorsteuerAnspruch).filter(
        VorsteuerAnspruch.rechnung_id == rechnung.id, VorsteuerAnspruch.typ == "korrektur",
    ).all()
    assert len(korrekturen) == 1
    assert korrekturen[0].datum == date.today(), "Korrektur muss auf heute datiert sein, nicht rechnung.datum"
    assert korrekturen[0].vorsteuer_betrag == Decimal("-19.00")

    kz_maerz = ustva_api._berechne_kz(date(2020, 3, 1), date(2020, 3, 31), db)
    assert kz_maerz["kz_66"] == Decimal("19.00"), "März (Rechnungsdatum-Periode) bleibt unveraendert"

    kz_heute = ustva_api._berechne_kz(date.today().replace(day=1), date.today(), db)
    assert kz_heute["kz_66"] == Decimal("-19.00"), "Korrektur zaehlt in der aktuellen Periode"


# ---------------------------------------------------------------------------
# Gemischte USt-Sätze
# ---------------------------------------------------------------------------

def test_gemischte_ust_saetze_erzeugen_getrennte_anspruch_zeilen(db):
    kat = _kategorie(db)
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-2", datum=date(2020, 3, 15),
        brutto_gesamt=Decimal("226.00"), netto_gesamt=Decimal("200.00"), ust_gesamt=Decimal("26.00"),
        ist_entwurf=True, kategorie_id=kat.id,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Ware 19%",
        menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19"),
        ust_betrag=Decimal("19.00"), brutto=Decimal("119.00"), kategorie_id=kat.id,
    ))
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=2, beschreibung="Ware 7%",
        menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("7"),
        ust_betrag=Decimal("7.00"), brutto=Decimal("107.00"), kategorie_id=kat.id,
    ))
    db.commit()
    db.refresh(rechnung)

    finalisiere_rechnung(rechnung.id, db)

    ansprueche = db.query(VorsteuerAnspruch).filter(VorsteuerAnspruch.rechnung_id == rechnung.id).all()
    assert len(ansprueche) == 2
    saetze = sorted(a.ust_satz for a in ansprueche)
    assert saetze == [Decimal("7.00"), Decimal("19.00")]

    kz = ustva_api._berechne_kz(date(2020, 3, 1), date(2020, 3, 31), db)
    assert kz["kz_66"] == Decimal("26.00")


# ---------------------------------------------------------------------------
# EÜR bleibt unberührt (weiterhin zahlungsdatumsbasiert, auch ab Cutover)
# ---------------------------------------------------------------------------

def test_euer_bleibt_zahlungsdatumsbasiert_auch_ab_cutover(db):
    from api.euer import _berechne_euer

    kat = _kategorie(db)
    rechnung = _eingangsrechnung_entwurf(db, date(2020, 3, 15), kategorie_id=kat.id)
    finalisiere_rechnung(rechnung.id, db)
    zahlung_bar_erstellen(
        rechnung.id,
        BarZahlungCreate(datum=date(2020, 5, 20), zahlungsart="Bank", kategorie_id=kat.id),
        db,
    )

    # Zeile 57 = abziehbare Vorsteuer - muss weiterhin aus dem Zahlungs-Journaleintrag stammen,
    # unveraendert durch Issue #338 (EÜR folgt zurecht dem Zufluss-/Abflussprinzip §11 EStG).
    euer = _berechne_euer(2020, db)
    assert euer["zeilen"].get(57, Decimal("0")) == Decimal("19.00")
