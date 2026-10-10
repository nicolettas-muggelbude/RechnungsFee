"""
Regressionstest für Issue #428.

ELSTER erwartet Bemessungsgrundlagen (KZ 81, 86, 89, 93, 84 etc.) in vollen Euro (§123 AO,
kaufmännische Rundung) und berechnet bei festen Steuersätzen (KZ 81/86/89/93) die zugehörige
Steuer automatisch AUS DIESEM GERUNDETEN Betrag, nicht aus dem centgenauen Buchungswert.
KZ 84/85 (§13b Abs. 2): Bemessungsgrundlage (84) wird gerundet, der zugehörige Steuerbetrag
(85) bleibt centgenau und darf NICHT aus der gerundeten Bemessungsgrundlage neu berechnet
werden (explizite Warnung des Melders UweKoslowski).

Beide Beispiele exakt aus dem Issue übernommen:
  KZ 81: 930,50 € → ELSTER-Eingabe 931 € → ELSTER-Steuer 176,89 € (nicht 176,80 €)
  KZ 84/85: 10,71 € → ELSTER-Eingabe KZ 84 = 11 €, KZ 85 bleibt 2,03 € (centgenau, unverändert)
"""
from decimal import Decimal

from api.ustva import ALL_KZ_KEYS, ZERO, _elster_rundung, _voller_euro

ZERO = ZERO  # re-export für Lesbarkeit


def _leere_kz(**overrides) -> dict:
    kz = {k: ZERO for k in ALL_KZ_KEYS}
    kz.update(overrides)
    return kz


def test_volle_euro_rundung_kaufmaennisch_123_ao():
    assert _voller_euro(Decimal("930.50")) == Decimal("931")
    assert _voller_euro(Decimal("930.49")) == Decimal("930")
    assert _voller_euro(Decimal("10.71")) == Decimal("11")
    assert _voller_euro(Decimal("10.49")) == Decimal("10")


def test_kz81_beispiel_aus_issue():
    """930,50 € Bemessungsgrundlage → ELSTER rundet auf 931 € und berechnet daraus die
    Steuer (176,89 €), nicht aus dem centgenauen Buchungswert (wäre 176,80 € gewesen)."""
    kz = _leere_kz(
        kz_81=Decimal("930.50"),
        kz_83=Decimal("176.80"),  # centgenau gebucht - nicht die tatsächliche ELSTER-Steuer
        zahllast=Decimal("176.80"),
    )
    gerundet, zahllast_elster, differenz = _elster_rundung(kz)

    assert gerundet["81"] == Decimal("931")
    assert zahllast_elster == Decimal("176.89")
    assert differenz == Decimal("0.09")


def test_kz84_85_bemessungsgrundlage_gerundet_steuer_bleibt_centgenau():
    """10,71 € Bemessungsgrundlage (§13b Abs. 2) → KZ 84 wird für ELSTER auf 11 € gerundet,
    KZ 85 (Steuer) bleibt unverändert bei 2,03 € - NICHT neu aus den 11 € berechnet (das wären
    2,09 € und damit falsch - Warnung des Melders im Issue)."""
    kz = _leere_kz(
        kz_84=Decimal("10.71"),
        kz_85=Decimal("2.03"),
        kz_67=Decimal("2.03"),  # voller Vorsteuerabzug
        zahllast=Decimal("0.00"),
    )
    gerundet, zahllast_elster, _differenz = _elster_rundung(kz)

    assert gerundet["84"] == Decimal("11")
    # KZ 85 taucht bewusst NICHT in "gerundet" auf - es ist keine Bemessungsgrundlage.
    assert "85" not in gerundet
    # zahllast_elster muss die centgenauen 2,03 € verwenden, nicht 11 € × 19 % = 2,09 €.
    assert zahllast_elster == Decimal("0.00")  # 2.03 USt - 2.03 VSt


def test_voller_vorsteuerabzug_ohne_rundungsdifferenz():
    """Vorsteuer-Kennzahlen (66/61/62/67) sind keine Bemessungsgrundlagen und werden nie
    gerundet - ändert sich bei dieser Erweiterung nichts an ihnen."""
    kz = _leere_kz(kz_66=Decimal("50.00"), zahllast=Decimal("-50.00"))
    gerundet, zahllast_elster, differenz = _elster_rundung(kz)

    assert "66" not in gerundet
    assert zahllast_elster == Decimal("-50.00")
    assert differenz == Decimal("0.00")


def test_keine_differenz_wenn_bemessungsgrundlage_bereits_voller_euro():
    kz = _leere_kz(kz_81=Decimal("1000.00"), kz_83=Decimal("190.00"), zahllast=Decimal("190.00"))
    gerundet, zahllast_elster, differenz = _elster_rundung(kz)

    assert gerundet["81"] == Decimal("1000")
    assert zahllast_elster == Decimal("190.00")
    assert differenz == Decimal("0.00")
