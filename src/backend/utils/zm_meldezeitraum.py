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

from sqlalchemy.orm import Session, selectinload

from database.models import Journaleintrag, Rechnung
from utils.konten import ist_ig_lieferung_konto

# Beginn eines Meldezeitraums, mindestens 4-6 Wochen nach dem Release, damit realistisch alle
# Nutzer das Update vorher erhalten haben. Geprüft beim Release v0.7.8 (08.11.2026): knapp 8 Wochen.
CUTOVER_DATUM = date(2027, 1, 1)

ZERO = Decimal("0.00")

# Dokumenttypen, die nach der neuen Regel gemeldet werden. Abschlagsrechnungen gehören dazu,
# melden selbst aber 0 - gemeldet wird die Schlussrechnung (Issue #419, siehe _betrag()).
# Gutschriften zu diesen Rechnungen melden als Korrektur nach §17 (siehe _korrekturen()).
_DOKUMENT_TYPEN = ("Rechnung", "Abschlagsrechnung")


@dataclass
class IgUmsatz:
    """Ein Beitrag zu ZM L/S bzw. UStVA KZ 41/21 aus einer Rechnung des neuen Verfahrens."""
    rechnung_id: int
    rechnungsnummer: str | None
    kennzeichen: str    # "L" (KZ 41) oder "S" (KZ 21)
    betrag: Decimal     # vorzeichenbehaftet (Korrekturen nach §17 negativ)
    datum: date         # Meldedatum - bestimmt den Monat der UStVA bzw. ZM
    art: str            # "rechnung" | "storno" | "gutschrift" | "gutschrift_storno" | "skonto"
    rechnungsdatum: date | None = None  # nur bei art="rechnung": Datum der Rechnung (Posten-Text)
    nach_storno_original: bool = False  # nur bei art="rechnung": Ersatzrechnung, die erst im
                                        # Monat des Stornos ihres Originals meldet (meldedatum())


# Hinweis beim Buchen (Issue #497): eine freie Buchung auf ig. Lieferung ohne Rechnungsbezug
# zählt weiter nach Buchungsdatum (z. B. wenn die Rechnungen in einem anderen Programm
# entstehen). Gibt es zur selben Leistung eine Rechnung ab CUTOVER_DATUM, meldet diese bereits
# selbst - der Umsatz stünde doppelt in KZ 41 und der ZM. Keine Sperre, nur ein Hinweis.
HINWEIS_FREIE_IG_BUCHUNG = (
    "Gibt es zu diesem Umsatz eine Rechnung in RechnungsFee, buche die Zahlung bitte an der "
    "Rechnung, sonst steht er doppelt in KZ 41/21 und der ZM."
)


def hinweis_freie_ig_buchung(eintrag: Journaleintrag) -> str | None:
    """HINWEIS_FREIE_IG_BUCHUNG für eine Einnahme auf ig. Lieferung (8125/4125) ohne
    rechnung_id ab CUTOVER_DATUM, sonst None. Freie Buchungen auf eine EU-Dienstleistung gibt es
    nicht: KZ 21 und ZM S erkennen die Leistung nur über die Rechnung (ist_reverse_charge)."""
    if (
        eintrag.rechnung_id is None
        and eintrag.art == "Einnahme"
        and eintrag.datum >= CUTOVER_DATUM
        and ist_ig_lieferung_konto(eintrag.konto_skr03, eintrag.konto_skr04)
    ):
        return HINWEIS_FREIE_IG_BUCHUNG
    return None


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


def meldedatum(rechnung: Rechnung, original: Rechnung | None = None) -> date:
    """Datum, dessen Monat die Rechnung in ZM und UStVA KZ 41/21 meldet.

    L: Rechnungsdatum, spätestens das Ende des Monats nach der Lieferung (§18a Abs. 8 Satz 1) -
       eine Rechnung vor der Lieferung (kein Abschlag) meldet im Monat der Rechnung.
    S: Tag der Leistung (§18a Abs. 8 Satz 2).

    Nie vor CUTOVER_DATUM: eine Rechnung ab dem Stichtag über eine Leistung davor wird im ersten
    Monat des neuen Verfahrens gemeldet, nicht rückwirkend in einem Zeitraum, der nach altem
    Verfahren schon abgegeben ist (Rahmen zu #497: nichts rückwirkend, keine Doppel- oder
    Fehlmeldungen).

    original: die stornierte Rechnung des neuen Verfahrens, die diese Ersatzrechnung ersetzt
    (ersatz_fuer_rechnung_id, Issue #304). Die Ersatzrechnung meldet nicht vor deren Storno -
    sonst stünde die Leistung bis zum Storno-Monat doppelt in der Meldung und ein bereits
    abgegebener Monat müsste nachträglich berichtigt werden."""
    if kennzeichen(rechnung) == "L":
        d = min(rechnung.datum, _ende_folgemonat(leistungsdatum(rechnung)))
    else:
        d = leistungsdatum(rechnung)
    if original is not None and original.storniert and original.storno_datum:
        d = max(d, original.storno_datum)
    return max(d, CUTOVER_DATUM)


