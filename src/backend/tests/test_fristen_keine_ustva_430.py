"""
Regressionstest für Issue #430: voranmeldungsrhythmus="keine" (Finanzamt-Befreiung nach
§18 Abs. 2 Satz 3 UStG) darf keine UStVA-Fristen erzeugen, andere Fristen (ESt/GewSt-VZ)
aber unverändert.
"""
from datetime import date

from api.fristen import fristen_berechnen


def test_keine_rhythmus_erzeugt_keine_ustva_fristen():
    fristen = fristen_berechnen(
        bundesland="NW", voranmeldungsrhythmus="keine", dauerfristverlaengerung=False,
        est_aktiv=False, gewst_aktiv=False, ab_datum=date(2026, 1, 1), monate=6,
    )
    assert fristen == []


def test_keine_rhythmus_laesst_est_fristen_unberuehrt():
    fristen = fristen_berechnen(
        bundesland="NW", voranmeldungsrhythmus="keine", dauerfristverlaengerung=False,
        est_aktiv=True, gewst_aktiv=False, ab_datum=date(2026, 1, 1), monate=6,
    )
    assert fristen  # ESt-VZ-Fristen entstehen weiterhin
    assert all(f["typ"] != "UStVA" for f in fristen)


def test_quartal_rhythmus_erzeugt_weiterhin_ustva_fristen():
    fristen = fristen_berechnen(
        bundesland="NW", voranmeldungsrhythmus="quartal", dauerfristverlaengerung=False,
        est_aktiv=False, gewst_aktiv=False, ab_datum=date(2026, 1, 1), monate=6,
    )
    assert any(f["typ"] == "UStVA" for f in fristen)
