r"""Tests für den ELSTER-UStVA-XML-Export (Mein-ELSTER-Upload, Issue #360).

Format-Vertrag verifiziert gegen:
- offizielle ELSTER-Hilfe (themaGlobal=ustva_upload): Nutzdaten-only,
  Root <Anmeldungssteuern>, ISO-8859-15, version-Attribut = Jahresversion
- Jahresdokumentation UStVA 2026 (ERiC 43.4): Pflichtfelder Jahr, Zeitraum,
  Steuernummer, Kz09, Kz83; DatenLieferant Name/Strasse/PLZ/Ort pflicht;
  Typen \d{4}0\d{8} / Ganzzahl / ".dd"; Zeitraum 01-12 bzw. 41-44
- Forum-Praxisbeispiel (thread 425731): funktionierender Upload-Aufbau
"""
import asyncio
import re

from datetime import date
from decimal import Decimal
from xml.etree import ElementTree as ET

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.ustva import ustva_xml
from database.connection import Base
from database.models import Journaleintrag, Kategorie, Unternehmen
from utils.elster import ElsterExportFehler, build_ustva_xml

NS = "http://finkonsens.de/elster/elsteranmeldung/ustva/v2026"


def _unternehmen(**kw) -> Unternehmen:
    base = dict(
        firmenname="Muster GmbH", vorname="Max", nachname="Mustermann",
        strasse="Musterweg", hausnummer="12", plz="12345", ort="Musterstadt",
        email="steuer@muster.de", telefon="030/123456",
        steuernummer="151/815/08154", bundesland="BY",
    )
    base.update(kw)
    return Unternehmen(**base)


def _parse(xml: bytes) -> ET.Element:
    return ET.fromstring(xml.decode("iso-8859-15"))


async def _lese_body(resp) -> bytes:
    return b"".join([c async for c in resp.body_iterator])


def test_deklaration_und_root():
    xml = build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(), kz_werte={"81": Decimal("150000"), "83": Decimal("28500.00")},
    )
    assert xml.startswith(b'<?xml version="1.0" encoding="ISO-8859-15" standalone="no"?>')
    root = _parse(xml)
    assert root.tag == f"{{{NS}}}Anmeldungssteuern"
    assert root.get("version") == "2026"
    assert f'xmlns="{NS}"' in xml.decode("iso-8859-15")


def test_namespace_und_version_folgen_dem_jahr_des_zeitraums():
    xml = build_ustva_xml(
        zeitraum="2024-Q2", steuernummer13="9151081508154",
        unternehmen=_unternehmen(), kz_werte={"83": Decimal("0.00")},
    )
    root = _parse(xml)
    assert root.get("version") == "2024"
    assert 'xmlns="http://finkonsens.de/elster/elsteranmeldung/ustva/v2024"' in xml.decode("iso-8859-15")


def test_elementstruktur_und_reihenfolge():
    xml = build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(), kz_werte={"83": Decimal("0.00")},
    )
    root = _parse(xml)
    kinder = [c.tag.split("}")[-1] for c in root]
    assert kinder == ["Erstellungsdatum", "DatenLieferant", "Steuerfall"]
    assert re.fullmatch(r"\d{8}", root.findtext("{*}Erstellungsdatum"))
    steuerfall = root.find("{*}Steuerfall")
    ustva = steuerfall.find("{*}Umsatzsteuervoranmeldung")
    assert ustva.findtext("{*}Jahr") == "2026"
    assert ustva.findtext("{*}Zeitraum") == "03"
    assert ustva.findtext("{*}Steuernummer") == "9151081508154"


@pytest.mark.parametrize("zeitraum,ziel", [
    ("2026-01", "01"), ("2026-12", "12"),
    ("2026-Q1", "41"), ("2026-Q2", "42"), ("2026-Q3", "43"), ("2026-Q4", "44"),
])
def test_zeitraum_mapping(zeitraum, ziel):
    xml = build_ustva_xml(
        zeitraum=zeitraum, steuernummer13="9151081508154",
        unternehmen=_unternehmen(), kz_werte={"83": Decimal("0.00")},
    )
    ustva = _parse(xml).find("{*}Steuerfall/{*}Umsatzsteuervoranmeldung")
    assert ustva.findtext("{*}Zeitraum") == ziel
    assert ustva.findtext("{*}Jahr") == "2026"


