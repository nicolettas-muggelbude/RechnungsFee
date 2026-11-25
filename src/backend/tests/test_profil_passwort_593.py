"""
Issue #593: Profilauswahl beim Start und optionales Passwort je Profil (Zugangssperre, keine
Verschlüsselung). Endpunktfunktionen direkt aufgerufen wie in test_profile_api.py, die Sperre
in der SicherheitMiddleware wie in test_security_sitzungstoken.py.
"""
import asyncio
import json
import time

import pytest
from fastapi import HTTPException

import api.profile as profile_modul
from api.profile import (
    ProfilAnmeldenRequest, ProfilCreateRequest, ProfilPasswortRequest, StartEinstellungen,
    aktiviere_profil, create_profil, get_profil_start, get_profile, melde_an,
    setze_profil_passwort, setze_start_einstellungen,
)
from utils import profil_zugang
from utils.sicherheit_middleware import SicherheitMiddleware


@pytest.fixture(autouse=True)
def isoliert(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_modul, "BASE_DIR", tmp_path)
    monkeypatch.setattr(profile_modul, "_PROFILE_ROOT", tmp_path / "profile")
    monkeypatch.setattr(profile_modul, "_ZEIGER_PFAD", tmp_path / "profile.json")
    monkeypatch.setattr(profile_modul, "_FEHLER_PAUSE_S", 0)
    monkeypatch.setattr(profil_zugang, "_auswahl_erledigt", False)


def _ordner(tmp_path, name):
    return tmp_path / "profile" / name


def _starte_prozess(tmp_path, name):
    """Simuliert den Programmstart mit diesem Profil."""
    profil_zugang.initialisiere(_ordner(tmp_path, name))


# ── Passwort-Hash ─────────────────────────────────────────────────────────────

def test_hash_statt_klartext(tmp_path):
    profil_zugang.setze_passwort(tmp_path, "geheim123")
    inhalt = (tmp_path / "zugang.json").read_text(encoding="utf-8")
    assert "geheim123" not in inhalt
    assert json.loads(inhalt)["verfahren"] == "scrypt"
    assert profil_zugang.pruefe_passwort(tmp_path, "geheim123")
    assert not profil_zugang.pruefe_passwort(tmp_path, "geheim124")
    assert not profil_zugang.pruefe_passwort(tmp_path, None)


def test_ohne_passwort_immer_offen(tmp_path):
    assert profil_zugang.pruefe_passwort(tmp_path, None)
    assert profil_zugang.pruefe_passwort(tmp_path, "egal")


def test_beschaedigte_datei_entsperrt_nie(tmp_path):
    (tmp_path / "zugang.json").write_text("{kaputt", encoding="utf-8")
    assert not profil_zugang.pruefe_passwort(tmp_path, "x")


def test_zu_kurz(tmp_path):
    with pytest.raises(ValueError):
        profil_zugang.setze_passwort(tmp_path, "abc")


# ── Anlegen, Setzen, Ändern, Entfernen ────────────────────────────────────────

def test_profil_ohne_passwort_wie_bisher(tmp_path):
    create_profil(ProfilCreateRequest(name="Ohne"))
    assert not (_ordner(tmp_path, "Ohne") / "zugang.json").exists()
    assert get_profile().profile[0].passwort is False


def test_profil_mit_passwort_anlegen(tmp_path):
    create_profil(ProfilCreateRequest(name="Mit", passwort="geheim1"))
    assert get_profile().profile[0].passwort is True
    # gerade angelegt: nach dem Neustart weder Passwort noch Startauswahl
    _starte_prozess(tmp_path, "Mit")
    assert not profil_zugang.gesperrt()
    assert profil_zugang.auswahl_erledigt()


def test_anlegen_mit_zu_kurzem_passwort_legt_nichts_an(tmp_path):
    with pytest.raises(HTTPException) as exc:
        create_profil(ProfilCreateRequest(name="Kurz", passwort="ab"))
    assert exc.value.status_code == 422
    assert not _ordner(tmp_path, "Kurz").exists()


def test_passwort_aendern_und_entfernen_braucht_das_alte(tmp_path):
    create_profil(ProfilCreateRequest(name="A"))
    setze_profil_passwort("A", ProfilPasswortRequest(neues_passwort="erstes1"))
    ordner = _ordner(tmp_path, "A")

    with pytest.raises(HTTPException) as exc:
        setze_profil_passwort("A", ProfilPasswortRequest(neues_passwort="zweites2"))
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException):
        setze_profil_passwort("A", ProfilPasswortRequest(altes_passwort="falsch", neues_passwort=None))

    setze_profil_passwort("A", ProfilPasswortRequest(altes_passwort="erstes1", neues_passwort="zweites2"))
    assert profil_zugang.pruefe_passwort(ordner, "zweites2")

    liste = setze_profil_passwort("A", ProfilPasswortRequest(altes_passwort="zweites2"))
    assert liste.profile[0].passwort is False
    assert not (ordner / "zugang.json").exists()


# ── Programmstart, Sperre, Anmeldung ──────────────────────────────────────────

