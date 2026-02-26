"""
Rechnungen-API (Eingang + Ausgang) mit Kassenbuch-Verknüpfung.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import (
    Rechnung, Rechnungsposition, Kassenbucheintrag,
    Kategorie, Unternehmen, Nummernkreis,
)
from utils.signatur import signatur_kassenbucheintrag
from .schemas_rechnungen import (
    RechnungCreate, RechnungUpdate, RechnungResponse,
    BarZahlungCreate, BarZahlungResult, ZahlungKompakt,
)

router = APIRouter(prefix="/api/rechnungen", tags=["Rechnungen"])


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

import re as _re


def _belegnr_aus_format(format_str: str, datum: date, nr: int) -> str:
    year_4 = str(datum.year)
    year_2 = year_4[-2:]
    result = format_str.replace("YYYY", year_4).replace("YY", year_2)

    def _pad(m: _re.Match) -> str:
        return str(nr).zfill(len(m.group()))

    return _re.sub(r"#+", _pad, result)


def _naechste_belegnr_kassenbuch(db: Session, datum: date) -> str:
    """Kassenbuch-Belegnummer (analog zu kassenbuch.py)."""
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "kassenbuch").first()
    if not nk:
        count = db.query(Kassenbucheintrag).count()
        return f"{str(datum.year)[-2:]}{count + 1:04d}"
    if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != datum.year:
        nk.naechste_nr = 1
    nk.letztes_jahr = datum.year
    nr = nk.naechste_nr
    nk.naechste_nr += 1
    return _belegnr_aus_format(nk.format, datum, nr)


def _berechne_position(pos_data) -> tuple[Decimal, Decimal, Decimal]:
    """Gibt (ust_betrag, brutto, netto_rund) zurück."""
    netto = pos_data.netto.quantize(Decimal("0.01"), ROUND_HALF_UP)
    if pos_data.ust_satz == 0:
        return Decimal("0.00"), netto, netto
    ust_betrag = (netto * pos_data.ust_satz / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    brutto = netto + ust_betrag
    return ust_betrag, brutto, netto


def _aktualisiere_zahlungsstatus(rechnung: Rechnung) -> None:
    """Berechnet bezahlt_betrag aus verknüpften Kassenbucheinträgen und setzt zahlungsstatus."""
    bezahlt = sum(e.brutto_betrag for e in rechnung.kassenbucheintraege)
    rechnung.bezahlt_betrag = bezahlt.quantize(Decimal("0.01"), ROUND_HALF_UP) if bezahlt else Decimal("0.00")

    if rechnung.bezahlt_betrag >= rechnung.brutto_gesamt:
        rechnung.zahlungsstatus = "bezahlt"
        rechnung.bezahlt = True
        rechnung.zahlungsdatum = date.today()
    elif rechnung.bezahlt_betrag > 0:
        rechnung.zahlungsstatus = "teilweise"
        rechnung.bezahlt = False
    else:
        rechnung.zahlungsstatus = "offen"
        rechnung.bezahlt = False
        rechnung.zahlungsdatum = None


def _partner_name(rechnung: Rechnung) -> str:
    """Lesbare Bezeichnung des Rechnungspartners."""
    if rechnung.partner_freitext:
        return rechnung.partner_freitext
    if rechnung.typ == "ausgang" and rechnung.kunde:
        parts = [rechnung.kunde.firmenname or "", rechnung.kunde.vorname or "", rechnung.kunde.nachname or ""]
        return " ".join(p for p in parts if p)
    if rechnung.typ == "eingang" and rechnung.lieferant:
        parts = [rechnung.lieferant.firmenname or "", rechnung.lieferant.vorname or "", rechnung.lieferant.nachname or ""]
        return " ".join(p for p in parts if p)
    return "Unbekannt"


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/offene", response_model=list[RechnungResponse])
def get_offene_rechnungen(db: Session = Depends(get_db)):
    """Offene und teilweise bezahlte Rechnungen (für Zahlungs-Vorschläge)."""
    rechnungen = (
        db.query(Rechnung)
        .filter(Rechnung.zahlungsstatus.in_(["offen", "teilweise"]))
        .order_by(Rechnung.datum.desc())
        .all()
    )
    return [RechnungResponse.from_orm_extended(r) for r in rechnungen]


@router.get("", response_model=list[RechnungResponse])
def list_rechnungen(
    typ: Optional[str] = Query(None, description="eingang|ausgang"),
    zahlungsstatus: Optional[str] = Query(None, description="offen|teilweise|bezahlt"),
    monat: Optional[str] = Query(None, description="YYYY-MM"),
    datum_von: Optional[date] = Query(None, description="YYYY-MM-DD"),
    datum_bis: Optional[date] = Query(None, description="YYYY-MM-DD"),
    kunde_id: Optional[int] = None,
    lieferant_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Rechnung)
    if typ:
        if typ not in ("eingang", "ausgang"):
            raise HTTPException(status_code=422, detail="typ muss 'eingang' oder 'ausgang' sein")
        q = q.filter(Rechnung.typ == typ)
    if zahlungsstatus:
        q = q.filter(Rechnung.zahlungsstatus == zahlungsstatus)
    if monat:
        try:
            jahr, mon = monat.split("-")
            q = q.filter(
                extract("year", Rechnung.datum) == int(jahr),
                extract("month", Rechnung.datum) == int(mon),
            )
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="monat muss im Format YYYY-MM sein")
    if datum_von:
        q = q.filter(Rechnung.datum >= datum_von)
    if datum_bis:
        q = q.filter(Rechnung.datum <= datum_bis)
    if kunde_id is not None:
        q = q.filter(Rechnung.kunde_id == kunde_id)
    if lieferant_id is not None:
        q = q.filter(Rechnung.lieferant_id == lieferant_id)
    rechnungen = q.order_by(Rechnung.datum.desc(), Rechnung.id.desc()).all()
    return [RechnungResponse.from_orm_extended(r) for r in rechnungen]


@router.get("/{rechnung_id}", response_model=RechnungResponse)
def get_rechnung(rechnung_id: int, db: Session = Depends(get_db)):
    r = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    return RechnungResponse.from_orm_extended(r)


@router.post("", response_model=RechnungResponse, status_code=201)
def create_rechnung(data: RechnungCreate, db: Session = Depends(get_db)):
    """Rechnung mit Positionen anlegen. Summen werden automatisch berechnet."""
    unternehmen = db.query(Unternehmen).first()
    ist_kleinunternehmer = unternehmen.ist_kleinunternehmer if unternehmen else False

    # Rechnungsnummer: aus Nummernkreis wenn nicht angegeben
    rechnungsnummer = data.rechnungsnummer
    if not rechnungsnummer:
        nk_typ = "rechnung_ausgang" if data.typ == "ausgang" else "rechnung_eingang"
        nk = db.query(Nummernkreis).filter(Nummernkreis.typ == nk_typ).first()
        if nk:
            if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != data.datum.year:
                nk.naechste_nr = 1
            nk.letztes_jahr = data.datum.year
            nr = nk.naechste_nr
            nk.naechste_nr += 1
            prefix = "RE" if data.typ == "ausgang" else "ER"
            rechnungsnummer = f"{prefix}-{_belegnr_aus_format(nk.format, data.datum, nr)}"
        else:
            count = db.query(Rechnung).filter(Rechnung.typ == data.typ).count()
            prefix = "RE" if data.typ == "ausgang" else "ER"
            rechnungsnummer = f"{prefix}-{str(data.datum.year)[-2:]}{count + 1:04d}"

    rechnung = Rechnung(
        typ=data.typ,
        rechnungsnummer=rechnungsnummer,
        datum=data.datum,
        leistungsdatum=data.leistungsdatum,
        faellig_am=data.faellig_am,
        kunde_id=data.kunde_id,
        lieferant_id=data.lieferant_id,
        partner_freitext=data.partner_freitext,
        kategorie_id=data.kategorie_id,
        notizen=data.notizen,
        ist_entwurf=data.ist_entwurf,
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=Decimal("0.00"),
        ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()  # ID erzeugen

    netto_sum = Decimal("0.00")
    ust_sum = Decimal("0.00")

    for i, pos_data in enumerate(data.positionen, start=1):
        ust_satz = Decimal("0") if ist_kleinunternehmer else pos_data.ust_satz
        ust_betrag, brutto, netto = _berechne_position(pos_data)
        if ist_kleinunternehmer:
            ust_betrag = Decimal("0.00")
            brutto = netto

        pos = Rechnungsposition(
            rechnung_id=rechnung.id,
            position_nr=i,
            beschreibung=pos_data.beschreibung,
            menge=pos_data.menge,
            einheit=pos_data.einheit,
            netto=netto,
            ust_satz=ust_satz,
            ust_betrag=ust_betrag,
            brutto=brutto,
        )
        db.add(pos)
        netto_sum += netto * pos_data.menge
        ust_sum += ust_betrag * pos_data.menge

    rechnung.netto_gesamt = netto_sum.quantize(Decimal("0.01"), ROUND_HALF_UP)
    rechnung.ust_gesamt = ust_sum.quantize(Decimal("0.01"), ROUND_HALF_UP)
    rechnung.brutto_gesamt = (rechnung.netto_gesamt + rechnung.ust_gesamt).quantize(Decimal("0.01"), ROUND_HALF_UP)

    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.put("/{rechnung_id}", response_model=RechnungResponse)
def update_rechnung(rechnung_id: int, data: RechnungUpdate, db: Session = Depends(get_db)):
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if not rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Nur Entwürfe können bearbeitet werden.")

    unternehmen = db.query(Unternehmen).first()
    ist_kleinunternehmer = unternehmen.ist_kleinunternehmer if unternehmen else False

    for field in ("rechnungsnummer", "datum", "leistungsdatum", "faellig_am", "kunde_id",
                  "lieferant_id", "partner_freitext", "kategorie_id", "notizen"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(rechnung, field, val)

    if data.positionen is not None:
        # Bestehende Positionen löschen und neu anlegen
        for pos in rechnung.positionen:
            db.delete(pos)
        db.flush()

        netto_sum = Decimal("0.00")
        ust_sum = Decimal("0.00")
        for i, pos_data in enumerate(data.positionen, start=1):
            ust_satz = Decimal("0") if ist_kleinunternehmer else pos_data.ust_satz
            ust_betrag, brutto, netto = _berechne_position(pos_data)
            if ist_kleinunternehmer:
                ust_betrag = Decimal("0.00")
                brutto = netto
            pos = Rechnungsposition(
                rechnung_id=rechnung.id,
                position_nr=i,
                beschreibung=pos_data.beschreibung,
                menge=pos_data.menge,
                einheit=pos_data.einheit,
                netto=netto,
                ust_satz=ust_satz,
                ust_betrag=ust_betrag,
                brutto=brutto,
            )
            db.add(pos)
            netto_sum += netto * pos_data.menge
            ust_sum += ust_betrag * pos_data.menge

        rechnung.netto_gesamt = netto_sum.quantize(Decimal("0.01"), ROUND_HALF_UP)
        rechnung.ust_gesamt = ust_sum.quantize(Decimal("0.01"), ROUND_HALF_UP)
        rechnung.brutto_gesamt = (rechnung.netto_gesamt + rechnung.ust_gesamt).quantize(Decimal("0.01"), ROUND_HALF_UP)

    if data.ist_entwurf is not None:
        rechnung.ist_entwurf = data.ist_entwurf

    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.post("/{rechnung_id}/finalisieren", response_model=RechnungResponse)
def finalisiere_rechnung(rechnung_id: int, db: Session = Depends(get_db)):
    """Entwurf finalisieren – danach nicht mehr bearbeitbar."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if not rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Rechnung ist bereits finalisiert.")
    rechnung.ist_entwurf = False
    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.delete("/{rechnung_id}", status_code=204)
