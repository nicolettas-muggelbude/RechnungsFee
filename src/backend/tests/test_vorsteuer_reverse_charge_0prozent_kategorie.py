"""
Regressionstest Issue #339: Reverse Charge (§13b/ig. Erwerb) auf einer Kategorie mit
vorsteuer_prozent=0 verwarf den Vorsteuerabzug stillschweigend.

Bug: _berechne_vorsteuer() multiplizierte kat.vorsteuer_prozent auch dann noch auf den
USt-Betrag, wenn der Sonderfall (ust_sonderfall) bereits gesetzt war. kat.vorsteuer_prozent=0
beschreibt aber nur den inländischen Normalfall der Ausgabenart (z.B. Bankgebühren, §4 Nr. 8
UStG steuerfrei) - beim Reverse Charge greift §15 Abs. 1 Nr. 3/4 UStG unabhängig davon, die
selbst geschuldete USt ist in voller Höhe als Vorsteuer abziehbar.

Betroffen waren alle vier Aufrufer der (in journal.py und rechnungen.py duplizierten)
Funktion: freie Journal-Ausgabe, Journal-Splitbuchung, Eingangsrechnung-Zahlung und der
neue Vorsteuer-Anspruch bei Finalisierung (Issue #338, vorsteuer_ansprueche-Tabelle).
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import _buche_pfad_a
from api.journal import create_eintrag
from api.rechnungen import zahlung_bar_erstellen, finalisiere_rechnung
from api.schemas import JournalEintragCreate
from api.schemas_rechnungen import BarZahlungCreate
from database.connection import Base
from database.models import (
    BankImport, BankTemplate, BankTransaktion, Journaleintrag, Kategorie, Konto,
    Rechnung, Rechnungsposition, Unternehmen, VorsteuerAnspruch,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _bankgebuehren_kategorie(db) -> Kategorie:
    """Nachgebaut aus dem Issue: inländisch steuerfreie Kategorie (§4 Nr. 8 UStG),
    vorsteuer_prozent=0 - korrekt für den Normalfall, nicht für Reverse Charge."""
    kat = Kategorie(
        name="Bankgebühren", kontenart="Aufwand",
        konto_skr03="4970", konto_skr04="6855", vorsteuer_prozent=0, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    return kat


def test_journal_ausgabe_13b_mit_0prozent_kategorie_erhaelt_vollen_vorsteuerabzug(db):
    """Exakter Repro-Fall aus Issue #339: Finom-Kontoführungsgebühr, §13b Abs. 1."""
    kat = _bankgebuehren_kategorie(db)

    create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 1, 5), beschreibung="Finom Kontoführung",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("128.38"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, ust_sonderfall="13b_abs1",
            zahlungsart="Bank",
        ),
        db,
    )

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.beschreibung == "Finom Kontoführung").first()
    assert eintrag.ust_betrag == Decimal("24.39")
    assert eintrag.vorsteuer_betrag == Decimal("24.39")


def test_journal_ausgabe_0prozent_kategorie_ohne_sonderfall_bleibt_ohne_vorsteuer(db):
    """Regression: der Normalfall (keine Reverse-Charge-Kennzeichnung) darf sich nicht ändern."""
    kat = _bankgebuehren_kategorie(db)

    create_eintrag(
        JournalEintragCreate(
            datum=date(2026, 1, 5), beschreibung="Inländische Kontoführung",
            kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal("10.00"),
            ust_satz=Decimal("19"), vorsteuerabzug=True, zahlungsart="Bank",
        ),
        db,
    )

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.beschreibung == "Inländische Kontoführung").first()
    assert eintrag.vorsteuer_betrag == Decimal("0.00")


def _eingangsrechnung_mit_0prozent_kategorie(db, kat: Kategorie) -> Rechnung:
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-1", datum=date(2026, 1, 1),
        brutto_gesamt=Decimal("128.38"), netto_gesamt=Decimal("128.38"),
        ist_entwurf=False, kategorie_id=kat.id,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Kontoführung Finom",
        kategorie_id=kat.id, menge=Decimal("1"), netto=Decimal("128.38"),
        ust_satz=Decimal("19"), ust_betrag=Decimal("24.39"), brutto=Decimal("128.38"),
    ))
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_eingangsrechnung_zahlung_13b_mit_0prozent_kategorie_erhaelt_vollen_vorsteuerabzug(db):
    kat = Kategorie(
        name="EU-Dienstleistungen (§13b Abs. 1) - Sonderfall-Test", kontenart="Aufwand",
        konto_skr03="3123", konto_skr04="5923", vorsteuer_prozent=0, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    rechnung = _eingangsrechnung_mit_0prozent_kategorie(db, kat)

    zahlung_bar_erstellen(
        rechnung.id,
        BarZahlungCreate(datum=date(2026, 1, 5), zahlungsart="Bank", kategorie_id=kat.id),
        db,
    )

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).first()
    assert eintrag is not None
    assert eintrag.ust_sonderfall == "13b_abs1"
    # Reverse Charge: der Zahlbetrag IST bereits der Nettobetrag (kein ausländischer
    # Lieferant weist deutsche USt aus) - USt wird additiv aufgeschlagen, nicht aus dem
    # Zahlbetrag herausgerechnet (Issue #339-Folgefund in _erstelle_eintrag()).
    assert eintrag.netto_betrag == Decimal("128.38")
    assert eintrag.ust_betrag == Decimal("24.39")
    # Vorsteuer muss dem vollen USt-Betrag entsprechen (nicht 0), unabhängig vom
    # 0%-Vorsteuerprozentsatz der Kategorie - das ist der eigentliche Fix von #339.
    assert eintrag.vorsteuer_betrag == Decimal("24.39")


