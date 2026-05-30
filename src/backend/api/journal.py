"""
Journal-API (GoBD-konform, unveränderbar).
Kein PUT/DELETE – nur Storno als Gegenbuchung.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import func, extract, or_
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Journaleintrag, Kategorie, Unternehmen, Nummernkreis
from utils.signatur import signatur_journaleintrag
from .schemas import (
    JournalEintragCreate,
    JournalEintragResponse,
    StornoRequest,
    SplitBuchungCreate,
    MonatsUebersicht,
)

router = APIRouter(prefix="/api/journal", tags=["Journal"])


import re as _re


def _belegnr_aus_format(format_str: str, datum: date, nr: int) -> str:
    """Wendet das Format-Template an. Y=Jahrsstelle, MM=Monat, TT=Tag, #=Nummernstelle."""
    year_4 = str(datum.year)
    year_2 = year_4[-2:]
    month  = f"{datum.month:02d}"
    day    = f"{datum.day:02d}"
    result = (format_str
              .replace("YYYY", year_4)
              .replace("YY",   year_2)
              .replace("MM",   month)
              .replace("TT",   day))

    def _pad(m: _re.Match) -> str:
        return str(nr).zfill(len(m.group()))

    return _re.sub(r"#+", _pad, result)


def _naechste_belegnr(db: Session, datum: date) -> str:
    """Liest den Journal-Nummernkreis, generiert die nächste Belegnummer
    und speichert den inkrementierten Zähler (atomar im selben Commit)."""
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "journal").first()
    if not nk:
        # Fallback falls Seed fehlt
        count = db.query(Journaleintrag).count()
        return f"{str(datum.year)[-2:]}{count + 1:04d}"

    # Jahreswechsel-Reset
    if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != datum.year:
        nk.naechste_nr = 1
    nk.letztes_jahr = datum.year

    nr = nk.naechste_nr
    nk.naechste_nr += 1
    # Wird im selben db.commit() des Eintrags gespeichert
    return _belegnr_aus_format(nk.format, datum, nr)


def _berechne_ust(brutto: Decimal, ust_satz: Decimal) -> tuple[Decimal, Decimal]:
    """Gibt (netto, ust_betrag) zurück. ROUND_HALF_UP auf 2 Stellen."""
    if ust_satz == 0:
        return brutto, Decimal("0.00")
    netto = (brutto * 100 / (100 + ust_satz)).quantize(Decimal("0.01"), ROUND_HALF_UP)
    ust_betrag = (brutto - netto).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return netto, ust_betrag


