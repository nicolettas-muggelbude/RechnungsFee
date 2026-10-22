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

def test_import_quelle_ist_nicht_als_clientfeld_freigegeben():
    from api.schemas_rechnungen import RechnungCreate

    assert "import_quelle" not in RechnungCreate.model_fields


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
    assert r1.import_quelle == "papierkram"

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


def test_import_beleg_mit_mapping_bucht_vorsteuer_und_zahlungskategorie(db):
    """Der echte Importpfad übernimmt das explizite Mapping auch bei Vorsteuer."""
    from database.models import Journaleintrag, Rechnungsposition

    unternehmen = db.query(Unternehmen).first()
    unternehmen.ist_kleinunternehmer = False
    kategorie = db.query(Kategorie).filter(Kategorie.name == "Bürobedarf").first()
    kategorie.ust_satz_standard = 19
    kategorie.vorsteuer_prozent = Decimal("100")
    db.commit()

    csv_inhalt = BELEGE_CSV.replace(
        b"-56,99;0,00;-56,99;0;domestic;B\xc3\xbcrobedarf",
        b"-100,00;-19,00;-119,00;0;domestic;Alt-Kategorie",
    ).replace(b"03.08.2026;03.08.2026;2026-07-19;paid;", b"03.10.2026;03.10.2026;2026-10-15;paid;")
    mapping = '{"Alt-Kategorie":"Bürobedarf"}'
    preview = asyncio.run(import_vorschau(_FakeUpload(csv_inhalt), TYP_BELEGE, mapping, db=db))
    assert preview[0].kategorie == "Bürobedarf"
    assert preview[0].fehler == []

    result = asyncio.run(import_durchfuehren(_FakeUpload(csv_inhalt), TYP_BELEGE, mapping, db=db))
    assert result.importiert == 1
    assert result.fehler == 0
    rechnung = db.query(Rechnung).filter(Rechnung.externe_belegnr == "B-00001").one()
    position = db.query(Rechnungsposition).filter(Rechnungsposition.rechnung_id == rechnung.id).one()
    journal = db.query(Journaleintrag).filter(Journaleintrag.rechnung_id == rechnung.id).one()
    assert rechnung.kategorie_id == kategorie.id
    assert position.kategorie_id == kategorie.id
    assert rechnung.ust_gesamt == Decimal("19.00")
    assert journal.kategorie_id == kategorie.id
    assert journal.brutto_betrag == Decimal("119.00")


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


@pytest.mark.parametrize("status", ["teilweise", "teilbezahlt", "partially paid"])
def test_vorschau_lehnt_teilzahlung_mit_hinweis_ab(db, status):
    csv_inhalt = RECHNUNGEN_CSV.replace(b"R-00001", b"R-00990", 1).replace(
        b"Bezahlt;Rechnung;45,00;0,00;45,00;0,00;45,00",
        f"{status};Rechnung;100,00;0,00;100,00;0,00;40,00".encode(), 1,
    )
    zeile = asyncio.run(import_vorschau(_FakeUpload(csv_inhalt), TYP_RECHNUNGEN, "", db=db))[0]
    assert any("Teilzahlungen/Ratenzahlungen" in fehler and "manuell erfassen" in fehler for fehler in zeile.fehler)


@pytest.mark.parametrize("status", ["teilweise", "teilbezahlt", "partially paid", "offen", "unbezahlt"])
def test_import_lehnt_nicht_abbildbare_positive_zahlung_ohne_side_effects(db, status):
    from database.models import Journaleintrag

    csv_inhalt = RECHNUNGEN_CSV.replace(b"R-00001", b"R-00989", 1).replace(
        b"Bezahlt;Rechnung;45,00;0,00;45,00;0,00;45,00",
        f"{status};Rechnung;100,00;0,00;100,00;0,00;40,00".encode(), 1,
    )
    result = asyncio.run(import_durchfuehren(_FakeUpload(csv_inhalt), TYP_RECHNUNGEN, "", db=db))
    assert result.fehler == 1
    assert result.importiert == 1
    rejected = next(row for row in result.zeilen if row.rechnungsnummer == "R-00989")
    assert rejected.status == "fehler"
    assert "Teilzahlungen/Ratenzahlungen" in rejected.begruendung
    assert db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00989").count() == 0
    assert db.query(Journaleintrag).count() == 0