def test_eingangsrechnung_zahlung_normale_kategorie_bleibt_brutto_inklusive_split(db):
    """Regression: eine normale (nicht-Reverse-Charge) Eingangsrechnung bleibt beim bisherigen
    Verhalten - der Zahlbetrag ist brutto (inkl. USt) und wird weiterhin herausgerechnet."""
    kat = Kategorie(
        name="Bürobedarf - Split-Regressionstest", kontenart="Aufwand",
        konto_skr03="4930", konto_skr04="6815", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-2", datum=date(2026, 1, 1),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"),
        ist_entwurf=False, kategorie_id=kat.id,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Bürobedarf",
        kategorie_id=kat.id, menge=Decimal("1"), netto=Decimal("100.00"),
        ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"), brutto=Decimal("119.00"),
    ))
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.commit()
    db.refresh(rechnung)

    zahlung_bar_erstellen(
        rechnung.id,
        BarZahlungCreate(datum=date(2026, 1, 5), zahlungsart="Bank", kategorie_id=kat.id),
        db,
    )

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).first()
    assert eintrag is not None
    assert eintrag.ust_sonderfall is None
    assert eintrag.netto_betrag == Decimal("100.00")
    assert eintrag.ust_betrag == Decimal("19.00")
    assert eintrag.vorsteuer_betrag == Decimal("19.00")


def test_vorsteuer_anspruch_bei_finalisierung_13b_mit_0prozent_kategorie(db, monkeypatch):
    """Issue #338-Pfad (Soll-Prinzip): derselbe Bug steckte in _erzeuge_vorsteuer_ansprueche()."""
    import api.rechnungen as rechnungen_api
    monkeypatch.setattr(rechnungen_api, "CUTOVER_DATUM_VORSTEUER", date(2020, 1, 1))

    kat = Kategorie(
        name="EU-Dienstleistungen (§13b Abs. 1) - Finalisierung-Test", kontenart="Aufwand",
        konto_skr03="3123", konto_skr04="5923", vorsteuer_prozent=0, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    rechnung = _eingangsrechnung_mit_0prozent_kategorie(db, kat)
    rechnung.ist_entwurf = True
    db.commit()

    finalisiere_rechnung(rechnung.id, db)

    anspruch = db.query(VorsteuerAnspruch).filter(VorsteuerAnspruch.rechnung_id == rechnung.id).first()
    assert anspruch is not None
    assert anspruch.ust_sonderfall == "13b_abs1"
    assert anspruch.vorsteuer_betrag == Decimal("24.39")


def test_bank_import_reverse_charge_erhaelt_additive_ust_statt_herausrechnung(db):
    """Issue #339-Folgefund: bank_import.py._buche_pfad_a() hat eine eigene, von
    rechnungen.py._erstelle_eintrag() unabhaengige Kopie derselben Netto/USt-Split-Logik -
    hatte denselben Fehler (Zahlbetrag faelschlich als brutto-inklusive behandelt)."""
    kat = Kategorie(
        name="EU-Dienstleistungen (§13b Abs. 1) - Bank-Import-Test", kontenart="Aufwand",
        konto_skr03="3123", konto_skr04="5923", vorsteuer_prozent=0, ust_satz_standard=19,
    )
    db.add(kat)
    konto = Konto(name="Testkonto", anbieter="Testbank")
    db.add(konto)
    db.flush()
    tmpl = BankTemplate(id="test-tmpl", name="Test", bank="Testbank", format="Standard", column_mapping="{}")
    db.add(tmpl)
    db.flush()
    imp = BankImport(konto_id=konto.id, template_id=tmpl.id, dateiname="test.csv")
    db.add(imp)
    db.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    db.commit()

    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-3", datum=date(2026, 1, 1),
        brutto_gesamt=Decimal("128.38"), netto_gesamt=Decimal("128.38"),
        ist_entwurf=False, kategorie_id=kat.id, ist_reverse_charge=True,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Kontoführung Finom",
        kategorie_id=kat.id, menge=Decimal("1"), netto=Decimal("128.38"),
        ust_satz=Decimal("19"), ust_betrag=Decimal("24.39"), brutto=Decimal("128.38"),
    ))
    db.commit()
    db.refresh(rechnung)

    tx = BankTransaktion(
        konto_id=konto.id, import_id=imp.id, datum=date(2026, 1, 5), betrag=Decimal("-128.38"),
        verwendungszweck="Finom Kontoführung",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    eintrag, _ = _buche_pfad_a(db, tx, rechnung)
    db.commit()
    db.refresh(eintrag)

    assert eintrag.ust_sonderfall == "13b_abs1"
    assert eintrag.netto_betrag == Decimal("128.38")
    assert eintrag.ust_betrag == Decimal("24.39")
    assert eintrag.vorsteuer_betrag == Decimal("24.39")
