"""
Issue #579-Nebenfund: Die GuV ordnete EÜR-Zeilen über eine feste Liste zu. AfA (Zeile 33 seit
Migration 121) und die später ergänzten Zeilen 45/48/50/64/66/71 fehlten darin - ihre Kosten
fielen still aus der GuV, das Jahresergebnis war zu hoch.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import AUSGABEN_ZEILEN, EINNAHMEN_ZEILEN, EUR_ZEILEN_META
from api.guv import GUV_POSITIONEN, _GUV_AUSGESCHLOSSEN, berechne_guv
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Unternehmen
from database.seed import seed_kategorien


def test_jede_euer_zeile_ist_zugeordnet():
    zugeordnet = [z for *_, zeilen in GUV_POSITIONEN for z in zeilen]
    assert len(zugeordnet) == len(set(zugeordnet)), "Zeile doppelt zugeordnet"
    offen = (set(EINNAHMEN_ZEILEN) | set(AUSGABEN_ZEILEN)) - set(zugeordnet) - _GUV_AUSGESCHLOSSEN
    assert not offen, f"EÜR-Zeilen ohne GuV-Position: {sorted(offen)}"
    assert set(zugeordnet) <= set(EUR_ZEILEN_META)


def test_afa_mindert_das_jahresergebnis():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Unternehmen(firmenname="T", strasse="S", hausnummer="1", plz="12345", ort="O"))
    seed_kategorien(db)
    afa = db.query(Kategorie).filter(Kategorie.euer_zeile == 33).first()
    db.add(Journaleintrag(datum=date(2026, 12, 31), belegnr="J-1", beschreibung="AfA", kategorie_id=afa.id,
                          zahlungsart="Keine", art="Ausgabe", netto_betrag=Decimal("300"), ust_satz=Decimal("0"),
                          ust_betrag=Decimal("0"), vorsteuer_betrag=Decimal("0"), brutto_betrag=Decimal("300")))
    db.commit()
    guv = berechne_guv(2026, db)
    abschreibungen = next(p for p in guv.positionen if p.bezeichnung == "Abschreibungen")
    assert Decimal(abschreibungen.betrag) == Decimal("300.00")
    assert Decimal(guv.jahresergebnis) == Decimal("-300.00")
