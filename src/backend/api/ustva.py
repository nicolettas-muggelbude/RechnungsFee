"""
UStVA – Umsatzsteuer-Voranmeldung 2026
Berechnet Kennziffern aus dem Journal und exportiert als PDF-Anzeigehilfe.

Zeitraum-Formate:
  Monatlich:       zeitraum=2026-01 … 2026-12
  Vierteljährlich: zeitraum=2026-Q1 … 2026-Q4

KZ-Mapping (SKR03/SKR04 → Kennziffer):
  1776 / 3806 → KZ 81 (Netto-Umsätze 19%) + KZ 83 (USt 19%)
  1771 / 3801 → KZ 86 (Netto-Umsätze 7%)  + KZ 88 (USt 7%)
  vorsteuer_betrag > 0, art='Ausgabe' → KZ 66 (Vorsteuer Inland)
"""

import calendar
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Journaleintrag, Unternehmen, UstvaExport

router = APIRouter(prefix="/api/ustva", tags=["UStVA"])

ZERO = Decimal("0.00")

# USt-Konten → Kennziffer-Name
_UST_KONTO_KZ = {
    "1776": "kz_81", "3806": "kz_81",   # 19% Ausgangsumsatz SKR03/04
    "1771": "kz_86", "3801": "kz_86",   # 7%  Ausgangsumsatz SKR03/04
}


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _zeitraum_grenzen(zeitraum: str) -> tuple[date, date, str]:
    """Parst 'YYYY-MM' oder 'YYYY-QN', gibt (von, bis, typ) zurück."""
    if "-Q" in zeitraum:
        try:
            jahr_s, q_s = zeitraum.split("-Q")
            jahr, q = int(jahr_s), int(q_s)
            if q not in (1, 2, 3, 4):
                raise ValueError
            von_monat = (q - 1) * 3 + 1
            bis_monat = von_monat + 2
            von = date(jahr, von_monat, 1)
            bis = date(jahr, bis_monat, calendar.monthrange(jahr, bis_monat)[1])
            return von, bis, "quartalsweise"
        except (ValueError, AttributeError):
            raise HTTPException(422, f"Ungültiges Quartal: '{zeitraum}' – erwartet z.B. '2026-Q1'")
    else:
        try:
            jahr_s, mon_s = zeitraum.split("-")
            jahr, monat = int(jahr_s), int(mon_s)
            if not (1 <= monat <= 12):
                raise ValueError
            von = date(jahr, monat, 1)
            bis = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
            return von, bis, "monatlich"
        except (ValueError, AttributeError):
            raise HTTPException(422, f"Ungültiges Zeitraum-Format: '{zeitraum}' – erwartet z.B. '2026-01'")


def _berechne_kz(von: date, bis: date, db: Session) -> dict:
    """Aggregiert Journaleinträge im Zeitraum zu UStVA-Kennziffern."""
    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .all()
    )

    kz: dict[str, Decimal] = {
        "kz_81": ZERO, "kz_83": ZERO,
        "kz_86": ZERO, "kz_88": ZERO,
        "kz_66": ZERO,
        "kz_41": ZERO,
    }

    for e in eintraege:
        ust_konto = e.konto_ust_skr03 or e.konto_ust_skr04 or ""
        kz_name = _UST_KONTO_KZ.get(ust_konto)

        # Ausgangsumsätze (Einnahmen mit USt-Buchung)
        if kz_name and e.art == "Einnahme" and e.ust_betrag != 0:
            kz[kz_name] += e.netto_betrag
            kz["kz_83" if kz_name == "kz_81" else "kz_88"] += e.ust_betrag

        # Vorsteuer Inland (Ausgaben mit abziehbarem Vorsteueranteil)
        if e.art == "Ausgabe" and e.vorsteuer_betrag and e.vorsteuer_betrag != 0:
            kz["kz_66"] += e.vorsteuer_betrag

    q = Decimal("0.01")
    for k in kz:
        kz[k] = kz[k].quantize(q, ROUND_HALF_UP)

    ust_gesamt = kz["kz_83"] + kz["kz_88"]
    kz["zahllast"] = (ust_gesamt - kz["kz_66"]).quantize(q, ROUND_HALF_UP)
    return kz


def _zeitraum_label(zeitraum: str) -> str:
    MONATE = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
              "Juli", "August", "September", "Oktober", "November", "Dezember"]
    if "-Q" in zeitraum:
        jahr, q = zeitraum.split("-Q")
        return f"Q{q}/{jahr}"
    try:
        jahr, monat = zeitraum.split("-")
        return f"{MONATE[int(monat)]} {jahr}"
    except Exception:
        return zeitraum


# ---------------------------------------------------------------------------
# PDF-Anzeigehilfe
# ---------------------------------------------------------------------------

