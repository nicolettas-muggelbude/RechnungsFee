"""
Anlage AVEÜR – Abschreibungsplan für Anlagegüter (KFZ, EDV, Sonstiges)

Ermöglicht:
- CRUD für Wirtschaftsgüter im Anlagevermögen
- Lineare AfA-Berechnung (Monatsprinzip im Kaufjahr)
- Abschreibungsplan als JSON und PDF-Export
"""

import calendar
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from math import ceil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, model_validator
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Anlagegut, Unternehmen

router = APIRouter(prefix="/api/anlageverzeichnis", tags=["Anlageverzeichnis"])

ZERO = Decimal("0.00")
ONE_CENT = Decimal("0.01")


# ---------------------------------------------------------------------------
# Pydantic-Schemas
# ---------------------------------------------------------------------------

class AnlagegutBase(BaseModel):
    bezeichnung: str
    typ: str = "sonstig"            # kfz | edv | sonstig
    kaufdatum: date
    kaufpreis_netto: Decimal
    nutzungsdauer_jahre: int
    afa_methode: str = "linear"
    kennzeichen: Optional[str] = None
    privat_anteil_prozent: Decimal = ZERO
    verkauft_am: Optional[date] = None
    notizen: Optional[str] = None
    aktiv: bool = True

    @model_validator(mode="after")
    def check_afa_methode(self) -> "AnlagegutBase":
        if self.afa_methode not in ("linear", "degressiv"):
            raise ValueError("afa_methode muss 'linear' oder 'degressiv' sein")
        if self.afa_methode == "degressiv" and not degressiv_moeglich(self.kaufdatum):
            raise ValueError(
                "Degressive AfA gilt nur für Anschaffungen zwischen 01.07.2025 und 31.12.2027 (§7 Abs. 2 EStG)."
            )
        return self

class AnlagegutCreate(AnlagegutBase):
    pass

class AnlagegutOut(AnlagegutBase):
    id: int
    erstellt_am: datetime
    aktualisiert_am: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# AfA-Berechnung
# ---------------------------------------------------------------------------

# Degressive AfA ("Investitionsbooster", §7 Abs. 2 EStG): bewegliche Wirtschaftsgüter,
# angeschafft zwischen 01.07.2025 und 31.12.2027. Satz: bis zum 3-fachen der linearen
# AfA, gedeckelt auf 30 % vom (jeweiligen) Restbuchwert. Wechsel zu linear ist jederzeit
# möglich (und Pflicht sobald linear auf den Restbuchwert günstiger ist) – umgekehrt
# (linear→degressiv) ist nicht zulässig.
DEGRESSIV_AB = date(2025, 7, 1)
DEGRESSIV_BIS = date(2027, 12, 31)


def degressiv_moeglich(kaufdatum: date) -> bool:
    return DEGRESSIV_AB <= kaufdatum <= DEGRESSIV_BIS


