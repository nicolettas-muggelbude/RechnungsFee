"""
API-Endpunkte für Unternehmensstammdaten.
Es gibt immer genau einen Datensatz (id=1).
"""

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database.connection import get_db, APP_DATA_DIR
from database.models import Unternehmen
from .schemas import UnternehmenCreate, UnternehmenUpdate, UnternehmenResponse

router = APIRouter(prefix="/api/unternehmen", tags=["Stammdaten"])

# War früher hartkodiert auf Path.home()/".local/share/RechnungsFee/uploads" - ignorierte
# sowohl Windows/macOS (dort landete das Logo faktisch in einem toten Ordner) als auch
# den Profilmanager (siehe database/connection.py: APP_DATA_DIR zeigt jetzt auf das aktive
# Profil, profile/<name>/uploads/ statt direkt uploads/).
UPLOAD_DIR = APP_DATA_DIR / "uploads"
ERLAUBTE_TYPEN = {"image/png", "image/jpeg", "image/webp", "image/svg+xml"}
MAX_LOGO_BYTES = 2 * 1024 * 1024  # 2 MB


def _upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


@router.get("", response_model=UnternehmenResponse | None)
def get_unternehmen(db: Session = Depends(get_db)):
    """Gibt die Unternehmensdaten zurück, oder null wenn noch nicht eingerichtet."""
    return db.query(Unternehmen).first()


@router.post("", response_model=UnternehmenResponse, status_code=201)
def create_unternehmen(data: UnternehmenCreate, db: Session = Depends(get_db)):
    """Erstellt die Unternehmensdaten (nur beim ersten Setup)."""
    if db.query(Unternehmen).first():
        raise HTTPException(
            status_code=409,
            detail="Unternehmensdaten bereits vorhanden. Bitte PUT verwenden.",
        )
    unternehmen = Unternehmen(**data.model_dump())
    db.add(unternehmen)
    db.commit()
    db.refresh(unternehmen)
    return unternehmen


@router.put("", response_model=UnternehmenResponse)
def update_unternehmen(data: UnternehmenUpdate, db: Session = Depends(get_db)):
    """Aktualisiert die Unternehmensdaten."""
    unternehmen = db.query(Unternehmen).first()
    if not unternehmen:
        raise HTTPException(status_code=404, detail="Unternehmensdaten noch nicht angelegt.")
    # logo_pfad wird ausschließlich über POST/DELETE /logo verwaltet – nie überschreiben
    for key, value in data.model_dump(exclude_unset=True, exclude={"logo_pfad"}).items():
        setattr(unternehmen, key, value)
    db.commit()
    db.refresh(unternehmen)
    return unternehmen


# ---------------------------------------------------------------------------
# Logo-Endpunkte
# ---------------------------------------------------------------------------

# CSS-Referenz: 96px = 1in (https://www.w3.org/TR/css-values-3/#absolute-lengths)
_SVG_EINHEIT_ZU_PX = {
    "": 1.0, "px": 1.0, "in": 96.0, "cm": 96.0 / 2.54, "mm": 96.0 / 25.4,
    "pt": 96.0 / 72.0, "pc": 16.0,
}


def _svg_ohne_ungueltige_groesse(svg_text: str) -> str:
    """Normalisiert width/height am Wurzel-<svg>-Element für resvg.

    resvg lehnt eine SVG mit width/height <= 0 mit "SVG has an invalid size" ab, selbst wenn
    ein gültiges viewBox vorhanden ist - die ungültige Quellgröße wird zuerst geprüft. Manche
    Export-Tools legen aber genau solche Platzhalter-Nullen an. Wird das Attribut entfernt,
    fällt resvg auf das viewBox zurück (oder eine Standardgröße, falls auch das fehlt).

    Zusätzlich unterstützt resvg_py physische Einheiten wie "25mm" offenbar nicht direkt -
    selbst ein gültiger positiver Wert scheitert dann mit derselben Fehlermeldung. Solche Werte
    werden deshalb in eine einheitenlose Pixelzahl umgerechnet (96-DPI-Referenz nach
    CSS-Spezifikation) statt nur entfernt - das erhält den beabsichtigten Maßstab relativ zu
    einem eventuell vorhandenen viewBox, statt ihn wegzuwerfen (Windows-11-Meldung 2026-08-04,
    Folgefehler: „mit dem was 25mm hoch ist funktioniert es nicht")."""
    def _px_wert(rohwert: str) -> float | None:
        m = re.match(r"\s*(-?[\d.]+)\s*([a-zA-Z%]*)\s*$", rohwert)
        if not m:
            return None  # kein erkennbares Zahlenformat - lieber unangetastet lassen
        einheit = m.group(2).lower()
        if einheit not in _SVG_EINHEIT_ZU_PX:
            return None  # z.B. "%", em, ex - keine verlässliche absolute Umrechnung, unangetastet
        return float(m.group(1)) * _SVG_EINHEIT_ZU_PX[einheit]

    def _repl(m: re.Match) -> str:
        tag = m.group(0)
        for attr in ("width", "height"):
            am = re.search(rf'\s{attr}\s*=\s*["\']([^"\']*)["\']', tag)
            if not am:
                continue
            px = _px_wert(am.group(1))
            if px is None:
                continue
            ersatz = "" if px <= 0 else f' {attr}="{px:.4f}"'
            tag = tag[:am.start()] + ersatz + tag[am.end():]
        return tag
    return re.sub(r"<svg\b[^>]*>", _repl, svg_text, count=1)


