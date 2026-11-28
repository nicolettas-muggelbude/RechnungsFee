"""
Issue #562: Schalter „Artikelnummern anzeigen“ (Einstellungen → Rechnungsvorlagen) für die Spalte
„Art.-Nr.“ - Eintrag im Feld Artikelcode, sonst automatisch vergebene Nummer (ART-####).
Snapshots finalisierter Dokumente ohne den Schlüssel behalten das alte Verhalten (Issue #169).
Migration 195 schaltet den Schalter ein, wenn es schon Artikel mit Artikelcode gibt.
"""
from datetime import date
from decimal import Decimal
from io import BytesIO

import pytest
from pypdf import PdfReader
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import main
from database.connection import Base
from database.models import Artikel, Rechnung, Rechnungsposition
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_base import art_nr_anzeige, art_nr_spalte
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1

UNT = {"firmenname": "T", "strasse": "S", "hausnummer": "1", "plz": "12345", "ort": "O",
       "steuernummer": "12/345/67890", "ist_kleinunternehmer": True}


@pytest.fixture
def rechnung():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    eigen = Artikel(artikelnummer="ART-0001", typ="artikel", bezeichnung="Leiste", einheit="Stück",
                    steuersatz=Decimal("0"), vk_brutto=Decimal("10"), vk_netto=Decimal("10"), artikelcode="PR-4711")
    auto = Artikel(artikelnummer="ART-0005", typ="artikel", bezeichnung="Schraube", einheit="Stück",
                   steuersatz=Decimal("0"), vk_brutto=Decimal("1"), vk_netto=Decimal("1"))
    db.add_all([eigen, auto])
    db.flush()
    r = Rechnung(typ="ausgang", rechnungsnummer="RE-260001", datum=date(2026, 11, 21), partner_freitext="Kunde",
                 netto_gesamt=Decimal("11"), ust_gesamt=Decimal("0"), brutto_gesamt=Decimal("11"),
                 ist_entwurf=False, eingabemodus="brutto")
    db.add(r)
    db.flush()
    db.add_all([
        Rechnungsposition(rechnung_id=r.id, position_nr=1, beschreibung="Leiste", menge=Decimal("1"),
                          netto=Decimal("10"), ust_satz=Decimal("0"), brutto=Decimal("10"), artikel_id=eigen.id),
        Rechnungsposition(rechnung_id=r.id, position_nr=2, beschreibung="Schraube", menge=Decimal("1"),
                          netto=Decimal("1"), ust_satz=Decimal("0"), brutto=Decimal("1"), artikel_id=auto.id),
        Rechnungsposition(rechnung_id=r.id, position_nr=3, beschreibung="Anfahrt", menge=Decimal("1"),
                          netto=Decimal("0"), ust_satz=Decimal("0"), brutto=Decimal("0")),
    ])
    db.commit()
    db.refresh(r)
    yield r
    db.close()


def test_schalter_an(rechnung):
    unt = {**UNT, "pdf_artikelnummer": True}
    assert art_nr_spalte(unt, rechnung.positionen)
    assert [art_nr_anzeige(p, unt) for p in rechnung.positionen] == ["PR-4711", "ART-0005", ""]


def test_schalter_aus(rechnung):
    assert not art_nr_spalte({**UNT, "pdf_artikelnummer": False}, rechnung.positionen)


def test_alter_snapshot_ohne_schluessel(rechnung):
    """Vor #562 finalisiert: Spalte nur bei eigenem Eintrag, kein ART-#### als Rückfall."""
    assert art_nr_spalte(UNT, rechnung.positionen)
    assert [art_nr_anzeige(p, UNT) for p in rechnung.positionen] == ["PR-4711", "", ""]


@pytest.mark.parametrize("erzeuge", [generate_rechnung_pdf, generate_rechnung_pdf_vorlage1])
def test_pdf_zeigt_beide_nummern(rechnung, erzeuge):
    text_ = PdfReader(BytesIO(erzeuge(rechnung, {**UNT, "pdf_artikelnummer": True}, ist_netto=False))) \
        .pages[0].extract_text()
    assert "Art.-Nr." in text_ and "PR-4711" in text_ and "ART-0005" in text_


def test_suche_und_inventur_zeigen_eigene_nummer(rechnung):
    """Artikelauswahl liefert den Artikelcode mit, die Inventurliste zeigt die eigene Nummer."""
    from sqlalchemy.orm import object_session
    from api.artikel import suche_artikel
    from api.inventurliste import _inventur_zeilen
    db = object_session(rechnung)
    treffer = {t.bezeichnung: t for t in suche_artikel(q="e", db=db)}
    assert treffer["Leiste"].artikelcode == "PR-4711"
    assert treffer["Schraube"].artikelcode is None
    for a in db.query(Artikel):
        a.lager_aktiv = True
        a.bestand_aktuell = Decimal("1")
    db.commit()
    assert {z.bezeichnung: z.artikelnummer for z in _inventur_zeilen(db)} == {
        "Leiste": "PR-4711", "Schraube": "ART-0005"}


@pytest.mark.parametrize("mit_code", [True, False])
def test_migration_195(tmp_path, monkeypatch, mit_code):
    from database.models import Unternehmen
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as s:
        s.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O"))
        s.add(Artikel(artikelnummer="ART-0001", typ="artikel", bezeichnung="X", einheit="Stück",
                      steuersatz=Decimal("0"), vk_brutto=Decimal("1"), vk_netto=Decimal("1"),
                      artikelcode="PR-1" if mit_code else None))
        s.commit()
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE unternehmen DROP COLUMN pdf_artikelnummer"))
        conn.execute(text("PRAGMA user_version = 194"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        assert conn.execute(text("SELECT pdf_artikelnummer FROM unternehmen")).scalar() == (1 if mit_code else 0)
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION
