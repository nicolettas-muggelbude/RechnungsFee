"""
Regressionstests für Issue #364 (Lieferantengutschrift) - Bank-Import-Teil.

Deckt zwei Richtungen ab:
1. Eine positive Banktransaktion (Erstattung vom Lieferanten) muss eine offene Eingangs-
   Gutschrift finden und korrekt negativ verbuchen (neu).
2. Eine negative Banktransaktion (Erstattung an den Kunden) muss eine offene Ausgangs-
   Gutschrift finden - das war laut Recherche vermutlich schon VOR dieser Änderung defekt
   (nie gemeldet, da via Bar-Zahlungsdialog nie aufgefallen) und wird hier als Nebenbefund
   mitbehoben/gegengetestet.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.bank_import import _buche_pfad_a, _offene_rechnungen_fuer_tx, auto_buchen
from api.rechnungen import create_gutschrift, finalisiere_rechnung
from database.connection import Base
from database.models import (
    BankImport, BankTemplate, BankTransaktion, Forderung, Journaleintrag, Kategorie, Konto,
    Rechnung, Rechnungsposition, Unternehmen,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    konto = Konto(name="Testkonto", anbieter="Testbank")
    session.add(konto)
    session.flush()
    tmpl = BankTemplate(id="test-tmpl", name="Test", bank="Testbank", format="Standard", column_mapping="{}")
    session.add(tmpl)
    session.flush()
    imp = BankImport(konto_id=konto.id, template_id=tmpl.id, dateiname="test.csv")
    session.add(imp)
    session.commit()
    session.konto_id = konto.id
    session.import_id = imp.id
    yield session
    session.close()


def _tx(db, betrag: str, datum=date(2026, 3, 5)) -> BankTransaktion:
    tx = BankTransaktion(konto_id=db.konto_id, import_id=db.import_id, datum=datum, betrag=Decimal(betrag))
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def _eingangsrechnung_mit_gutschrift(db) -> Rechnung:
    kat = Kategorie(
        name="Bürobedarf", kontenart="Aufwand", konto_skr03="4930", konto_skr04="6815",
        vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-2026-1", datum=date(2026, 3, 1),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"), kategorie_id=kat.id,
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Büromaterial", menge=Decimal("1"),
        einheit="Stk.", netto=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto=Decimal("119.00"), kategorie_id=kat.id,
    ))
    db.commit()
    db.refresh(rechnung)
    resp = create_gutschrift(rechnung.id, db)
    finalisiere_rechnung(resp.id, db)
    return db.query(Rechnung).filter(Rechnung.id == resp.id).first()


def _ausgangsrechnung_mit_gutschrift(db) -> Rechnung:
    kat = Kategorie(
        name="Betriebseinnahmen", kontenart="Erlös", konto_skr03="8400", konto_skr04="4400",
        vorsteuer_prozent=0, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-1", datum=date(2026, 3, 1),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"),
        einheit="Stk.", netto=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto=Decimal("119.00"), kategorie_id=kat.id,
    ))
    db.commit()
    db.refresh(rechnung)
    resp = create_gutschrift(rechnung.id, db)
    finalisiere_rechnung(resp.id, db)
    return db.query(Rechnung).filter(Rechnung.id == resp.id).first()


def test_positive_tx_findet_offene_eingangs_gutschrift(db):
    gutschrift = _eingangsrechnung_mit_gutschrift(db)
    tx = _tx(db, "119.00")

    kandidaten = _offene_rechnungen_fuer_tx(db, tx)
    assert gutschrift.id in {r.id for r in kandidaten}


def test_negative_tx_findet_offene_ausgangs_gutschrift(db):
    """Nebenbefund: war vor Issue #364 vermutlich bereits kaputt (nie gemeldet)."""
    gutschrift = _ausgangsrechnung_mit_gutschrift(db)
    tx = _tx(db, "-119.00")

    kandidaten = _offene_rechnungen_fuer_tx(db, tx)
    assert gutschrift.id in {r.id for r in kandidaten}


def test_buche_pfad_a_eingangs_gutschrift_bucht_negative_ausgabe(db):
    gutschrift = _eingangsrechnung_mit_gutschrift(db)
    tx = _tx(db, "119.00")

    eintrag, forderung = _buche_pfad_a(db, tx, gutschrift)
    db.commit()
    db.refresh(eintrag)

    assert eintrag.art == "Ausgabe"
    assert eintrag.brutto_betrag == Decimal("-119.00")
    assert eintrag.netto_betrag == Decimal("-100.00")
    assert eintrag.ust_betrag == Decimal("-19.00")
    assert eintrag.vorsteuer_betrag == Decimal("-19.00")
    assert eintrag.kategorie_id is not None
    assert forderung is None


def test_buche_pfad_a_ausgangs_gutschrift_bucht_negative_einnahme(db):
    gutschrift = _ausgangsrechnung_mit_gutschrift(db)
    tx = _tx(db, "-119.00")

    eintrag, forderung = _buche_pfad_a(db, tx, gutschrift)
    db.commit()
    db.refresh(eintrag)

    assert eintrag.art == "Einnahme"
    assert eintrag.brutto_betrag == Decimal("-119.00")
    assert eintrag.netto_betrag == Decimal("-100.00")
    assert eintrag.ust_betrag == Decimal("-19.00")
    assert forderung is None


def test_bestehendes_lieferantenguthaben_hat_vorrang_vor_neuem_gutschrift_matching(db):
    """Schritt 5 des Plans: eine Transaktion darf niemals beide Mechanismen gleichzeitig
    auslösen. _match_lieferantenguthaben() läuft in auto_buchen() bewusst VOR dem neuen
    Gutschrift-fähigen Rechnungs-Matching und muss weiterhin Vorrang haben."""
    gutschrift = _eingangsrechnung_mit_gutschrift(db)
    # Forderung mit demselben Betrag wie die offene Gutschrift - ohne strikte Priorisierung
    # waere unklar, welcher der beiden Mechanismen "gewinnt".
    db.add(Forderung(
        typ="lieferantenguthaben", status="offen", betrag=Decimal("119.00"),
        partner_typ="lieferant",
    ))
    db.commit()

    tx = BankTransaktion(
        konto_id=db.konto_id, import_id=db.import_id, datum=date(2026, 3, 5),
        betrag=Decimal("119.00"), verwendungszweck="Erstattung Lieferant",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    auto_buchen(db.konto_id, db.import_id, db)

    db.refresh(tx)
    assert tx.ist_rueckerstattung is True
    assert tx.journal_id is None  # Forderung-Pfad bucht keinen Journaleintrag

    forderung = db.query(Forderung).filter(Forderung.typ == "lieferantenguthaben").first()
    assert forderung.status == "ausgeglichen"

    # Gutschrift bleibt unberührt (nicht faelschlich ueber den Rechnungs-Matching-Pfad gebucht)
    db.refresh(gutschrift)
    assert gutschrift.zahlungsstatus == "offen"
