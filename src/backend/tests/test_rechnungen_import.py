"""
Tests für den CSV-Import von Alt-Rechnungen und Alt-Belegen (Issue #445).

Der Import muss Original-Nummern und Original-Daten erhalten und Zahlungen
über den regulären Zahlungspfad (signaturierter Journaleintrag, Zuflussprinzip)
buchen. Fehlerhafte Zeilen werden übersprungen, nicht teilweise gebucht.
"""
from datetime import date
from decimal import Decimal

import asyncio
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.rechnungen_import import (
    TYP_BELEGE,
    TYP_RECHNUNGEN,
    _parse_amount,
    _parse_date,
    import_durchfuehren,
    import_vorschau,
)
from database.connection import Base
from database.models import Kategorie, Kunde, Lieferant, Nummernkreis, Rechnung, Unternehmen


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="Teststr.", hausnummer="1", plz="12345", ort="Testort"))
    session.add(Kunde(firmenname="Beispiel Kunde", kundennummer="K-00010"))
    session.add(Lieferant(firmenname="Beispiel Lieferant GmbH"))
    session.add(Kategorie(name="Bürobedarf", kontenart="Aufwand", konto_skr03="4220", konto_skr04="6420"))
    session.add(Nummernkreis(bezeichnung="Eingangsrechnungen", typ="rechnung_eingang", format="ER-YY####", naechste_nr=1, reset_jaehrlich=True))
    session.commit()
    yield session
    session.close()


class _FakeUpload:
    """Minimaler Ersatz für fastapi.UploadFile (nur .file.read wird benutzt)."""
    def __init__(self, content: bytes):
        import io
        self.file = io.BytesIO(content)


RECHNUNGEN_CSV = (
    "Rechnungsnr.;Betreff;Kunde;Land;Projekt;Kundennummer;Datum;Fälligkeitsdatum;"
    "Status;Typ;Netto;USt.;Brutto;Skonto;Bezahlt;letztes Bezahldatum;Notiz;Mahnungsdatum;"
    "Waren & Dienstleistungen\n"
    "R-00001;Rechnung Mai 2026;Beispiel Kunde;Deutschland;;K-00010;15.05.2026;29.05.2026;"
    "Bezahlt;Rechnung;45,00;0,00;45,00;0,00;45,00;2026-05-20;;;\n"
    "R-00002;Rechnung Juni 2026;Beispiel Kunde;Deutschland;;K-00010;15.06.2026;29.06.2026;"
    "Unbezahlt;Rechnung;60,00;0,00;60,00;0,00;0,00;;;;\n"
).encode("utf-8")


BELEGE_CSV = (
    "Belegnummer;Gegenstand;Lieferant;Datum;Zahlungsfrist;Zahlung am;Status;Netto;USt.;"
    "Brutto;Privatanteil;Herkunftsort;Kategorien;Projekte;Projektkunden;Projektkunden-Nr;"
    "Zusatz;Notizen\n"
    "B-00001;Bürobedarf;Beispiel Lieferant GmbH;03.08.2026;03.08.2026;2026-07-19;paid;"
    "-56,99;0,00;-56,99;0;domestic;Bürobedarf;;;;;;\n"
).encode("utf-8")


# ---------------------------------------------------------------------------
# Parsing-Helfer
# ---------------------------------------------------------------------------

def test_parse_amount_deutsche_formate():
    assert _parse_amount("15,00") == Decimal("15.00")
    assert _parse_amount("-56,99") == Decimal("-56.99")
    assert _parse_amount("1.234,56") == Decimal("1234.56")
    assert _parse_amount("45,00 €") == Decimal("45.00")
    assert _parse_amount("") is None
    assert _parse_amount(None) is None


def test_parse_date_deutsch_und_iso():
    assert _parse_date("15.10.2026") == date(2026, 10, 15)
    assert _parse_date("2026-10-16") == date(2026, 10, 16)
    assert _parse_date("unsinn") is None


# ---------------------------------------------------------------------------
# Ausgangsrechnungen (rechnungen.csv)
# ---------------------------------------------------------------------------