def _afa_jahresplan(gut: Anlagegut, bis_jahr: Optional[int] = None) -> list[dict]:
    """
    Gibt den vollständigen Abschreibungsplan zurück.
    Jedes Dict: { jahr, afa_brutto, afa_abziehbar, restbuchwert_ende }

    Monatsprinzip im Kaufjahr: AfA nur für die Monate ab Kaufmonat (inkl.).
    Für KFZ: abziehbarer Anteil = brutto * (1 - privat_anteil_prozent / 100).
    Bei afa_methode="degressiv": jährlicher Wechsel-Check auf linear (s.o.).
    """
    kauf = gut.kaufdatum
    preis = Decimal(str(gut.kaufpreis_netto))
    nd = gut.nutzungsdauer_jahre
    privat = Decimal(str(gut.privat_anteil_prozent)) / 100
    betrieb = Decimal("1") - privat
    ist_degressiv = gut.afa_methode == "degressiv"

    afa_voll_linear = (preis / nd).quantize(ONE_CENT, ROUND_HALF_UP)
    degressiv_satz = min(Decimal("3") / nd, Decimal("0.30")) if ist_degressiv else None

    # Monate im Kaufjahr (inkl. Kaufmonat bis Dezember)
    monate_kaufjahr = 12 - kauf.month + 1

    # Restjahr: was nach ND vollständigen Jahren noch übrig bleibt
    ende_jahr = kauf.year + nd  # das Jahr in dem ggf. ein kleiner Rest abgeschrieben wird

    plan = []
    restbuchwert = preis
    linear_aktiv = not ist_degressiv  # sobald True, bleibt es (Wechsel degressiv→linear ist einseitig)
    afa_jahr_voll = afa_voll_linear  # voller Jahresbetrag vor Monatsanteil; für degressiv pro Jahr neu ermittelt

    year = kauf.year
    max_year = bis_jahr if bis_jahr else (kauf.year + nd + 1)

    while restbuchwert > ZERO and year <= max_year + 1:
        wechsel_dieses_jahr = False
        if year < ende_jahr and ist_degressiv:
            verbleibende_jahre = max(nd - (year - kauf.year), 1)
            if linear_aktiv:
                afa_jahr_voll = (restbuchwert / verbleibende_jahre).quantize(ONE_CENT, ROUND_HALF_UP)
            else:
                afa_degressiv = (restbuchwert * degressiv_satz).quantize(ONE_CENT, ROUND_HALF_UP)
                afa_linear_rest = (restbuchwert / verbleibende_jahre).quantize(ONE_CENT, ROUND_HALF_UP)
                if afa_linear_rest >= afa_degressiv:
                    linear_aktiv = True
                    wechsel_dieses_jahr = True  # Issue #270: Hinweis im Plan, in welchem Jahr gewechselt wird
                    afa_jahr_voll = afa_linear_rest
                else:
                    afa_jahr_voll = afa_degressiv

        if year == kauf.year:
            afa = min((afa_jahr_voll * monate_kaufjahr / 12).quantize(ONE_CENT, ROUND_HALF_UP), restbuchwert)
        elif year == ende_jahr and monate_kaufjahr < 12:
            # Restjahr: übrige Monate aus dem ersten Jahr
            restmonate = 12 - monate_kaufjahr
            afa = min((afa_jahr_voll * restmonate / 12).quantize(ONE_CENT, ROUND_HALF_UP), restbuchwert)
        elif year > ende_jahr:
            break
        else:
            afa = min(afa_jahr_voll, restbuchwert)

        if afa <= ZERO:
            break

        afa_abziehbar = (afa * betrieb).quantize(ONE_CENT, ROUND_HALF_UP)
        restbuchwert = (restbuchwert - afa).quantize(ONE_CENT, ROUND_HALF_UP)

        plan.append({
            "jahr": year,
            "afa_brutto": float(afa),
            "afa_abziehbar": float(afa_abziehbar),
            "restbuchwert_ende": float(restbuchwert),
            "wechsel_zu_linear": wechsel_dieses_jahr,
        })
        year += 1

    return plan


def _afa_fuer_jahr(gut: Anlagegut, jahr: int) -> Decimal:
    """Gibt den abziehbaren AfA-Betrag für ein bestimmtes Jahr zurück."""
    for zeile in _afa_jahresplan(gut, bis_jahr=jahr):
        if zeile["jahr"] == jahr:
            return Decimal(str(zeile["afa_abziehbar"]))
    return ZERO


# ---------------------------------------------------------------------------
# CRUD-Endpunkte
# ---------------------------------------------------------------------------

@router.get("", response_model=list[AnlagegutOut])
def liste(db: Session = Depends(get_db)):
    return db.query(Anlagegut).order_by(Anlagegut.kaufdatum.desc()).all()


@router.post("", response_model=AnlagegutOut, status_code=201)
def erstellen(data: AnlagegutCreate, db: Session = Depends(get_db)):
    gut = Anlagegut(**data.model_dump())
    db.add(gut)
    db.commit()
    db.refresh(gut)
    return gut