def test_import_unbezahlte_rechnung_ohne_betrag_bleibt_unveraendert(db):
    csv_inhalt = RECHNUNGEN_CSV.replace(b"R-00002", b"R-00988", 1)
    result = asyncio.run(import_durchfuehren(_FakeUpload(csv_inhalt), TYP_RECHNUNGEN, "", db=db))
    assert result.fehler == 0
    rechnung = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00988").one()
    assert rechnung.zahlungsstatus == "offen"
    assert rechnung.bezahlt_betrag == Decimal("0.00")


@pytest.mark.parametrize("netto,ust,brutto", [
    ("100,00", "19,00", "119,00"),
    ("100,00", "7,00", "107,00"),
    ("100,00", "0,00", "100,00"),
    ("100,00", "13,53", "113,53"),
])
def test_ust_satz_nur_0_7_19_mit_rundungstoleranz(db, netto, ust, brutto):
    csv_inhalt = RECHNUNGEN_CSV.replace(b"R-00001", b"R-00991", 1).replace(
        b"45,00;0,00;45,00;0,00;45,00", f"{netto};{ust};{brutto};0,00;0,00".encode(), 1
    )
    zeile = asyncio.run(import_vorschau(_FakeUpload(csv_inhalt), TYP_RECHNUNGEN, "", db=db))[0]
    if ust == "13,53":
        assert any("gemischte Steuersätze".lower() in f.lower() for f in zeile.fehler)
    else:
        assert not zeile.fehler


def test_import_rundungstoleranz_erhaelt_originalbetraege(db):
    csv_inhalt = RECHNUNGEN_CSV.replace(
        b"45,00;0,00;45,00;0,00;45,00",
        b"100,00;19,01;119,01;0,00;0,00",
        1,
    )
    asyncio.run(import_durchfuehren(_FakeUpload(csv_inhalt), TYP_RECHNUNGEN, "", db=db))
    rechnung = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00001").first()
    assert rechnung.netto_gesamt == Decimal("100.00")
    assert rechnung.ust_gesamt == Decimal("19.01")
    assert rechnung.brutto_gesamt == Decimal("119.01")


def test_beleg_nicht_inland_wird_mit_hinweis_abgelehnt(db):
    csv_inhalt = BELEGE_CSV.replace(b"domestic", b"EU")
    zeile = asyncio.run(import_vorschau(_FakeUpload(csv_inhalt), TYP_BELEGE, "", db=db))[0]
    assert any("Herkunftsort" in f and "Reverse-Charge" in f for f in zeile.fehler)


def test_offener_beleg_erfordert_keine_kategoriezuordnung(db):
    csv_inhalt = BELEGE_CSV.replace(b";paid;", b";open;")
    zeile = asyncio.run(import_vorschau(_FakeUpload(csv_inhalt), TYP_BELEGE, "", db=db))[0]
    assert zeile.kategorie_quelle is None
    assert not zeile.fehler


def test_beleg_kann_nicht_auf_erloeskategorie_gebucht_werden(db):
    db.add(Kategorie(name="Umsatz", kontenart="Erlös", konto_skr03="8400", konto_skr04="4400"))
    db.commit()
    csv_inhalt = BELEGE_CSV.replace("domestic;Bürobedarf".encode(), b"domestic;Umsatz")
    zeile = asyncio.run(import_vorschau(
        _FakeUpload(csv_inhalt), TYP_BELEGE, '{"Umsatz":"Umsatz"}', db=db
    ))[0]
    assert any("Erlöskategorie" in f for f in zeile.fehler)


def test_importierte_rechnung_mailversand_wird_serverseitig_blockiert(db, monkeypatch):
    from fastapi import HTTPException
    import api.mail as mail_api
    from api.mail import MailSendenRequest, _pdf_bytes_fuer
    from api.rechnungen import markiere_ausgegeben, rechnung_als_pdf, rechnung_als_zugferd

    asyncio.run(import_durchfuehren(_FakeUpload(RECHNUNGEN_CSV), TYP_RECHNUNGEN, "", db=db))
    rechnung = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00001").first()
    with pytest.raises(HTTPException) as exc:
        _pdf_bytes_fuer(rechnung.id, db)
    assert exc.value.status_code == 409
    monkeypatch.setattr(mail_api, "_smtp_einstellungen", lambda _db: None)
    with pytest.raises(HTTPException) as exc:
        mail_api.mail_senden(
            MailSendenRequest(an="test@example.invalid", betreff="Test", text="Test", rechnung_id=rechnung.id),
            db=db,
        )
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        rechnung_als_pdf(rechnung.id, db=db)
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        rechnung_als_zugferd(rechnung.id, db=db)
    assert exc.value.status_code == 409
    with pytest.raises(HTTPException) as exc:
        markiere_ausgegeben(rechnung.id, db=db)
    assert exc.value.status_code == 409


