"""
Meldezeitraum für ZM und UStVA KZ 41/21 nach Rechnung statt Zahlung (Issue #497).

§18a Abs. 8 und §18b Satz 1 Nr. 1/2 UStG knüpfen den Meldezeitraum - unabhängig von der
Ist-Versteuerung - an die Leistung bzw. die Rechnung, nicht an den Zahlungseingang:

  L / KZ 41 (ig. Lieferung): Monat der Rechnungsausstellung, spätestens der Monat, der auf die
            Lieferung folgt (§18a Abs. 8 Satz 1).
  S / KZ 21 (sonstige Leistung §3a Abs. 2): Monat, in dem die Leistung ausgeführt wurde
            (§18a Abs. 8 Satz 2) - leistung_bis → leistung_von → Rechnungsdatum.

Bis zu diesem Feature liefen beide Kennzeichen über das Datum der Zahlungsbuchung - eine
unbezahlte ig. Lieferung erschien nie in der ZM. Quelle ist jetzt die Rechnung (Netto); UStVA
(api/ustva.py) und ZM (api/zm.py) lesen beide über ig_umsaetze(), damit KZ 41/21 und die ZM
nicht auseinanderlaufen.

Übergang wie beim Vorsteuer-Cutover (#338, utils/vorsteuer_soll.py): Ausgangsrechnungen mit
datum >= CUTOVER_DATUM laufen nach der neuen Regel, ältere bleiben vollständig auf dem
bisherigen Zahlungsdatum-Pfad (inkl. ihrer Stornos, Gutschriften und Skonti) - sonst würde
dieselbe Rechnung doppelt oder gar nicht gemeldet. Wie dort ein fest verankertes Kalender-
datum, keine Einstellung.

Eigenständiges Modul ohne Abhängigkeit zu api/* (wird von api/ustva.py und api/zm.py
importiert, verhindert Zirkelimporte).
"""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from database.models import Rechnung

# TODO vor Release prüfen/anpassen: Beginn eines Meldezeitraums, mindestens 4-6 Wochen nach dem
# geplanten Release-Datum, damit realistisch alle Nutzer das Update vorher erhalten haben.
CUTOVER_DATUM = date(2027, 1, 1)

ZERO = Decimal("0.00")

# Dokumenttypen, die nach der neuen Regel gemeldet werden. Abschlagsrechnungen gehören dazu,
# melden selbst aber 0 - gemeldet wird die Schlussrechnung (Issue #419, siehe _betrag()).
# Gutschriften kommen mit den Korrekturen nach §17 hinzu (siehe _korrekturen()).
_DOKUMENT_TYPEN = ("Rechnung", "Abschlagsrechnung")


@dataclass
class IgUmsatz:
    """Ein Beitrag zu ZM L/S bzw. UStVA KZ 41/21 aus einer Rechnung des neuen Verfahrens."""
    rechnung_id: int
    rechnungsnummer: str | None
    kennzeichen: str    # "L" (KZ 41) oder "S" (KZ 21)
    betrag: Decimal     # vorzeichenbehaftet (Korrekturen nach §17 negativ)
    datum: date         # Meldedatum - bestimmt den Monat der UStVA bzw. ZM
    art: str            # "rechnung"; Korrekturen nach §17 bringen eigene Arten mit


def _monatsende(jahr: int, monat: int) -> date:
    return date(jahr, monat, calendar.monthrange(jahr, monat)[1])


def _ende_folgemonat(d: date) -> date:
    if d.month == 12:
        return _monatsende(d.year + 1, 1)
    return _monatsende(d.year, d.month + 1)


def leistungsdatum(rechnung: Rechnung) -> date:
    """Tag der Lieferung/Leistung: leistung_bis → leistung_von → Rechnungsdatum (wie im
    Rahmen zu #497 für S beschrieben; für L mit Leistungszeitraum gilt dieselbe Reihenfolge)."""
    return rechnung.leistung_bis or rechnung.leistung_von or rechnung.datum


def kennzeichen(rechnung: Rechnung) -> str | None:
    """L vor S, wie bisher in der ZM (api/zm.py)."""
    if rechnung.ist_eu_lieferung:
        return "L"
    if rechnung.ist_reverse_charge:
        return "S"
    return None


