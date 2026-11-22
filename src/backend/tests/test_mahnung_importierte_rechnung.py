"""
Community-Frage (nach v0.7.13): Importierte bzw. extern erstellte Ausgangsrechnungen sind mahnbar.
- erscheinen in der Fälligkeits-/Kundenliste
- eine im Altsystem bereits verschickte Mahnstufe samt Datum wird festgehalten (Migration 196):
  die Zählung geht dort weiter, die Fälligkeit rechnet ab dem Altsystem-Datum
- Anhang „Rechnung“: das angehängte Original statt eines neu erzeugten PDFs, ohne Original kein Anhang
"""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import api.mahnwesen as mw
import main
from api.schemas import MahnungErstellenRequest
from database.connection import Base
from database.models import Beleg, Kunde, Mahnung, Mahnstufe, Nummernkreis, Rechnung, Unternehmen

HEUTE = date.today()


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    s.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O"))
    s.add(Nummernkreis(bezeichnung="mahnung", typ="mahnung", format="MA-YY####", naechste_nr=1,
                       reset_jaehrlich=True, aktiv=True))
    s.add_all([
        Mahnstufe(stufe=1, bezeichnung="Zahlungserinnerung", tage_nach_faelligkeit=7, mahngebuehr_aktiv=False),
        Mahnstufe(stufe=2, bezeichnung="1. Mahnung", tage_nach_vorheriger=14, mahngebuehr_aktiv=False),
        Mahnstufe(stufe=3, bezeichnung="2. Mahnung", tage_nach_vorheriger=14, mahngebuehr_aktiv=False,
                  anhang_rechnung=True),
    ])
    s.add(Kunde(firmenname="Kunde GmbH"))
    s.commit()
    mw._get_or_create_einstellungen(s)
    yield s
    s.close()


def _import(db, faellig=HEUTE - timedelta(days=40), quelle="papierkram"):
    r = Rechnung(typ="ausgang", kunde_id=db.query(Kunde).one().id, rechnungsnummer="ALT-1", dokument_typ="Rechnung",
                 datum=faellig - timedelta(days=14), faellig_am=faellig, brutto_gesamt=Decimal("119.00"),
                 netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"), ist_entwurf=False,
                 zahlungsstatus="offen", bezahlt_betrag=Decimal("0.00"), import_quelle=quelle)
    db.add(r)
    db.commit()
    return r


@pytest.mark.parametrize("quelle", ["papierkram", "extern"])
def test_importierte_rechnung_ist_faellig_und_mahnbar(db, quelle):
    r = _import(db, quelle=quelle)
    assert [f.rechnung_id for f in mw.faellig_liste(db)] == [r.id]
    mahnung = mw.erstellen(MahnungErstellenRequest(rechnung_ids=[r.id], stufe=1), db)
    assert mahnung.rechnung_ids == [r.id]


def test_altsystem_stufe_setzt_zaehlung_fort(db):
    r = _import(db)
    mw.altsystem_mahnstufe_setzen(r.id, mw.AltsystemMahnstufeRequest(stufe=1, datum=HEUTE - timedelta(days=5)), db)
    db.refresh(r)
    assert (r.mahnstufe_aktuell, r.altsystem_mahnstufe) == (1, 1)
    # nächste Stufe 2 erst 14 Tage nach der Altsystem-Mahnung fällig
    assert mw._faellige_naechste_stufe(db, r, HEUTE) is None
    assert mw._faellige_naechste_stufe(db, r, HEUTE + timedelta(days=9)).stufe == 2

    # Entwurf anlegen und wieder löschen: Stufe fällt nicht unter die Altsystem-Stufe zurück
    mahnung = mw.erstellen(MahnungErstellenRequest(rechnung_ids=[r.id], stufe=2), db)
    db.refresh(r)
    assert r.mahnstufe_aktuell == 2
    with pytest.raises(HTTPException) as e:   # nach einer Mahnung in RechnungsFee gesperrt
        mw.altsystem_mahnstufe_setzen(r.id, mw.AltsystemMahnstufeRequest(stufe=0), db)
    assert e.value.status_code == 409
    mw.mahnung_loeschen(mahnung.id, db)
    db.refresh(r)
    assert r.mahnstufe_aktuell == 1