def test_importierte_offene_rechnung_bleibt_im_offenen_posten_und_kontokorrent_sichtbar(db):
    from api.kunden import kontokorrent_kunde
    from api.rechnungen import list_rechnungen

    asyncio.run(import_durchfuehren(_FakeUpload(RECHNUNGEN_CSV), TYP_RECHNUNGEN, "", db=db))
    offene_rechnungen = list_rechnungen(
        typ="ausgang",
        zahlungsstatus=["offen"],
        monat=None,
        datum_von=None,
        datum_bis=None,
        kunde_id=None,
        lieferant_id=None,
        dokument_typ=None,
        kette_von_id=None,
        db=db,
    )
    offene = next(r for r in offene_rechnungen if r.rechnungsnummer == "R-00002")
    assert offene.import_quelle == "papierkram"
    assert offene.kunde_id is not None

    bewegungen = kontokorrent_kunde(offene.kunde_id, db)
    assert any(b.belegnr == "R-00002" and b.betrag == 60.0 for b in bewegungen)


def test_importierte_rechnung_zeigt_vorhandenes_original_pdf_an(db, tmp_path, monkeypatch):
    from io import BytesIO
    from pypdf import PdfReader, PdfWriter
    from api.rechnungen import rechnung_als_pdf
    import api.rechnungen as rechnungen_api

    asyncio.run(import_durchfuehren(_FakeUpload(RECHNUNGEN_CSV), TYP_RECHNUNGEN, "", db=db))
    rechnung = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00001").first()
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    pdf_fixture = BytesIO()
    writer.write(pdf_fixture)
    synthetic_pdf = pdf_fixture.getvalue()
    (uploads / "original.pdf").write_bytes(synthetic_pdf)
    rechnung.original_pdf_pfad = "uploads/original.pdf"
    db.commit()
    monkeypatch.setattr(rechnungen_api, "APP_DATA_DIR", tmp_path)

    response = rechnung_als_pdf(rechnung.id, nur_ansehen=True, db=db)
    assert response.body == synthetic_pdf
    assert response.headers["Content-Disposition"].startswith("inline;")
    assert len(PdfReader(BytesIO(response.body)).pages) == 1


def test_importierte_rechnung_ist_vor_neuer_mahnung_geschuetzt(db):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from api.mahnwesen import _berechne_mahnung

    asyncio.run(import_durchfuehren(_FakeUpload(RECHNUNGEN_CSV), TYP_RECHNUNGEN, "", db=db))
    rechnung = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00002").first()
    with pytest.raises(HTTPException) as exc:
        _berechne_mahnung(db, [rechnung.id], None, SimpleNamespace())
    assert exc.value.status_code == 409


def test_importierte_rechnung_kann_nicht_in_eine_mahnung_als_pdf_ausgegeben_werden(db):
    from datetime import datetime
    from fastapi import HTTPException
    from api.mahnwesen import mahnung_pdf_bytes
    from database.models import Mahnung, MahnungRechnung

    asyncio.run(import_durchfuehren(_FakeUpload(RECHNUNGEN_CSV), TYP_RECHNUNGEN, "", db=db))
    rechnung = db.query(Rechnung).filter(Rechnung.rechnungsnummer == "R-00002").first()
    mahnung = Mahnung(kunde_id=rechnung.kunde_id, stufe=1, erstellt_am=datetime.now())
    db.add(mahnung)
    db.flush()
    db.add(MahnungRechnung(mahnung_id=mahnung.id, rechnung_id=rechnung.id, offener_betrag=rechnung.brutto_gesamt))
    db.commit()

    with pytest.raises(HTTPException) as exc:
        mahnung_pdf_bytes(db, mahnung, nur_ansehen=True)
    assert exc.value.status_code == 409