def test_kz_formate_ganzzahl_vs_cent():
    xml = build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(),
        kz_werte={
            "81": Decimal("150000"),      # Bemessungsgrundlage → Ganzzahl
            "86": Decimal("25000"),
            "66": Decimal("15000.55"),    # Vorsteuer → 2 Dezimalen, Punkt
            "83": Decimal("-1200.50"),    # Zahllast negativ erlaubt
        },
    )
    ustva = _parse(xml).find("{*}Steuerfall/{*}Umsatzsteuervoranmeldung")
    assert ustva.findtext("{*}Kz81") == "150000"
    assert ustva.findtext("{*}Kz86") == "25000"
    assert ustva.findtext("{*}Kz66") == "15000.55"
    assert ustva.findtext("{*}Kz83") == "-1200.50"


def test_kz83_ist_pflicht_auch_bei_null():
    ustva = _parse(build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(), kz_werte={},
    )).find("{*}Steuerfall/{*}Umsatzsteuervoranmeldung")
    assert ustva.findtext("{*}Kz83") == "0.00"


def test_nulle_kz_werden_nicht_emitiert():
    ustva = _parse(build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(),
        kz_werte={"81": Decimal("0"), "86": Decimal("0.00"), "83": Decimal("0.00")},
    )).find("{*}Steuerfall/{*}Umsatzsteuervoranmeldung")
    kzs = [e.tag.split("}")[-1] for e in ustva if e.tag.split("}")[-1].startswith("Kz")]
    assert kzs == ["Kz09", "Kz83"]


def test_kz09_als_schema_pflichtfeld_vorhanden():
    ustva = _parse(build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(), kz_werte={},
    )).find("{*}Steuerfall/{*}Umsatzsteuervoranmeldung")
    assert ustva.findtext("{*}Kz09") == "00000"


def test_umlaute_und_escapes_in_iso_8859_15():
    xml = build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(firmenname="Müller & Söhne — €uro"),
        kz_werte={"83": Decimal("0.00")},
    )
    text = xml.decode("iso-8859-15")
    assert "Müller" in text and "&amp;" in text
    # Parse über die Bytes prüft Encoding-Konsistenz
    _parse(xml)


def test_kein_unternehmer_block_im_steuerfall():
    """Der optionale <Unternehmer>-Block wird nicht emittiert (Jahresdoku erlaubt
    dort als Hausnummer nur Ziffern) - Anschrift steht im Pflichtblock
    <DatenLieferant>."""
    root = _parse(build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(), kz_werte={},
    ))
    assert root.find("{*}Steuerfall/{*}Unternehmer") is None
    lieferant = root.find("{*}DatenLieferant")
    assert lieferant.findtext("{*}Name") == "Muster GmbH"
    assert lieferant.findtext("{*}Strasse") == "Musterweg 12"
    assert lieferant.findtext("{*}PLZ") == "12345"
    assert lieferant.findtext("{*}Ort") == "Musterstadt"


def test_name_genau_45_zeichen_mit_ampersand():
    name45 = "Müller & Söhne GmbH & Co. KG Garten- und Land"
    assert len(name45) == 45
    lieferant = _parse(build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(firmenname=name45), kz_werte={},
    )).find("{*}DatenLieferant")
    assert lieferant.findtext("{*}Name") == name45


def test_name_laenger_45_wird_vor_dem_escapen_gekuerzt():
    # "&" an Position 44: Escape nach dem Kürzen, sonst würde "&amp;" halbiert
    lieferant = _parse(build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(firmenname="A" * 41 + " & Co"), kz_werte={},
    )).find("{*}DatenLieferant")
    assert len(lieferant.findtext("{*}Name")) == 45


