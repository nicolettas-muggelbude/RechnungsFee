"""
Zusammenfassende Meldung (ZM) – §18a UStG

Pflicht für alle USt-pflichtigen Unternehmer mit innergemeinschaftlichen
Lieferungen oder Dienstleistungen. Kleinunternehmer §19 sind befreit.

Kennzeichen (wie ELSTER):
  L = Innergemeinschaftliche Lieferung  (konto_skr03=8125 / konto_skr04=3125)
  S = Sonstige Leistung §3a Abs. 2 UStG an EU-Unternehmer (Ausgangsrechnung mit
      ist_reverse_charge, Kunde schuldet die Steuer) – gleiche Quelle wie UStVA KZ 21
  (D = Dreiecksgeschäft – nicht unterstützt)

Rhythmus / Frist:
  < 50.000 € ig. Lieferungen pro Quartal → quartalsweise, bis 25. des Folgemonats
  ≥ 50.000 € ig. Lieferungen pro Quartal → monatlich,    bis 25. des Folgemonats
"""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from database.connection import get_db
from utils.konten import IG_LIEFERUNG_SKR04
from database.models import Journaleintrag, Rechnung, Kunde, Unternehmen
from utils.elster import ElsterExportFehler, build_zm_csv

router = APIRouter(prefix="/api/zm", tags=["ZM"])

ZERO = Decimal("0.00")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _zeitraum_grenzen(zeitraum: str) -> tuple[date, date, str]:
    if "-Q" in zeitraum:
        j, q = zeitraum.split("-Q")
        jahr, q = int(j), int(q)
        vm = (q - 1) * 3 + 1
        bm = vm + 2
        return date(jahr, vm, 1), date(jahr, bm, calendar.monthrange(jahr, bm)[1]), "quartal"
    j, m = zeitraum.split("-")
    jahr, monat = int(j), int(m)
    return date(jahr, monat, 1), date(jahr, monat, calendar.monthrange(jahr, monat)[1]), "monat"


def _deadline(zeitraum: str) -> date:
    if "-Q" in zeitraum:
        j, q = zeitraum.split("-Q")
        bm = int(q) * 3
        if bm == 12:
            return date(int(j) + 1, 1, 25)
        return date(int(j), bm + 1, 25)
    j, m = zeitraum.split("-")
    monat = int(m)
    if monat == 12:
        return date(int(j) + 1, 1, 25)
    return date(int(j), monat + 1, 25)


def _letztes_quartal(heute: date) -> str:
    q = (heute.month - 1) // 3  # laufendes Quartal 0-basiert
    if q == 0:
        return f"{heute.year - 1}-Q4"
    return f"{heute.year}-Q{q}"


def _zeitraum_label(zeitraum: str) -> str:
    MONATE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    if "-Q" in zeitraum:
        j, q = zeitraum.split("-Q")
        return f"Q{q}/{j}"
    j, m = zeitraum.split("-")
    return f"{MONATE[int(m)]} {j}"


@dataclass
class _IgBuchung:
    netto_betrag: Decimal   # vorzeichenbehaftet - Storno-Gegenbuchungen zaehlen negativ
    kennzeichen: str        # "L" oder "S"
    rechnung_id: int | None


def _ig_lieferung_filter(e):
    # SKR04 4125 seit Migration 179; 3125 (Verbindlichkeitenkonto) steht noch in alten Konto-Snapshots
    return (e.konto_skr03.in_(["8125"])) | (e.konto_skr04.in_(IG_LIEFERUNG_SKR04))


def _eu_dl_rechnungen():
    """Ausgangsrechnungen mit EU-B2B-Dienstleistung (§3a Abs. 2 UStG) - wie UStVA KZ 21."""
    return select(Rechnung.id).where(Rechnung.typ == "ausgang", Rechnung.ist_reverse_charge == True)  # noqa: E712


def _ig_lieferung_rechnungen():
    """Ausgangsrechnungen mit ig. Lieferung (§4 Nr. 1b UStG) - wie UStVA KZ 41 (Issue #458)."""
    return select(Rechnung.id).where(Rechnung.typ == "ausgang", Rechnung.ist_eu_lieferung == True)  # noqa: E712


