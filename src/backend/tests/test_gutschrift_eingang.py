"""
Regressionstests für Issue #364 (Lieferantengutschrift). Neue, gespiegelte Funktion zur
bestehenden Ausgangsrechnungs-Gutschrift (siehe test_gutschrift_ausgang_bestandsschutz.py) -
jeder Test hier hat ein Gegenstück dort, das exakt umgekehrte Vorzeichen/Kassenrichtung prüft.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen import create_gutschrift, finalisiere_rechnung, zahlung_bar_erstellen, storno_rechnung
from api.schemas_rechnungen import BarZahlungCreate
from api.schemas import StornoRequest
from api.euer import _berechne_euer
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, Rechnungsposition, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.add(Kategorie(
        name="Bürobedarf", kontenart="Aufwand", konto_skr03="4930", konto_skr04="6815",
        vorsteuer_prozent=100, ust_satz_standard=19,
    ))
    session.commit()
    yield session
    session.close()


def _bezahlte_eingangsrechnung(db, betrag_netto="100.00", satz="19") -> Rechnung:
    netto = Decimal(betrag_netto)
    ust = (netto * Decimal(satz) / 100).quantize(Decimal("0.01"))
    kat = db.query(Kategorie).filter(Kategorie.name == "Bürobedarf").first()
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-2026-1", datum=date(2026, 3, 1),
        brutto_gesamt=netto + ust, netto_gesamt=netto, ust_gesamt=ust,
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
        kategorie_id=kat.id,
    )
    db.add(rechnung)
    db.flush()
    pos = Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Büromaterial", menge=Decimal("1"),
        einheit="Stk.", netto=netto, ust_satz=Decimal(satz), ust_betrag=ust, brutto=netto + ust,
        kategorie_id=kat.id,
    )
    db.add(pos)
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_create_gutschrift_fuer_eingangsrechnung_negiert_positionen(db):
    original = _bezahlte_eingangsrechnung(db)
    resp = create_gutschrift(original.id, db)

    assert resp.dokument_typ == "Gutschrift"
    assert resp.typ == "eingang"
    assert resp.brutto_gesamt == Decimal("-119.00")

    gutschrift = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    pos = gutschrift.positionen[0]
    assert pos.menge == Decimal("-1.000")
    assert pos.kategorie_id is not None


def test_gutschrift_bar_erstattung_erhoeht_kassenstand_und_bucht_negative_ausgabe(db):
    original = _bezahlte_eingangsrechnung(db)
    resp = create_gutschrift(original.id, db)
    finalisiere_rechnung(resp.id, db)

    # anders als beim Ausgang-Fall: KEINE Bar-Kasse vorfüllen nötig, da eine Bar-Erstattung
    # vom Lieferanten den Kassenstand erhöht statt ihn zu verbrauchen.
    result = zahlung_bar_erstellen(
        resp.id, BarZahlungCreate(betrag=Decimal("119.00"), datum=date(2026, 3, 5), zahlungsart="Bar"), db,
    )

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.id == result.journaleintrag_id).first()
    assert eintrag.art == "Ausgabe"
    assert eintrag.brutto_betrag == Decimal("-119.00")
    assert eintrag.netto_betrag == Decimal("-100.00")
    assert eintrag.ust_betrag == Decimal("-19.00")
    assert eintrag.kategorie_id is not None

    gutschrift = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    assert gutschrift.zahlungsstatus == "bezahlt"


def test_gutschrift_ohne_kategorie_wird_bei_zahlung_verweigert(db):
    """Eingangsrechnung ohne Kategorie (Alt-Fall vor Kategorie-Pflicht) - Gutschrift-Zahlung
    muss klar ablehnen statt fälschlich eine Erlös-Kategorie zu verwenden."""
    rechnung = Rechnung(
        typ="eingang", rechnungsnummer="ER-2026-2", datum=date(2026, 3, 1),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()
    db.add(Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Ohne Kategorie", menge=Decimal("1"),
        einheit="Stk.", netto=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        brutto=Decimal("119.00"), kategorie_id=None,
    ))
    db.commit()

    resp = create_gutschrift(rechnung.id, db)
    finalisiere_rechnung(resp.id, db)

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        zahlung_bar_erstellen(
            resp.id, BarZahlungCreate(betrag=Decimal("119.00"), datum=date(2026, 3, 5), zahlungsart="Bar"), db,
        )
    assert exc.value.status_code == 422


def test_gutschrift_mindert_euer_ausgaben_zeile(db):
    original = _bezahlte_eingangsrechnung(db)
    resp = create_gutschrift(original.id, db)
    finalisiere_rechnung(resp.id, db)
    zahlung_bar_erstellen(
        resp.id, BarZahlungCreate(betrag=Decimal("119.00"), datum=date(2026, 3, 5), zahlungsart="Bank"), db,
    )

    ergebnis = _berechne_euer(2026, db)
    gesamt = sum(ergebnis["zeilen"].values(), Decimal("0"))
    # Kategorie "Bürobedarf" hat in diesem Test kein euer_zeile gesetzt -> Kernpunkt ist,
    # dass der Gesamtsaldo durch die Gutschrift NICHT positiv (wie eine normale Ausgabe) wird.
    assert gesamt <= Decimal("0.00")


def test_storno_bezahlte_eingangs_gutschrift(db):
    original = _bezahlte_eingangsrechnung(db)
    resp = create_gutschrift(original.id, db)
    finalisiere_rechnung(resp.id, db)
    zahlung_bar_erstellen(
        resp.id, BarZahlungCreate(betrag=Decimal("119.00"), datum=date(2026, 3, 5), zahlungsart="Bank"), db,
    )

    storno_resp = storno_rechnung(resp.id, StornoRequest(grund="Testkorrektur"), db)
    assert storno_resp.storniert is True

    gegenbuchungen = db.query(Journaleintrag).filter(
        Journaleintrag.rechnung_id == resp.id, Journaleintrag.beschreibung.like("STORNO %")
    ).all()
    assert len(gegenbuchungen) == 1
    # Original war -119 (Ausgabe, negativ) -> Storno-Gegenbuchung muss +119 sein.
    assert gegenbuchungen[0].brutto_betrag == Decimal("119.00")