def test_import_rechnungen_erhaelt_nummern_und_zahlungsdaten(db):
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(RECHNUNGEN_CSV), TYP_RECHNUNGEN, "", db=db))
    assert ergebnis.importiert == 2
    assert ergebnis.fehler == 0

    r1 = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00001").first()
    assert r1 is not None
    assert r1.typ == "ausgang"
    assert not r1.ist_entwurf
    assert r1.datum == date(2026, 5, 15)
    assert r1.faellig_am == date(2026, 5, 29)
    assert r1.brutto_gesamt == Decimal("45.00")
    assert r1.zahlungsstatus == "bezahlt"
    assert r1.zahlungsdatum == date(2026, 5, 20)  # Original-Zahlungsdatum (Zuflussprinzip)
    assert r1.kunde_id is not None

    r2 = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00002").first()
    assert r2 is not None
    assert r2.zahlungsstatus == "offen"
    assert r2.bezahlt_betrag == Decimal("0.00")


def test_import_rechnungen_zahlung_ueber_regulaeren_journalpfad(db):
    from database.models import Journaleintrag
    asyncio.run(import_durchfuehren(_FakeUpload(RECHNUNGEN_CSV), TYP_RECHNUNGEN, "", db=db))
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.art == "Einnahme").first()
    assert eintrag is not None
    assert eintrag.datum == date(2026, 5, 20)
    assert eintrag.brutto_betrag == Decimal("45.00")
    assert eintrag.signatur  # GoBD-Signatur wie bei manueller Erfassung
    # Nur die bezahlte Rechnung erzeugt einen Journaleintrag
    assert db.query(Journaleintrag).count() == 1


def test_import_rechnungen_doppelte_nummer_wird_uebersprungen(db):
    db.add(Rechnung(typ="ausgang", rechnungsnummer="R-00001", datum=date(2026, 1, 1), partner_freitext="Altbestand"))
    db.commit()
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(RECHNUNGEN_CSV), TYP_RECHNUNGEN, "", db=db))
    assert ergebnis.importiert == 1
    assert ergebnis.fehler == 1
    fehlerhafte = [z for z in ergebnis.zeilen if z.status == "fehler"]
    assert "existiert bereits" in fehlerhafte[0].begruendung
    # Die bestehende Rechnung bleibt unberührt
    assert db.query(Rechnung).filter(Rechnung.partner_freitext == "Altbestand").count() == 1


def test_import_rechnungen_duplikat_innerhalb_der_csv(db):
    doppel = RECHNUNGEN_CSV + b"R-00001;Rechnung Mai 2026;Beispiel Kunde;Deutschland;;K-00010;15.05.2026;29.05.2026;Unbezahlt;Rechnung;45,00;0,00;45,00;0,00;0,00;;;\n"
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(doppel), TYP_RECHNUNGEN, "", db=db))
    assert ergebnis.importiert == 2
    assert ergebnis.fehler == 1  # dritte Zeile: Nummer kommt in der CSV mehrfach vor


def test_import_rechnungen_unbekannter_kunde_als_freitext(db):
    csv_inhalt = RECHNUNGEN_CSV.replace(b"Beispiel Kunde", b"Fremder Kunde").replace(b"K-00010", b"K-99999")
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(csv_inhalt), TYP_RECHNUNGEN, "", db=db))
    assert ergebnis.importiert == 2
    r1 = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00001").first()
    assert r1.kunde_id is None
    assert r1.partner_freitext == "Fremder Kunde"


def test_import_rechnungen_ueberzahlung_laeuft_ueber_kundenguthaben_pfad(db):
    csv_inhalt = (
        "Rechnungsnr.;Betreff;Kunde;Land;Projekt;Kundennummer;Datum;Fälligkeitsdatum;"
        "Status;Typ;Netto;USt.;Brutto;Skonto;Bezahlt;letztes Bezahldatum;Notiz;Mahnungsdatum;"
        "Waren & Dienstleistungen\n"
        "R-00042;Rechnung August 2026;Beispiel Kunde;Deutschland;;K-00010;11.08.2026;25.08.2026;"
        "Überbezahlt;Rechnung;61,20;0,00;61,20;0,00;61,50;2026-08-12;;;\n"
    ).encode("utf-8")
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(csv_inhalt), TYP_RECHNUNGEN, "", db=db))
    assert ergebnis.importiert == 1
    assert ergebnis.fehler == 0
    r = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00042").first()
    assert r.zahlungsstatus == "bezahlt"


