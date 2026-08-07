"""
Vorsteuerabzug nach Soll-Prinzip (§15 UStG, Issue #338).

Vorsteuer ist rechtlich bereits mit Rechnungseingang (Leistungsbezug + ordnungsgemäße Rechnung)
abzugsfähig, unabhängig vom Zahlungsdatum. RechnungsFee bucht Vorsteuer bis zu diesem Feature
ausschließlich beim tatsächlichen Zahlungsdatum - CUTOVER_DATUM markiert den Stichtag, ab dem
neu finalisierte Eingangsrechnungen stattdessen über vorsteuer_ansprueche (Rechnungsdatum) laufen.

WICHTIG: Fest im Code verankertes Kalenderdatum, keine Einstellung/kein "erster Start nach
Update" - RechnungsFee ist eine Desktop-App mit einer SQLite-DB pro Installation, jeder Nutzer
aktualisiert zu einem anderen Zeitpunkt. Ein individueller Cutover je Installation würde dazu
führen, dass unterschiedliche Nutzer für dieselbe Rechnung unterschiedlich behandelt würden.

Wird sowohl von api/rechnungen.py (Finalisierung/Storno) als auch von api/ustva.py (KZ-Aggregation)
verwendet - deshalb als eigenständiges Modul ohne weitere Abhängigkeiten (verhindert Zirkelimporte).
"""

from datetime import date

# TODO vor Release prüfen/anpassen: mindestens 4-6 Wochen nach dem geplanten Release-Datum,
# damit realistisch alle Nutzer das Update vor Erreichen des Cutovers erhalten haben.
CUTOVER_DATUM = date(2026, 10, 1)
