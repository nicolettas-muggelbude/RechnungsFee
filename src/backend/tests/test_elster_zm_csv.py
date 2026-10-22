"""Tests für den ZM-CSV-Export (Meldeliste-Import in Mein ELSTER, Issue #360).

Format-Vertrag aus der offiziellen ELSTER-Importhilfe (themaGlobal=zmdo_import_eop
+ allgemeine_csv-anleitung):
- Zeile 1: #v3.0, Zeile 2: #ve3.2.1 (aktuelle Schnittstellen-Versionen)
- Kopfzeile mit Feldbezeichnungen, dann eine Meldezeile pro Position
- Felder: USt-IdNr. (AN 7-14, mit Länderkennzeichen), Summe in Euro (ganzzahlig,
  optionales Minus), Art der Leistung (L=ig. Lieferung, S=sonstige Leistung,
  D=Dreiecksgeschäft)
- Encoding UTF-8, Trennzeichen ",", keine Leerzeilen, max. 1500 Zeilen
"""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api.zm as zm_api
from api.zm import ZMPosition
from api.zm import zm_csv, ZMErgebnis
from database.connection import Base
from database.models import Unternehmen
from utils.elster import ElsterExportFehler, build_zm_csv


def _pos(ust_idnr="FRWL247100014", betrag=Decimal("1234.00"), kennzeichen="L"):
    return ZMPosition(ust_idnr=ust_idnr, land=ust_idnr[:2], kennzeichen=kennzeichen, betrag=betrag)


def test_offizielles_format():
    # RF-Kennzeichen L/D; "D" (§13b-Dienstleistung) wird zu ELSTER-"S" gemappt.
    csv_text = build_zm_csv([
        _pos("FRWL247100014", Decimal("12345678911"), "L"),
        _pos("HR12345678903", Decimal("-12345678911"), "D"),
        _pos("HR12345678900", Decimal("2000"), "D"),
    ]).decode("utf-8")
    assert csv_text == (
        "#v3.0\n"
        "#ve3.2.1\n"
        "Umsatzsteuer-Identifikationsnummer (USt-IdNr.),Summe (Euro),Art der Leistung\n"
        "FRWL247100014,12345678911,L\n"
        "HR12345678903,-12345678911,S\n"
        "HR12345678900,2000,S\n"
    )


def test_encoding_utf8():
    b = build_zm_csv([_pos()])
    b.decode("utf-8")  # muss sauber dekodieren
    assert b.startswith(b"#v3.0\n")


def test_summe_wird_auf_ganze_euro_gerundet():
    csv_text = build_zm_csv([_pos(betrag=Decimal("1234.56"))]).decode()
    assert ",1235," in csv_text
    csv_text = build_zm_csv([_pos(betrag=Decimal("1234.49"))]).decode()
    assert ",1234," in csv_text


def test_rf_dienstleistung_d_wird_zu_s():
    """Internes Kennzeichen 'D' (§13b-Dienstleistung) → ELSTER-Code 'S'
    (sonstige Leistung). 'D' ist bei ELSTER das Dreiecksgeschäft."""
    csv_text = build_zm_csv([_pos(kennzeichen="D")]).decode()
    assert csv_text.rstrip().endswith(",S")


def test_ig_lieferung_l_bleibt_l():
    csv_text = build_zm_csv([_pos(kennzeichen="L")]).decode()
    assert csv_text.rstrip().endswith(",L")


def test_leere_positionen_fehler():
    with pytest.raises(ElsterExportFehler):
        build_zm_csv([])


def test_fehlende_ust_idnr_fehler():
    with pytest.raises(ElsterExportFehler, match="USt-IdNr"):
        build_zm_csv([_pos(ust_idnr="")])


def test_ungueltige_ust_idnr_fehler():
    with pytest.raises(ElsterExportFehler, match="USt-IdNr"):
        build_zm_csv([_pos(ust_idnr="XX")])


def test_kennzeichen_unbekannt_fehler():
    with pytest.raises(ElsterExportFehler):
        build_zm_csv([_pos(kennzeichen="X")])


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Unternehmen(firmenname="Test GmbH", strasse="T", hausnummer="1",
                            plz="12345", ort="Testort"))
    session.commit()
    yield session
    session.close()


def test_endpoint_422_wenn_keine_positionen(db):
    with pytest.raises(Exception) as exc:
        zm_csv(zeitraum="2026-Q1", db=db)
    assert "422" in str(exc.value)


def test_endpoint_422_kleinunternehmer(db):
    db.query(Unternehmen).first().ist_kleinunternehmer = True
    db.commit()
    with pytest.raises(Exception) as exc:
        zm_csv(zeitraum="2026-Q1", db=db)
    assert "422" in str(exc.value)


def test_endpoint_liefert_csv(db):
    fake = zm_api.ZMErgebnis(
        zeitraum="2026-Q1", zeitraum_label="Q1/2026",
        von=date(2026, 1, 1), bis=date(2026, 3, 31), deadline=date(2026, 4, 25),
        positionen=[_pos()], gesamt=Decimal("1234.00"), ueber_50k=False,
    )
    with patch.object(zm_api, "zm_berechnen", return_value=fake):
        resp = zm_csv(zeitraum="2026-Q1", db=db)
    assert resp.media_type.startswith("text/csv")
    assert "attachment" in resp.headers["Content-Disposition"]
    assert "ZM_2026-Q1_ELSTER.csv" in resp.headers["Content-Disposition"]
