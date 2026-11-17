"""
Ablage von Zugangsdaten (Security-Audit F6).

SMTP-, IMAP-, SMB- und Backup-Verschlüsselungspasswort standen früher im Klartext in der Tabelle
`unternehmen` – damit auch in den lokalen Snapshots unter backups/, im Backup-Download und in
jeder API-Antwort von GET /api/unternehmen. Wer die Datenbank hatte, konnte so auch die
verschlüsselten externen Backups öffnen.

Jetzt steht in der jeweiligen Spalte nur noch ein Marker:

    NULL               nicht gesetzt
    "keyring:v1"       Passwort liegt im Schlüsselbund des Betriebssystems (Windows Credential
                       Manager, macOS Keychain, Secret Service/KWallet unter Linux)
    "enc:v1:<base64>"  Ersatzweg ohne nutzbaren Schlüsselbund (z. B. Linux ohne Secret Service,
                       WSLg): AES-256-GCM, Schlüssel in <Profilordner>/geheimnis.key (0600) –
                       außerhalb von uploads/, also weder im Backup-Download noch im Voll-Backup

Jeder andere Wert ist ein Alt-Klartext aus einer Version vor F6 und wird beim Start von
main.py::_migrate_geheimnisse() umgezogen.

Schlüssel im Schlüsselbund: Dienst "RechnungsFee", Benutzer "<profil-id>:<feld>". Die Profil-ID
ist eine UUID in <Profilordner>/geheimnis_id – bewusst nicht der Profilname (umbenennbar) und
nicht in der Datenbank (ein Backup aus Profil A, in Profil B wiederhergestellt, soll nicht auf
die Einträge von A zeigen).
"""

from __future__ import annotations

import base64
import os
import secrets
import uuid
from pathlib import Path

FELDER: tuple[str, ...] = (
    "smtp_passwort",
    "imap_passwort",
    "backup_extern_passwort",
    "backup_smb_passwort",
)

DIENST = "RechnungsFee"
MARKER_KEYRING = "keyring:v1"
PRAEFIX_DATEI = "enc:v1:"

_ID_DATEI = "geheimnis_id"
_SCHLUESSEL_DATEI = "geheimnis.key"

# Für Tests überschreibbar; None = aktives Profil (database.connection.APP_DATA_DIR)
DATEN_DIR: Path | None = None


class GeheimnisFehlt(Exception):
    """Marker gesetzt, Passwort aber nicht (mehr) lesbar – z. B. nach Wiederherstellung auf einem
    anderen Rechner oder nach Löschen des Schlüsselbund-Eintrags."""


# ---------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------

def ist_marker(wert: str | None) -> bool:
    """True für NULL und alle Marker – False nur für Alt-Klartext."""
    return wert is None or wert == "" or wert == MARKER_KEYRING or wert.startswith(PRAEFIX_DATEI)


def ist_gesetzt(wert: str | None) -> bool:
    return bool(wert)


def _daten_dir() -> Path:
    if DATEN_DIR is not None:
        return Path(DATEN_DIR)
    from database.connection import APP_DATA_DIR
    return APP_DATA_DIR


def _datei_exklusiv_schreiben(pfad: Path, inhalt: bytes) -> None:
    """Legt die Datei nur für den eigenen Benutzer an (0600); existiert sie schon, bleibt sie."""
    pfad.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(pfad), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return
    try:
        os.write(fd, inhalt)
    finally:
        os.close(fd)


def profil_id(daten_dir: Path | None = None) -> str:
    pfad = (daten_dir or _daten_dir()) / _ID_DATEI
    if not pfad.exists():
        _datei_exklusiv_schreiben(pfad, uuid.uuid4().hex.encode("ascii"))
    return pfad.read_text(encoding="ascii").strip()


def _benutzer(feld: str, daten_dir: Path | None = None) -> str:
    if feld not in FELDER:
        raise ValueError(f"unbekanntes Geheimnis-Feld {feld!r}")
    return f"{profil_id(daten_dir)}:{feld}"


def _schluesselbund():
    """Liefert das keyring-Backend oder None, wenn keins taugt.

    Abgelehnt werden: fail/null-Backends (kein Schlüsselbund vorhanden) und alles aus
    keyrings.alt – dessen PlaintextKeyring legt Passwörter im Klartext unter ~/.local/share ab,
    das wäre kein Gewinn gegenüber vorher."""
    if os.environ.get("RECHNUNGSFEE_KEIN_SCHLUESSELBUND") == "1":
        return None
    try:
        import keyring
        from keyring.backends import fail
        kr = keyring.get_keyring()
    except Exception:
        return None
    if isinstance(kr, fail.Keyring):
        return None
    modul = type(kr).__module__
    if modul.startswith("keyrings.alt") or modul == "keyring.backends.null":
        return None
    # Chainer ohne echte Backends (Linux ohne D-Bus) wäre faktisch ein fail-Backend
    backends = getattr(kr, "backends", None)
    if backends is not None and not backends:
        return None
    return kr