def _berechne_vorsteuer(ust_betrag: Decimal, vorsteuerabzug: bool, kat) -> Decimal:
    """Tatsächlich abziehbarer Vorsteuer-Betrag.
    Berücksichtigt kat.vorsteuer_prozent (z.B. 70 bei Bewirtungskosten → 70% von ust_betrag).
    Storno-Einträge übergeben -ust_betrag damit sich Originalwert und Storno aufheben."""
    if not vorsteuerabzug or ust_betrag == 0:
        return Decimal("0.00")
    if kat is not None and int(kat.vorsteuer_prozent) < 100:
        return (ust_betrag * kat.vorsteuer_prozent / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return ust_betrag


def _ust_konto(art: str, ust_satz: Decimal) -> tuple[str | None, str | None]:
    """Gibt (konto_skr03, konto_skr04) für den USt-Anteil zurück."""
    satz = int(ust_satz)
    if art == "Einnahme":
        skr03 = {19: "1776", 7: "1771"}.get(satz)
        skr04 = {19: "3806", 7: "3801"}.get(satz)
    else:
        skr03 = {19: "1575", 7: "1570"}.get(satz)
        skr04 = {19: "1406", 7: "1401"}.get(satz)
    return skr03, skr04


def _get_bar_kassenstand(db: Session) -> Decimal:
    """Gibt den aktuellen Kassenstand der Barkasse zurück (nur Bar-Buchungen)."""
    einnahmen = db.query(func.sum(Journaleintrag.brutto_betrag)).filter(
        Journaleintrag.art == "Einnahme",
        Journaleintrag.zahlungsart == "Bar",
    ).scalar() or Decimal("0")
    ausgaben = db.query(func.sum(Journaleintrag.brutto_betrag)).filter(
        Journaleintrag.art == "Ausgabe",
        Journaleintrag.zahlungsart == "Bar",
    ).scalar() or Decimal("0")
    return Decimal(str(einnahmen)) - Decimal(str(ausgaben))


@router.get("/kassenstand")
def get_kassenstand(db: Session = Depends(get_db)):
    """Gibt den aktuellen Kassenstand der Barkasse zurück."""
    return {"kassenstand": str(_get_bar_kassenstand(db))}


@router.get("/naechste-belegnr")
def naechste_belegnr(datum: date = Query(default=None), db: Session = Depends(get_db)):
    """Gibt die nächste freie Belegnummer zurück."""
    d = datum or date.today()
    return {"belegnr": _naechste_belegnr(db, d)}


@router.get("/statistik/monat", response_model=MonatsUebersicht)
def monat_statistik(monat: str = Query(..., description="Format: YYYY-MM"), db: Session = Depends(get_db)):
    """Monatsstatistik: Einnahmen, Ausgaben, Saldo."""
    try:
        jahr, mon = monat.split("-")
        jahr_int, mon_int = int(jahr), int(mon)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="monat muss im Format YYYY-MM sein")

    # Privateinlagen/-entnahmen (kontenart="Privat") gehören nicht zu den
    # betrieblichen Einnahmen/Ausgaben und werden herausgefiltert.
    betrieb_filter = or_(
        Journaleintrag.kategorie_id.is_(None),
        Kategorie.kontenart != "Privat",
    )
    einnahmen = (
        db.query(func.sum(Journaleintrag.brutto_betrag))
        .outerjoin(Journaleintrag.kategorie)
        .filter(
            extract("year", Journaleintrag.datum) == jahr_int,
            extract("month", Journaleintrag.datum) == mon_int,
            Journaleintrag.art == "Einnahme",
            betrieb_filter,
        )
        .scalar()
        or Decimal("0")
    )
    ausgaben = (
        db.query(func.sum(Journaleintrag.brutto_betrag))
        .outerjoin(Journaleintrag.kategorie)
        .filter(
            extract("year", Journaleintrag.datum) == jahr_int,
            extract("month", Journaleintrag.datum) == mon_int,
            Journaleintrag.art == "Ausgabe",
            betrieb_filter,
        )
        .scalar()
        or Decimal("0")
    )
    anzahl = (
        db.query(func.count(Journaleintrag.id))
        .filter(
            extract("year", Journaleintrag.datum) == jahr_int,
            extract("month", Journaleintrag.datum) == mon_int,
        )
        .scalar()
        or 0
    )
    return MonatsUebersicht(
        monat=monat,
        einnahmen=Decimal(str(einnahmen)),
        ausgaben=Decimal(str(ausgaben)),
        saldo=Decimal(str(einnahmen)) - Decimal(str(ausgaben)),
        anzahl_buchungen=anzahl,
    )


@router.get("", response_model=list[JournalEintragResponse])
def list_eintraege(
    monat: Optional[str] = Query(None, description="Format: YYYY-MM"),
    datum_von: Optional[date] = Query(None, description="Von-Datum (YYYY-MM-DD)"),
    datum_bis: Optional[date] = Query(None, description="Bis-Datum (YYYY-MM-DD)"),
    kategorie_id: Optional[int] = None,
    art: Optional[str] = Query(None, description="Einnahme oder Ausgabe"),
    zahlungsart_typ: Optional[str] = Query(None, description="bar oder unbar"),
    db: Session = Depends(get_db),
):
    """Journaleinträge mit optionalen Filtern."""
    q = db.query(Journaleintrag)
    if monat:
        try:
            jahr, mon = monat.split("-")
            q = q.filter(
                extract("year", Journaleintrag.datum) == int(jahr),
                extract("month", Journaleintrag.datum) == int(mon),
            )
        except (ValueError, AttributeError):
            raise HTTPException(status_code=422, detail="monat muss im Format YYYY-MM sein")
    else:
        if datum_von:
            q = q.filter(Journaleintrag.datum >= datum_von)
        if datum_bis:
            q = q.filter(Journaleintrag.datum <= datum_bis)
    if kategorie_id is not None:
        q = q.filter(Journaleintrag.kategorie_id == kategorie_id)
    if art:
        if art not in ("Einnahme", "Ausgabe"):
            raise HTTPException(status_code=422, detail="art muss Einnahme oder Ausgabe sein")
        q = q.filter(Journaleintrag.art == art)
    if zahlungsart_typ == "bar":
        q = q.filter(Journaleintrag.zahlungsart == "Bar")
    elif zahlungsart_typ == "unbar":
        q = q.filter(Journaleintrag.zahlungsart != "Bar")
    eintraege = q.order_by(Journaleintrag.datum.desc(), Journaleintrag.id.desc()).all()
    return [JournalEintragResponse.from_orm_with_kunde(e) for e in eintraege]