def _neu_filter(query):
    """Filter für finalisierte Ausgangsrechnungen mit ig. Lieferung oder EU-B2B-Dienstleistung
    ab dem Stichtag - die nach neuer Regel gemeldet werden."""
    return query.filter(
        Rechnung.typ == "ausgang",
        Rechnung.ist_entwurf == False,  # noqa: E712
        Rechnung.dokument_typ.in_(_DOKUMENT_TYPEN),
        Rechnung.datum >= CUTOVER_DATUM,
        (Rechnung.ist_eu_lieferung == True) | (Rechnung.ist_reverse_charge == True),  # noqa: E712
    )


def neue_rechnungen(db: Session) -> list[Rechnung]:
    """Rechnungen des neuen Verfahrens (siehe _neu_filter), Positionen gleich mitgeladen."""
    return _neu_filter(db.query(Rechnung)).options(selectinload(Rechnung.positionen)).all()


def hat_neue_rechnungen(db: Session) -> bool:
    """True, sobald es mindestens eine Rechnung des neuen Verfahrens gibt (Menüpunkt ZM)."""
    return _neu_filter(db.query(Rechnung.id)).first() is not None


def _gutschriften(db: Session, neue_ids: set[int]) -> list[Rechnung]:
    """Gutschriften (auch Entwürfe) zu Rechnungen des neuen Verfahrens - das Verfahren richtet
    sich nach dem Datum der Originalrechnung, nicht nach dem der Gutschrift."""
    if not neue_ids:
        return []
    return (
        db.query(Rechnung)
        .filter(Rechnung.dokument_typ == "Gutschrift", Rechnung.gutschrift_zu_rechnung_id.in_(neue_ids))
        .all()
    )


def neue_rechnung_ids(db: Session) -> set[int]:
    """IDs der Rechnungen des neuen Verfahrens und ihrer Gutschriften. Deren Journalbuchungen
    (Zahlung, Storno-Gegenbuchung, Skonto, Auszahlung/Verrechnung einer Gutschrift) zählen in ZM
    und KZ 41/21 nicht mehr - sonst doppelt; gemeldet wird über ig_umsaetze()."""
    ids = {i for (i,) in _neu_filter(db.query(Rechnung.id)).all()}
    if not ids:
        return ids
    return ids | {i for (i,) in db.query(Rechnung.id).filter(
        Rechnung.dokument_typ == "Gutschrift", Rechnung.gutschrift_zu_rechnung_id.in_(ids),
    ).all()}


def _meldedaten(rechnungen: list[Rechnung]) -> dict[int, date]:
    """meldedatum() je Rechnung; eine Ersatzrechnung sucht ihr Original unter den Rechnungen
    des neuen Verfahrens (ein Original vor dem Stichtag wird nach altem Verfahren storniert)."""
    nach_id = {r.id: r for r in rechnungen}
    return {r.id: meldedatum(r, nach_id.get(r.ersatz_fuer_rechnung_id)) for r in rechnungen}


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


def _ist_storno_gegenbuchung(e: Journaleintrag, rechnung: Rechnung) -> bool:
    """Gegenbuchung aus storno_rechnung() ("STORNO <Beleg>: <Re-Nr> – <Grund>"). Sie steht für
    EÜR auf dem Datum der Originalbuchung (#320); für §17 ist sie im Storno-Betrag enthalten.
    Die Storno-Buchung einer Zahlungskorrektur ("STORNO <Beleg>: Korrektur") ist keine."""
    re_nr = rechnung.rechnungsnummer or f"#{rechnung.id}"
    return bool(rechnung.storniert and e.beschreibung
                and e.beschreibung.startswith("STORNO ") and f": {re_nr} – " in e.beschreibung)


