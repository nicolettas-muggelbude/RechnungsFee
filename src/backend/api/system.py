"""
Systemverwaltungs-Endpunkte: Tesseract OCR prüfen und installieren.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from fastapi import APIRouter

router = APIRouter(prefix="/api/system", tags=["system"])


# ---------------------------------------------------------------------------
# Bekannte Installations-Pfade (falls Tesseract nicht im Prozess-PATH landet)
# Hintergrund: winget / apt / brew aktualisieren den Benutzer-PATH im Registry,
# aber laufende Prozesse und deren Kinder erben den alten PATH. Selbst nach
# App-Neustart kann der neue PATH noch fehlen, wenn der Windows-Explorer die
# Umgebungsvariablen noch nicht neu eingelesen hat.
# ---------------------------------------------------------------------------
_BEKANNTE_PFADE: dict[str, list[str]] = {
    "Windows": [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Programs\Tesseract-OCR\tesseract.exe"),
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ],
    "Darwin": [
        "/opt/homebrew/bin/tesseract",   # Apple Silicon
        "/usr/local/bin/tesseract",       # Intel
    ],
    "Linux": [
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ],
}


def finde_tesseract() -> str | None:
    """
    Gibt den Pfad zur tesseract-Binärdatei zurück oder None.
    Prüft zuerst PATH, dann bekannte Installationsverzeichnisse.
    Öffentliche Funktion – kann von anderen Modulen importiert werden.
    """
    pfad = shutil.which("tesseract")
    if pfad:
        return pfad
    for p in _BEKANNTE_PFADE.get(platform.system(), []):
        if p and os.path.isfile(p):
            return p
    return None


def _no_window() -> dict:
    """Unterdrückt ein Konsolenfenster auf Windows."""
    if platform.system() == "Windows":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


@router.get("/tesseract")
def tesseract_status():
    """Prüft ob tesseract-ocr installiert und erreichbar ist."""
    return {"installiert": finde_tesseract() is not None}


@router.get("/tesseract/voraussetzungen")
def tesseract_voraussetzungen():
    """
    Gibt zurück welche Installations-Voraussetzungen auf diesem System erfüllt sind.
    Hilft dem Frontend die richtige Installations-Strategie zu wählen.
    """
    os_name = platform.system()
    return {
        "os": os_name,                                     # "Windows" | "Darwin" | "Linux"
        "winget":  shutil.which("winget") is not None,    # Windows
        "brew":    shutil.which("brew") is not None,      # macOS
        "apt":     shutil.which("apt") is not None,       # Debian/Ubuntu
        "dnf":     shutil.which("dnf") is not None,       # Fedora/RHEL
        "pacman":  shutil.which("pacman") is not None,    # Arch
        "pkexec":  shutil.which("pkexec") is not None,    # Linux: GUI-Passwortabfrage
    }


@router.post("/tesseract/installieren")
def tesseract_installieren():
    """
    Installiert tesseract-ocr automatisch über den plattformeignen Paketmanager.
    Windows: winget  |  macOS: brew  |  Linux: pkexec + apt/dnf/pacman
    Gibt {"erfolg": bool, "fehler": str|None} zurück.
    """
    os_name = platform.system()

    try:
        # ── Windows ──────────────────────────────────────────────────────────
        if os_name == "Windows":
            winget = shutil.which("winget")
            if not winget:
                return {"erfolg": False, "fehler": "WINGET_FEHLT"}
            r = subprocess.run(
                [winget, "install", "-e", "--id", "UB-Mannheim.TesseractOCR",
                 "--silent", "--accept-source-agreements", "--accept-package-agreements"],
                capture_output=True, text=True, timeout=180,
                **_no_window(),
            )
            # winget gibt 0 oder -1978335189 (bereits installiert) zurück
            return {"erfolg": r.returncode in (0, -1978335189)}

        # ── macOS ─────────────────────────────────────────────────────────────
        if os_name == "Darwin":
            brew = shutil.which("brew")
            if not brew:
                return {"erfolg": False, "fehler": "BREW_FEHLT"}
            r = subprocess.run(
                [brew, "install", "tesseract", "tesseract-lang"],
                capture_output=True, text=True, timeout=300,
            )
            return {"erfolg": r.returncode == 0}

        # ── Linux ─────────────────────────────────────────────────────────────
        pkexec = shutil.which("pkexec")
        if not pkexec:
            return {"erfolg": False, "fehler": "PKEXEC_FEHLT"}

        apt    = shutil.which("apt")
        dnf    = shutil.which("dnf")
        pacman = shutil.which("pacman")

        if apt:
            cmd = [pkexec, "apt", "install", "-y", "tesseract-ocr", "tesseract-ocr-deu"]
        elif dnf:
            cmd = [pkexec, "dnf", "install", "-y", "tesseract", "tesseract-langpack-deu"]
        elif pacman:
            cmd = [pkexec, "pacman", "-S", "--noconfirm", "tesseract", "tesseract-data-deu"]
        else:
            return {"erfolg": False, "fehler": "KEIN_PAKETMANAGER"}

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {"erfolg": r.returncode == 0}

    except subprocess.TimeoutExpired:
        return {"erfolg": False, "fehler": "TIMEOUT"}
    except FileNotFoundError as exc:
        return {"erfolg": False, "fehler": f"NICHT_GEFUNDEN: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"erfolg": False, "fehler": str(exc)}
