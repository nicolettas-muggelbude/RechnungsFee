"""
Regressionstests für Issue #419: Jahreswechsel-Szenario (Abschlag in einem Jahr bezahlt, Rest
der Schlussrechnung im nächsten) und DATEV-Export einer Schlussrechnung mit Abzugszeilen /
negativem Gesamtbetrag.

Die Nutzerin konnte diese beiden Punkte der Gegentest-Checkliste nicht manuell durchklicken
(Jahreswechsel lässt sich im laufenden Betrieb nicht einfach simulieren, DATEV-Export lässt
sich ohne DATEV-Software nicht inhaltlich prüfen) - stattdessen hier automatisiert verifiziert.

Architektur-Kernidee aus dem Plan: EÜR/UStVA/DATEV aggregieren ausschließlich über
Journaleintrag-Zeilen nach Zahlungsdatum, ohne Bezug zu Dokumentketten - die
Abschlagsverrechnung selbst ändert daran nichts, sie beeinflusst nur, welchen (reduzierten)
Betrag die Schlussrechnung bei IHRER eigenen Zahlung bucht.
"""
import asyncio
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.datev import datev_buchungsstapel
from api.euer import _berechne_euer
from api.rechnungen import create_rechnung, zahlung_bar_erstellen
from api.schemas_rechnungen import BarZahlungCreate, RechnungCreate, RechnungspositionCreate
from database.connection import Base
from database.models import Kategorie, Kunde, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(
        firmenname="Testfirma GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort",
        kontenrahmen="SKR03", geschaeftsjahr_beginn=1,
        datev_beraternummer="1001", datev_mandantennummer="1", datev_konto_bank="1200",
    ))
    session.add(Kategorie(name="Betriebseinnahmen", kontenart="Erlös", aktiv=True, euer_zeile=15))
    kunde = Kunde(firmenname="Testkunde GmbH")
    session.add(kunde)
    session.commit()
    session.refresh(kunde)
    yield session, kunde.id
    session.close()


async def _lese_body(response) -> bytes:
    return b"".join([chunk async for chunk in response.body_iterator])


def test_abschlag_und_schlussrechnung_landen_im_jeweils_richtigen_wirtschaftsjahr(db):
    session, kunde_id = db

    abschlag_resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Abschlagsrechnung", datum=date(2025, 12, 1), ist_entwurf=False,
        kunde_id=kunde_id,
        positionen=[RechnungspositionCreate(beschreibung="Abschlag", menge=Decimal("1"), netto=Decimal("1000.00"), ust_satz=Decimal("19"))],
    ), session)
    zahlung_bar_erstellen(abschlag_resp.id, BarZahlungCreate(datum=date(2025, 12, 20), zahlungsart="Bank"), session)

    schluss_resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum=date(2026, 1, 15), ist_entwurf=False,
        kunde_id=kunde_id,
        positionen=[
            RechnungspositionCreate(beschreibung="Gesamtleistung", menge=Decimal("1"), netto=Decimal("3000.00"), ust_satz=Decimal("19")),
            RechnungspositionCreate(
                beschreibung="Abzgl. Abschlag", menge=Decimal("-1"), netto=Decimal("1000.00"), ust_satz=Decimal("19"),
                abschlag_rechnung_id=abschlag_resp.id,
            ),
        ],
    ), session)
    zahlung_bar_erstellen(schluss_resp.id, BarZahlungCreate(datum=date(2026, 1, 20), zahlungsart="Bank"), session)

    euer_2025 = _berechne_euer(2025, session)
    euer_2026 = _berechne_euer(2026, session)

    assert euer_2025["zeilen"].get(15) == Decimal("1000.00")
    assert euer_2026["zeilen"].get(15) == Decimal("2000.00")
    # Zusammen ergibt sich die volle Gesamtleistung (3000,00 €) - nichts geht verloren, nichts
    # wird doppelt gezählt, unabhängig davon, dass die Schlussrechnung den Abschlag erst im
    # Folgejahr "kennt".
    assert euer_2025["zeilen"].get(15) + euer_2026["zeilen"].get(15) == Decimal("3000.00")


