"""
Regressionstest für Migration 153 (Issue #375): kategorien.ust_sonderfall persistent
+ Datenfix "Drittland-Dienstleistungen" §13b Abs. 1 -> Abs. 2.

Simuliert eine Bestandsinstallation: Kategorie mit dem alten (falschen) Namen und Konto,
ein bereits gebuchter Journaleintrag UND ein Vorsteuer-Anspruch mit ust_sonderfall='13b_abs1'
auf dieser Kategorie - beide muessen nach der Migration auf '13b_abs2' korrigiert sein.

Testet zusätzlich den Blocker, der beim Planen gefunden wurde: vorsteuer_ansprueche hat eigene
GoBD-Schutz-Trigger, die vor dieser Migration nicht in der Drop-Liste von _run_migrations()
standen - ohne die Ergänzung dort würde das UPDATE auf die immutable Zeile mit "GoBD-Verstoß"
abbrechen (Trigger wird hier bewusst VOR dem Migrationsaufruf angelegt, um genau die Situation
einer echten Bestandsinstallation nachzustellen, bei der der Trigger vom letzten App-Start
bereits aktiv ist).
"""
import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Rechnung, VorsteuerAnspruch


def make_engine(db_path: Path):
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def test_bestehende_drittland_kategorie_und_altbelege_werden_korrigiert(tmp_path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)
    db = Session()

    kat = Kategorie(
        name="Drittland-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand",
        konto_skr03="3125", konto_skr04="5925", vorsteuer_prozent=100, ust_satz_standard=19,
    )
    db.add(kat)
    db.commit()
    db.refresh(kat)

    rechnung = Rechnung(
        typ="eingang", datum=date(2026, 1, 10),
        brutto_gesamt=Decimal("119.00"), netto_gesamt=Decimal("100.00"), ust_gesamt=Decimal("19.00"),
        ist_entwurf=False, kategorie_id=kat.id,
    )
    db.add(rechnung)
    db.commit()
    db.refresh(rechnung)

    alt_journal = Journaleintrag(
        datum=date(2026, 1, 10), belegnr="ER-ALT-1", beschreibung="Altbeleg Drittland-DL",
        kategorie_id=kat.id, zahlungsart="Bank", art="Ausgabe",
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        vorsteuer_betrag=Decimal("19.00"), brutto_betrag=Decimal("100.00"),
        ust_sonderfall="13b_abs1", rechnung_id=rechnung.id, immutable=True,
    )
    db.add(alt_journal)

    alt_anspruch = VorsteuerAnspruch(
        rechnung_id=rechnung.id, datum=date(2026, 1, 10), kategorie_id=kat.id,
        netto_betrag=Decimal("100.00"), ust_satz=Decimal("19"), ust_betrag=Decimal("19.00"),
        vorsteuer_betrag=Decimal("19.00"), ust_sonderfall="13b_abs1", typ="anspruch", immutable=True,
    )
    db.add(alt_anspruch)
    db.commit()
    kat_id, journal_id, anspruch_id = kat.id, alt_journal.id, alt_anspruch.id
    db.close()

    # GoBD-Schutz-Trigger vorab anlegen (simuliert eine Bestandsinstallation, bei der die
    # Trigger vom letzten App-Start noch aktiv sind) - der Blocker aus der Planung.
    con = sqlite3.connect(str(db_path))
    con.execute("""
        CREATE TRIGGER protect_vorsteuer_ansprueche_update
        BEFORE UPDATE ON vorsteuer_ansprueche
        WHEN OLD.immutable = 1
        BEGIN
            SELECT RAISE(ABORT, 'GoBD-Verstoß: Vorsteuer-Ansprüche sind unveränderbar.');
        END
    """)
    con.execute("PRAGMA user_version = 152")
    con.commit()
    con.close()

    main._run_migrations()

    con = sqlite3.connect(str(db_path))
    kat_row = con.execute("SELECT name, ust_sonderfall FROM kategorien WHERE id = ?", (kat_id,)).fetchone()
    journal_sf = con.execute("SELECT ust_sonderfall FROM journal WHERE id = ?", (journal_id,)).fetchone()[0]
    anspruch_sf = con.execute(
        "SELECT ust_sonderfall FROM vorsteuer_ansprueche WHERE id = ?", (anspruch_id,)
    ).fetchone()[0]
    con.close()

    assert kat_row[0] == "Drittland-Dienstleistungen (§13b Abs. 2)"
    assert kat_row[1] == "13b_abs2"
    assert journal_sf == "13b_abs2"
    assert anspruch_sf == "13b_abs2"
    assert main.SCHEMA_VERSION >= 153


def test_andere_sonderfall_kategorien_werden_ueber_namen_gebackfillt(tmp_path, monkeypatch):
    db_path = tmp_path / "alt2.db"
    eng = make_engine(db_path)
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)

    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)
    db = Session()
    db.add(Kategorie(name="Wareneinkauf EU", kontenart="Aufwand", konto_skr03="3425", konto_skr04="5425"))
    db.add(Kategorie(name="EU-Dienstleistungen (§13b Abs. 1)", kontenart="Aufwand", konto_skr03="3123", konto_skr04="5923"))
    db.add(Kategorie(name="Bauleistungen / §13b Abs. 2", kontenart="Aufwand", konto_skr03="3120", konto_skr04="5920"))
    db.add(Kategorie(name="Einfuhrumsatzsteuer (Zoll/DHL)", kontenart="Aufwand", konto_skr03="1588", konto_skr04="1433"))
    # user_modified: Konto abweichend vom Standard, Name unveraendert - Backfill laeuft ueber
    # den Namen, muss davon unberuehrt bleiben.
    db.add(Kategorie(
        name="Sonstiges (angepasst)", kontenart="Aufwand", konto_skr03="4930", konto_skr04="6815",
    ))
    db.commit()
    db.close()

    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA user_version = 152")
    con.commit()
    con.close()

    main._run_migrations()

    con = sqlite3.connect(str(db_path))
    rows = dict(con.execute("SELECT name, ust_sonderfall FROM kategorien").fetchall())
    con.close()

    assert rows["Wareneinkauf EU"] == "ig_erwerb"
    assert rows["EU-Dienstleistungen (§13b Abs. 1)"] == "13b_abs1"
    assert rows["Bauleistungen / §13b Abs. 2"] == "13b_abs2"
    assert rows["Einfuhrumsatzsteuer (Zoll/DHL)"] == "einfuhr_ust"
    assert rows["Sonstiges (angepasst)"] is None
