"""
UStVA – Umsatzsteuer-Voranmeldung 2026
Berechnet Kennziffern aus dem Journal und exportiert als PDF-Anzeigehilfe.

Zeitraum-Formate:
  Monatlich:       zeitraum=2026-01 … 2026-12
  Vierteljährlich: zeitraum=2026-Q1 … 2026-Q4

KZ-Mapping (konto_ust_skr03/04 → Kennziffer):
  1776 / 3806 → KZ 81/83  (19% Ausgangsumsatz)
  1771 / 3801 → KZ 86/88  (7%  Ausgangsumsatz)
  1780        → KZ 89/93  (ig. Erwerb 19%)
  1781        → KZ 96/97  (ig. Erwerb 7% – selten)
  1583 / 1402 → KZ 61     (Vorsteuer ig. Erwerb)
  1787        → KZ 84/85  (§13b Abs. 2, Empfänger schuldet)
  1789        → KZ 46/47  (§13b Abs. 1, EU-Dienstleistungen)
  vorsteuer_betrag, art=Ausgabe, andere Konten → KZ 66 (Vorsteuer Inland)

KZ 41 (EU-Lieferungen steuerfreie Einnahmen) und KZ 87 (Ausfuhr etc.)
können nicht sicher aus dem Journal abgeleitet werden – manuelle Eingabe.
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

# ---------------------------------------------------------------------------
# KZ-Definitionen: Reihenfolge wie im amtlichen Formular USt 1 A 2026
# (abschnitt, kz_nr, bezeichnung, ist_steuer_zeile, auto_berechenbar)
# ist_steuer_zeile: rechte Spalte = USt-Betrag (nicht Bemessungsgrundlage)
# auto_berechenbar: True = aus Journal ableitbar
# ---------------------------------------------------------------------------
KZ_META = [
    ("A. Steuerpflichtige Ausgangsumsätze", "81",
     "Umsätze 19 % – Bemessungsgrundlage", False, True),
    ("", "83", "Umsatzsteuer 19 %", True, True),
    ("", "86", "Umsätze 7 % – Bemessungsgrundlage", False, True),
    ("", "88", "Umsatzsteuer 7 %", True, True),

    ("B. Steuerfreie Umsätze mit Vorsteuerabzug", "41",
     "Innergemeinschaftliche Lieferungen (§4 Nr. 1b) an Abnehmer mit USt-IdNr.", False, False),
    ("", "87",
     "Weitere steuerfreie Umsätze mit Vorsteuerabzug (Ausfuhr, §4 Nr. 2–7 UStG)", False, False),

    ("C. Innergemeinschaftliche Erwerbe", "89",
     "Steuerpflichtige Erwerbe 19 %", False, True),
    ("", "93", "Umsatzsteuer ig. Erwerb 19 %", True, True),

    ("D. Leistungsempfänger als Steuerschuldner (§13b UStG)", "46",
     "Sonstige Leistungen EU-Unternehmer (§13b Abs. 1 UStG)", False, True),
    ("", "47", "Umsatzsteuer §13b Abs. 1", True, True),
    ("", "84",
     "Andere §13b-Leistungen (Abs. 2 Nr. 1, 2, 4–12 UStG)", False, True),
    ("", "85", "Umsatzsteuer §13b Abs. 2", True, True),

    ("F. Abziehbare Vorsteuerbeträge", "66",
     "Vorsteuer aus Rechnungen (§15 Abs. 1 Satz 1 Nr. 1 UStG)", False, True),
    ("", "61",
     "Vorsteuer ig. Erwerb (§15 Abs. 1 Satz 1 Nr. 3 UStG)", False, True),
    ("", "67",
     "Vorsteuer aus §13b-Leistungen (§15 Abs. 1 Satz 1 Nr. 4 UStG)", False, True),
]

# USt-Konto → (Bemessungsgrundlage-KZ, Steuer-KZ) für Einnahmen
_KONTO_EINNAHME: dict[str, tuple[str, str]] = {
    "1776": ("kz_81", "kz_83"), "3806": ("kz_81", "kz_83"),  # 19%
    "1771": ("kz_86", "kz_88"), "3801": ("kz_86", "kz_88"),  # 7%
    "1780": ("kz_89", "kz_93"),                               # ig. Erwerb 19%
    "1787": ("kz_84", "kz_85"),                               # §13b Abs. 2
    "1789": ("kz_46", "kz_47"),                               # §13b Abs. 1 (EU-DL)
}

# USt-Konto → Vorsteuer-KZ für Ausgaben
_KONTO_AUSGABE_VST: dict[str, str] = {
    "1583": "kz_61", "1402": "kz_61",   # Vorsteuer ig. Erwerb
    "1787": "kz_67", "1789": "kz_67",   # Vorsteuer §13b
}

ALL_KZ_KEYS = [f"kz_{m[1]}" for m in KZ_META] + ["zahllast"]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _zeitraum_grenzen(zeitraum: str) -> tuple[date, date, str]:
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
            raise HTTPException(422, f"Ungültiges Quartal: '{zeitraum}'")
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
            raise HTTPException(422, f"Ungültiges Zeitraum-Format: '{zeitraum}'")


def _berechne_kz(von: date, bis: date, db: Session) -> dict[str, Decimal]:
    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .all()
    )

    kz: dict[str, Decimal] = {k: ZERO for k in ALL_KZ_KEYS}

    for e in eintraege:
        ust_konto = e.konto_ust_skr03 or e.konto_ust_skr04 or ""

        if e.art == "Einnahme" and e.ust_betrag and e.ust_betrag != 0:
            mapping = _KONTO_EINNAHME.get(ust_konto)
            if mapping:
                kz[mapping[0]] += e.netto_betrag
                kz[mapping[1]] += e.ust_betrag

        if e.art == "Ausgabe" and e.vorsteuer_betrag and e.vorsteuer_betrag != 0:
            vst_kz = _KONTO_AUSGABE_VST.get(ust_konto, "kz_66")
            kz[vst_kz] += e.vorsteuer_betrag

    q = Decimal("0.01")
    for k in kz:
        if k != "zahllast":
            kz[k] = kz[k].quantize(q, ROUND_HALF_UP)

    ust = kz["kz_83"] + kz["kz_88"] + kz["kz_93"] + kz["kz_47"] + kz["kz_85"]
    vst = kz["kz_66"] + kz["kz_61"] + kz["kz_67"]
    kz["zahllast"] = (ust - vst).quantize(q, ROUND_HALF_UP)
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

    BLAU   = (37, 99, 235)
    GRAU   = (245, 246, 248)
    DUNKEL = (30, 41, 59)
    MITTEL = (100, 116, 139)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    fonts = _find_dejavu_dir()
    pdf.add_font("DejaVu", "",  str(fonts / "DejaVuSans.ttf"))
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

    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*MITTEL)
    name = unt.firmenname or f"{unt.vorname or ''} {unt.nachname or ''}".strip()
    pdf.cell(0, 5,
        f"{name}  ·  Steuernummer: {unt.steuernummer or '—'}  ·  Finanzamt: {unt.finanzamt or '—'}",
        ln=True, align="L")
    if unt.w_idnr:
        pdf.cell(0, 5, f"Wirtschafts-IdNr. (Zeile 1): {unt.w_idnr}", ln=True, align="L")
    pdf.ln(4)

    def euro(v: Decimal) -> str:
        neg = v < 0
        s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
        return f"− {s}" if neg else s

    def kz_row(kz_nr: str, bezeichnung: str, wert: Decimal, ist_steuer: bool = False, bold: bool = False):
        y = pdf.get_y()
        h = 7
        pdf.set_fill_color(*BLAU)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(20, y)
        pdf.cell(12, h, kz_nr, border=0, fill=True, align="C")

        font_size = 8 if ist_steuer else 9
        pdf.set_font("DejaVu", "B" if bold else "", font_size)
        pdf.set_text_color(MITTEL if ist_steuer else DUNKEL)
        pdf.set_xy(34, y)
        pdf.cell(120, h, bezeichnung, border=0, align="L")

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

    # Nur Zeilen mit Wert ≠ 0 rendern, Abschnitte bei Bedarf
    letzter_abschnitt = None
    for (abschnitt, kz_nr, bezeichnung, ist_steuer, _auto) in KZ_META:
        key = f"kz_{kz_nr}"
        wert = kz.get(key, ZERO)
        if wert == ZERO:
            continue
        eff_abschnitt = abschnitt if abschnitt else letzter_abschnitt
        if eff_abschnitt != letzter_abschnitt:
            if letzter_abschnitt is not None:
                pdf.ln(2)
            section(eff_abschnitt)
            letzter_abschnitt = eff_abschnitt
        kz_row(kz_nr, bezeichnung, wert, ist_steuer=ist_steuer)

    # Zahllast immer anzeigen
    pdf.ln(2)
    section("H. Vorauszahlung / Überschuss")
    zahllast = kz.get("zahllast", ZERO)
    label = "Verbleibender Überschuss (Erstattung)" if zahllast < 0 else "Umsatzsteuer-Vorauszahlung"
    kz_row("—", label, zahllast, bold=True)
    pdf.ln(4)

    # Hinweis
    pdf.set_fill_color(254, 243, 199)
    pdf.set_x(20)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(120, 80, 0)
    pdf.multi_cell(170, 5,
        "Hinweis: Dieses Dokument ist eine Anzeigehilfe und kein amtliches Formular. "
        "Bitte übertrage die Kennziffern in ELSTER (www.elster.de) oder übergib sie "
        "deinem Steuerberater. Grundlage: Journalbuchungen nach Ist-Versteuerung "
        "(Zahlungsdatum). Bei Soll-Versteuerung ggf. abweichend. "
        "Nicht automatisch berechnete Felder (z.B. EU-Lieferungen KZ 41) müssen "
        "manuell eingetragen werden.",
        fill=True, align="L"
    )

    # Fußzeile
    pdf.set_y(-15)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*MITTEL)
    name_kurz = (unt.firmenname or f"{unt.vorname or ''} {unt.nachname or ''}".strip())[:40]
    pdf.cell(85, 5, f"Erstellt mit RechnungsFee  ·  {name_kurz}", align="L")
    pdf.cell(85, 5, _zeitraum_label(zeitraum), align="R")

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
    # A – Ausgangsumsätze
    kz_81: Decimal = ZERO
    kz_83: Decimal = ZERO
    kz_86: Decimal = ZERO
    kz_88: Decimal = ZERO
    # B – Steuerfreie Umsätze (manuell)
    kz_41: Decimal = ZERO
    kz_87: Decimal = ZERO
    # C – ig. Erwerb
    kz_89: Decimal = ZERO
    kz_93: Decimal = ZERO
    # D – §13b
    kz_46: Decimal = ZERO
    kz_47: Decimal = ZERO
    kz_84: Decimal = ZERO
    kz_85: Decimal = ZERO
    # F – Vorsteuer
    kz_66: Decimal = ZERO
    kz_61: Decimal = ZERO
    kz_67: Decimal = ZERO
    zahllast: Decimal = ZERO
    ist_kleinunternehmer: bool = False
    hinweis: Optional[str] = None


class UStVASpeichernRequest(BaseModel):
    zeitraum: str
    kz_81: Decimal = ZERO
    kz_83: Decimal = ZERO
    kz_86: Decimal = ZERO
    kz_88: Decimal = ZERO
    kz_41: Decimal = ZERO
    kz_87: Decimal = ZERO
    kz_89: Decimal = ZERO
    kz_93: Decimal = ZERO
    kz_46: Decimal = ZERO
    kz_47: Decimal = ZERO
    kz_84: Decimal = ZERO
    kz_85: Decimal = ZERO
    kz_66: Decimal = ZERO
    kz_61: Decimal = ZERO
    kz_67: Decimal = ZERO
    zahllast: Decimal = ZERO


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/berechnen", response_model=UStVAErgebnis)
def ustva_berechnen(
    zeitraum: str = Query(..., description="YYYY-MM oder YYYY-QN"),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")

    von, bis, typ = _zeitraum_grenzen(zeitraum)
    ist_ku = bool(unt.ist_kleinunternehmer)

    if ist_ku:
        kz: dict = {k: ZERO for k in ALL_KZ_KEYS}
        hinweis = ("Als Kleinunternehmer nach §19 UStG bist du von der UStVA befreit. "
                   "Umsätze werden in Zeile 23 (KZ 48) als steuerfreie Umsätze ohne "
                   "Vorsteuerabzug eingetragen – nur einmal jährlich in der Jahressteuererklärung.")
    else:
        kz = _berechne_kz(von, bis, db)
        hinweis = None

    return UStVAErgebnis(
        zeitraum=zeitraum, zeitraum_typ=typ, von=von, bis=bis,
        ist_kleinunternehmer=ist_ku, hinweis=hinweis,
        **{k: v for k, v in kz.items() if k != "zahllast"},
        zahllast=kz["zahllast"],
    )


@router.post("/speichern")
def ustva_speichern(req: UStVASpeichernRequest, db: Session = Depends(get_db)):
    _zeitraum_grenzen(req.zeitraum)
    eintrag = db.query(UstvaExport).filter(UstvaExport.zeitraum == req.zeitraum).first()
    if not eintrag:
        eintrag = UstvaExport(zeitraum=req.zeitraum)
        db.add(eintrag)
    _, _, typ = _zeitraum_grenzen(req.zeitraum)
    eintrag.zeitraum_typ = typ
    eintrag.kz_81 = req.kz_81; eintrag.kz_83 = req.kz_83
    eintrag.kz_86 = req.kz_86; eintrag.kz_88 = req.kz_88
    eintrag.kz_66 = req.kz_66; eintrag.kz_41 = req.kz_41
    eintrag.zahllast = req.zahllast
    eintrag.daten_json = json.dumps({k: str(v) for k, v in req.model_dump().items()})
    db.commit()
    return {"ok": True, "zeitraum": req.zeitraum}


@router.get("/historie")
def ustva_historie(db: Session = Depends(get_db)):
    eintraege = db.query(UstvaExport).order_by(UstvaExport.zeitraum.desc()).all()
    return [
        {"zeitraum": e.zeitraum, "zeitraum_typ": e.zeitraum_typ,
         "zahllast": float(e.zahllast), "erstellt_am": e.erstellt_am.isoformat()}
        for e in eintraege
    ]


@router.get("/pdf")
def ustva_pdf(
    zeitraum: str = Query(...),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")
    von, bis, _ = _zeitraum_grenzen(zeitraum)
    kz = _berechne_kz(von, bis, db)
    pdf_bytes = _generate_pdf(zeitraum, kz, unt)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="UStVA_{zeitraum}.pdf"'},
    )