def _ig_eintraege(von: date, bis: date, db: Session) -> list[_IgBuchung]:
    """Alle ZM-relevanten Buchungen im Zeitraum.

    L - ig. Lieferung (§4 Nr. 1b, Konto 8125/3125): Einnahme-Buchungen plus deren Storno-
    Gegenbuchungen. Eine Storno-Gegenbuchung hat art="Ausgabe" (Original->Storno kehrt die
    Buchungsrichtung um, siehe rechnungen.storno_rechnung()) und wird über gruppe_id auf ihre
    Original-Buchung zurückverfolgt und negativ gezählt.

    S - sonstige Leistung an EU-Unternehmer (Issue #456): Erkennung wie UStVA KZ 21 über die
    rechnung_id einer Ausgangsrechnung mit ist_reverse_charge, nicht über ust_sonderfall - seit
    #372 bekommen diese Zahlungen keinen Sonderfall mehr. Einnahme zählt positiv, Ausgabe
    (Storno, Gutschrift-Zahlung) negativ; Skonto-Gegeneinträge bleiben außen vor, weil der
    Zahlungseingang den reduzierten Betrag bereits enthält (identisch zu ustva._berechne_kz()).

    Eingangsseitige §13b-/ig.-Erwerb-Buchungen (wir als Leistungsempfänger) gehören nie in die
    ZM - auch nicht deren Storno-Gegenbuchung (art="Einnahme", ust_sonderfall="13b_abs1"), die
    ein früherer Sonderfall-Filter fälschlich als Dienstleistung gemeldet hatte."""
    ergebnis: list[_IgBuchung] = []

    einnahmen = db.query(Journaleintrag).filter(
        Journaleintrag.datum >= von, Journaleintrag.datum <= bis,
        Journaleintrag.art == "Einnahme", _ig_lieferung_filter(Journaleintrag),
    ).all()
    for e in einnahmen:
        ergebnis.append(_IgBuchung(e.netto_betrag or ZERO, "L", e.rechnung_id))

    Original = aliased(Journaleintrag)
    stornos = (
        db.query(Journaleintrag, Original)
        .join(Original, Journaleintrag.gruppe_id == Original.id)
        .filter(
            Journaleintrag.datum >= von, Journaleintrag.datum <= bis,
            Journaleintrag.art == "Ausgabe",
            Original.art == "Einnahme",
            _ig_lieferung_filter(Original),
        )
        .all()
    )
    for storno_e, orig_e in stornos:
        ergebnis.append(_IgBuchung(-(storno_e.netto_betrag or ZERO), "L", orig_e.rechnung_id))

    # Über die Rechnung erkannt: sonstige Leistungen (S) und ig. Lieferungen (L) aus Rechnungen,
    # deren Zahlungsbuchung auf einer anderen Kategorie als 8125/3125 liegt (Issue #458)
    lieferung_ids = {r[0] for r in db.execute(_ig_lieferung_rechnungen()).all()}
    ueber_rechnung = db.query(Journaleintrag).filter(
        Journaleintrag.datum >= von, Journaleintrag.datum <= bis,
        Journaleintrag.rechnung_id.in_(_eu_dl_rechnungen()) | Journaleintrag.rechnung_id.in_(_ig_lieferung_rechnungen()),
    ).all()
    for e in ueber_rechnung:
        # schon oben als L über das Konto gezählt (in Python statt per SQL-NOT: Konten sind hier oft NULL)
        if e.konto_skr03 == "8125" or e.konto_skr04 in IG_LIEFERUNG_SKR04:
            continue
        kz = "L" if e.rechnung_id in lieferung_ids else "S"
        if e.art == "Einnahme":
            ergebnis.append(_IgBuchung(e.netto_betrag or ZERO, kz, e.rechnung_id))
        elif e.art == "Ausgabe" and e.zahlungsart != "Skonto":
            ergebnis.append(_IgBuchung(-(e.netto_betrag or ZERO), kz, e.rechnung_id))

    return ergebnis


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ZMPosition(BaseModel):
    ust_idnr: str
    land: str
    kennzeichen: str          # L oder S
    betrag: Decimal

class ZMErgebnis(BaseModel):
    zeitraum: str
    zeitraum_label: str
    von: date
    bis: date
    deadline: date
    positionen: list[ZMPosition]
    gesamt: Decimal
    ueber_50k: bool           # → monatliche ZM erforderlich

class ZMPruefung(BaseModel):
    faellig: bool
    hat_ig_eintraege: bool = False   # True wenn irgendwann ig-Buchungen existieren → ZM-Menüpunkt zeigen
    zeitraum: str = ""
    zeitraum_label: str = ""
    deadline: str = ""
    grund: str = ""           # "kleinunternehmer" | "keine_lieferungen" | "faellig" | "abgelaufen"


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

