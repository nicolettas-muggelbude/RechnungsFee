"""
Original-PDF-Archivierung und KOPIE-Wasserzeichen.

Beim ersten Drucken/Mailen wird das Original-PDF gespeichert.
Alle weiteren Ausgaben laden das Original und legen ein Wasserzeichen drüber.
"""
from io import BytesIO
from pathlib import Path

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

_RECHNUNGEN_PDF_SUBDIR = "uploads/rechnungen"


def _storage_dir(data_dir: Path) -> Path:
    d = data_dir / _RECHNUNGEN_PDF_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def speichere_original_pdf(data_dir: Path, rechnung_id: int, pdf_bytes: bytes) -> str:
    """Speichert Original-PDF auf Disk. Gibt relativen Pfad zurück (für DB-Feld)."""
    pfad = _storage_dir(data_dir) / f"{rechnung_id}.pdf"
    pfad.write_bytes(pdf_bytes)
    return f"{_RECHNUNGEN_PDF_SUBDIR}/{rechnung_id}.pdf"


def lade_original_mit_kopie_stempel(data_dir: Path, rel_pfad: str) -> bytes | None:
    """Lädt gespeichertes Original und legt KOPIE-Wasserzeichen drüber.
    Gibt None zurück wenn die Datei fehlt (Fallback: frisch generieren)."""
    datei = data_dir / rel_pfad
    if not datei.exists():
        return None
    return _overlay_kopie(datei.read_bytes())


def _wasserzeichen_seite(breite_mm: float, hoehe_mm: float) -> bytes:
    """Erstellt eine KOPIE-Wasserzeichen-Seite (diagonal, halbtransparent rot)."""
    pdf = FPDF(format=(breite_mm, hoehe_mm))
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=72)
    with pdf.local_context(fill_opacity=0.25, stroke_opacity=0.25):
        pdf.set_text_color(180, 0, 0)
        with pdf.rotation(45, x=breite_mm / 2, y=hoehe_mm / 2):
            pdf.text(x=breite_mm / 2 - 33, y=hoehe_mm / 2 + 12, txt="KOPIE")
    return bytes(pdf.output())


def _overlay_kopie(original_bytes: bytes) -> bytes:
    """Legt das KOPIE-Wasserzeichen auf Seite 1 des PDFs."""
    reader = PdfReader(BytesIO(original_bytes))
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        if i == 0:
            w_mm = float(page.mediabox.width) * 0.352778   # pt → mm
            h_mm = float(page.mediabox.height) * 0.352778
            stamp = PdfReader(BytesIO(_wasserzeichen_seite(w_mm, h_mm))).pages[0]
            page.merge_page(stamp)
        writer.add_page(page)

    out = BytesIO()
    writer.write(out)
    return out.getvalue()
