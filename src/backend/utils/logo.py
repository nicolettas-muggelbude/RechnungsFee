"""
Firmenlogo-Datei auflösen (Issue #454).

logo_pfad wurde lange als ABSOLUTER Pfad gespeichert (z. B. "C:\\Users\\…\\uploads\\logo.png") -
auch im eingefrorenen absender_snapshot finalisierter Dokumente. Nach einem Backup-Import auf
einem anderen System, einem Profilwechsel oder einem Umzug des Datenordners existiert dieser
Pfad nicht mehr, die Datei selbst liegt aber (aus dem Voll-Backup wiederhergestellt) unter
gleichem Namen im aktuellen uploads/-Ordner.

Neu gespeichert wird relativ zum Datenordner ("uploads/logo.png"). Für alte Werte wird der
Dateiname unabhängig vom Trennzeichen ermittelt - unter macOS/Linux kennt pathlib "\\" nicht als
Trenner, Path("C:\\…\\logo.png").name lieferte dort den ganzen String.
"""
from pathlib import Path, PureWindowsPath
from typing import Optional

from database.connection import APP_DATA_DIR

LOGO_RELATIV_BASIS = "uploads"


def logo_relativ(dateiname: str) -> str:
    """Speicherform für logo_pfad: relativ zum Datenordner."""
    return f"{LOGO_RELATIV_BASIS}/{dateiname}"


def logo_datei(logo_pfad: Optional[str], app_data_dir: Optional[Path] = None) -> Optional[Path]:
    """Tatsächliche Logo-Datei zum gespeicherten Pfad, oder None wenn keine auffindbar ist."""
    if not logo_pfad:
        return None
    basis = app_data_dir or APP_DATA_DIR
    pfad = Path(logo_pfad)
    if not pfad.is_absolute():
        pfad = basis / pfad
    if pfad.is_file():
        return pfad
    # PureWindowsPath trennt sowohl an "\" als auch an "/" - funktioniert für Windows-, macOS-
    # und Linux-Pfade gleichermaßen
    name = PureWindowsPath(logo_pfad).name
    if not name:
        return None
    alternativ = basis / LOGO_RELATIV_BASIS / name
    return alternativ if alternativ.is_file() else None
