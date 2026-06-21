"""Anlage G – Einkünfte aus Gewerbebetrieb (§15 EStG).

Anzeigehilfe: Zeigt die relevanten Werte für ELSTER auf Basis der EÜR
und der Unternehmensstammdaten. Keine Steuerberatung, keine Übermittlung.
"""
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sqlalchemy import extract, func

from api.euer import _berechne_euer
from database.connection import get_db
from database.models import Anlagegut, Journaleintrag, Kategorie, Unternehmen

router = APIRouter(prefix="/api/anlage-g", tags=["Anlage G"])

GEWST_FREIBETRAG = Decimal("24500")
STEUERMESSZAHL = Decimal("0.035")   # 3,5 ‰ für Einzelunternehmer
ANRECHNUNGSFAKTOR = Decimal("4.0")  # §35 EStG, seit VZ 2020 (JStG 2019)


class AnlageGKfzHinweis(BaseModel):
    bezeichnung: str
    kennzeichen: str
    privat_anteil_prozent: Decimal


class AnlageGErgebnis(BaseModel):
    jahr: int
    vorname: str
    nachname: str
    steuernummer: str
    finanzamt: str
    art_des_gewerbes: str
    gewinn_verlust: Decimal
    kfz_hinweise: list[AnlageGKfzHinweis]
    taetigkeitsart: str
    # Gewerbesteuer
    gewst_pflichtig: bool
    gewst_gezahlt: Decimal      # Summe gebuchter Gewerbesteuer-Zahlungen im Jahr
    gewst_messbetrag_approx: Decimal   # Schätzung ohne Hinzurechnungen/Kürzungen


