"""
Issue #593: optionales Passwort je Profil und Profilauswahl beim Start.

Das Passwort ist eine Zugangssperre, keine Verschlüsselung: Datenbank, Belege und Backups bleiben
unverändert auf der Festplatte. Gespeichert wird nur ein scrypt-Hash in `zugang.json` im
Profilordner (nicht in der Datenbank – ein Backup oder eine Wiederherstellung ändert das Passwort
nicht). Passwort vergessen → `zugang.json` löschen (Wiki „Profile“).

Solange das aktive Profil ein Passwort hat und noch nicht entsperrt ist, weist die
SicherheitMiddleware alle API-Aufrufe außer der Profilauswahl mit 423 ab – sonst ließe sich die
Sperre über die API umgehen.

Profilwechsel: Ein Profil lässt sich nur beim Programmstart laden. Wer vor dem Wechsel das
Passwort des Zielprofils eingegeben hat, bekommt einen Einmal-Freigabeschein (`.freigabe.json`,
kurze Gültigkeit) in den Zielordner; der neue Prozess verbraucht ihn beim Start und fragt nicht
ein zweites Mal (auch die Startauswahl entfällt dann).
"""
import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

ZUGANG_DATEI = "zugang.json"
FREIGABE_DATEI = ".freigabe.json"
FREIGABE_GUELTIG_S = 120
MIN_LAENGE = 4
_N, _R, _P, _DKLEN = 2 ** 14, 8, 1, 32


def _hash(passwort: str, salt: bytes, n: int = _N, r: int = _R, p: int = _P) -> bytes:
    return hashlib.scrypt(passwort.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=_DKLEN)


def hat_passwort(ordner: Path) -> bool:
    return (ordner / ZUGANG_DATEI).is_file()


def setze_passwort(ordner: Path, passwort: str) -> None:
    if len(passwort) < MIN_LAENGE:
        raise ValueError(f"Das Passwort muss mindestens {MIN_LAENGE} Zeichen lang sein.")
    salt = secrets.token_bytes(16)
    daten = {
        "verfahren": "scrypt", "n": _N, "r": _R, "p": _P,
        "salt": salt.hex(), "hash": _hash(passwort, salt).hex(),
    }
    (ordner / ZUGANG_DATEI).write_text(json.dumps(daten), encoding="utf-8")


def entferne_passwort(ordner: Path) -> None:
    (ordner / ZUGANG_DATEI).unlink(missing_ok=True)


def pruefe_passwort(ordner: Path, passwort: str | None) -> bool:
    """True, wenn das Profil kein Passwort hat oder es stimmt. Eine beschädigte zugang.json
    entsperrt nie (Ausweg: Datei löschen)."""
    if not hat_passwort(ordner):
        return True
    if not passwort:
        return False
    try:
        d = json.loads((ordner / ZUGANG_DATEI).read_text(encoding="utf-8"))
        soll = bytes.fromhex(d["hash"])
        ist = _hash(passwort, bytes.fromhex(d["salt"]), int(d["n"]), int(d["r"]), int(d["p"]))
    except (OSError, ValueError, KeyError, TypeError):
        return False
    return hmac.compare_digest(soll, ist)


def schreibe_freigabe(ordner: Path) -> None:
    (ordner / FREIGABE_DATEI).write_text(
        json.dumps({"bis": time.time() + FREIGABE_GUELTIG_S}), encoding="utf-8")


def _verbrauche_freigabe(ordner: Path) -> bool:
    pfad = ordner / FREIGABE_DATEI
    if not pfad.exists():
        return False
    try:
        bis = float(json.loads(pfad.read_text(encoding="utf-8"))["bis"])
    except (OSError, ValueError, KeyError, TypeError):
        bis = 0.0
    pfad.unlink(missing_ok=True)
    return bis >= time.time()


# ── Zustand dieses Prozesses (ein Prozess = ein Profil) ──────────────────────
_entsperrt: bool | None = None
_auswahl_erledigt = False


def initialisiere(ordner: Path | None = None) -> None:
    """Beim Start: Freigabeschein verbrauchen, sonst gesperrt, wenn das Profil ein Passwort hat."""
    global _entsperrt, _auswahl_erledigt
    if ordner is None:
        from database.connection import APP_DATA_DIR
        ordner = APP_DATA_DIR
    freigabe = _verbrauche_freigabe(ordner)
    _entsperrt = freigabe or not hat_passwort(ordner)
    _auswahl_erledigt = freigabe


def gesperrt() -> bool:
    if _entsperrt is None:
        initialisiere()
    return not _entsperrt


def auswahl_erledigt() -> bool:
    return _auswahl_erledigt


def entsperre() -> None:
    """Passwort geprüft bzw. Startauswahl bestätigt."""
    global _entsperrt, _auswahl_erledigt
    _entsperrt = True
    _auswahl_erledigt = True


# Was bei gesperrtem Profil erreichbar bleibt: Startauswahl/Anmeldung, Backup beim Schließen
# (liest nichts aus), Beenden für den Updater, Health-Check.
_OFFEN_EXAKT = {
    ("GET", "/api/profile/start"),
    ("POST", "/api/backup/erstellen"),
    ("POST", "/api/shutdown"),
    ("GET", "/health"),
}


def erlaubt_wenn_gesperrt(methode: str, pfad: str) -> bool:
    if methode == "OPTIONS" or (methode, pfad) in _OFFEN_EXAKT:
        return True
    teile = pfad.split("/")
    # POST /api/profile/<name>/anmelden
    return methode == "POST" and len(teile) == 5 and teile[1:3] == ["api", "profile"] and teile[4] == "anmelden"