@router.post("", response_model=JournalEintragResponse, status_code=201)
def create_eintrag(data: JournalEintragCreate, db: Session = Depends(get_db)):
    """Legt einen neuen unveränderlichen Journaleintrag an."""
    # Kleinunternehmer-Check
    unternehmen = db.query(Unternehmen).first()
    ust_satz = data.ust_satz
    vorsteuerabzug = data.vorsteuerabzug
    steuerbefreiung_grund = None
    if unternehmen and unternehmen.ist_kleinunternehmer:
        ust_satz = Decimal("0")
        steuerbefreiung_grund = "§19 UStG"

    # Privat-Kategorie: keine USt, kein Vorsteuerabzug
    if data.kategorie_id:
        kat = db.query(Kategorie).filter(Kategorie.id == data.kategorie_id).first()
        if kat and kat.kontenart == "Privat":
            ust_satz = Decimal("0")
            vorsteuerabzug = False
            if not steuerbefreiung_grund:
                steuerbefreiung_grund = "Privatbuchung"

    # Barkassen-Prüfung: Bar-Ausgabe darf den Kassenstand nicht übersteigen
    if data.art == "Ausgabe" and data.zahlungsart == "Bar":
        kassenstand = _get_bar_kassenstand(db)
        if data.brutto_betrag > kassenstand:
            raise HTTPException(
                status_code=409,
                detail=f"Kassenstand nicht ausreichend. Aktueller Kassenstand: {kassenstand:.2f} €, Ausgabe: {data.brutto_betrag:.2f} €.",
            )

    netto, ust_betrag = _berechne_ust(data.brutto_betrag, ust_satz)
    belegnr = _naechste_belegnr(db, data.datum)

    kat = db.query(Kategorie).filter(Kategorie.id == data.kategorie_id).first() if data.kategorie_id else None
    konto_ust_skr03, konto_ust_skr04 = _ust_konto(data.art, ust_satz) if ust_satz > 0 else (None, None)
    journaleintrag = Journaleintrag(
        datum=data.datum,
        belegnr=belegnr,
        beschreibung=data.beschreibung,
        kategorie_id=data.kategorie_id,
        konto_skr03=kat.konto_skr03 if kat else None,
        konto_skr04=kat.konto_skr04 if kat else None,
        konto_ust_skr03=konto_ust_skr03,
        konto_ust_skr04=konto_ust_skr04,
        kunde_id=data.kunde_id,
        zahlungsart=data.zahlungsart,
        art=data.art,
        netto_betrag=netto,
        ust_satz=ust_satz,
        ust_betrag=ust_betrag,
        vorsteuer_betrag=_berechne_vorsteuer(ust_betrag, vorsteuerabzug, kat),
        brutto_betrag=data.brutto_betrag,
        vorsteuerabzug=vorsteuerabzug,
        steuerbefreiung_grund=steuerbefreiung_grund,
        externe_belegnr=data.externe_belegnr,
        immutable=True,
    )
    journaleintrag.signatur = signatur_journaleintrag(journaleintrag)
    db.add(journaleintrag)
    db.commit()
    db.refresh(journaleintrag)
    return JournalEintragResponse.from_orm_with_kunde(journaleintrag)