@router.get("/berechnen", response_model=AnlageGErgebnis)
def anlage_g_berechnen(
    jahr: int = Query(..., ge=2020, le=2100),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")

    euer = _berechne_euer(jahr, db)
    gv: Decimal = euer["gewinn_verlust"]

    kfz_list = (
        db.query(Anlagegut)
        .filter(
            Anlagegut.typ == "kfz",
            Anlagegut.aktiv == True,  # noqa: E712
            Anlagegut.privat_anteil_prozent > 0,
            Anlagegut.verkauft_am == None,  # noqa: E711
        )
        .all()
    )

    # Gezahlte Gewerbesteuer aus dem Journal summieren
    gewst_kategorie = (
        db.query(Kategorie)
        .filter(Kategorie.name.ilike("%gewerbesteuer%"))
        .first()
    )
    gewst_gezahlt = Decimal("0")
    if gewst_kategorie:
        row = (
            db.query(func.sum(Journaleintrag.brutto_betrag))
            .filter(
                Journaleintrag.kategorie_id == gewst_kategorie.id,
                extract("year", Journaleintrag.datum) == jahr,
            )
            .scalar()
        )
        if row:
            gewst_gezahlt = Decimal(str(row)).quantize(Decimal("0.01"))

    # Grobe Gewerbeertrag-Schätzung (ohne Hinzurechnungen/Kürzungen)
    # §11 Abs. 1 GewStG: Abrundung auf volle 100 € vor Messbetrag-Berechnung
    gewerbeertrag = max(gv - GEWST_FREIBETRAG, Decimal("0"))
    gewerbeertrag_gerundet = (gewerbeertrag // 100) * 100
    messbetrag_approx = (gewerbeertrag_gerundet * STEUERMESSZAHL).quantize(Decimal("0.01"))

    return AnlageGErgebnis(
        jahr=jahr,
        vorname=unt.vorname or "",
        nachname=unt.nachname or "",
        steuernummer=unt.steuernummer or "",
        finanzamt=unt.finanzamt or "",
        art_des_gewerbes=unt.bezeichnung_des_gewerbes or "",
        gewinn_verlust=gv,
        kfz_hinweise=[
            AnlageGKfzHinweis(
                bezeichnung=k.bezeichnung or "",
                kennzeichen=k.kennzeichen or "",
                privat_anteil_prozent=k.privat_anteil_prozent,
            )
            for k in kfz_list
        ],
        taetigkeitsart=unt.taetigkeitsart or "gewerbe",
        gewst_pflichtig=gv > GEWST_FREIBETRAG,
        gewst_gezahlt=gewst_gezahlt,
        gewst_messbetrag_approx=messbetrag_approx,
    )


# ---------------------------------------------------------------------------
# PDF
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


def _euro(v: Decimal) -> str:
    neg = v < 0
    s = f"{abs(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    return ("− " if neg else "") + s


def _generate_anlage_g_pdf(ergebnis: AnlageGErgebnis, messbetrag: float, hebesatz: int = 0) -> bytes:
    messbetrag_d = Decimal(str(messbetrag)).quantize(Decimal("0.01"))
    from fpdf import FPDF

    BLAU = (22, 163, 74)    # Grün statt Blau – visuell von Anlage S unterscheidbar
    GRAU = (229, 231, 235)
    DUNKEL = (30, 41, 59)
    MITTEL = (100, 116, 139)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    fonts = _fonts()
    pdf.add_font("DejaVu", "",  str(fonts / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", "B", str(fonts / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, margin=20)

    pdf.set_fill_color(*BLAU)
    pdf.rect(0, 0, 210, 18, "F")
    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(20, 5)
    pdf.cell(0, 8, f"Anlage G – Einkünfte aus Gewerbebetrieb {ergebnis.jahr}", ln=True)
    pdf.set_text_color(*DUNKEL)

    name = f"{ergebnis.nachname}, {ergebnis.vorname}".strip(", ")
    pdf.set_xy(20, 24)
    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(0, 7, name or "—", ln=True)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(*MITTEL)
    pdf.cell(0, 5, f"Steuernummer: {ergebnis.steuernummer or '—'}  ·  Finanzamt: {ergebnis.finanzamt or '—'}", ln=True)
    pdf.ln(4)

    def section_header(titel: str):
        pdf.set_fill_color(*GRAU)
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_x(20)
        pdf.cell(170, 6, f"  {titel.upper()}", fill=True, ln=True)
        pdf.ln(1)

    def zeile_row(zeile: str, bez: str, wert: str):
        y = pdf.get_y()
        h = 6.5
        pdf.set_fill_color(*BLAU)
        pdf.set_font("DejaVu", "B", 8)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(20, y)
        pdf.cell(16, h, f"Z. {zeile}", border=0, fill=True, align="C")
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.set_xy(38, y)
        pdf.cell(110, h, bez, border=0, align="L")
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_xy(148, y)
        pdf.cell(42, h, wert, border=0, align="L")
        pdf.ln(h + 1)

    def text_row(bez: str, wert: str):
        y = pdf.get_y()
        h = 6.5
        pdf.set_xy(38, y)
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*DUNKEL)
        pdf.cell(110, h, bez, border=0, align="L")
        pdf.set_font("DejaVu", "B", 9)
        pdf.set_xy(148, y)
        pdf.cell(42, h, wert or "—", border=0, align="L")
        pdf.ln(h + 1)

    section_header("Persönliche Angaben")
    zeile_row("1", "Name, Vorname", name or "—")
    text_row("Finanzamt", ergebnis.finanzamt or "—")
    zeile_row("3", "Steuernummer", ergebnis.steuernummer or "—")
    zeile_row("4", "genaue Bezeichnung des Gewerbes", ergebnis.art_des_gewerbes or "—")
    pdf.ln(2)

    gv = ergebnis.gewinn_verlust
    ist_gewinn = gv >= 0
    section_header("Laufende Einkünfte (aus EÜR §4 Abs. 3 EStG, ELSTER KZ 10/11)")
    text_row("Gewinn 1. Betrieb", _euro(gv) if ist_gewinn else "—")
    text_row("Verlust 1. Betrieb", _euro(gv) if not ist_gewinn else "—")
    pdf.ln(2)

    if ergebnis.kfz_hinweise:
        section_header("KFZ – Privatnutzung")
        for k in ergebnis.kfz_hinweise:
            bez = f"{k.bezeichnung}"
            if k.kennzeichen:
                bez += f" ({k.kennzeichen})"
            bez += f" – {int(k.privat_anteil_prozent)} % Privatanteil"
            zeile_row("→", bez, "manuell ermitteln")
        pdf.ln(2)

    section_header("Gewerbesteuer-Anrechnung §35 EStG")
    text_row("Freibetrag: 24.500 € (Einzelunternehmer)", "")
    if ergebnis.gewst_pflichtig:
        if ergebnis.gewst_gezahlt > 0:
            zeile_row("52", "Gewerbesteuer-Vorauszahlungen (lt. Journal)", _euro(ergebnis.gewst_gezahlt))
        zeile_row("51", "Gewerbesteuer-Messbetrag (lt. Bescheid)",
                  _euro(messbetrag_d) if messbetrag_d > 0 else "→ aus Bescheid")
        if hebesatz > 0:
            text_row("Hebesatz (aus Bescheid)", f"{hebesatz} %")
        # §35 EStG: anrechenbarer Betrag = Messbetrag × 4,0, gedeckelt auf tatsächliche GewSt
        # Deckelung greift wenn Hebesatz < 400 % (tatsächl. GewSt < Messbetrag × 4,0)
        faktor = min(ANRECHNUNGSFAKTOR, Decimal(hebesatz) / 100) if hebesatz > 0 else ANRECHNUNGSFAKTOR
        anrechnung = (messbetrag_d * faktor).quantize(Decimal("0.01"))
        faktor_label = f"{faktor:.1f}".replace(".", ",")
        text_row(f"Anrechenbarer Betrag (Messbetrag × {faktor_label}, §35 EStG)",
                 _euro(anrechnung) if messbetrag_d > 0 else "—")
        if ergebnis.gewst_messbetrag_approx > 0 and messbetrag_d == 0:
            text_row("Richtwert Messbetrag (Schätzung, ohne Hinzurechnungen/Kürzungen)",
                     _euro(ergebnis.gewst_messbetrag_approx))
    else:
        text_row("Gewinn unter Freibetrag – voraussichtlich keine Gewerbesteuer", "")
    pdf.ln(2)

    pdf.set_fill_color(*DUNKEL)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("DejaVu", "B", 10)
    pdf.set_x(20)
    label = f"Gewinn {ergebnis.jahr} (ELSTER KZ 10/11)" if ist_gewinn else f"Verlust {ergebnis.jahr} (ELSTER KZ 10/11)"
    pdf.cell(100, 8, f"  {label}", fill=True, align="L")
    pdf.set_text_color(255, 100, 100) if not ist_gewinn else pdf.set_text_color(255, 255, 255)
    pdf.cell(70, 8, _euro(gv), fill=True, align="L")
    pdf.ln(10)

    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(*MITTEL)
    pdf.set_x(20)
    pdf.multi_cell(
        170, 4,
        f"Anzeigehilfe – keine Steuerberatung. Grundlage: EÜR {ergebnis.jahr} (Zuflussprinzip). "
        "Gewerbesteuer-Messbetrag bitte aus dem Gewerbesteuer-Festsetzungsbescheid übernehmen. "
        "Zeilennummern nach Anlage G des jeweiligen Jahres – bitte vor der Übertragung in ELSTER prüfen.",
        align="L",
    )

    return pdf.output()


@router.get("/pdf")
def anlage_g_pdf(
    jahr: int = Query(..., ge=2020, le=2100),
    messbetrag: float = Query(default=0.0, ge=0),
    hebesatz: int = Query(default=0, ge=0, le=1000),
    db: Session = Depends(get_db),
):
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(404, "Unternehmensdaten nicht gefunden.")
    ergebnis = anlage_g_berechnen(jahr=jahr, db=db)
    pdf_bytes = _generate_anlage_g_pdf(ergebnis, messbetrag, hebesatz)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="AnlageG_{jahr}.pdf"'},
    )
