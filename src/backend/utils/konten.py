"""Kontonummern, an denen Buchungslogik und Auswertungen etwas erkennen."""

# Steuerfreie innergemeinschaftliche Lieferungen (§ 4 Nr. 1b UStG): SKR04 4125 laut
# DATEV-Kontenrahmen 2026. Bis Migration 179 trug die Kategorie fälschlich SKR04 3125
# (Verbindlichkeitenkonto) - Journaleinträge behalten ihren Konto-Snapshot (GoBD), deshalb
# muss die Erkennung beide Nummern kennen. SKR03 ist unverändert 8125.
IG_LIEFERUNG_SKR03 = ("8125",)
IG_LIEFERUNG_SKR04 = ("4125", "3125")


def ist_ig_lieferung_konto(konto_skr03: str | None, konto_skr04: str | None) -> bool:
    return konto_skr03 in IG_LIEFERUNG_SKR03 or konto_skr04 in IG_LIEFERUNG_SKR04
