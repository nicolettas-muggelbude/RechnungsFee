"""
Profilmanager (docs/ROADMAP.md): Verwaltung mehrerer Firmenprofile pro Installation.
Rein dateisystembasiert, kein Depends(get_db) - analog zu api/setup.py. Ein Wechsel
oder Neuanlegen erfordert zwingend einen Prozess-Neustart (siehe Kommentar in
database/connection.py): mehrere Backend-Module binden APP_DATA_DIR-abgeleitete Pfade
als Modul-Level-Konstante zur Importzeit, ein Wechsel zur Laufzeit würde zu stillem
Datensalat zwischen Profilen führen.
"""
import json
import shutil
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.connection import BASE_DIR, ist_gueltiger_profilname
from utils import geheimnisse, profil_zugang

router = APIRouter(prefix="/api/profile", tags=["Profilmanager"])

_PROFILE_ROOT = BASE_DIR / "profile"
_ZEIGER_PFAD = BASE_DIR / "profile.json"


# Issue #593: Pause nach falschem Passwort (bremst Durchprobieren)
_FEHLER_PAUSE_S = 1.0


def _lese_zeiger() -> dict:
    try:
        zeiger = json.loads(_ZEIGER_PFAD.read_text(encoding="utf-8"))
        return zeiger if isinstance(zeiger, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _schreibe_zeiger(**werte) -> None:
    """Weitere Schlüssel (auswahl_beim_start, Issue #593) bleiben beim Profilwechsel erhalten."""
    zeiger = _lese_zeiger()
    zeiger.update(werte)
    _ZEIGER_PFAD.write_text(json.dumps(zeiger), encoding="utf-8")


def _aktives_profil() -> str:
    aktiv = _lese_zeiger().get("active", "Standard")
    if isinstance(aktiv, str) and ist_gueltiger_profilname(aktiv):
        return aktiv
    return "Standard"


def _setze_aktives_profil(name: str) -> None:
    _schreibe_zeiger(active=name)


def _auswahl_beim_start() -> bool:
    return bool(_lese_zeiger().get("auswahl_beim_start", False))


def _pruefe_passwort_oder_403(ordner, passwort: str | None) -> None:
    if not profil_zugang.pruefe_passwort(ordner, passwort):
        time.sleep(_FEHLER_PAUSE_S)
        raise HTTPException(status_code=403, detail="Das Passwort ist falsch.")


def _archiv_ordner(name: str):
    """Ein archiviertes Profil ist derselbe Ordner, nur Punkt-präfigiert - dadurch
    ignoriert get_profile() ihn automatisch (bestehender Filter not p.name.startswith('.')),
    ohne dass Datenbank/Belege/Backups angefasst werden. Voll reversibel per
    stelle_profil_wieder_her(), im Gegensatz zum endgültigen Löschen."""
    return _PROFILE_ROOT / f".{name}"


class ProfilItem(BaseModel):
    name: str
    aktiv: bool
    passwort: bool = False   # Issue #593: Profil ist mit Passwort gesperrt


class ProfilListe(BaseModel):
    profile: list[ProfilItem]
    archiviert: list[str] = []
    auswahl_beim_start: bool = False


class ProfilStart(BaseModel):
    """Issue #593: alles, was der Startbildschirm vor der Anmeldung braucht."""
    profile: list[ProfilItem]
    gesperrt: bool
    auswahl_anzeigen: bool


class ProfilCreateRequest(BaseModel):
    name: str
    passwort: str | None = None


class ProfilAnmeldenRequest(BaseModel):
    passwort: str | None = None


class ProfilPasswortRequest(BaseModel):
    altes_passwort: str | None = None
    neues_passwort: str | None = None   # leer = Passwort entfernen


class StartEinstellungen(BaseModel):
    auswahl_beim_start: bool


class ProfilUmbenennenRequest(BaseModel):
    neuer_name: str


class ProfilLoeschenRequest(BaseModel):
    bestaetigung: str  # muss exakt dem Profilnamen entsprechen - zweite Absicherung
    # neben der Tippen-zum-Bestätigen-Eingabe im Frontend, da hier eine ganze Firma
    # inkl. aller GoBD-relevanten Aufzeichnungen unwiderruflich gelöscht wird.


class ProfilAktion(BaseModel):
    neustart_erforderlich: bool = True


def _profil_items() -> list[ProfilItem]:
    aktiv = _aktives_profil()
    if not _PROFILE_ROOT.exists():
        return []
    namen = sorted(p.name for p in _PROFILE_ROOT.iterdir() if p.is_dir() and not p.name.startswith("."))
    return [
        ProfilItem(name=n, aktiv=(n == aktiv), passwort=profil_zugang.hat_passwort(_PROFILE_ROOT / n))
        for n in namen
    ]


@router.get("", response_model=ProfilListe)
def get_profile():
    """Liste aller vorhandenen Profile, markiert welches aktiv ist, plus separat die
    archivierten (Punkt-präfigierten) Profile."""
    if not _PROFILE_ROOT.exists():
        return ProfilListe(profile=[], auswahl_beim_start=_auswahl_beim_start())
    archiviert = sorted(
        p.name[1:] for p in _PROFILE_ROOT.iterdir()
        if p.is_dir() and p.name.startswith(".") and ist_gueltiger_profilname(p.name[1:])
    )
    return ProfilListe(
        profile=_profil_items(),
        archiviert=archiviert,
        auswahl_beim_start=_auswahl_beim_start(),
    )


@router.get("/start", response_model=ProfilStart)
def get_profil_start():
    """Issue #593: auch bei gesperrtem Profil erreichbar (profil_zugang.erlaubt_wenn_gesperrt).
    Der Startbildschirm erscheint, wenn das Profil gesperrt ist oder die Auswahl beim Start
    eingeschaltet und in diesem Programmlauf noch nicht bestätigt wurde."""
    return ProfilStart(
        profile=_profil_items(),
        gesperrt=profil_zugang.gesperrt(),
        auswahl_anzeigen=_auswahl_beim_start() and not profil_zugang.auswahl_erledigt(),
    )


@router.put("/start/einstellungen", response_model=ProfilListe)
def setze_start_einstellungen(data: StartEinstellungen):
    """Issue #593: Profilauswahl beim Start ein-/ausschalten. Liegt in profile.json, nicht in
    einer Profil-Datenbank – der Schalter wird vor der Profilwahl gebraucht."""
    _schreibe_zeiger(auswahl_beim_start=data.auswahl_beim_start)
    return get_profile()


@router.post("/{name}/anmelden", response_model=ProfilAktion)
def melde_an(name: str, data: ProfilAnmeldenRequest):
    """Issue #593, Startbildschirm: gewähltes Profil öffnen (mit Passwort, falls gesetzt).
    Aktives Profil → entsperren, kein Neustart. Anderes Profil → Zeiger umstellen und
    Freigabeschein in dessen Ordner, damit nach dem Neustart nicht erneut gefragt wird."""
    ziel = _PROFILE_ROOT / name
    if not ist_gueltiger_profilname(name) or not ziel.is_dir():
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")
    _pruefe_passwort_oder_403(ziel, data.passwort)
    if name == _aktives_profil():
        profil_zugang.entsperre()
        return ProfilAktion(neustart_erforderlich=False)
    _setze_aktives_profil(name)
    profil_zugang.schreibe_freigabe(ziel)
    return ProfilAktion()


@router.post("/{name}/passwort", response_model=ProfilListe)
def setze_profil_passwort(name: str, data: ProfilPasswortRequest):
    """Issue #593: Passwort setzen, ändern (neues_passwort) oder entfernen (leer). Ist schon
    eines gesetzt, muss das bisherige mitkommen."""
    ziel = _PROFILE_ROOT / name
    if not ist_gueltiger_profilname(name) or not ziel.is_dir():
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")
    _pruefe_passwort_oder_403(ziel, data.altes_passwort)
    if data.neues_passwort:
        try:
            profil_zugang.setze_passwort(ziel, data.neues_passwort)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    else:
        profil_zugang.entferne_passwort(ziel)
    return get_profile()


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
    if data.passwort and len(data.passwort) < profil_zugang.MIN_LAENGE:
        raise HTTPException(
            status_code=422,
            detail=f"Das Passwort muss mindestens {profil_zugang.MIN_LAENGE} Zeichen lang sein.",
        )

    ziel.mkdir(parents=True)
    if data.passwort:
        profil_zugang.setze_passwort(ziel, data.passwort)
    _setze_aktives_profil(name)
    # Issue #593: gerade angelegt – nach dem Neustart weder Passwort noch Startauswahl abfragen
    profil_zugang.schreibe_freigabe(ziel)
    return ProfilAktion()


@router.post("/{name}/aktivieren", response_model=ProfilAktion)
def aktiviere_profil(name: str, data: ProfilAnmeldenRequest | None = None):
    """Wechselt das aktive Profil - wirkt erst nach einem Neustart der App. Issue #593: Hat
    das Zielprofil ein Passwort, wird es hier geprüft; der Freigabeschein erspart nach dem
    Neustart die zweite Abfrage."""
    ziel = _PROFILE_ROOT / name
    if not ist_gueltiger_profilname(name) or not ziel.exists():
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")
    _pruefe_passwort_oder_403(ziel, data.passwort if data else None)

    _setze_aktives_profil(name)
    profil_zugang.schreibe_freigabe(ziel)
    return ProfilAktion()


@router.put("/{name}", response_model=ProfilAktion)
def benenne_profil_um(name: str, data: ProfilUmbenennenRequest):
    """Benennt ein Profil um (Ordner-Rename). Ist es das aktive Profil, muss der
    Zeiger mitgeführt werden und ein Neustart folgen - die laufende Instanz hat ihre
    Datenbankverbindung noch über den alten Ordnernamen geöffnet (siehe Modul-Docstring:
    APP_DATA_DIR wird nur beim Start aufgelöst). Bei einem inaktiven Profil ist kein
    Neustart nötig, da während der Laufzeit nichts auf dessen Ordner zugreift."""
    if not ist_gueltiger_profilname(name):
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")
    quelle = _PROFILE_ROOT / name
    if not quelle.exists():
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")

    neuer_name = data.neuer_name.strip()
    if not ist_gueltiger_profilname(neuer_name):
        raise HTTPException(
            status_code=422,
            detail="Ungültiger Profilname – nur Buchstaben, Zahlen, Leerzeichen, Binde-/Unterstrich (max. 50 Zeichen).",
        )
    if neuer_name == name:
        return ProfilAktion(neustart_erforderlich=False)

    ziel = _PROFILE_ROOT / neuer_name
    if ziel.exists():
        raise HTTPException(status_code=409, detail=f"Profil '{neuer_name}' existiert bereits.")

    war_aktiv = (name == _aktives_profil())
    quelle.rename(ziel)
    if war_aktiv:
        _setze_aktives_profil(neuer_name)
    return ProfilAktion(neustart_erforderlich=war_aktiv)


@router.post("/{name}/archivieren", response_model=ProfilAktion)
def archiviere_profil(name: str):
    """Blendet ein Profil aus der Liste aus, ohne irgendetwas zu löschen (Ordner-Rename
    auf einen Punkt-Präfix) - die sichere Alternative zum endgültigen Löschen. Lässt
    sich jederzeit per stelle_profil_wieder_her() rückgängig machen. Das aktive Profil
    kann nicht archiviert werden (die laufende Instanz hätte sonst keinen gültigen
    Datenordner mehr)."""
    if not ist_gueltiger_profilname(name):
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")
    quelle = _PROFILE_ROOT / name
    if not quelle.exists():
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")
    if name == _aktives_profil():
        raise HTTPException(
            status_code=409,
            detail="Das aktive Profil kann nicht archiviert werden – zuerst zu einem anderen Profil wechseln.",
        )
    ziel = _archiv_ordner(name)
    if ziel.exists():
        raise HTTPException(status_code=409, detail=f"Es existiert bereits ein archiviertes Profil '{name}'.")

    quelle.rename(ziel)
    return ProfilAktion(neustart_erforderlich=False)


@router.post("/{name}/wiederherstellen", response_model=ProfilAktion)
def stelle_profil_wieder_her(name: str):
    """Macht archiviere_profil() rückgängig - Ordner-Rename zurück ohne Punkt-Präfix.
    Kein Datenverlust, da beim Archivieren nichts als der Ordnername verändert wurde."""
    if not ist_gueltiger_profilname(name):
        raise HTTPException(status_code=404, detail=f"Archiviertes Profil '{name}' nicht gefunden.")
    quelle = _archiv_ordner(name)
    if not quelle.exists():
        raise HTTPException(status_code=404, detail=f"Archiviertes Profil '{name}' nicht gefunden.")
    ziel = _PROFILE_ROOT / name
    if ziel.exists():
        raise HTTPException(status_code=409, detail=f"Profil '{name}' existiert bereits.")

    quelle.rename(ziel)
    return ProfilAktion(neustart_erforderlich=False)


def _loesche_profilordner(ordner, name: str, data: ProfilLoeschenRequest) -> None:
    if not ordner.exists():
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")
    if data.bestaetigung != name:
        raise HTTPException(status_code=422, detail="Bestätigung stimmt nicht mit dem Profilnamen überein.")
    # Security-Audit F6: Passwörter dieses Profils liegen im Schlüsselbund, nicht im Ordner
    geheimnisse.profil_entfernen(ordner)
    shutil.rmtree(ordner)


@router.delete("/{name}", status_code=204)
def loesche_profil(name: str, data: ProfilLoeschenRequest):
    """Löscht ein (nicht archiviertes) Profil direkt und unwiderruflich - Datenbank,
    Belege und Backups dieses Profils sind danach weg. Das aktive Profil kann nicht
    gelöscht werden (die laufende Instanz hätte sonst keinen gültigen Datenordner
    mehr). data.bestaetigung muss exakt dem Profilnamen entsprechen - zusätzliche
    serverseitige Hürde neben der Tippen-zum-Bestätigen-Eingabe im Frontend, da hier
    ganze Firmen samt aller GoBD-relevanten Aufzeichnungen unwiderruflich gelöscht
    werden. Die sicherere Alternative ist archiviere_profil() + hier später gezielt
    das archivierte Profil löschen (siehe loesche_archiviertes_profil())."""
    if not ist_gueltiger_profilname(name):
        raise HTTPException(status_code=404, detail=f"Profil '{name}' nicht gefunden.")
    if name == _aktives_profil():
        raise HTTPException(
            status_code=409,
            detail="Das aktive Profil kann nicht gelöscht werden – zuerst zu einem anderen Profil wechseln.",
        )
    _loesche_profilordner(_PROFILE_ROOT / name, name, data)


@router.delete("/{name}/archiv", status_code=204)
def loesche_archiviertes_profil(name: str, data: ProfilLoeschenRequest):
    """Löscht ein bereits archiviertes Profil endgültig - der zweite, bewusste Schritt
    nach archiviere_profil() für alle, die den Ordner wirklich nicht mehr brauchen."""
    if not ist_gueltiger_profilname(name):
        raise HTTPException(status_code=404, detail=f"Archiviertes Profil '{name}' nicht gefunden.")
    _loesche_profilordner(_archiv_ordner(name), name, data)