def _korrekturen(rechnungen: list[Rechnung], neue_ids: set[int], meldedaten: dict[int, date],
                 db: Session) -> list[IgUmsatz]:
    """Korrekturen nach §17 UStG (§18a Abs. 7, §18b Satz 4) für Rechnungen des neuen
    Verfahrens - eigene Beträge im Monat des Ereignisses, nie vor dem Meldedatum der Rechnung
    (ein Ereignis davor mindert die Meldung im Meldemonat selbst):

    - Skonto: minus am Datum der Skonto-Buchung; deren Storno per Zahlungskorrektur plus.
    - Gutschrift (finalisiert): ihr Netto (negativ) am Gutschriftsdatum; Storno der Gutschrift
      plus am storno_datum.
    - Storno der Rechnung: am storno_datum minus alles, was die Rechnung bis dahin gemeldet hat
      (Netto bzw. Schlussrechnung nach _betrag(), abzüglich Skonti und Gutschriften bis zum
      Storno) - danach steht sie auf 0. Beiträge mit späterem Datum (etwa eine erst nach dem
      Storno finalisierte Gutschrift oder das Storno einer Gutschrift) entfallen: zu einer
      stornierten Rechnung gibt es nichts mehr zu berichtigen.

    Abschlagsrechnungen melden 0 (Issue #419) und damit auch keine Korrekturen; gemeldet und
    korrigiert wird die Schlussrechnung. Forderungsausfall (§17 Abs. 2 Nr. 1) ist hier noch
    nicht enthalten."""
    ids = [r.id for r in rechnungen if r.dokument_typ != "Abschlagsrechnung"]
    if not ids:
        return []
    skonti: dict[int, list[Journaleintrag]] = {}
    for e in db.query(Journaleintrag).filter(
        Journaleintrag.rechnung_id.in_(ids), Journaleintrag.zahlungsart == "Skonto",
    ).all():
        skonti.setdefault(e.rechnung_id, []).append(e)
    gutschriften: dict[int, list[Rechnung]] = {}
    for g in _gutschriften(db, set(ids)):
        if not g.ist_entwurf:
            gutschriften.setdefault(g.gutschrift_zu_rechnung_id, []).append(g)

    ergebnis: list[IgUmsatz] = []
    for r in rechnungen:
        if r.dokument_typ == "Abschlagsrechnung":
            continue
        kz, ab = kennzeichen(r), meldedaten[r.id]
        beitraege: list[IgUmsatz] = []
        for e in skonti.get(r.id, []):
            if _ist_storno_gegenbuchung(e, r):
                continue
            netto = e.netto_betrag or ZERO
            beitraege.append(IgUmsatz(r.id, r.rechnungsnummer, kz,
                                      -netto if e.art == "Ausgabe" else netto, max(e.datum, ab), "skonto"))
        for g in gutschriften.get(r.id, []):
            netto = g.netto_gesamt or ZERO
            beitraege.append(IgUmsatz(g.id, g.rechnungsnummer, kz, netto, max(g.datum, ab), "gutschrift"))
            if g.storniert and g.storno_datum:
                beitraege.append(IgUmsatz(g.id, g.rechnungsnummer, kz, -netto,
                                          max(g.storno_datum, ab), "gutschrift_storno"))
        if r.storniert and r.storno_datum:
            storno_am = max(r.storno_datum, ab)
            # nach dem Storno steht die Rechnung auf 0 - spätere Beiträge melden nichts mehr
            beitraege = [b for b in beitraege if b.datum <= storno_am]
            gemeldet = _betrag(r, neue_ids) + sum((b.betrag for b in beitraege), ZERO)
            beitraege.append(IgUmsatz(r.id, r.rechnungsnummer, kz, -gemeldet, storno_am, "storno"))
        ergebnis += beitraege
    return ergebnis


def ig_umsaetze(von: date, bis: date, db: Session) -> list[IgUmsatz]:
    """Gemeinsame Quelle für ZM (L/S) und UStVA (KZ 41/21) für Rechnungen ab CUTOVER_DATUM:
    alle Beiträge, deren Meldedatum im Zeitraum [von, bis] liegt."""
    rechnungen = neue_rechnungen(db)
    neue_ids = {r.id for r in rechnungen}
    meldedaten = _meldedaten(rechnungen)
    umsaetze = [
        IgUmsatz(r.id, r.rechnungsnummer, kennzeichen(r), _betrag(r, neue_ids), meldedaten[r.id], "rechnung",
                 r.datum, meldedaten[r.id] > meldedatum(r))
        for r in rechnungen
    ]
    umsaetze += _korrekturen(rechnungen, neue_ids, meldedaten, db)
    return [u for u in umsaetze if von <= u.datum <= bis and u.betrag != 0]