def meldedatum(rechnung: Rechnung) -> date:
    """Datum, dessen Monat die Rechnung in ZM und UStVA KZ 41/21 meldet.

    L: Rechnungsdatum, spätestens das Ende des Monats nach der Lieferung (§18a Abs. 8 Satz 1) -
       eine Rechnung vor der Lieferung (kein Abschlag) meldet im Monat der Rechnung.
    S: Tag der Leistung (§18a Abs. 8 Satz 2).

    Nie vor CUTOVER_DATUM: eine Rechnung ab dem Stichtag über eine Leistung davor wird im ersten
    Monat des neuen Verfahrens gemeldet, nicht rückwirkend in einem Zeitraum, der nach altem
    Verfahren schon abgegeben ist (Rahmen zu #497: nichts rückwirkend, keine Doppel- oder
    Fehlmeldungen)."""
    if kennzeichen(rechnung) == "L":
        d = min(rechnung.datum, _ende_folgemonat(leistungsdatum(rechnung)))
    else:
        d = leistungsdatum(rechnung)
    return max(d, CUTOVER_DATUM)


def neue_rechnungen(db: Session) -> list[Rechnung]:
    """Finalisierte Ausgangsrechnungen mit ig. Lieferung oder EU-B2B-Dienstleistung ab dem
    Stichtag - die nach neuer Regel gemeldet werden."""
    return (
        db.query(Rechnung)
        .filter(
            Rechnung.typ == "ausgang",
            Rechnung.ist_entwurf == False,  # noqa: E712
            Rechnung.dokument_typ.in_(_DOKUMENT_TYPEN),
            Rechnung.datum >= CUTOVER_DATUM,
            (Rechnung.ist_eu_lieferung == True) | (Rechnung.ist_reverse_charge == True),  # noqa: E712
        )
        .all()
    )


def neue_rechnung_ids(db: Session) -> set[int]:
    """IDs der Rechnungen aus neue_rechnungen(). Deren Journalbuchungen (Zahlung, Storno-
    Gegenbuchung, Skonto) zählen in ZM und KZ 41/21 nicht mehr - sonst doppelt."""
    return {r.id for r in neue_rechnungen(db)}


def _betrag(rechnung: Rechnung, neue_ids: set[int]) -> Decimal:
    """Netto, das die Rechnung meldet (Issue #419):
    - Abschlagsrechnung: 0 - die Anzahlung wird mit der Schlussrechnung gemeldet.
    - Schlussrechnung: volle Leistung, also ohne die Abzugszeilen für Abschläge des neuen
      Verfahrens (die selbst 0 gemeldet haben). Abzüge für Abschläge vor dem Stichtag bleiben
      stehen - die sind über ihre Zahlung schon gemeldet."""
    if rechnung.dokument_typ == "Abschlagsrechnung":
        return ZERO
    betrag = rechnung.netto_gesamt or ZERO
    for pos in rechnung.positionen:
        if pos.abschlag_rechnung_id and pos.abschlag_rechnung_id in neue_ids:
            betrag -= (pos.brutto or ZERO) - (pos.ust_betrag or ZERO)
    return betrag


def _korrekturen(rechnungen: list[Rechnung], neue_ids: set[int], db: Session) -> list[IgUmsatz]:
    """Korrekturen nach §17 UStG (§18a Abs. 7, §18b Satz 4) für Rechnungen des neuen
    Verfahrens: eigene Beträge im Monat des Ereignisses (Storno, Gutschrift, Skonto).
    Noch leer - folgt als eigener Schritt."""
    return []


def ig_umsaetze(von: date, bis: date, db: Session) -> list[IgUmsatz]:
    """Gemeinsame Quelle für ZM (L/S) und UStVA (KZ 41/21) für Rechnungen ab CUTOVER_DATUM:
    alle Beiträge, deren Meldedatum im Zeitraum [von, bis] liegt."""
    rechnungen = neue_rechnungen(db)
    neue_ids = {r.id for r in rechnungen}
    umsaetze = [
        IgUmsatz(r.id, r.rechnungsnummer, kennzeichen(r), _betrag(r, neue_ids), meldedatum(r), "rechnung")
        for r in rechnungen
    ]
    umsaetze += _korrekturen(rechnungen, neue_ids, db)
    return [u for u in umsaetze if von <= u.datum <= bis and u.betrag != 0]