@pytest.mark.parametrize("stufe,datum,code", [
    (2, None, 422),                              # Datum fehlt
    (9, HEUTE, 422),                             # Stufe gibt es nicht
    (1, HEUTE + timedelta(days=1), 422),         # Zukunft
])
def test_altsystem_stufe_pruefungen(db, stufe, datum, code):
    r = _import(db)
    with pytest.raises(HTTPException) as e:
        mw.altsystem_mahnstufe_setzen(r.id, mw.AltsystemMahnstufeRequest(stufe=stufe, datum=datum), db)
    assert e.value.status_code == code


def test_altsystem_stufe_nur_bei_importierten_rechnungen(db):
    r = _import(db, quelle=None)
    with pytest.raises(HTTPException) as e:
        mw.altsystem_mahnstufe_setzen(r.id, mw.AltsystemMahnstufeRequest(stufe=1, datum=HEUTE), db)
    assert e.value.status_code == 422


def test_anhang_rechnung_ist_das_original(db, tmp_path, monkeypatch):
    import database.connection as dc
    monkeypatch.setattr(dc, "APP_DATA_DIR", tmp_path)
    r = _import(db)
    mw.altsystem_mahnstufe_setzen(r.id, mw.AltsystemMahnstufeRequest(stufe=2, datum=HEUTE - timedelta(days=30)), db)
    mahnung = mw.erstellen(MahnungErstellenRequest(rechnung_ids=[r.id], stufe=3), db)
    m = db.query(Mahnung).get(mahnung.id)

    # ohne Original: kein Anhang (kein neu erzeugtes Rechnungs-PDF)
    assert [n for _, n in mw.sammle_mahnung_anhaenge(db, m) if n.startswith("Rechnung_")] == []

    (tmp_path / "uploads" / "belege").mkdir(parents=True)
    (tmp_path / "uploads" / "belege" / "orig.pdf").write_bytes(b"%PDF-original")
    b = Beleg(dateiname="belege/orig.pdf", original_name="Rechnung ALT-1.pdf", mime_type="application/pdf",
              dateigroesse=13, sha256="x")
    db.add(b)
    db.flush()
    r.beleg_id = b.id
    db.commit()
    anhaenge = {n: inhalt for inhalt, n in mw.sammle_mahnung_anhaenge(db, m)}
    assert anhaenge["Rechnung_ALT-1.pdf"] == b"%PDF-original"


def test_migration_196(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE rechnungen DROP COLUMN altsystem_gemahnt_am"))
        conn.execute(text("ALTER TABLE rechnungen DROP COLUMN altsystem_mahnstufe"))
        conn.execute(text("PRAGMA user_version = 195"))
    monkeypatch.setattr(main, "engine", engine)
    main._run_migrations()
    with engine.begin() as conn:
        spalten = {r[1] for r in conn.execute(text("PRAGMA table_info(rechnungen)"))}
        assert {"altsystem_mahnstufe", "altsystem_gemahnt_am"} <= spalten
        assert conn.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION


def test_zusatzanhaenge_endpunkte_fuer_thunderbird(db, tmp_path, monkeypatch):
    """Issue #582: Zusatzanhänge der Stufe als Liste + einzeln abrufbar (Thunderbird/Mailprogramm)."""
    import database.connection as dc
    monkeypatch.setattr(dc, "APP_DATA_DIR", tmp_path)
    r = _import(db)
    (tmp_path / "uploads" / "belege").mkdir(parents=True)
    (tmp_path / "uploads" / "belege" / "orig.pdf").write_bytes(b"%PDF-original")
    b = Beleg(dateiname="belege/orig.pdf", original_name="Rechnung ALT-1.pdf", mime_type="application/pdf",
              dateigroesse=13, sha256="x")
    db.add(b)
    db.flush()
    r.beleg_id = b.id
    db.commit()
    mw.altsystem_mahnstufe_setzen(r.id, mw.AltsystemMahnstufeRequest(stufe=2, datum=HEUTE - timedelta(days=30)), db)
    mahnung = mw.erstellen(MahnungErstellenRequest(rechnung_ids=[r.id], stufe=3), db)
    liste = mw.mahnung_zusatzanhaenge(mahnung.id, db)
    assert liste == [{"index": 0, "dateiname": "Rechnung_ALT-1.pdf"}]
    assert mw.mahnung_zusatzanhang(mahnung.id, 0, db).body == b"%PDF-original"
    with pytest.raises(HTTPException):
        mw.mahnung_zusatzanhang(mahnung.id, 5, db)
