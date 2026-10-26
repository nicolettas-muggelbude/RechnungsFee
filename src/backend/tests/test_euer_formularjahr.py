"""
Issue #470: EÜR-Zeilen je Formularjahr und Zuordnungen nach dem Vordruck der Anlage EÜR.

Die euer_zeile der Kategorien folgt dem Vordruck 2025. Der Vordruck 2026 (BMF 01.09.2026) hat
eine neue Zeile 27 (Rücklage Tierbewertung, LuF): Waren 27 → 29, Ausgaben ab 29 und ergänzende
Angaben ab 100 jeweils +1, Einnahmen unverändert. Geprüft an beiden amtlichen Vordrucken.
"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.euer import EUR_ZEILEN_META, euer_berechnen, euer_kategorien, formular_zeile
from api.journal import create_eintrag
from api.schemas import JournalEintragCreate
from database.connection import Base
from database.models import Kategorie, Unternehmen
from database.seed import STANDARD_KATEGORIEN


@pytest.mark.parametrize("basis,z2025,z2026", [
    (12, 12, 12), (15, 15, 15), (17, 17, 17), (21, 21, 21),   # Einnahmen unverändert
    (27, 27, 29),                                              # Waren hinter die Übertragszeile
    (29, 29, 30), (33, 33, 34), (43, 43, 44), (49, 49, 50),
    (57, 57, 58), (60, 60, 61), (63, 63, 64), (64, 64, 65),
    (66, 66, 67), (70, 70, 71), (75, 75, 76),                  # Ausgaben +1
    (106, 106, 107), (107, 107, 108),                          # Entnahmen/Einlagen +1
])
def test_formular_zeile(basis, z2025, z2026):
    assert formular_zeile(basis, 2025) == z2025
    assert formular_zeile(basis, 2024) == z2025
    assert formular_zeile(basis, 2026) == z2026
    assert formular_zeile(basis, 2027) == z2026


def test_beschriftungen_nach_vordruck_2025():
    assert 28 not in EUR_ZEILEN_META  # Übertragszeile, keine Kategorie
    assert EUR_ZEILEN_META[49][0].startswith("Beiträge, Gebühren, Abgaben und Versicherungen")
    assert EUR_ZEILEN_META[50][0].startswith("Laufende EDV-Kosten")
    assert EUR_ZEILEN_META[64][0] == "Verpflegungsmehraufwendungen"
    assert "Tagespauschale" in EUR_ZEILEN_META[66][0]


def test_kategorien_zuordnung_und_konten():
    kat = {k["name"]: k for k in STANDARD_KATEGORIEN}
    assert kat["Verpflegungsmehraufwand"]["euer_zeile"] == 64
    assert kat["Mitgliedsbeiträge"]["euer_zeile"] == 49
    # DATEV-Kontenrahmen 2026: 4805 / 6470 "Reparaturen und Instandhaltung von anderen Anlagen und BGA"
    assert (kat["Reparatur Anlagevermögen"]["konto_skr03"], kat["Reparatur Anlagevermögen"]["konto_skr04"]) == ("4805", "6470")
    assert kat["Reparatur Anlagevermögen"]["euer_zeile"] == 48
    # DATEV 4287 / 6347 "Tagespauschale für die Tätigkeit in der häuslichen Wohnung"
    tp = kat["Homeoffice-Tagespauschale"]
    assert (tp["konto_skr03"], tp["konto_skr04"], tp["euer_zeile"]) == ("4287", "6347", 66)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test", strasse="X", hausnummer="1", plz="12345", ort="Y",
                            ist_kleinunternehmer=True))
    session.add(Kategorie(name="Telefon & Internet", kontenart="Aufwand", konto_skr03="4920",
                          konto_skr04="6805", euer_zeile=43, vorsteuer_prozent=0, ust_satz_standard=0))
    session.commit()
    yield session
    session.close()


@pytest.mark.parametrize("jahr,zeile,summe_ausgaben", [(2025, 43, 75), (2026, 44, 76)])
def test_euer_ausgabe_nach_formularjahr(db, jahr, zeile, summe_ausgaben):
    kat = db.query(Kategorie).one()
    create_eintrag(JournalEintragCreate(
        datum=date(jahr, 3, 1), beschreibung="Telefon", kategorie_id=kat.id, art="Ausgabe",
        brutto_betrag=Decimal("50.00"), ust_satz=Decimal("0"), vorsteuerabzug=False, zahlungsart="Bank",
    ), db)
    ergebnis = euer_berechnen(jahr, db=db)
    assert [(z.zeile, z.betrag) for z in ergebnis.zeilen] == [(zeile, Decimal("50.00"))]
    assert ergebnis.zeile_summe_ausgaben == summe_ausgaben
    assert ergebnis.zeile_summe_einnahmen == 23
    detail = euer_kategorien(jahr, db=db)
    assert [z.zeile for z in detail.zeilen] == [zeile]