@router.post("/logo", response_model=UnternehmenResponse)
async def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Lädt ein Firmenlogo hoch (PNG/JPEG/WEBP, max 2 MB)."""
    unternehmen = db.query(Unternehmen).first()
    if not unternehmen:
        raise HTTPException(status_code=404, detail="Unternehmensdaten noch nicht angelegt.")

    inhalt = await file.read()
    if len(inhalt) > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="Logo darf maximal 2 MB groß sein.")

    # Content-Type aus Magic-Bytes ermitteln (imghdr wurde in Python 3.13 entfernt)
    def _detect_image_type(data: bytes) -> str | None:
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "png"
        if data[:3] == b"\xff\xd8\xff":
            return "jpeg"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "webp"
        stripped = data[:512].lstrip()
        if stripped.startswith(b"<?xml") or stripped.startswith(b"<svg"):
            return "svg"
        return None

    erkannt = _detect_image_type(inhalt)
    typ_map = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp", "svg": "image/svg+xml"}
    content_type = typ_map.get(erkannt or "", file.content_type or "")
    if content_type not in ERLAUBTE_TYPEN:
        raise HTTPException(status_code=400, detail="Nur PNG, JPEG, WEBP und SVG sind erlaubt.")

    # SVG → PNG konvertieren (resvg_py, Zoom entspricht 300 DPI – unterstützt Gradienten,
    # Clipping, eingebettete Raster). Vorher cairosvg: brauchte auf Windows eine separat zu
    # installierende libcairo-2.dll (GTK3-Runtime), die im PyInstaller-Build fehlte und den
    # Upload mit "no library called libcairo-2.dll was found" scheitern ließ (Windows 11,
    # gemeldet 2026-08-04). resvg_py bindet die Rust-Bibliothek statisch ins Wheel ein -
    # keine externen DLLs nötig, funktioniert plattformübergreifend ohne Zusatzinstallation.
    if content_type == "image/svg+xml":
        try:
            import resvg_py
            svg_text = _svg_ohne_ungueltige_groesse(inhalt.decode("utf-8"))
            inhalt = bytes(resvg_py.svg_to_bytes(svg_string=svg_text, zoom=300 / 96))
            content_type = "image/png"
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"SVG-Konvertierung fehlgeschlagen: {e}")

    # Dateierweiterung bestimmen
    ext_map = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
    ext = ext_map[content_type]
    ziel = _upload_dir() / f"logo.{ext}"

    # Altes Logo löschen (andere Erweiterung)
    if unternehmen.logo_pfad and unternehmen.logo_pfad != str(ziel):
        try:
            os.unlink(unternehmen.logo_pfad)
        except FileNotFoundError:
            pass

    with open(ziel, "wb") as f:
        f.write(inhalt)

    unternehmen.logo_pfad = str(ziel)
    db.commit()
    db.refresh(unternehmen)
    return unternehmen


@router.get("/logo")
def get_logo(db: Session = Depends(get_db)):
    """Liefert das gespeicherte Firmenlogo als Datei aus."""
    unternehmen = db.query(Unternehmen).first()
    if not unternehmen or not unternehmen.logo_pfad:
        raise HTTPException(status_code=404, detail="Kein Logo hinterlegt.")
    pfad = Path(unternehmen.logo_pfad)
    if not pfad.exists():
        # Selbstheilung: logo_pfad wurde als absoluter Pfad gespeichert (Altfehler, siehe
        # UPLOAD_DIR-Kommentar oben) - nach einer Profil-Migration oder einem Datenordner-
        # Umzug (z.B. macOS-Migration) liegt die Datei nicht mehr dort, sondern unter dem
        # gleichen Dateinamen im aktuellen UPLOAD_DIR. Pfad in der DB gleich dauerhaft
        # korrigieren, damit dieser Fallback nur einmal greifen muss.
        alternativ = UPLOAD_DIR / pfad.name
        if not alternativ.exists():
            raise HTTPException(status_code=404, detail="Logo-Datei nicht gefunden.")
        pfad = alternativ
        unternehmen.logo_pfad = str(pfad)
        db.commit()
    return FileResponse(str(pfad))


@router.delete("/logo", status_code=204)
def delete_logo(db: Session = Depends(get_db)):
    """Löscht das Firmenlogo."""
    unternehmen = db.query(Unternehmen).first()
    if not unternehmen:
        raise HTTPException(status_code=404, detail="Unternehmensdaten noch nicht angelegt.")
    if unternehmen.logo_pfad:
        try:
            os.unlink(unternehmen.logo_pfad)
        except FileNotFoundError:
            pass
        unternehmen.logo_pfad = None
        db.commit()