def _generate_pdf(zeitraum: str, kz: dict, unt: Unternehmen) -> bytes:
    from fpdf import FPDF

    def _find_dejavu_dir() -> Path:
        import sys
        if getattr(sys, "frozen", False):
            p = Path(sys._MEIPASS) / "fonts"  # type: ignore[attr-defined]
            if (p / "DejaVuSans.ttf").exists():
                return p
        local = Path(__file__).parent.parent / "fonts"
        if (local / "DejaVuSans.ttf").exists():
            return local
        for p in [
            Path("/usr/share/fonts/truetype/dejavu"),
            Path("/usr/share/fonts/dejavu"),
            Path("/usr/share/fonts/dejavu-sans-fonts"),
        ]:
            if (p / "DejaVuSans.ttf").exists():
                return p
        raise FileNotFoundError("DejaVu-Fonts nicht gefunden.")

    BLAU = (37, 99, 235)
    GRAU = (245, 246, 248)
    DUNKEL = (30, 41, 59)
    MITTEL = (100, 116, 139)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    fonts = _find_dejavu_dir()
    pdf.add_font("DejaVu", "", str(fonts / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonts / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, margin=20)

    # Kopfzeile
    pdf.set_fill_color(*BLAU)
    pdf.rect(0, 0, 210, 18, "F")
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 5)
    pdf.cell(0, 8, "Umsatzsteuer-Voranmeldung 2026 – Anzeigehilfe", ln=True, align="L")
    pdf.set_text_color(*DUNKEL)

    pdf.set_xy(20, 24)
    pdf.set_font("DejaVu", "B", 14)
    pdf.cell(0, 8, _zeitraum_label(zeitraum), ln=True, align="L")

    # Unternehmensdaten
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*MITTEL)
    name = unt.firmenname or f"{unt.vorname or ''} {unt.nachname or ''}".strip()
    pdf.cell(0, 5, f"{name}  ·  Steuernummer: {unt.steuernummer or '—'}  ·  Finanzamt: {unt.finanzamt or '—'}", ln=True, align="L")
    if unt.w_idnr:
        pdf.cell(0, 5, f"Wirtschafts-IdNr. (Zeile 1): {unt.w_idnr}", ln=True, align="L")
    pdf.ln(4)

    def euro(v: Decimal) -> str:
        neg = v < 0
        s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        return f"− {s}" if neg else s

    def kz_row(kz_nr: str, bezeichnung: str, wert: Decimal, *, sub: bool = False, bold: bool = False):
        pdf.set_fill_color(*GRAU)
        x = pdf.get_x()
        y = pdf.get_y()
        h = 7

        # KZ-Chip
        pdf.set_fill_color(*BLAU)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(255, 255, 255)
        chip_w = 12
        pdf.set_xy(20, y)
        pdf.cell(chip_w, h, kz_nr, border=0, fill=True, align="C")

        # Bezeichnung
        pdf.set_fill_color(*GRAU)
        font_size = 8 if sub else 9
        pdf.set_font("DejaVu", "B" if bold else "", font_size)
        pdf.set_text_color(MITTEL if sub else DUNKEL)
        pdf.set_xy(20 + chip_w + 2, y)
        pdf.cell(122, h, bezeichnung, border=0, align="L")

        # Betrag
        color = (220, 38, 38) if wert < 0 else DUNKEL
        pdf.set_text_color(*color)
        pdf.set_font("DejaVu", "B" if bold else "", 9)
        pdf.set_xy(155, y)
        pdf.cell(35, h, euro(wert), align="R", border=0)
        pdf.ln(h + 1)

    def section(titel: str):
        pdf.set_fill_color(229, 231, 235)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_x(20)
        pdf.cell(170, 6, f"  {titel}", fill=True, ln=True, align="L")
        pdf.ln(1)

    # A – Ausgangsumsätze
    section("A. Steuerpflichtige Ausgangsumsätze")
    kz_row("81", "Umsätze zum Steuersatz 19 % – Bemessungsgrundlage", kz["kz_81"])
    kz_row("83", "Umsatzsteuer 19 %", kz["kz_83"], sub=True)
    pdf.ln(1)
    kz_row("86", "Umsätze zum Steuersatz 7 % – Bemessungsgrundlage", kz["kz_86"])
    kz_row("88", "Umsatzsteuer 7 %", kz["kz_88"], sub=True)
    pdf.ln(3)

    # F – Vorsteuer
    section("F. Abziehbare Vorsteuerbeträge")
    kz_row("66", "Vorsteuer aus Eingangsrechnungen (§ 15 Abs. 1 Nr. 1 UStG)", kz["kz_66"])
    pdf.ln(3)

    # H – Zahllast
    section("H. Vorauszahlung / Überschuss")
    zahllast = kz["zahllast"]
    label = "Verbleibender Überschuss (negativ)" if zahllast < 0 else "Umsatzsteuer-Vorauszahlung"
    kz_row("—", label, zahllast, bold=True)
    pdf.ln(5)

    # Hinweis
    pdf.set_fill_color(254, 243, 199)
    pdf.set_x(20)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(120, 80, 0)
    pdf.multi_cell(170, 5,
        "Hinweis: Dieses Dokument ist eine Anzeigehilfe und kein amtliches Formular. "
        "Bitte übertrage die Kennziffern in ELSTER (www.elster.de) oder übergib sie "
        "deinem Steuerberater. Grundlage: Journalbuchungen nach Ist-Versteuerung "
        "(Zahlungsdatum). Bei Soll-Versteuerung ggf. abweichend.",
        fill=True, align="L"
    )

    # Fußzeile
    pdf.set_y(-15)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*MITTEL)
    pdf.cell(0, 5, f"Erstellt mit RechnungsFee  ·  {_zeitraum_label(zeitraum)}", align="C")

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Response-Schema
# ---------------------------------------------------------------------------

