"""
Issue #470 (Folgemeldung): Zeile 71 (Vordruck 2025, ab 2026 Zeile 72) "Fahrtkosten für nicht zum
Betriebsvermögen gehörende Fahrzeuge (Nutzungseinlage)", Kz 147, fehlte. Eine eigene Kategorie mit
dieser Zeile fiel still aus der Summe der Betriebsausgaben - jetzt kennt die EÜR die Zeile, und
unbekannte Zeilen werden beim Speichern abgewiesen bzw. in der Auswertung gemeldet.
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import EUR_ZEILEN_META, euer_berechnen, euer_zeilen
from api.journal import create_eintrag
from api.kategorien import create_kategorie, update_konten
from api.schemas import JournalEintragCreate, KategorieCreate, KategorieKontoUpdate
from database.connection import Base
from database.models import Kategorie, Unternehmen
from database.seed import STANDARD_KATEGORIEN


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test", strasse="X", hausnummer="1", plz="12345", ort="Y",
                            ist_kleinunternehmer=True))
    session.commit()
    yield session
    session.close()


def _buche(db, kat, jahr, betrag="30.00"):
    create_eintrag(JournalEintragCreate(
        datum=date(jahr, 3, 1), beschreibung="Fahrradreparatur (betrieblicher Anteil)",
        kategorie_id=kat.id, art="Ausgabe", brutto_betrag=Decimal(betrag), ust_satz=Decimal("0"),
        vorsteuerabzug=False, zahlungsart="Bank",
    ), db)


def test_zeile_71_bekannt():
    assert "Nutzungseinlage" in EUR_ZEILEN_META[71][0]
    assert EUR_ZEILEN_META[71][1] == "B"
    assert "km-Pauschale" not in EUR_ZEILEN_META[70][0]
    assert 71 in {z["zeile"] for z in euer_zeilen()}


@pytest.mark.parametrize("jahr,zeile", [(2025, 71), (2026, 72)])
def test_nutzungseinlage_in_summe(db, jahr, zeile):
    kat = Kategorie(name="Fahrrad", kontenart="Aufwand", euer_zeile=71, vorsteuer_prozent=0, ust_satz_standard=0)
    db.add(kat)
    db.commit()
    _buche(db, kat, jahr)
    erg = euer_berechnen(jahr, db=db)
    assert [(z.zeile, z.betrag) for z in erg.zeilen] == [(zeile, Decimal("30.00"))]
    assert erg.summe_ausgaben == Decimal("30.00")
    assert erg.gewinn_verlust == Decimal("-30.00")
    assert erg.nicht_zugeordnet == []


def test_unbekannte_zeile_wird_gemeldet(db):
    # Altbestand: Kategorie mit einer Zeile, die die Auswertung nicht kennt (vor der Prüfung angelegt)
    kat = Kategorie(name="Eigene Kategorie", kontenart="Aufwand", euer_zeile=72, vorsteuer_prozent=0, ust_satz_standard=0)
    db.add(kat)
    db.commit()
    _buche(db, kat, 2026)
    erg = euer_berechnen(2026, db=db)
    assert erg.zeilen == []
    assert erg.summe_ausgaben == Decimal("0.00")
    assert [(n.zeile, n.betrag, n.kategorien) for n in erg.nicht_zugeordnet] == [
        (72, Decimal("30.00"), ["Eigene Kategorie"])
    ]


def test_kategorie_mit_unbekannter_zeile_abgewiesen(db):
    with pytest.raises(HTTPException) as e:
        create_kategorie(KategorieCreate(name="X", kontenart="Aufwand", euer_zeile=72), db=db)
    assert e.value.status_code == 422
    kat = create_kategorie(KategorieCreate(name="Y", kontenart="Aufwand", euer_zeile=71), db=db)
    assert kat.euer_zeile == 71
    with pytest.raises(HTTPException):
        update_konten(kat.id, KategorieKontoUpdate(euer_zeile=999), db=db)
    assert update_konten(kat.id, KategorieKontoUpdate(euer_zeile=70), db=db).euer_zeile == 70


def test_standardkategorien_nur_bekannte_zeilen():
    for k in STANDARD_KATEGORIEN:
        assert k["euer_zeile"] is None or k["euer_zeile"] in EUR_ZEILEN_META, k["name"]


def test_standardkategorien_fahrt_und_reisekosten():
    kat = {k["name"]: k for k in STANDARD_KATEGORIEN}

    def konten(name):
        return (kat[name]["konto_skr03"], kat[name]["konto_skr04"])

    # DATEV-Kontenrahmen 2026, "Reisekosten Unternehmer"
    assert konten("Reisekosten – Übernachtung") == ("4676", "6680")
    assert konten("Reisekosten – Nebenkosten") == ("4676", "6680")
    assert konten("Reisekosten – ÖPNV") == ("4673", "6673")
    assert konten("Verpflegungsmehraufwand") == ("4674", "6674")
    # "Kosten für betrieblich genutzte, zum Privatvermögen gehörende Fahrzeuge"
    assert konten("Fahrtkosten Privat-PKW (0,10 €/km)") == ("4590", "6590")
    assert kat["Fahrtkosten Privat-PKW (0,10 €/km)"]["euer_zeile"] == 71
    neu = kat["Fahrtkosten nicht betriebliche Fahrzeuge (Nutzungseinlage)"]
    assert (neu["konto_skr03"], neu["konto_skr04"], neu["euer_zeile"]) == ("4590", "6590", 71)
    # § 35 UStDV: Fahrausweise berechtigen zum Vorsteuerabzug
    oepnv = kat["Reisekosten – ÖPNV"]
    assert (oepnv["vorsteuer_prozent"], oepnv["ust_satz_standard"]) == (100, 7)