def speicherort() -> str:
    """'schluesselbund' oder 'datei' – für Log und Hinweis in der Oberfläche."""
    return "schluesselbund" if _schluesselbund() is not None else "datei"


# ---------------------------------------------------------------------------
# Ersatzweg: AES-256-GCM mit Schlüsseldatei
# ---------------------------------------------------------------------------

def _datei_schluessel(daten_dir: Path | None = None) -> bytes:
    pfad = (daten_dir or _daten_dir()) / _SCHLUESSEL_DATEI
    if not pfad.exists():
        _datei_exklusiv_schreiben(pfad, secrets.token_bytes(32))
    schluessel = pfad.read_bytes()
    if len(schluessel) != 32:
        raise GeheimnisFehlt(f"{_SCHLUESSEL_DATEI} ist beschädigt")
    return schluessel


def _aad(feld: str, daten_dir: Path | None) -> bytes:
    # Bindet den Chiffretext an Feld und Profil – ein in eine andere Spalte kopierter Wert
    # lässt sich dort nicht entschlüsseln.
    return _benutzer(feld, daten_dir).encode("ascii")


def _datei_verschluesseln(feld: str, wert: str, daten_dir: Path | None) -> str:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = secrets.token_bytes(12)
    ct = AESGCM(_datei_schluessel(daten_dir)).encrypt(nonce, wert.encode("utf-8"), _aad(feld, daten_dir))
    return PRAEFIX_DATEI + base64.b64encode(nonce + ct).decode("ascii")


def _datei_entschluesseln(feld: str, marker: str, daten_dir: Path | None) -> str:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    try:
        roh = base64.b64decode(marker[len(PRAEFIX_DATEI):], validate=True)
        klartext = AESGCM(_datei_schluessel(daten_dir)).decrypt(roh[:12], roh[12:], _aad(feld, daten_dir))
    except (InvalidTag, ValueError) as e:
        raise GeheimnisFehlt("Passwort lässt sich nicht entschlüsseln") from e
    return klartext.decode("utf-8")


# ---------------------------------------------------------------------------
# Öffentliche Funktionen (auf Spaltenwerten)
# ---------------------------------------------------------------------------

def speichern(feld: str, wert: str, daten_dir: Path | None = None) -> str:
    """Legt das Passwort ab und gibt den Marker zurück, der in die Spalte gehört."""
    kr = _schluesselbund()
    if kr is not None:
        try:
            kr.set_password(DIENST, _benutzer(feld, daten_dir), wert)
            return MARKER_KEYRING
        except Exception as e:
            print(f"[Geheimnisse] Schlüsselbund nicht nutzbar ({type(e).__name__}), verschlüsselte Datei als Ersatz")
    return _datei_verschluesseln(feld, wert, daten_dir)


def lesen(feld: str, spaltenwert: str | None, daten_dir: Path | None = None) -> str | None:
    """Gibt das Passwort zum Spaltenwert zurück (None = nicht gesetzt)."""
    if not spaltenwert:
        return None
    if spaltenwert == MARKER_KEYRING:
        kr = _schluesselbund()
        wert = None
        if kr is not None:
            try:
                wert = kr.get_password(DIENST, _benutzer(feld, daten_dir))
            except Exception:
                wert = None
        if wert is None:
            raise GeheimnisFehlt("Passwort nicht im Schlüsselbund gefunden")
        return wert
    if spaltenwert.startswith(PRAEFIX_DATEI):
        return _datei_entschluesseln(feld, spaltenwert, daten_dir)
    # Alt-Klartext (vor F6) – wird beim Start migriert, hier nur noch für den Übergang
    return spaltenwert


def entfernen(feld: str, spaltenwert: str | None, daten_dir: Path | None = None) -> None:
    """Löscht den Schlüsselbund-Eintrag (falls vorhanden). Die Spalte setzt der Aufrufer auf NULL."""
    if spaltenwert != MARKER_KEYRING:
        return
    kr = _schluesselbund()
    if kr is None:
        return
    try:
        kr.delete_password(DIENST, _benutzer(feld, daten_dir))
    except Exception:
        pass  # schon weg – Ziel erreicht


def profil_entfernen(daten_dir: Path) -> None:
    """Löscht alle Schlüsselbund-Einträge eines Profils (beim endgültigen Löschen des Profils)."""
    if not (daten_dir / _ID_DATEI).exists():
        return
    for feld in FELDER:
        entfernen(feld, MARKER_KEYRING, daten_dir)


# ---------------------------------------------------------------------------
# Komfort auf dem ORM-Objekt
# ---------------------------------------------------------------------------

def passwort(unternehmen, feld: str) -> str | None:
    """Passwort aus einem Unternehmen-Objekt lesen."""
    return lesen(feld, getattr(unternehmen, feld, None))


def passwort_setzen(unternehmen, feld: str, wert: str | None) -> None:
    """Passwort setzen (None/"" = entfernen)."""
    alt = getattr(unternehmen, feld, None)
    if not wert:
        entfernen(feld, alt)
        setattr(unternehmen, feld, None)
        return
    setattr(unternehmen, feld, speichern(feld, wert))