class UStVAErgebnis(BaseModel):
    zeitraum: str
    zeitraum_typ: str
    von: date
    bis: date
    kz_81: Decimal
    kz_83: Decimal
    kz_86: Decimal
    kz_88: Decimal
    kz_66: Decimal
    kz_41: Decimal
    zahllast: Decimal
    ist_kleinunternehmer: bool
    hinweis: Optional[str] = None


class UStVASpeichernRequest(BaseModel):
    zeitraum: str
    kz_81: Decimal = ZERO
    kz_83: Decimal = ZERO
    kz_86: Decimal = ZERO
    kz_88: Decimal = ZERO
    kz_66: Decimal = ZERO
    kz_41: Decimal = ZERO
    zahllast: Decimal = ZERO


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/berechnen", response_model=UStVAErgebnis)
def ustva_berechnen(
    zeitraum: str = Query(..., description="YYYY-MM oder YYYY-QN, z.B. '2026-01' oder '2026-Q1'"),
    db: Session = Depends(get_db),
):
    """Berechnet UStVA-Kennziffern aus dem Journal (ohne zu speichern)."""
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")

    von, bis, typ = _zeitraum_grenzen(zeitraum)
    ist_ku = bool(unt.ist_kleinunternehmer)

    if ist_ku:
        # §19-Kleinunternehmer: keine Steuerpflicht, Kennziffern sind 0
        kz = {k: ZERO for k in ("kz_81", "kz_83", "kz_86", "kz_88", "kz_66", "kz_41", "zahllast")}
        hinweis = ("Als Kleinunternehmer nach §19 UStG bist du von der UStVA befreit. "
                   "Umsätze werden in Zeile 23 (KZ 48) als steuerfreie Umsätze ohne Vorsteuerabzug eingetragen – "
                   "dies geschieht jedoch nur einmal jährlich in der Jahressteuererklärung.")
    else:
        kz = _berechne_kz(von, bis, db)
        hinweis = None

    return UStVAErgebnis(
        zeitraum=zeitraum,
        zeitraum_typ=typ,
        von=von,
        bis=bis,
        **kz,
        ist_kleinunternehmer=ist_ku,
        hinweis=hinweis,
    )


@router.post("/speichern")
def ustva_speichern(req: UStVASpeichernRequest, db: Session = Depends(get_db)):
    """Speichert berechnete UStVA-Daten (überschreibt bestehenden Eintrag)."""
    von, bis, typ = _zeitraum_grenzen(req.zeitraum)
    eintrag = db.query(UstvaExport).filter(UstvaExport.zeitraum == req.zeitraum).first()
    if not eintrag:
        eintrag = UstvaExport(zeitraum=req.zeitraum)
        db.add(eintrag)
    eintrag.zeitraum_typ = typ
    eintrag.kz_81 = req.kz_81
    eintrag.kz_83 = req.kz_83
    eintrag.kz_86 = req.kz_86
    eintrag.kz_88 = req.kz_88
    eintrag.kz_66 = req.kz_66
    eintrag.kz_41 = req.kz_41
    eintrag.zahllast = req.zahllast
    eintrag.daten_json = json.dumps({k: str(v) for k, v in req.model_dump().items()})
    db.commit()
    return {"ok": True, "zeitraum": req.zeitraum}


@router.get("/historie")
def ustva_historie(db: Session = Depends(get_db)):
    """Liste aller gespeicherten UStVA-Zeiträume."""
    eintraege = db.query(UstvaExport).order_by(UstvaExport.zeitraum.desc()).all()
    return [
        {
            "zeitraum": e.zeitraum,
            "zeitraum_typ": e.zeitraum_typ,
            "zahllast": float(e.zahllast),
            "erstellt_am": e.erstellt_am.isoformat(),
        }
        for e in eintraege
    ]


@router.get("/pdf")
def ustva_pdf(
    zeitraum: str = Query(..., description="YYYY-MM oder YYYY-QN"),
    db: Session = Depends(get_db),
):
    """PDF-Anzeigehilfe zur manuellen Übertragung in ELSTER."""
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")
    von, bis, _ = _zeitraum_grenzen(zeitraum)
    kz = _berechne_kz(von, bis, db)
    pdf_bytes = _generate_pdf(zeitraum, kz, unt)
    filename = f"UStVA_{zeitraum}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