@router.put("/{gut_id}", response_model=AnlagegutOut)
def aktualisieren(gut_id: int, data: AnlagegutCreate, db: Session = Depends(get_db)):
    gut = db.get(Anlagegut, gut_id)
    if not gut:
        raise HTTPException(404, "Wirtschaftsgut nicht gefunden")
    for k, v in data.model_dump().items():
        setattr(gut, k, v)
    db.commit()
    db.refresh(gut)
    return gut


@router.delete("/{gut_id}", status_code=204)
def loeschen(gut_id: int, db: Session = Depends(get_db)):
    gut = db.get(Anlagegut, gut_id)
    if not gut:
        raise HTTPException(404, "Wirtschaftsgut nicht gefunden")
    db.delete(gut)
    db.commit()


@router.get("/{gut_id}/plan")
def abschreibungsplan(gut_id: int, db: Session = Depends(get_db)):
    gut = db.get(Anlagegut, gut_id)
    if not gut:
        raise HTTPException(404, "Wirtschaftsgut nicht gefunden")
    return _afa_jahresplan(gut)


@router.get("/zusammenfassung")
def zusammenfassung(jahr: int = Query(...), db: Session = Depends(get_db)):
    """Gesamt-AfA aller aktiven Güter für ein Jahr (→ EÜR Zeile 33)."""
    gueter = db.query(Anlagegut).filter(Anlagegut.aktiv == True).all()
    einzel = []
    gesamt = ZERO
    for g in gueter:
        afa = _afa_fuer_jahr(g, jahr)
        if afa > ZERO:
            gesamt += afa
            einzel.append({
                "id": g.id,
                "bezeichnung": g.bezeichnung,
                "typ": g.typ,
                "afa_abziehbar": float(afa),
            })
    return {"jahr": jahr, "gesamt_afa": float(gesamt), "einzel": einzel}


# ---------------------------------------------------------------------------
# PDF-Export
# ---------------------------------------------------------------------------

