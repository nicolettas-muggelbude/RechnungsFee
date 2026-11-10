"""RechnungTyp/DokumentTyp (StrEnum): kompatibel zu den gespeicherten Strings, Validierung an der API-Grenze."""

import json

import pytest
from pydantic import ValidationError

from api.schemas_rechnungen import RechnungCreate, RechnungVorschauRequest
from database.enums import DokumentTyp, RechnungTyp


def _create(**kw):
    daten = {"typ": "ausgang", "datum": "2026-01-15", "kunde_id": 1,
             "positionen": [{"beschreibung": "X", "menge": 1, "einzelpreis": 10, "ust_satz": 19, "netto": 10}]}
    daten.update(kw)
    return RechnungCreate(**daten)


def test_enum_werte_entsprechen_db_strings():
    assert RechnungTyp.AUSGANG == "ausgang"
    assert DokumentTyp.ABSCHLAGSRECHNUNG == "Abschlagsrechnung"
    assert f"{DokumentTyp.ANGEBOT}" == "Angebot"
    assert json.dumps(DokumentTyp.PROFORMA) == '"Proforma"'
    # Dict-Lookup mit dem rohen DB-String trifft den Enum-Schlüssel
    assert {DokumentTyp.LIEFERSCHEIN: 1}.get("Lieferschein") == 1


def test_create_wandelt_strings_in_enum():
    r = _create(dokument_typ="Angebot")
    assert r.typ is RechnungTyp.AUSGANG
    assert r.dokument_typ is DokumentTyp.ANGEBOT
    assert _create().dokument_typ is DokumentTyp.RECHNUNG


@pytest.mark.parametrize("feld,wert,meldung", [
    ("typ", "Ausgang", "typ muss 'eingang' oder 'ausgang' sein"),
    ("dokument_typ", "angebot", "dokument_typ muss einer dieser Werte sein"),
])
def test_ungueltige_werte_deutsche_meldung(feld, wert, meldung):
    with pytest.raises(ValidationError) as exc:
        _create(**{feld: wert})
    assert meldung in str(exc.value)


def test_vorschau_default_ausgang():
    v = RechnungVorschauRequest(positionen=[])
    assert v.typ is RechnungTyp.AUSGANG
