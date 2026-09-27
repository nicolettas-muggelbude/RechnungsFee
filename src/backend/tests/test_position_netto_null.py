"""
Regressionstest für Issue #408: Eine einzelne Position mit netto=0 (z.B. ein importierter
0-Euro-Gratisposten neben regulären Positionen) durfte nicht finalisiert werden ("Position netto
darf nicht 0 sein"), obwohl die Gesamtrechnung einen Betrag ungleich 0 hatte. Betraf typ='eingang'
und typ='ausgang' identisch (derselbe Validator, keine typ-Unterscheidung).

Zusätzlich: eine komplett auf 0 € summierende Rechnung (Gegenrechnung, Preiserlass, 100 % Rabatt)
ist ebenfalls ein legitimer Fall und darf nicht blockiert werden - keine Ausnahmeregel, der
Validator wurde komplett entfernt statt nur gelockert.
"""
from api.schemas_rechnungen import RechnungCreate


def _position(netto: str, beschreibung: str = "Position") -> dict:
    return {"beschreibung": beschreibung, "menge": "1", "einheit": "Stk", "netto": netto, "ust_satz": "19"}


def test_einzelne_null_euro_position_neben_regulaerer_position_eingang():
    RechnungCreate(
        typ="eingang", dokument_typ="Rechnung", datum="2026-09-27", kunde_id=None,
        partner_freitext="Testlieferant",
        positionen=[_position("100.00"), _position("0.00", "Gratisposten")],
    )


def test_einzelne_null_euro_position_neben_regulaerer_position_ausgang():
    RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum="2026-09-27", kunde_id=None,
        partner_freitext="Testkunde",
        positionen=[_position("100.00"), _position("0.00", "Gratisposten")],
    )


def test_komplette_rechnung_null_euro_gegenrechnung_erlaubt():
    RechnungCreate(
        typ="ausgang", dokument_typ="Rechnung", datum="2026-09-27", kunde_id=None,
        partner_freitext="Testkunde",
        positionen=[_position("100.00"), _position("-100.00", "Gegenrechnung")],
    )


def test_alle_positionen_null_euro_preiserlass_erlaubt():
    RechnungCreate(
        typ="ausgang", dokument_typ="Gutschrift", datum="2026-09-27", kunde_id=None,
        partner_freitext="Testkunde",
        positionen=[_position("0.00", "Preiserlass")],
    )
