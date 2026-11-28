"""
Nebenfund zu Issue #578: „Verkauft am“ im Anlagenverzeichnis wurde nur gespeichert - die AfA lief
nach dem Verkauf unverändert weiter. Jetzt im Veräußerungsjahr zeitanteilig bis einschließlich
Verkaufsmonat (R 7.4 Abs. 8 EStR), danach keine AfA mehr.
"""
from datetime import date
from decimal import Decimal

from api.anlageverzeichnis import _afa_fuer_jahr, _afa_jahresplan
from database.models import Anlagegut


def _kfz(**kw) -> Anlagegut:
    daten = dict(bezeichnung="Auto", typ="kfz", kaufdatum=date(2024, 1, 10), kaufpreis_netto=Decimal("36000"),
                 nutzungsdauer_jahre=6, afa_methode="linear", privat_anteil_prozent=Decimal("0"),
                 afa_sofort=False, verkauft_am=None)
    daten.update(kw)
    return Anlagegut(**daten)


def test_ohne_verkauf_unveraendert():
    g = _kfz()
    assert _afa_fuer_jahr(g, 2026) == Decimal("6000.00")
    assert _afa_fuer_jahr(g, 2027) == Decimal("6000.00")


def test_verkauf_im_juni_halbes_jahr_danach_nichts():
    g = _kfz(verkauft_am=date(2026, 6, 15))
    assert _afa_fuer_jahr(g, 2025) == Decimal("6000.00")
    assert _afa_fuer_jahr(g, 2026) == Decimal("3000.00")   # Januar–Juni
    assert _afa_fuer_jahr(g, 2027) == Decimal("0")
    letzte = _afa_jahresplan(g)[-1]
    assert (letzte["jahr"], letzte["restbuchwert_ende"]) == (2026, 21000.0)


def test_verkauf_im_kaufjahr():
    g = _kfz(kaufdatum=date(2026, 3, 1), verkauft_am=date(2026, 8, 31))
    assert _afa_fuer_jahr(g, 2026) == Decimal("3000.00")   # März–August: 6 von 12 Monaten
    assert _afa_fuer_jahr(g, 2027) == Decimal("0")


def test_privatanteil_anteilig():
    g = _kfz(privat_anteil_prozent=Decimal("30"), verkauft_am=date(2026, 6, 1))
    assert _afa_fuer_jahr(g, 2026) == Decimal("2100.00")   # 3000 × 70 %


def test_sofortabzug_bleibt_voll():
    g = Anlagegut(bezeichnung="Laptop", typ="edv", kaufdatum=date(2026, 5, 10), kaufpreis_netto=Decimal("3000"),
                  nutzungsdauer_jahre=1, afa_methode="linear", privat_anteil_prozent=Decimal("0"),
                  afa_sofort=True, verkauft_am=date(2026, 9, 1))
    assert _afa_fuer_jahr(g, 2026) == Decimal("3000.00")