@router.post("/split", response_model=list[JournalEintragResponse], status_code=201)
def create_split_buchung(data: SplitBuchungCreate, db: Session = Depends(get_db)):
    """Erstellt mehrere Journaleinträge als atomare Split-Buchung (ein Beleg, mehrere Positionen)."""
    # Barkassen-Prüfung für Split-Ausgaben (nur Bar, Gesamtbetrag aller Positionen)
    if data.art == "Ausgabe" and data.zahlungsart == "Bar":
        gesamt = sum(pos.brutto_betrag for pos in data.positionen)
        kassenstand = _get_bar_kassenstand(db)
        if gesamt > kassenstand:
            raise HTTPException(
                status_code=409,
                detail=f"Kassenstand nicht ausreichend. Aktueller Kassenstand: {kassenstand:.2f} €, Ausgabe gesamt: {gesamt:.2f} €.",
            )

    unternehmen = db.query(Unternehmen).first()
    ergebnisse = []
    for pos in data.positionen:
        ust_satz = pos.ust_satz
        vorsteuerabzug = pos.vorsteuerabzug
        steuerbefreiung_grund = None
        if unternehmen and unternehmen.ist_kleinunternehmer:
            ust_satz = Decimal("0")
            steuerbefreiung_grund = "§19 UStG"
        if pos.kategorie_id:
            kat = db.query(Kategorie).filter(Kategorie.id == pos.kategorie_id).first()
            if kat and kat.kontenart == "Privat":
                ust_satz = Decimal("0")
                vorsteuerabzug = False
                if not steuerbefreiung_grund:
                    steuerbefreiung_grund = "Privatbuchung"
        netto, ust_betrag = _berechne_ust(pos.brutto_betrag, ust_satz)
        belegnr = _naechste_belegnr(db, data.datum)
        split_kat = db.query(Kategorie).filter(Kategorie.id == pos.kategorie_id).first() if pos.kategorie_id else None
        konto_ust_skr03, konto_ust_skr04 = _ust_konto(data.art, ust_satz) if ust_satz > 0 else (None, None)
        journaleintrag = Journaleintrag(
            datum=data.datum,
            belegnr=belegnr,
            beschreibung=pos.beschreibung,
            externe_belegnr=data.externe_belegnr,
            kategorie_id=pos.kategorie_id,
            konto_skr03=split_kat.konto_skr03 if split_kat else None,
            konto_skr04=split_kat.konto_skr04 if split_kat else None,
            konto_ust_skr03=konto_ust_skr03,
            konto_ust_skr04=konto_ust_skr04,
            kunde_id=data.kunde_id,
            zahlungsart=data.zahlungsart,
            art=data.art,
            netto_betrag=netto,
            ust_satz=ust_satz,
            ust_betrag=ust_betrag,
            vorsteuer_betrag=_berechne_vorsteuer(ust_betrag, vorsteuerabzug, split_kat),
            brutto_betrag=pos.brutto_betrag,
            vorsteuerabzug=vorsteuerabzug,
            steuerbefreiung_grund=steuerbefreiung_grund,
            immutable=True,
        )
        journaleintrag.signatur = signatur_journaleintrag(journaleintrag)
        db.add(journaleintrag)
        ergebnisse.append(journaleintrag)
    db.commit()
    for e in ergebnisse:
        db.refresh(e)
    return [JournalEintragResponse.from_orm_with_kunde(e) for e in ergebnisse]


@router.get("/{eintrag_id}/beleg", response_class=HTMLResponse)
def get_beleg(eintrag_id: int, drucken: bool = Query(False), download: bool = Query(False), db: Session = Depends(get_db)):
    """Gibt einen druckbaren HTML-Beleg für einen Journaleintrag zurück."""
    eintrag = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Journaleintrag nicht gefunden.")

    datum = eintrag.datum.strftime("%d.%m.%Y")
    ust_satz = float(eintrag.ust_satz)
    print_script = "<script>window.addEventListener('load', () => { window.print() })</script>" if drucken else ""

    html = f"""<!DOCTYPE html><html><head>
    <meta charset="utf-8">
    <title>Beleg {eintrag.belegnr}</title>
    {print_script}
    <style>
      body {{ font-family: Arial, sans-serif; margin: 40px; color: #1e293b; }}
      h1 {{ font-size: 18px; margin-bottom: 4px; }}
      .meta {{ color: #64748b; font-size: 13px; margin-bottom: 24px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
      td {{ padding: 8px 0; border-bottom: 1px solid #e2e8f0; font-size: 14px; }}
      td:last-child {{ text-align: right; }}
      .label {{ color: #64748b; }}
      .total {{ font-weight: bold; font-size: 16px; }}
      .footer {{ margin-top: 40px; font-size: 12px; color: #94a3b8; }}
    </style>
    </head><body>
    <h1>RechnungsFee – Beleg</h1>
    <div class="meta">{eintrag.belegnr} &nbsp;·&nbsp; {datum} &nbsp;·&nbsp; {eintrag.art}</div>
    <table>
      <tr><td class="label">Beschreibung</td><td>{eintrag.beschreibung}</td></tr>
      <tr><td class="label">Zahlungsart</td><td>{eintrag.zahlungsart}</td></tr>
      <tr><td class="label">Netto</td><td>{float(eintrag.netto_betrag):.2f} €</td></tr>
      <tr><td class="label">USt ({ust_satz:.0f} %)</td><td>{float(eintrag.ust_betrag):.2f} €</td></tr>
      {"" if not eintrag.steuerbefreiung_grund else f'<tr><td class="label">Steuerbefreiung</td><td>{eintrag.steuerbefreiung_grund}</td></tr>'}
      <tr class="total"><td>Brutto</td><td>{float(eintrag.brutto_betrag):.2f} €</td></tr>
    </table>
    <div class="footer">Erstellt mit RechnungsFee &nbsp;·&nbsp; {datetime.now().strftime("%d.%m.%Y")}</div>
    </body></html>"""

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="Beleg_{eintrag.belegnr}.html"'
    return HTMLResponse(content=html, headers=headers)


