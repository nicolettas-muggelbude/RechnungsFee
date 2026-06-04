"""
PDF/A-3 Konvertierung via ocrmypdf (CLI-Tool).

Benötigt: ocrmypdf (pip) + ghostscript (Systempaket)
  Ubuntu/Debian: sudo apt install ocrmypdf ghostscript
  Windows:       ocrmypdf via pip, Ghostscript von ghostscript.com
"""
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def ocrmypdf_verfuegbar() -> bool:
    """Prüft ob ocrmypdf im PATH vorhanden ist."""
    try:
        result = subprocess.run(
            ["ocrmypdf", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def konvertiere_zu_pdfa(src_path: Path, mime_type: str | None) -> Path | None:
    """
    Konvertiert eine Datei zu PDF/A-3.

    - PDF  → ocrmypdf --skip-text (Text-Layer beibehalten, nur Format konvertieren)
    - Bild → Pillow → PDF → ocrmypdf (mit OCR für Durchsuchbarkeit)

    Gibt den Pfad der PDF/A-Datei zurück oder None bei Fehler / fehlendem ocrmypdf.
    Die Ausgabedatei liegt im gleichen Verzeichnis wie src_path mit _pdfa-Suffix.
    """
    if not ocrmypdf_verfuegbar():
        logger.info("ocrmypdf nicht installiert – PDF/A-Konvertierung übersprungen.")
        return None

    pdfa_path = src_path.parent / (src_path.stem + "_pdfa.pdf")
    tmp_pdf = src_path.parent / (src_path.stem + "_tmp_pillow.pdf")

    try:
        if mime_type in ("image/jpeg", "image/png", "image/tiff"):
            _bild_zu_pdf(src_path, tmp_pdf)
            _pdf_zu_pdfa(tmp_pdf, pdfa_path, skip_text=False)
        else:
            _pdf_zu_pdfa(src_path, pdfa_path, skip_text=True)

        if pdfa_path.exists() and pdfa_path.stat().st_size > 0:
            return pdfa_path

        logger.warning(f"PDF/A-Ausgabedatei nicht vorhanden oder leer: {pdfa_path}")
        return None

    except Exception as exc:
        logger.warning(f"PDF/A-Konvertierung fehlgeschlagen ({src_path.name}): {exc}")
        pdfa_path.unlink(missing_ok=True)
        return None
    finally:
        tmp_pdf.unlink(missing_ok=True)


def _bild_zu_pdf(src: Path, dst: Path) -> None:
    """Konvertiert Bild-Datei zu einseiteigem PDF via Pillow."""
    from PIL import Image

    img = Image.open(src)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    img.save(dst, "PDF", resolution=150)


def _pdf_zu_pdfa(src: Path, dst: Path, skip_text: bool) -> None:
    """
    Ruft ocrmypdf auf um src als PDF/A-3 nach dst zu schreiben.

    ocrmypdf Exit-Codes:
      0 = Erfolg
      6 = Eingabe ist bereits PDF/A (Ausgabe trotzdem geschrieben)
    Alle anderen Codes werden als Fehler behandelt.
    """
    cmd = [
        "ocrmypdf",
        "--output-type", "pdfa-3",
        "--quiet",
    ]
    if skip_text:
        cmd.append("--skip-text")
    cmd += [str(src), str(dst)]

    result = subprocess.run(cmd, capture_output=True, timeout=120)

    if result.returncode in (0, 6):
        # 6 = already PDF/A; ocrmypdf schreibt die Datei trotzdem
        if not dst.exists():
            # Fallback: original kopieren falls dst nicht erzeugt wurde
            shutil.copy2(src, dst)
        return

    stderr = result.stderr.decode(errors="replace")[:400]
    raise RuntimeError(f"ocrmypdf exit {result.returncode}: {stderr}")