def test_import_rechnungen_zukunftsdatum_und_inkonsistente_betaege_fehler(db):
    csv_inhalt = (
        "Rechnungsnr.;Betreff;Kunde;Land;Projekt;Kundennummer;Datum;Fälligkeitsdatum;"
        "Status;Typ;Netto;USt.;Brutto;Skonto;Bezahlt;letztes Bezahldatum;Notiz;Mahnungsdatum;"
        "Waren & Dienstleistungen\n"
        "R-00100;Zukunft;Beispiel Kunde;Deutschland;;K-00010;31.12.2099;31.12.2099;"
        "Unbezahlt;Rechnung;10,00;0,00;10,00;0,00;0,00;;;\n"
        "R-00101;Kaputt;Beispiel Kunde;Deutschland;;K-00010;15.05.2026;29.05.2026;"
        "Unbezahlt;Rechnung;10,00;5,00;20,00;0,00;0,00;;;\n"
    ).encode("utf-8")
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(csv_inhalt), TYP_RECHNUNGEN, "", db=db))
    assert ergebnis.importiert == 0
    assert ergebnis.fehler == 2
    assert db.query(Rechnung).count() == 0


# ---------------------------------------------------------------------------
# Belege / Eingangsrechnungen (belege.csv)
# ---------------------------------------------------------------------------

def test_import_belege_mit_kategorie_bucht_zahlung(db):
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(BELEGE_CSV), TYP_BELEGE, "", db=db))
    assert ergebnis.importiert == 1
    assert ergebnis.fehler == 0

    r = db.query(Rechnung).filter(Rechnung.externe_belegnr == "B-00001").first()
    assert r is not None
    assert r.typ == "eingang"
    assert r.brutto_gesamt == Decimal("56.99")  # negative Papierkram-Beträge → positiv
    assert r.lieferant_id is not None
    assert r.rechnungsnummer  # eigene Nummer aus Nummernkreis, Original in externe_belegnr

    from database.models import Journaleintrag
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.art == "Ausgabe").first()
    assert eintrag is not None
    assert eintrag.datum == date(2026, 7, 19)  # Original-Zahlungsdatum
    assert eintrag.brutto_betrag == Decimal("56.99")
    assert eintrag.kategorie_id is not None
    assert eintrag.signatur


def test_import_belege_ohne_kategorie_ohne_zahlung(db):
    csv_inhalt = BELEGE_CSV.replace(";Bürobedarf;".encode("utf-8"), ";Unbekannte Kategorie;".encode("utf-8"))
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(csv_inhalt), TYP_BELEGE, "", db=db))
    assert ergebnis.importiert == 1
    zeile = ergebnis.zeilen[0]
    assert zeile.zahlung_id is None
    assert any("Kategorie" in w for w in zeile.warnungen)
    from database.models import Journaleintrag
    assert db.query(Journaleintrag).count() == 0
    r = db.query(Rechnung).filter(Rechnung.externe_belegnr == "B-00001").first()
    assert r.zahlungsstatus == "offen"


def test_import_belege_kategorie_mit_komma_im_namen(db):
    """Papierkram-Kategorienamen können Kommas enthalten – das Spalten der
    Kategorien-Zelle darf solche Namen nicht kaputtmachen (Mapping-Treffer)."""
    mapping = '{"Sofortabschreibung ab 2021: PC, Laptop und andere Computer-Hardware": "Bürobedarf"}'
    csv_inhalt = BELEGE_CSV.replace("Bürobedarf;".encode("utf-8"), "Sofortabschreibung ab 2021: PC, Laptop und andere Computer-Hardware;".encode("utf-8"))
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(csv_inhalt), TYP_BELEGE, mapping, db=db))
    assert ergebnis.importiert == 1
    assert ergebnis.zeilen[0].zahlung_id is not None
    from database.models import Journaleintrag
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.art == "Ausgabe").first()
    assert eintrag is not None


def test_import_belege_duplikat_der_externen_belegnr(db):
    ergebnis = asyncio.run(import_durchfuehren(_FakeUpload(BELEGE_CSV), TYP_BELEGE, "", db=db))
    assert ergebnis.importiert == 1
    zweiter = asyncio.run(import_durchfuehren(_FakeUpload(BELEGE_CSV), TYP_BELEGE, "", db=db))
    assert zweiter.fehler == 1
    assert "existiert bereits" in zweiter.zeilen[0].begruendung


# ---------------------------------------------------------------------------
# Vorschau schreibt nichts
# ---------------------------------------------------------------------------

def test_vorschau_importiert_nichts(db):
    zeilen = asyncio.run(import_vorschau(_FakeUpload(RECHNUNGEN_CSV), TYP_RECHNUNGEN, "", db=db))
    assert len(zeilen) == 2
    assert all(z.partner_match == "stammdaten" for z in zeilen)
    assert not any(z.fehler for z in zeilen)
    assert db.query(Rechnung).count() == 0