def test_telefon_max_20_zeichen():
    lieferant = _parse(build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(telefon="+49 (0) 1234 / 567 890 12"), kz_werte={},
    )).find("{*}DatenLieferant")
    assert len(lieferant.findtext("{*}Telefon")) == 20


def test_datenlieferant_pflichtfelder_fehlen_fehler():
    with pytest.raises(ElsterExportFehler, match="Straße"):
        build_ustva_xml(
            zeitraum="2026-03", steuernummer13="9151081508154",
            unternehmen=_unternehmen(strasse=""), kz_werte={},
        )


def test_format_kz_rundung_und_minus_null():
    ustva = _parse(build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(),
        kz_werte={"81": Decimal("1234.50"), "83": Decimal("-0.00")},
    )).find("{*}Steuerfall/{*}Umsatzsteuervoranmeldung")
    assert ustva.findtext("{*}Kz81") == "1235"
    # ELSTER-Muster verbietet "-0"/"-0.00" – negative Null wird zu "0"/"0.00"
    assert ustva.findtext("{*}Kz83") == "0.00"


def test_format_kz_negativer_rundungsrest_wird_null():
    ustva = _parse(build_ustva_xml(
        zeitraum="2026-03", steuernummer13="9151081508154",
        unternehmen=_unternehmen(),
        kz_werte={"81": Decimal("-0.4"), "83": Decimal("0.00")},
    )).find("{*}Steuerfall/{*}Umsatzsteuervoranmeldung")
    # -0.4 ist ungleich 0, wird also emittiert – rundet aber zu -0 → "0"
    assert ustva.findtext("{*}Kz81") == "0"


def test_steuerummer_validierung_am_eingang():
    with pytest.raises(ElsterExportFehler):
        build_ustva_xml(
            zeitraum="2026-03", steuernummer13="15181508154",  # nur 11-stellig
            unternehmen=_unternehmen(), kz_werte={},
        )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(_unternehmen())
    session.commit()
    yield session
    session.close()


def test_endpoint_liefert_xml_mit_attachment_header(db):
    resp = ustva_xml(zeitraum="2026-Q1", db=db)
    assert resp.media_type == "application/xml"
    assert "attachment" in resp.headers["Content-Disposition"]
    assert "UStVA_2026-Q1_ELSTER.xml" in resp.headers["Content-Disposition"]
    body = asyncio.run(_lese_body(resp))
    assert body.startswith(b"<?xml")
    ustva = _parse(body).find("{*}Steuerfall/{*}Umsatzsteuervoranmeldung")
    assert ustva.findtext("{*}Steuernummer") == "9151081508154"
    assert ustva.findtext("{*}Zeitraum") == "41"


def test_endpoint_422_ohne_steuernummer(db):
    db.query(Unternehmen).first().steuernummer = None
    db.commit()
    with pytest.raises(HTTPException) as exc:
        ustva_xml(zeitraum="2026-Q1", db=db)
    assert exc.value.status_code == 422


def test_endpoint_422_ohne_bundesland(db):
    db.query(Unternehmen).first().bundesland = None
    db.commit()
    with pytest.raises(HTTPException) as exc:
        ustva_xml(zeitraum="2026-Q1", db=db)
    assert exc.value.status_code == 422


def test_endpoint_422_kleinunternehmer(db):
    db.query(Unternehmen).first().ist_kleinunternehmer = True
    db.commit()
    with pytest.raises(HTTPException) as exc:
        ustva_xml(zeitraum="2026-Q1", db=db)
    assert exc.value.status_code == 422


def test_endpoint_422_ungueltiger_zeitraum(db):
    with pytest.raises(HTTPException) as exc:
        ustva_xml(zeitraum="kein-zeitraum", db=db)
    assert exc.value.status_code == 422


def test_endpoint_422_ohne_strasse(db):
    unt = db.query(Unternehmen).first()
    unt.strasse = ""
    db.commit()
    with pytest.raises(HTTPException) as exc:
        ustva_xml(zeitraum="2026-Q1", db=db)
    assert exc.value.status_code == 422


