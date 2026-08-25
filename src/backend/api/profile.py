"""
Profilmanager (docs/ROADMAP.md): Verwaltung mehrerer Firmenprofile pro Installation.
Rein dateisystembasiert, kein Depends(get_db) - analog zu api/setup.py. Ein Wechsel
oder Neuanlegen erfordert zwingend einen Prozess-Neustart (siehe Kommentar in
database/connection.py): mehrere Backend-Module binden APP_DATA_DIR-abgeleitete Pfade
als Modul-Level-Konstante zur Importzeit, ein Wechsel zur Laufzeit würde zu stillem
Datensalat zwischen Profilen führen.
"""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.connection import BASE_DIR, ist_gueltiger_profilname

router = APIRouter(prefix="/api/profile", tags=["Profilmanager"])

_PROFILE_ROOT = BASE_DIR / "profile"
_ZEIGER_PFAD = BASE_DIR / "profile.json"


def _aktives_profil() -> str:
    try:
        zeiger = json.loads(_ZEIGER_PFAD.read_text(encoding="utf-8"))
        aktiv = zeiger.get("active", "Standard")
        if ist_gueltiger_profilname(aktiv):
            return aktiv
    except (json.JSONDecodeError, OSError):
        pass
    return "Standard"


def _setze_aktives_profil(name: str) -> None:
    _ZEIGER_PFAD.write_text(json.dumps({"active": name}), encoding="utf-8")


class ProfilItem(BaseModel):
    name: str
    aktiv: bool


class ProfilListe(BaseModel):
    profile: list[ProfilItem]


class ProfilCreateRequest(BaseModel):
    name: str


class ProfilAktion(BaseModel):
    neustart_erforderlich: bool = True


@router.get("", response_model=ProfilListe)
def get_profile():
    """Liste aller vorhandenen Profile, markiert welches aktiv ist."""
    aktiv = _aktives_profil()
    if not _PROFILE_ROOT.exists():
        return ProfilListe(profile=[])
    namen = sorted(p.name for p in _PROFILE_ROOT.iterdir() if p.is_dir() and not p.name.startswith("."))
    return ProfilListe(profile=[ProfilItem(name=n, aktiv=(n == aktiv)) for n in namen])


@router.post("", response_model=ProfilAktion, status_code=201)
def create_profil(data: ProfilCreateRequest):
    """Legt ein neues, leeres Profil an und aktiviert es direkt - nach dem Neustart
    landet die App automatisch im Setup-Wizard (die neue DB ist ja leer, siehe
    api/setup.py get_setup_status())."""
    name = data.name.strip()
    if not ist_gueltiger_profilname(name):
        raise HTTPException(
            status_code=422,
            detail="Ungültiger Profilname – nur Buchstaben, Zahlen, Leerzeichen, Binde-/Unterstrich (max. 50 Zeichen).",
        )
    ziel = _PROFILE_ROOT / name
    if ziel.exists():
        raise HTTPException(status_code=409, detail=f"Profil '{name}' existiert bereits.")

    ziel.mkdir(parents=True)
    _setze_aktives_profil(name)
    return ProfilAktion()


@router.post("/{name}/aktivieren", response_model=ProfilAktion)
def aktiviere_profil(name: str):
    """Wechselt das aktive Profil - wirkt erst nach einem Neustart der App."""
    ziel = _PROFILE_ROOT / name
    if not ist_gueltiger_profilname(name) or not ziel.exists():
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")

    _setze_aktives_profil(name)
    return ProfilAktion()