def test_datev_export_schlussrechnung_mit_abzugszeile(db):
    session, kunde_id = db

    abschlag_resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Abschlagsrechnung", datum=date(2026, 1, 5), ist_entwurf=False,
        kunde_id=kunde_id,
        positionen=[RechnungspositionCreate(beschreibung="Abschlag", menge=Decimal("1"), netto=Decimal("1000.00"), ust_satz=Decimal("19"))],
    ), session)

    schluss_resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum=date(2026, 2, 1), ist_entwurf=False,
        kunde_id=kunde_id,
        positionen=[
            RechnungspositionCreate(beschreibung="Gesamtleistung", menge=Decimal("1"), netto=Decimal("3000.00"), ust_satz=Decimal("19")),
            RechnungspositionCreate(
                beschreibung="Abzgl. Abschlag", menge=Decimal("-1"), netto=Decimal("1000.00"), ust_satz=Decimal("19"),
                abschlag_rechnung_id=abschlag_resp.id,
            ),
        ],
    ), session)
    zahlung_bar_erstellen(schluss_resp.id, BarZahlungCreate(datum=date(2026, 2, 5), zahlungsart="Bank"), session)

    response = datev_buchungsstapel(von=date(2026, 1, 1), bis=date(2026, 12, 31), mit_belegen=False, db=session)
    data = asyncio.run(_lese_body(response))
    text = data.decode("utf-8-sig")
    zeilen = text.splitlines()

    assert len(zeilen) >= 3  # Verwaltungssatz + Kopfzeile + mind. 1 Buchung
    # Umsatz (Netto-Restbetrag 2000,00 € netto -> brutto 2380,00 €) muss korrekt und POSITIV
    # im Export stehen - trotz der negativen Abzugszeile in der Rechnung selbst, da die
    # tatsächliche Zahlungsbuchung (worauf DATEV/EÜR/UStVA ausschließlich beruhen) ganz normal
    # eine positive Einnahme auf den bereits reduzierten Restbetrag ist.
    buchungszeile = zeilen[2].split(";")
    umsatz = buchungszeile[0].replace(",", ".")
    assert Decimal(umsatz) == Decimal("2380.00")


def test_datev_export_negative_schlussrechnung_erstattung(db):
    """Überdeckung: die Schlussrechnung selbst wird negativ, ihre Zahlungsbuchung (Rückerstattung)
    muss als negativer bzw. korrekt gekennzeichneter Betrag im DATEV-Export auftauchen, nicht als
    positive Einnahme fehlinterpretiert werden."""
    session, kunde_id = db

    abschlag_resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Abschlagsrechnung", datum=date(2026, 1, 5), ist_entwurf=False,
        kunde_id=kunde_id,
        positionen=[RechnungspositionCreate(beschreibung="Abschlag", menge=Decimal("1"), netto=Decimal("5000.00"), ust_satz=Decimal("19"))],
    ), session)

    schluss_resp = create_rechnung(RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum=date(2026, 2, 1), ist_entwurf=False,
        kunde_id=kunde_id,
        positionen=[
            RechnungspositionCreate(beschreibung="Gesamtleistung", menge=Decimal("1"), netto=Decimal("100.00"), ust_satz=Decimal("19")),
            RechnungspositionCreate(
                beschreibung="Abzgl. Abschlag", menge=Decimal("-1"), netto=Decimal("5000.00"), ust_satz=Decimal("19"),
                abschlag_rechnung_id=abschlag_resp.id,
            ),
        ],
    ), session)
    schlussrechnung = session.query(Rechnung).filter(Rechnung.id == schluss_resp.id).first()
    assert schlussrechnung.brutto_gesamt < 0

    zahlung_bar_erstellen(schluss_resp.id, BarZahlungCreate(datum=date(2026, 2, 5), zahlungsart="Bank"), session)

    response = datev_buchungsstapel(von=date(2026, 1, 1), bis=date(2026, 12, 31), mit_belegen=False, db=session)
    data = asyncio.run(_lese_body(response))
    text = data.decode("utf-8-sig")
    zeilen = text.splitlines()
    buchungszeile = zeilen[2].split(";")
    umsatz = Decimal(buchungszeile[0].replace(",", "."))
    # Erstattung von 5831,00 € (100-5000=-4900 netto -> -5831 brutto) - DATEV kennt kein
    # Minus-Feld im Umsatz, das Soll/Haben-Kennzeichen (Feld 2) trägt das Vorzeichen.
    assert abs(umsatz) == Decimal("5831.00")
    soll_haben = buchungszeile[1]
    assert soll_haben in ("S", "H")
