"""
Issue #375: §13b-Eingangsrechnungen wurden in der UStVA nicht korrekt ausgewertet.

Drei Bugs gefunden und hier abgedeckt:
1. "Drittland-Dienstleistungen" (Konto 3125/5925) lief im selben Konto-Zweig wie
   "EU-Dienstleistungen" (3123/5923) mit -> immer sonderfall="13b_abs1" (KZ 46/47) statt
   korrekt "13b_abs2" (KZ 84/85). §13b Abs. 1 gilt nur fuer EU-Lieferanten.
2. Die Erkennung haengt ausschliesslich am AKTUELLEN SKR-Konto der Kategorie - aendert eine
   Nutzerin das Konto (user_modified_skr03/04, ein unterstuetztes Feature), bricht die gesamte
   Sonderfall-Behandlung lautlos weg. Fix: neues persistentes Feld kategorien.ust_sonderfall
   als Quelle der Wahrheit, Konto-Heuristik nur noch Fallback.
3. api/bank_import.py::_buche_pfad_a() hatte GAR KEINE Kategorie-basierte Sonderfall-Erkennung
   fuer Eingangsrechnungen (nur ein Ausgangsrechnungs-Flag-Check) - eine per Bank-Import
   automatisch verbuchte §13b-Eingangsrechnung bekam nie die additive Netto/USt-Aufteilung
   und nie eine UStVA-Kennziffer.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import _buche_pfad_a
from api.rechnungen import _klassifiziere_sonderfall, finalisiere_rechnung, storno_rechnung, zahlung_bar_erstellen
from api.schemas import StornoRequest
from api.schemas_rechnungen import BarZahlungCreate
from database.connection import Base
from database.models import (
    BankImport, BankTemplate, BankTransaktion, Journaleintrag, Kategorie, Konto,
    Rechnung, Rechnungsposition, Unternehmen,
)


@pytest.fixture
def db(monkeypatch):
    import api.rechnungen as rechnungen_api
    import api.ustva as ustva_api
    monkeypatch.setattr(rechnungen_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    monkeypatch.setattr(ustva_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def _kategorie(db, name, konto_skr03, konto_skr04, ust_sonderfall) -> Kategorie:
    kat = Kategorie(
        name=name, kontenart="Aufwand", konto_skr03=konto_skr03, konto_skr04=konto_skr04,
        vorsteuer_prozent=100, ust_satz_standard=19, ust_sonderfall=ust_sonderfall,
    )
    db.add(kat)
    db.commit()
    db.refresh(kat)
    return kat


def _eingangsrechnung_finalisiert(db, kategorie_id, datum=date(2026, 1, 10)) -> Rechnung:
    netto, ust = Decimal("100.00"), Decimal("19.00")
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer=None, datum=datum,
        brutto_gesamt=netto + ust, netto_gesamt=netto, ust_gesamt=ust,
        ist_entwurf=True, kategorie_id=kategorie_id,
    )
    db.add(rechnung)
    db.commit()
    db.refresh(rechnung)
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"), einheit="Stk.",
        netto=netto, ust_satz=Decimal("19"), ust_betrag=ust, brutto=netto + ust, kategorie_id=kategorie_id,
    ))
    db.commit()
    finalisiere_rechnung(rechnung.id, db)
    db.refresh(rechnung)
    return rechnung


def test_eu_dienstleistung_erscheint_in_kz46_47_67(db):
    kat = _kategorie(db, "EU-Dienstleistungen (§13b Abs. 1)", "3123", "5923", "13b_abs1")
    _eingangsrechnung_finalisiert(db, kat.id)

    from api.ustva import _berechne_kz
    kz, _ = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)

    assert kz["kz_46"] == Decimal("100.00")
    assert kz["kz_47"] == Decimal("19.00")
    assert kz["kz_67"] == Decimal("19.00")
    assert kz["kz_66"] == Decimal("0.00")
    assert kz["kz_84"] == Decimal("0.00")
    assert kz["kz_85"] == Decimal("0.00")


def test_drittland_dienstleistung_erscheint_in_kz84_85_67_nicht_46_47(db):
    """Kernregression fuer Bug 1: Drittland darf NICHT in KZ 46/47 landen."""
    kat = _kategorie(db, "Drittland-Dienstleistungen (§13b Abs. 2)", "3125", "5925", "13b_abs2")
    _eingangsrechnung_finalisiert(db, kat.id)

    from api.ustva import _berechne_kz
    kz, _ = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)

    assert kz["kz_84"] == Decimal("100.00")
    assert kz["kz_85"] == Decimal("19.00")
    assert kz["kz_67"] == Decimal("19.00")
    assert kz["kz_46"] == Decimal("0.00")
    assert kz["kz_47"] == Decimal("0.00")
    assert kz["kz_66"] == Decimal("0.00")


def test_normale_eingangsrechnung_bleibt_in_kz66(db):
    """Regressionsschutz: eine normale Eingangsrechnung ohne Sonderfall darf unveraendert
    in KZ 66 erscheinen."""
    kat = _kategorie(db, "Bürobedarf", "4930", "6815", None)
    _eingangsrechnung_finalisiert(db, kat.id)

    from api.ustva import _berechne_kz
    kz, _ = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)

    assert kz["kz_66"] == Decimal("19.00")
    assert kz["kz_46"] == Decimal("0.00")
    assert kz["kz_84"] == Decimal("0.00")


def test_storno_hebt_kz84_85_67_wieder_auf(db):
    """Die Storno-Korrektur des Vorsteuer-Anspruchs wird auf HEUTE datiert (§17 Abs. 1 Satz 2
    UStG: Berichtigung im Zeitraum der Aenderung, nicht rueckwirkend, siehe storno_rechnung())
    - Fenster muss daher bis heute reichen, damit Original UND Korrektur erfasst werden."""
    kat = _kategorie(db, "Drittland-Dienstleistungen (§13b Abs. 2)", "3125", "5925", "13b_abs2")
    rechnung = _eingangsrechnung_finalisiert(db, kat.id)
    zahlung_bar_erstellen(rechnung.id, BarZahlungCreate(datum=date(2026, 1, 15), zahlungsart="Bank"), db)
    storno_rechnung(rechnung.id, StornoRequest(grund="Testkorrektur"), db)

    from api.ustva import _berechne_kz
    kz, _ = _berechne_kz(date(2026, 1, 1), date.today(), db)

    assert kz["kz_84"] == Decimal("0.00")
    assert kz["kz_85"] == Decimal("0.00")
    assert kz["kz_67"] == Decimal("0.00")


def test_klassifizierung_robust_gegen_kontoanpassung(db):
    """Bug 2: eine Kategorie mit persistiertem ust_sonderfall bleibt korrekt klassifiziert,
    auch wenn ihr SKR-Konto (z.B. per user_modified_skr03/04) auf ein neutrales Konto
    geaendert wurde - genau das war vorher nicht der Fall (reine Konto-Heuristik)."""
    kat = Kategorie(
        name="Drittland-Dienstleistungen (§13b Abs. 2) - angepasst", kontenart="Aufwand",
        konto_skr03="4930", konto_skr04="6815",  # neutrales Buerobedarf-Konto statt 3125/5925
        user_modified_skr03=True, user_modified_skr04=True,
        vorsteuer_prozent=100, ust_satz_standard=19, ust_sonderfall="13b_abs2",
    )
    sonderfall, _, _ = _klassifiziere_sonderfall(kat, False, Decimal("19"), None, None)
    assert sonderfall == "13b_abs2"


def test_bank_import_klassifiziert_drittland_eingangsrechnung_korrekt(db, monkeypatch):
    """Bug 3: bank_import.py hatte fuer Eingangsrechnungen GAR KEINE Kategorie-basierte
    Sonderfall-Erkennung - eine per Bank-Import automatisch verbuchte §13b-Eingangsrechnung
    bekam weder die additive Netto/USt-Aufteilung noch eine UStVA-Kennziffer.

    Diese Rechnung wird direkt konstruiert (ohne finalisiere_rechnung()), es entsteht also kein
    vorsteuer_ansprueche-Eintrag - die KZ-Pruefung braucht daher den JOURNAL-basierten Pfad
    (vor CUTOVER_DATUM_VORSTEUER), unabhaengig vom Fixture-weiten Cutover-Override auf 2020."""
    import api.ustva as ustva_api
    monkeypatch.setattr(ustva_api, "CUTOVER_DATUM_VORSTEUER", date(2030, 1, 1))
    kat = _kategorie(db, "Drittland-Dienstleistungen (§13b Abs. 2)", "3125", "5925", "13b_abs2")
    konto = Konto(name="Testkonto", anbieter="Testbank")
    db.add(konto)
    db.flush()
    tmpl = BankTemplate(id="test-tmpl", name="Test", bank="Testbank", format="Standard", column_mapping="{}")
    db.add(tmpl)
    db.flush()
    imp = BankImport(konto_id=konto.id, template_id=tmpl.id, dateiname="test.csv")
    db.add(imp)
    db.commit()

    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-375", datum=date(2026, 1, 1),
        brutto_gesamt=Decimal("128.38"), netto_gesamt=Decimal("128.38"),
        ist_entwurf=False, kategorie_id=kat.id,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Anthropic API",
        kategorie_id=kat.id, menge=Decimal("1"), netto=Decimal("128.38"),
        ust_satz=Decimal("19"), ust_betrag=Decimal("24.39"), brutto=Decimal("128.38"),
    ))
    db.commit()
    db.refresh(rechnung)

    tx = BankTransaktion(
        konto_id=konto.id, import_id=imp.id, datum=date(2026, 1, 5), betrag=Decimal("-128.38"),
        verwendungszweck="Anthropic API",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    eintrag, _ = _buche_pfad_a(db, tx, rechnung)
    db.commit()
    db.refresh(eintrag)

    assert eintrag.ust_sonderfall == "13b_abs2"
    # Reverse Charge: additive Aufteilung (Zahlbetrag = Netto), nicht Herausrechnung.
    assert eintrag.netto_betrag == Decimal("128.38")
    assert eintrag.ust_betrag == Decimal("24.39")
    assert eintrag.vorsteuer_betrag == Decimal("24.39")

    from api.ustva import _berechne_kz
    kz, _ = _berechne_kz(date(2026, 1, 1), date(2026, 1, 31), db)
    assert kz["kz_84"] == Decimal("128.38")
    assert kz["kz_85"] == Decimal("24.39")
    assert kz["kz_67"] == Decimal("24.39")
    assert kz["kz_46"] == Decimal("0.00")
    assert kz["kz_66"] == Decimal("0.00")


def test_bank_import_ausgangsrechnung_reverse_charge_bekommt_keinen_13b_sonderfall(db):
    """Regressionsschutz zu #372: eine Ausgangsrechnung mit ist_reverse_charge=True darf bei
    Bank-Import-Zahlung weiterhin NICHT als §13b-Eingangsfall (Empfaenger schuldet USt)
    behandelt werden - das ist ein reiner Ausgangsrechnungs-Hinweis fuer KZ 21/45
    (nicht steuerbare Auslands-Dienstleistung), siehe _berechne_kz()."""
    konto = Konto(name="Testkonto", anbieter="Testbank")
    db.add(konto)
    db.flush()
    tmpl = BankTemplate(id="test-tmpl", name="Test", bank="Testbank", format="Standard", column_mapping="{}")
    db.add(tmpl)
    db.flush()
    imp = BankImport(konto_id=konto.id, template_id=tmpl.id, dateiname="test.csv")
    db.add(imp)
    db.commit()

    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-375", datum=date(2026, 1, 1),
        brutto_gesamt=Decimal("1000.00"), netto_gesamt=Decimal("1000.00"), ust_gesamt=Decimal("0.00"),
        ist_entwurf=False, ist_reverse_charge=True, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung EU-Kunde",
        menge=Decimal("1"), netto=Decimal("1000.00"), ust_satz=Decimal("0"),
        ust_betrag=Decimal("0.00"), brutto=Decimal("1000.00"),
    ))
    db.commit()
    db.refresh(rechnung)

    tx = BankTransaktion(
        konto_id=konto.id, import_id=imp.id, datum=date(2026, 1, 5), betrag=Decimal("1000.00"),
        verwendungszweck="Beratung EU-Kunde",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    eintrag, _ = _buche_pfad_a(db, tx, rechnung)
    db.commit()
    db.refresh(eintrag)

    assert eintrag.ust_sonderfall is None