def test_endpoint_404_ohne_unternehmen(db):
    db.query(Unternehmen).delete()
    db.commit()
    with pytest.raises(HTTPException) as exc:
        ustva_xml(zeitraum="2026-Q1", db=db)
    assert exc.value.status_code == 404


def test_endpoint_mit_journaldaten_elster_rundung(db):
    """Reale Buchungen: Bemessungsgrundlagen gerundet (§123 AO), Steuer- und
    Vorsteuerbeträge centgenau; Kz83 = voraussichtliche ELSTER-Zahllast
    (aus gerundeten Grundlagen), NICHT die gebuchte 19%-Steuer kz_83."""
    kat_erloes = Kategorie(name="Betriebseinnahmen", kontenart="Erlös",
                           euer_zeile=17, konto_skr03="8400")
    kat_aufwand = Kategorie(name="Bürobedarf", kontenart="Aufwand",
                            konto_skr03="4930", vorsteuer_prozent=100,
                            ust_satz_standard=19)
    kat_bau = Kategorie(name="Bauleistungen §13b", kontenart="Aufwand",
                        konto_skr03="5920", vorsteuer_prozent=100,
                        ust_satz_standard=19)
    db.add_all([kat_erloes, kat_aufwand, kat_bau])
    db.commit()
    db.add_all([
        # a) regulärer 19%-Umsatz
        Journaleintrag(
            datum=date(2026, 2, 10), belegnr="B1", beschreibung="Umsatz 19%",
            kategorie_id=kat_erloes.id, zahlungsart="Bank", art="Einnahme",
            netto_betrag=Decimal("1000.40"), ust_satz=Decimal("19"),
            ust_betrag=Decimal("190.08"), brutto_betrag=Decimal("1190.48"),
            konto_ust_skr03="1776",
        ),
        # b) reguläre Vorsteuer
        Journaleintrag(
            datum=date(2026, 2, 12), belegnr="B2", beschreibung="Büromaterial",
            kategorie_id=kat_aufwand.id, zahlungsart="Bank", art="Ausgabe",
            netto_betrag=Decimal("266.05"), ust_satz=Decimal("19"),
            ust_betrag=Decimal("50.55"), brutto_betrag=Decimal("316.60"),
            vorsteuer_betrag=Decimal("50.55"), vorsteuerabzug=True,
        ),
        # c) §13b Abs. 2: Bemessungsgrundlage + Steuer + abziehbare Vorsteuer
        Journaleintrag(
            datum=date(2026, 2, 20), belegnr="B3", beschreibung="Bauleistung",
            kategorie_id=kat_bau.id, zahlungsart="Bank", art="Ausgabe",
            netto_betrag=Decimal("500.00"), ust_satz=Decimal("19"),
            ust_betrag=Decimal("95.00"), brutto_betrag=Decimal("595.00"),
            vorsteuer_betrag=Decimal("95.00"), vorsteuerabzug=True,
            ust_sonderfall="13b_abs2",
        ),
    ])
    db.commit()

    resp = ustva_xml(zeitraum="2026-Q1", db=db)
    body = asyncio.run(_lese_body(resp))
    ustva = _parse(body).find("{*}Steuerfall/{*}Umsatzsteuervoranmeldung")
    assert ustva.findtext("{*}Kz81") == "1000"      # gerundet aus 1000.40
    assert ustva.findtext("{*}Kz66") == "50.55"     # Vorsteuer centgenau
    assert ustva.findtext("{*}Kz84") == "500"       # §13b-Bemessungsgrundlage
    assert ustva.findtext("{*}Kz85") == "95.00"     # §13b-Steuer centgenau
    assert ustva.findtext("{*}Kz67") == "95.00"     # Vorsteuer aus §13b
    # 1000 × 19% − 50.55 = 139.45 (≠ gebuchte Steuer 190.08, ≠ 139.53 centgenau)
    assert ustva.findtext("{*}Kz83") == "139.45"