def _fonts() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        p = Path(sys._MEIPASS) / "fonts"  # type: ignore[attr-defined]
        if (p / "DejaVuSans.ttf").exists():
            return p
    local = Path(__file__).parent.parent / "fonts"
    if (local / "DejaVuSans.ttf").exists():
        return local
    for p in [Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/dejavu")]:
        if (p / "DejaVuSans.ttf").exists():
            return p
    raise FileNotFoundError("DejaVu-Fonts nicht gefunden.")


@router.get("/pdf")
def pdf_export(jahr: int = Query(...), db: Session = Depends(get_db)):
    """PDF-Abschreibungsplan (Anlage AVEÜR) für ein Wirtschaftsjahr."""
    gueter = db.query(Anlagegut).order_by(Anlagegut.kaufdatum).all()
    unt = db.query(Unternehmen).first()

    from fpdf import FPDF

    BLAU  = (37, 99, 235)
    DUNKEL = (30, 41, 59)
    MITTEL = (100, 116, 139)
    HELLGRAU = (245, 246, 248)
    ORANGE = (234, 88, 12)

    fonts = _fonts()
    pdf = FPDF(orientation="L", unit="mm", format="A4")  # Querformat wegen vieler Spalten
    pdf.add_font("DejaVu", "",  str(fonts / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonts / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(15, 20, 15)
    pdf.set_auto_page_break(True, margin=20)

    # Header-Banner
    pdf.set_fill_color(*BLAU)
    pdf.rect(0, 0, 297, 18, "F")
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 5)
    pdf.cell(0, 8, f"Anlagenverzeichnis / Anlage AVEÜR – Wirtschaftsjahr {jahr}", ln=True)

    name = (unt.firmenname or f"{unt.vorname or ''} {unt.nachname or ''}".strip()) if unt else "—"
    pdf.set_xy(15, 24)
    pdf.set_text_color(*DUNKEL)
    pdf.set_font("DejaVu", "B", 12)
    pdf.cell(0, 7, name, ln=True)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*MITTEL)
    stnr = (unt.steuernummer or "—") if unt else "—"
    pdf.cell(0, 5, f"Steuernummer: {stnr}  ·  Erstellt am: {date.today().strftime('%d.%m.%Y')}", ln=True)
    pdf.ln(5)

    def euro(v) -> str:
        d = Decimal(str(v))
        neg = d < 0
        s = f"{abs(d):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        return ("− " if neg else "") + s

    def fmt_date(d: Optional[date]) -> str:
        return d.strftime("%d.%m.%Y") if d else "—"

    # Spalten: Bezeichnung | Typ | Kaufdatum | Kaufpreis netto | ND | AfA/Jahr brutto | Privatanteil | AfA/Jahr abziehbar | AfA {jahr} | Restwert Ende {jahr}
    COL_W = [52, 14, 22, 28, 10, 28, 16, 30, 25, 32]
    HEADERS = [
        "Bezeichnung", "Typ", "Kaufdatum", "Kaufpreis netto",
        "ND", "AfA/Jahr", "Privat %", "AfA abziehbar",
        f"AfA {jahr}", f"RBW Ende {jahr}",
    ]
    ROW_H = 6.5
    HEADER_H = 7

    def table_header():
        pdf.set_fill_color(*BLAU)
        pdf.set_font("DejaVu", "B", 7.5)
        pdf.set_text_color(255, 255, 255)
        x = pdf.get_x()
        y = pdf.get_y()
        for i, (h, w) in enumerate(zip(HEADERS, COL_W)):
            align = "R" if i >= 3 else "L"
            pdf.set_xy(x + sum(COL_W[:i]), y)
            pdf.cell(w, HEADER_H, h, border=0, fill=True, align=align)
        pdf.ln(HEADER_H + 1)

    # Nach Typ gruppieren
    TYPEN = [("kfz", "Kraftfahrzeuge"), ("edv", "EDV / Software"), ("sonstig", "Übrige Wirtschaftsgüter")]

    gesamt_afa_jahr = ZERO
    hat_inhalt = False

    for typ_key, typ_label in TYPEN:
        typ_gueter = [g for g in gueter if g.typ == typ_key]
        if not typ_gueter:
            continue

        hat_inhalt = True

        # Abschnitts-Header
        pdf.set_fill_color(229, 231, 235)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_x(15)
        pdf.cell(267, 6, f"  {typ_label}", fill=True, ln=True)
        pdf.ln(1)

        table_header()

        abschnitt_afa = ZERO
        for i, g in enumerate(typ_gueter):
            plan = _afa_jahresplan(g, bis_jahr=jahr)
            plan_jahr = next((z for z in plan if z["jahr"] == jahr), None)
            preis = Decimal(str(g.kaufpreis_netto))
            nd = g.nutzungsdauer_jahre
            privat = Decimal(str(g.privat_anteil_prozent))
            ist_degressiv = g.afa_methode == "degressiv"
            afa_j = Decimal(str(plan_jahr["afa_abziehbar"])) if plan_jahr else ZERO
            rbw_ende = Decimal(str(plan_jahr["restbuchwert_ende"])) if plan_jahr else ZERO

            gesamt_afa_jahr += afa_j
            abschnitt_afa += afa_j

            fill_color = HELLGRAU if i % 2 == 0 else (255, 255, 255)
            pdf.set_fill_color(*fill_color)
            pdf.set_text_color(*DUNKEL)
            pdf.set_font("DejaVu", "", 8)

            if ist_degressiv:
                satz = min(Decimal("3") / nd, Decimal("0.30")) * 100
                afa_jahr_spalte = f"degressiv {satz:.0f}%"
                afa_abziehbar_spalte = "—"
            else:
                afa_brutto = (preis / nd).quantize(ONE_CENT, ROUND_HALF_UP)
                afa_jahr_spalte = euro(afa_brutto)
                afa_abziehbar_spalte = euro((afa_brutto * (1 - privat / 100)).quantize(ONE_CENT, ROUND_HALF_UP))

            x = 15
            y = pdf.get_y()
            vals = [
                (g.bezeichnung + (f" [{g.kennzeichen}]" if g.kennzeichen else ""), "L"),
                (g.typ.upper(), "L"),
                (fmt_date(g.kaufdatum), "L"),
                (euro(g.kaufpreis_netto), "R"),
                (str(nd), "R"),
                (afa_jahr_spalte, "R"),
                (f"{privat:.0f} %" if privat > 0 else "—", "R"),
                (afa_abziehbar_spalte, "R"),
                (euro(afa_j) if plan_jahr else "—", "R"),
                (euro(rbw_ende) if plan_jahr else "—", "R"),
            ]
            for j_col, (val, align) in enumerate(vals):
                pdf.set_xy(x + sum(COL_W[:j_col]), y)
                pdf.cell(COL_W[j_col], ROW_H, val, border=0, fill=True, align=align)
            pdf.ln(ROW_H)

        # Abschnitts-Summe
        pdf.set_fill_color(209, 213, 219)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(*DUNKEL)
        x = 15
        y = pdf.get_y()
        label_w = sum(COL_W[:-2])
        pdf.set_xy(x, y)
        pdf.cell(label_w, ROW_H, f"  Summe {typ_label}", fill=True, align="L")
        pdf.set_xy(x + sum(COL_W[:-2]), y)
        pdf.cell(COL_W[-2], ROW_H, euro(abschnitt_afa), fill=True, align="R")
        pdf.cell(COL_W[-1], ROW_H, "", fill=True)
        pdf.ln(ROW_H + 4)

    if not hat_inhalt:
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*MITTEL)
        pdf.set_x(15)
        pdf.cell(0, 8, "Keine Wirtschaftsgüter im Anlagevermögen erfasst.", ln=True)
    else:
        # Gesamt-Summe
        pdf.set_fill_color(*BLAU)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(255, 255, 255)
        x = 15
        y = pdf.get_y()
        label_w = sum(COL_W[:-2])
        pdf.set_xy(x, y)
        pdf.cell(label_w, 8, f"  Gesamt-AfA {jahr} (→ EÜR Zeile 33)", fill=True, align="L")
        pdf.set_xy(x + label_w, y)
        pdf.cell(COL_W[-2], 8, euro(gesamt_afa_jahr), fill=True, align="R")
        pdf.cell(COL_W[-1], 8, "", fill=True)
        pdf.ln(12)

    # Hinweis-Box
    pdf.set_fill_color(254, 243, 199)
    pdf.set_x(15)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(120, 80, 0)
    pdf.multi_cell(267, 5,
        "Hinweis: Anzeigehilfe auf Basis des Anlagenverzeichnisses. Bitte Werte in ELSTER (Anlage AVEÜR) oder mit dem "
        "Steuerberater übertragen. Nutzungsdauer nach AfA-Tabellen des BMF. Lineare oder degressive AfA "
        "(§7 Abs. 2 EStG, Investitionsbooster, nur für Anschaffungen 01.07.2025-31.12.2027; automatischer "
        "Wechsel zu linear sobald günstiger). Monatsprinzip im Kaufjahr (ab Kaufmonat).", fill=True)

    # Footer
    pdf.set_y(-15)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*MITTEL)
    pdf.set_x(15)
    pdf.cell(133, 5, f"Erstellt mit RechnungsFee  ·  {name[:50]}", align="L")
    pdf.cell(134, 5, f"Wirtschaftsjahr {jahr}", align="R")

    buf = BytesIO()
    buf.write(pdf.output())
    buf.seek(0)
    filename = f"anlageverzeichnis_{jahr}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