def test_start_mit_passwort_ist_gesperrt_bis_anmeldung(tmp_path):
    create_profil(ProfilCreateRequest(name="A", passwort="geheim1"))
    (_ordner(tmp_path, "A") / profil_zugang.FREIGABE_DATEI).unlink()
    _starte_prozess(tmp_path, "A")
    start = get_profil_start()
    assert start.gesperrt is True

    with pytest.raises(HTTPException) as exc:
        melde_an("A", ProfilAnmeldenRequest(passwort="falsch"))
    assert exc.value.status_code == 403
    assert profil_zugang.gesperrt()

    ergebnis = melde_an("A", ProfilAnmeldenRequest(passwort="geheim1"))
    assert ergebnis.neustart_erforderlich is False
    assert not profil_zugang.gesperrt()
    assert get_profil_start().auswahl_anzeigen is False


def test_startauswahl_nur_mit_schalter(tmp_path):
    create_profil(ProfilCreateRequest(name="A"))
    (_ordner(tmp_path, "A") / profil_zugang.FREIGABE_DATEI).unlink()
    _starte_prozess(tmp_path, "A")
    assert get_profil_start().auswahl_anzeigen is False

    liste = setze_start_einstellungen(StartEinstellungen(auswahl_beim_start=True))
    assert liste.auswahl_beim_start is True
    _starte_prozess(tmp_path, "A")
    start = get_profil_start()
    assert start.auswahl_anzeigen is True and start.gesperrt is False

    melde_an("A", ProfilAnmeldenRequest())
    assert get_profil_start().auswahl_anzeigen is False


def test_schalter_bleibt_beim_profilwechsel_erhalten(tmp_path):
    create_profil(ProfilCreateRequest(name="A"))
    create_profil(ProfilCreateRequest(name="B"))
    setze_start_einstellungen(StartEinstellungen(auswahl_beim_start=True))
    aktiviere_profil("A")
    zeiger = json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))
    assert zeiger == {"active": "A", "auswahl_beim_start": True}


def test_anmelden_an_anderem_profil_mit_freigabeschein(tmp_path):
    create_profil(ProfilCreateRequest(name="B", passwort="bbbb1"))
    create_profil(ProfilCreateRequest(name="A"))
    for n in ("A", "B"):
        (_ordner(tmp_path, n) / profil_zugang.FREIGABE_DATEI).unlink()
    setze_start_einstellungen(StartEinstellungen(auswahl_beim_start=True))
    _starte_prozess(tmp_path, "A")

    with pytest.raises(HTTPException):
        melde_an("B", ProfilAnmeldenRequest(passwort="falsch"))
    assert json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))["active"] == "A"

    ergebnis = melde_an("B", ProfilAnmeldenRequest(passwort="bbbb1"))
    assert ergebnis.neustart_erforderlich is True
    assert json.loads((tmp_path / "profile.json").read_text(encoding="utf-8"))["active"] == "B"

    # Neustart mit B: kein zweites Mal fragen, keine Startauswahl
    _starte_prozess(tmp_path, "B")
    assert not profil_zugang.gesperrt()
    assert get_profil_start().auswahl_anzeigen is False
    assert not (_ordner(tmp_path, "B") / profil_zugang.FREIGABE_DATEI).exists()

    # nächster normaler Start: wieder gesperrt
    _starte_prozess(tmp_path, "B")
    assert profil_zugang.gesperrt()


def test_abgelaufener_freigabeschein_zaehlt_nicht(tmp_path):
    create_profil(ProfilCreateRequest(name="A", passwort="geheim1"))
    (_ordner(tmp_path, "A") / profil_zugang.FREIGABE_DATEI).write_text(
        json.dumps({"bis": time.time() - 1}), encoding="utf-8")
    _starte_prozess(tmp_path, "A")
    assert profil_zugang.gesperrt()


def test_wechsel_ueber_sidebar_prueft_passwort_des_ziels(tmp_path):
    create_profil(ProfilCreateRequest(name="B", passwort="bbbb1"))
    create_profil(ProfilCreateRequest(name="A"))
    with pytest.raises(HTTPException) as exc:
        aktiviere_profil("B")
    assert exc.value.status_code == 403
    aktiviere_profil("B", ProfilAnmeldenRequest(passwort="bbbb1"))
    _starte_prozess(tmp_path, "B")
    assert not profil_zugang.gesperrt()


# ── Sperre in der Middleware ──────────────────────────────────────────────────

def _status(method, path):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": b"{}"})

    scope = {"type": "http", "method": method, "path": path,
             "headers": [(b"host", b"127.0.0.1:8002")], "query_string": b""}
    nachrichten = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        nachrichten.append(msg)

    asyncio.run(SicherheitMiddleware(app)(scope, receive, send))
    return nachrichten[0]["status"]


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/unternehmen"),
    ("GET", "/api/rechnungen/1/pdf"),
    ("GET", "/api/setup/status"),
    ("GET", "/api/profile"),
    ("POST", "/api/profile/A/passwort"),
    ("POST", "/api/profile/A/aktivieren"),
    ("POST", "/api/postfach/abrufen"),
])
def test_gesperrt_weist_ab(monkeypatch, method, path):
    monkeypatch.setattr(profil_zugang, "_entsperrt", False)
    assert _status(method, path) == 423


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/profile/start"),
    ("POST", "/api/profile/Mein Profil/anmelden"),
    ("POST", "/api/backup/erstellen"),
    ("POST", "/api/shutdown"),
    ("OPTIONS", "/api/unternehmen"),
])
def test_gesperrt_laesst_anmeldung_durch(monkeypatch, method, path):
    monkeypatch.setattr(profil_zugang, "_entsperrt", False)
    assert _status(method, path) == 200


def test_entsperrt_laesst_alles_durch():
    assert _status("GET", "/api/unternehmen") == 200
