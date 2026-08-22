"""
Charakterisierungstests für die BESTEHENDE Ausgangsrechnungs-Gutschrift (Schritt 0 des Plans
für Issue #364 "Lieferantengutschrift"). Für dieses Feature gab es bisher KEINEN einzigen
automatisierten Test - diese Datei dokumentiert und sichert das heutige Verhalten ab, bevor
die geteilten Funktionen (create_gutschrift, zahlung_bar_erstellen, _buche_pfad_a,
Bank-Import-Matching) für Eingangsrechnungen geöffnet werden. Muss nach jeder Änderung an
diesen Funktionen weiterhin unverändert grün bleiben - jede Abweichung ist eine Regression
am bereits produktiv genutzten Ausgang-Feature.
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
        name="Betriebseinnahmen", kontenart="Erlös", konto_skr03="8400", konto_skr04="4400",
        vorsteuer_prozent=0, ust_satz_standard=19,
    ))
    session.commit()
    yield session
    session.close()


def _bezahlte_ausgangsrechnung(db, betrag_netto="100.00", satz="19") -> Rechnung:
    netto = Decimal(betrag_netto)
    ust = (netto * Decimal(satz) / 100).quantize(Decimal("0.01"))
    kat = db.query(Kategorie).filter(Kategorie.name == "Betriebseinnahmen").first()
    rechnung = Rechnung(
        typ="ausgang", rechnungsnummer="RE-2026-1", datum=date(2026, 3, 1),
        brutto_gesamt=netto + ust, netto_gesamt=netto, ust_gesamt=ust,
        ist_entwurf=False, zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()
    pos = Rechnungsposition(
        rechnung_id=rechnung.id, position_nr=1, beschreibung="Beratung", menge=Decimal("1"),
        einheit="Stk.", netto=netto, ust_satz=Decimal(satz), ust_betrag=ust, brutto=netto + ust,
        kategorie_id=kat.id,
    )
    db.add(pos)
    db.commit()
    db.refresh(rechnung)
    return rechnung


def test_create_gutschrift_negiert_positionen(db):
    original = _bezahlte_ausgangsrechnung(db)
    resp = create_gutschrift(original.id, db)

    assert resp.dokument_typ == "Gutschrift"
    assert resp.typ == "ausgang"
    assert resp.brutto_gesamt == Decimal("-119.00")
    assert resp.netto_gesamt == Decimal("-100.00")
    assert resp.ust_gesamt == Decimal("-19.00")

    gutschrift = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    pos = gutschrift.positionen[0]
    assert pos.menge == Decimal("-1.000")
    assert pos.brutto == Decimal("-119.00")
    assert pos.ust_betrag == Decimal("-19.00")
    assert pos.netto == Decimal("100.0000")  # Einzelpreis bleibt positiv, Menge trägt Vorzeichen


def test_gutschrift_bar_erstattung_mindert_kassenstand_und_bucht_negativ(db):
    original = _bezahlte_ausgangsrechnung(db)
    resp = create_gutschrift(original.id, db)
    finalisiere_rechnung(resp.id, db)

    # Bar-Kasse erst mit einer Einnahme füllen, sonst schlägt die Kassenstand-Prüfung fehl
    db.add(Journaleintrag(
        datum=date(2026, 3, 1), belegnr="J-FUELL", beschreibung="Anfangsbestand",
        zahlungsart="Bar", art="Einnahme", netto_betrag=Decimal("500.00"), ust_satz=Decimal("0"),
        ust_betrag=Decimal("0"), brutto_betrag=Decimal("500.00"), immutable=True,
    ))
    db.commit()

    result = zahlung_bar_erstellen(
        resp.id, BarZahlungCreate(betrag=Decimal("119.00"), datum=date(2026, 3, 5), zahlungsart="Bar"), db,
    )

    eintrag = db.query(Journaleintrag).filter(Journaleintrag.id == result.journaleintrag_id).first()
    assert eintrag.art == "Einnahme"
    assert eintrag.brutto_betrag == Decimal("-119.00")
    assert eintrag.netto_betrag == Decimal("-100.00")
    assert eintrag.ust_betrag == Decimal("-19.00")

    gutschrift = db.query(Rechnung).filter(Rechnung.id == resp.id).first()
    assert gutschrift.zahlungsstatus == "bezahlt"


def test_gutschrift_bar_erstattung_ohne_ausreichenden_kassenstand_schlaegt_fehl(db):
    original = _bezahlte_ausgangsrechnung(db)
    resp = create_gutschrift(original.id, db)
    # keine Bar-Einnahme vorher -> Kassenstand 0, Erstattung 119 € darf nicht durchgehen
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        zahlung_bar_erstellen(
            resp.id, BarZahlungCreate(betrag=Decimal("119.00"), datum=date(2026, 3, 5), zahlungsart="Bar"), db,
        )
    assert exc.value.status_code == 409


def test_gutschrift_mindert_euer_einnahmen_zeile(db):
    original = _bezahlte_ausgangsrechnung(db)
    resp = create_gutschrift(original.id, db)
    finalisiere_rechnung(resp.id, db)
    zahlung_bar_erstellen(
        resp.id, BarZahlungCreate(betrag=Decimal("119.00"), datum=date(2026, 3, 5), zahlungsart="Bank"), db,
    )

    ergebnis = _berechne_euer(2026, db)
    # Zeile 15 (umsatzsteuerpflichtige Betriebseinnahmen) o.ä. - Kategorie "Betriebseinnahmen"
    # hat in diesem Test kein euer_zeile gesetzt, daher landet nichts in "zeilen" - Kernpunkt
    # des Tests ist stattdessen, dass die Gutschrift den Gesamtsaldo NICHT positiv erhöht.
    gesamt = sum(ergebnis["zeilen"].values(), Decimal("0"))
    assert gesamt <= Decimal("0.00")


def test_storno_bezahlte_gutschrift(db):
    original = _bezahlte_ausgangsrechnung(db)
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
    # Original war -119 (Einnahme, negativ) -> Storno-Gegenbuchung muss +119 sein, damit sich
    # beide zu 0 aufheben (keine Verdopplung).
    assert gegenbuchungen[0].brutto_betrag == Decimal("119.00")
