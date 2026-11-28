"""
Issue #568 Stufe 2: mehrere Belege einer Buchung zu einem PDF zusammenführen - DATEV kennt pro
Buchung nur einen Beleglink. PDFs werden angehängt (PDF/A-Fassung bevorzugt), Bilder (JPEG, PNG,
TIFF) als eigene Seiten eingefügt.
"""
import logging
from pathlib import Path
from typing import Iterable, Optional

from database.models import Beleg

log = logging.getLogger(__name__)


def _quelle(beleg: Beleg, uploads: Path) -> Optional[Path]:
    if beleg.beleg_pdfa_pfad:
        p = uploads / beleg.beleg_pdfa_pfad
        if p.is_file():
            return p
    p = uploads / beleg.dateiname
    return p if p.is_file() else None


def belege_als_ein_pdf(belege: Iterable[Beleg], uploads: Path) -> Optional[bytes]:
    """Alle lesbaren Belege in Reihenfolge zu einem PDF. None, wenn keiner lesbar war."""
    import fitz  # pymupdf

    ziel = fitz.open()
    for beleg in belege:
        pfad = _quelle(beleg, uploads)
        if pfad is None:
            continue
        try:
            with fitz.open(str(pfad)) as quelle:
                if quelle.is_pdf:
                    ziel.insert_pdf(quelle)
                else:
                    with fitz.open("pdf", quelle.convert_to_pdf()) as als_pdf:
                        ziel.insert_pdf(als_pdf)
        except Exception:
            log.warning("Beleg %s konnte nicht zusammengeführt werden", beleg.id, exc_info=True)
    if ziel.page_count == 0:
        ziel.close()
        return None
    daten = ziel.tobytes(garbage=3, deflate=True)
    ziel.close()
    return daten