@router.get("/{eintrag_id}", response_model=JournalEintragResponse)
def get_eintrag(eintrag_id: int, db: Session = Depends(get_db)):
    journaleintrag = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not journaleintrag:
        raise HTTPException(status_code=404, detail="Journaleintrag nicht gefunden.")
    return JournalEintragResponse.from_orm_with_kunde(journaleintrag)


@router.post("/{eintrag_id}/storno", response_model=JournalEintragResponse, status_code=201)
def storno_eintrag(eintrag_id: int, data: StornoRequest, db: Session = Depends(get_db)):
    """Storniert einen Eintrag durch eine Gegenbuchung (GoBD-konform)."""
    original = db.query(Journaleintrag).filter(Journaleintrag.id == eintrag_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Journaleintrag nicht gefunden.")
    # Storno eines Stornos verhindern
    if original.beschreibung.startswith("STORNO "):
        raise HTTPException(status_code=409, detail="Ein Storno-Eintrag kann nicht erneut storniert werden.")
    # Bereits stornierte Buchung erkennen
    bereits_storniert = db.query(Journaleintrag).filter(
        Journaleintrag.beschreibung.like(f"STORNO {original.belegnr}:%")
    ).first()
    if bereits_storniert:
        raise HTTPException(
            status_code=409,
            detail=f"Diese Buchung wurde bereits storniert (Gegenbuchung: {bereits_storniert.belegnr}).",
        )
    # Gegenbuchung: Betrag immer positiv.
    # Hatte das Original einen positiven Betrag (Normalfall): entgegengesetzte Art, gleicher Betrag.
    # Hatte das Original einen negativen Betrag (z. B. Gutschrift = Einnahme −x):
    #   → gleiche Art, negativer Betrag (= positive Zahl) → Gutschrift-Storno erscheint als Einnahme +x.
    storno_datum = date.today()
    belegnr = _naechste_belegnr(db, storno_datum)
    if original.brutto_betrag >= 0:
        storno_art = "Ausgabe" if original.art == "Einnahme" else "Einnahme"
        s_netto  = original.netto_betrag
        s_ust    = original.ust_betrag
        s_brutto = original.brutto_betrag
    else:
        storno_art = original.art
        s_netto  = -original.netto_betrag
        s_ust    = -original.ust_betrag
        s_brutto = -original.brutto_betrag

    storno = Journaleintrag(
        datum=storno_datum,
        belegnr=belegnr,
        beschreibung=f"STORNO {original.belegnr}: {data.grund}",
        kategorie_id=original.kategorie_id,
        konto_skr03=original.konto_skr03,
        konto_skr04=original.konto_skr04,
        konto_ust_skr03=original.konto_ust_skr03,
        konto_ust_skr04=original.konto_ust_skr04,
        zahlungsart=original.zahlungsart,
        art=storno_art,
        netto_betrag=s_netto,
        ust_satz=original.ust_satz,
        ust_betrag=s_ust,
        # Storno kehrt den Vorsteuer-Betrag um, damit sich Original und Storno in der EÜR aufheben.
        # Negativer Wert ist korrekt: EÜR summiert SUM(vorsteuer_betrag) ohne art-Filter.
        vorsteuer_betrag=-original.vorsteuer_betrag,
        brutto_betrag=s_brutto,
        vorsteuerabzug=False,
        steuerbefreiung_grund=None,
        immutable=True,
    )
    storno.signatur = signatur_journaleintrag(storno)
    db.add(storno)
    db.commit()
    db.refresh(storno)
    return JournalEintragResponse.from_orm_with_kunde(storno)
