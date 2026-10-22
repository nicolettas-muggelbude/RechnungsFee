"""
Regressionstest für Migration 174 (Issue #456-Nebenfund).

Vor v0.6.4 bekamen Zahlungen auf Ausgangsrechnungen mit ist_reverse_charge fälschlich
ust_sonderfall='13b_abs1'. Migration 160 hat genau diese Zeilen (13b + 0 %) zusätzlich um
19 % USt/Vorsteuer ergänzt. Migration 174 entfernt den Sonderfall und setzt die Änderung aus
Migration 160 auf den protokollierten Altwert zurück - echte §13b-Einkäufe bleiben unberührt.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

import main
from api.ustva import _berechne_kz
from database.connection import Base
from database.models import Journaleintrag, Rechnung
from utils.aenderungsprotokoll import protokolliere_aenderung


def _journal(rechnung_id, art, sonderfall, ust="0.00", satz="0.00", vst="0.00", belegnr="J-1"):
    return Journaleintrag(
        datum=date(2026, 5, 10), belegnr=belegnr, beschreibung="Altbuchung", art=art,
        brutto_betrag=Decimal("1000.00"), netto_betrag=Decimal("1000.00"),
        ust_satz=Decimal(satz), ust_betrag=Decimal(ust), vorsteuer_betrag=Decimal(vst),
        zahlungsart="Bank", rechnung_id=rechnung_id, ust_sonderfall=sonderfall,
    )


def test_reverse_charge_ausgangszahlung_wird_korrigiert(tmp_path, monkeypatch):
    db_path = tmp_path / "alt.db"
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    monkeypatch.setattr(main, "engine", eng)
    monkeypatch.setattr(main, "DB_PATH", db_path)
    Base.metadata.create_all(bind=eng)

    with eng.connect() as con:
        s = Session(bind=con)
        ausgang = Rechnung(typ="ausgang", rechnungsnummer="RE-1", datum=date(2026, 5, 1),
                           partner_freitext="EU-Kunde", ist_reverse_charge=True)
        eingang = Rechnung(typ="eingang", rechnungsnummer="ER-1", datum=date(2026, 5, 1),
                           partner_freitext="EU-Lieferant", ist_reverse_charge=True)
        s.add_all([ausgang, eingang])
        s.flush()
        # a) von Migration 160 "ergänzt" (19 %), b) ohne 160-Eingriff, c) echter §13b-Einkauf
        a = _journal(ausgang.id, "Einnahme", "13b_abs1", ust="190.00", satz="19.00", vst="190.00", belegnr="J-a")
        b = _journal(ausgang.id, "Einnahme", "13b_abs1", belegnr="J-b")
        c = _journal(eingang.id, "Ausgabe", "13b_abs1", ust="190.00", satz="19.00", vst="190.00", belegnr="J-c")
        s.add_all([a, b, c])
        s.flush()
        for feld, neu in (("ust_satz", "19.00"), ("ust_betrag", "190.00"), ("vorsteuer_betrag", "190.00")):
            protokolliere_aenderung(s, tabelle="journal", datensatz_id=a.id, feld=feld, alter_wert=0,
                                    neuer_wert=neu, migration_version=160, grund="Test")
        s.commit()
        ids = (a.id, b.id, c.id)
        s.close()
        con.execute(text("PRAGMA user_version = 173"))
        con.commit()

    main._run_migrations()

    with eng.connect() as con:
        def zeile(i):
            return con.execute(text(
                "SELECT ust_sonderfall, ust_satz, ust_betrag, vorsteuer_betrag FROM journal WHERE id = :id"
            ), {"id": i}).one()

        za, zb, zc = (zeile(i) for i in ids)
        protokoll = con.execute(text(
            "SELECT datensatz_id, feld FROM aenderungsprotokoll WHERE migration_version = 174"
        )).fetchall()
        assert con.execute(text("PRAGMA user_version")).scalar() == main.SCHEMA_VERSION

    assert za[0] is None and Decimal(str(za[1])) == 0 and Decimal(str(za[2])) == 0 and Decimal(str(za[3])) == 0
    assert zb[0] is None and Decimal(str(zb[2])) == 0
    assert zc[0] == "13b_abs1" and Decimal(str(zc[2])) == Decimal("190.00")  # echter Einkauf unberührt
    assert sorted(protokoll) == sorted([
        (ids[0], "ust_sonderfall"), (ids[0], "ust_satz"), (ids[0], "ust_betrag"), (ids[0], "vorsteuer_betrag"),
        (ids[1], "ust_sonderfall"),
    ])

    # Nach der Korrektur landen beide Zahlungen in KZ 21 statt als §13b-Storno
    with Session(bind=eng) as s:
        kz, _ = _berechne_kz(date(2026, 5, 1), date(2026, 5, 31), s)
    assert kz["kz_21"] == Decimal("2000.00")