def _hat_ig_eintraege_gesamt(db: Session) -> bool:
    """True wenn überhaupt je ig-Buchungen existieren (für Sidebar-Sichtbarkeit)."""
    return db.query(Journaleintrag).filter(
        Journaleintrag.art == "Einnahme",
        _ig_lieferung_filter(Journaleintrag)
        | Journaleintrag.rechnung_id.in_(_eu_dl_rechnungen())
        | Journaleintrag.rechnung_id.in_(_ig_lieferung_rechnungen()),
    ).limit(1).count() > 0


@router.get("/pruefen", response_model=ZMPruefung)
def zm_pruefen(db: Session = Depends(get_db)):
    """Prüft ob eine ZM fällig ist – für Dashboard-Hinweis und Sidebar-Sichtbarkeit."""
    unt = db.query(Unternehmen).first()
    if not unt or unt.ist_kleinunternehmer:
        return ZMPruefung(faellig=False, grund="kleinunternehmer")

    hat_ig = _hat_ig_eintraege_gesamt(db)

    heute = date.today()
    zeitraum = _letztes_quartal(heute)
    deadline = _deadline(zeitraum)

    if heute > deadline:
        return ZMPruefung(faellig=False, hat_ig_eintraege=hat_ig, grund="abgelaufen",
                          zeitraum=zeitraum, deadline=deadline.isoformat())

    von, bis, _ = _zeitraum_grenzen(zeitraum)
    eintraege = _ig_eintraege(von, bis, db)
    if not eintraege:
        return ZMPruefung(faellig=False, hat_ig_eintraege=hat_ig, grund="keine_lieferungen", zeitraum=zeitraum)

    return ZMPruefung(
        faellig=True,
        hat_ig_eintraege=True,
        grund="faellig",
        zeitraum=zeitraum,
        zeitraum_label=_zeitraum_label(zeitraum),
        deadline=deadline.isoformat(),
    )


@router.get("/berechnen", response_model=ZMErgebnis)
def zm_berechnen(
    zeitraum: str = Query(..., description="YYYY-QN oder YYYY-MM"),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")
    if unt.ist_kleinunternehmer:
        raise HTTPException(422, "Kleinunternehmer §19 sind von der ZM befreit.")

    try:
        von, bis, _ = _zeitraum_grenzen(zeitraum)
    except Exception:
        raise HTTPException(422, f"Ungültiges Zeitraum-Format: {zeitraum!r}")

    deadline = _deadline(zeitraum)
    eintraege = _ig_eintraege(von, bis, db)

    # Gruppieren nach USt-IdNr. + Kennzeichen
    gruppen: dict[tuple[str, str, str], Decimal] = {}
    for buchung in eintraege:
        # USt-IdNr. und Land aus verlinktem Kunden holen
        ust_idnr = ""
        land = ""
        if buchung.rechnung_id:
            rechnung = db.query(Rechnung).filter(Rechnung.id == buchung.rechnung_id).first()
            if rechnung and rechnung.kunde_id:
                kunde = db.query(Kunde).filter(Kunde.id == rechnung.kunde_id).first()
                if kunde:
                    ust_idnr = kunde.ust_idnr or ""
                    land = kunde.land or ""

        key = (ust_idnr or "unbekannt", land or "?", buchung.kennzeichen)
        gruppen[key] = gruppen.get(key, ZERO) + buchung.netto_betrag

    positionen = [
        ZMPosition(ust_idnr=uid, land=land, kennzeichen=kz,
                   betrag=betrag.quantize(Decimal("0.01")))
        for (uid, land, kz), betrag in sorted(gruppen.items())
        if betrag != 0  # vollstaendig stornierte Gruppen (z.B. eine einzelne stornierte
                         # Rechnung) nicht als leere Position an das Finanzamt melden
    ]
    gesamt = sum(p.betrag for p in positionen)

    return ZMErgebnis(
        zeitraum=zeitraum,
        zeitraum_label=_zeitraum_label(zeitraum),
        von=von, bis=bis, deadline=deadline,
        positionen=positionen,
        gesamt=gesamt,
        ueber_50k=gesamt >= Decimal("50000"),
    )


@router.get("/csv")
def zm_csv(
    zeitraum: str = Query(..., description="YYYY-QN oder YYYY-MM"),
    db: Session = Depends(get_db),
):
    """ZM als CSV-Meldeliste für den Import in Mein ELSTER. Issue #360."""
    ergebnis = zm_berechnen(zeitraum=zeitraum, db=db)
    try:
        csv_bytes = build_zm_csv(ergebnis.positionen)
    except ElsterExportFehler as exc:
        raise HTTPException(422, str(exc))
    return StreamingResponse(
        BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ZM_{zeitraum}_ELSTER.csv"'},
    )