def delete_rechnung(rechnung_id: int, db: Session = Depends(get_db)):
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if not rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Nur Entwürfe können gelöscht werden.")
    db.delete(rechnung)
    db.commit()


# ---------------------------------------------------------------------------
# Zahlungs-Endpunkte
# ---------------------------------------------------------------------------

@router.post("/{rechnung_id}/zahlung-bar", response_model=BarZahlungResult, status_code=201)
def zahlung_bar_erstellen(rechnung_id: int, data: BarZahlungCreate, db: Session = Depends(get_db)):
    """
    Erstellt eine Kassenbuchung für eine Bar-/Kartenzahlung und verknüpft sie mit der Rechnung.
    Bei Eingangsrechnung → Ausgabe, bei Ausgangsrechnung → Einnahme.
    """
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")

    restbetrag = rechnung.brutto_gesamt - rechnung.bezahlt_betrag
    if restbetrag <= 0:
        raise HTTPException(status_code=409, detail="Rechnung ist bereits vollständig bezahlt.")

    betrag = data.betrag if data.betrag is not None else restbetrag
    if betrag > restbetrag:
        raise HTTPException(
            status_code=422,
            detail=f"Betrag ({betrag}) übersteigt den Restbetrag ({restbetrag}).",
        )

    art = "Einnahme" if rechnung.typ == "ausgang" else "Ausgabe"
    partner = _partner_name(rechnung)
    beschreibung = data.beschreibung or f"Zahlung {rechnung.rechnungsnummer}: {partner}"

    # Kategorie der Rechnung übernehmen
    kategorie_id = rechnung.kategorie_id
    unternehmen = db.query(Unternehmen).first()
    ust_satz = Decimal("0")
    steuerbefreiung_grund = None

    if unternehmen and unternehmen.ist_kleinunternehmer:
        steuerbefreiung_grund = "§19 UStG"
    elif rechnung.positionen:
        # USt-Satz aus erster Position übernehmen (vereinfacht)
        ust_satz = rechnung.positionen[0].ust_satz

    # Netto aus Brutto berechnen
    if ust_satz > 0:
        netto = (betrag * 100 / (100 + ust_satz)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        ust_betrag = (betrag - netto).quantize(Decimal("0.01"), ROUND_HALF_UP)
    else:
        netto = betrag
        ust_betrag = Decimal("0.00")

    belegnr = _naechste_belegnr_kassenbuch(db, data.datum)

    eintrag = Kassenbucheintrag(
        datum=data.datum,
        belegnr=belegnr,
        beschreibung=beschreibung,
        kategorie_id=kategorie_id,
        zahlungsart=data.zahlungsart,
        art=art,
        netto_betrag=netto,
        ust_satz=ust_satz,
        ust_betrag=ust_betrag,
        brutto_betrag=betrag,
        vorsteuerabzug=(art == "Ausgabe" and ust_satz > 0),
        steuerbefreiung_grund=steuerbefreiung_grund,
        rechnung_id=rechnung_id,
        immutable=True,
    )
    eintrag.signatur = signatur_kassenbucheintrag(eintrag)
    db.add(eintrag)
    db.flush()

    # Zahlung finalisiert Entwurf automatisch
    rechnung.ist_entwurf = False

    # Zahlungsstatus der Rechnung aktualisieren
    _aktualisiere_zahlungsstatus(rechnung)

    db.commit()
    db.refresh(rechnung)
    db.refresh(eintrag)

    return BarZahlungResult(
        kassenbucheintrag_id=eintrag.id,
        kassenbucheintrag_belegnr=eintrag.belegnr,
        rechnung=RechnungResponse.from_orm_extended(rechnung),
    )


@router.post("/{rechnung_id}/storno", response_model=RechnungResponse)
def storno_rechnung(rechnung_id: int, db: Session = Depends(get_db)):
    """Rechnung als storniert markieren (irreversibel)."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if rechnung.ist_entwurf:
        raise HTTPException(status_code=409, detail="Entwürfe können nicht storniert werden. Bitte den Entwurf löschen.")
    if rechnung.storniert:
        raise HTTPException(status_code=409, detail="Rechnung ist bereits storniert.")
    if rechnung.kassenbucheintraege:
        raise HTTPException(
            status_code=409,
            detail="Rechnung hat verknüpfte Kassenbucheinträge und kann nicht storniert werden.",
        )
    rechnung.storniert = True
    rechnung.immutable = True
    db.commit()
    db.refresh(rechnung)
    return RechnungResponse.from_orm_extended(rechnung)


@router.get("/{rechnung_id}/zahlungen", response_model=list[ZahlungKompakt])
def get_rechnung_zahlungen(rechnung_id: int, db: Session = Depends(get_db)):
    """Alle verknüpften Kassenbucheinträge für eine Rechnung."""
    rechnung = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    return [
        ZahlungKompakt(
            id=e.id,
            belegnr=e.belegnr,
            datum=e.datum,
            brutto_betrag=e.brutto_betrag,
            art=e.art,
            zahlungsart=e.zahlungsart,
        )
        for e in rechnung.kassenbucheintraege
    ]
