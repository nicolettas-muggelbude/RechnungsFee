"""
Tests für die Profilmanager-API (api/profile.py) - Anlegen/Auflisten/Aktivieren von
Profilen. Rein dateisystembasiert (kein Depends(get_db)), Endpunktfunktionen werden
direkt aufgerufen - Stil wie der Rest der Testsuite (siehe z.B. test_gutschrift_*.py),
kein TestClient nötig und vermeidet, main.py's App-Startup-Flow (Migrationen etc. gegen
die echte lokale DB) versehentlich mit auszulösen.
"""
import pytest
from fastapi import HTTPException

import api.profile as profile_modul
from api.profile import ProfilCreateRequest, aktiviere_profil, create_profil, get_profile


@pytest.fixture(autouse=True)
def isoliertes_profilverzeichnis(tmp_path, monkeypatch):
    monkeypatch.setattr(profile_modul, "BASE_DIR", tmp_path)
    monkeypatch.setattr(profile_modul, "_PROFILE_ROOT", tmp_path / "profile")
    monkeypatch.setattr(profile_modul, "_ZEIGER_PFAD", tmp_path / "profile.json")


def test_liste_ohne_profile_ist_leer():
    resp = get_profile()
    assert resp.profile == []


def test_profil_anlegen_und_auflisten(tmp_path):
    ergebnis = create_profil(ProfilCreateRequest(name="Gewerbe"))

    assert ergebnis.neustart_erforderlich is True
    assert (tmp_path / "profile" / "Gewerbe").is_dir()
    assert (tmp_path / "profile.json").read_text(encoding="utf-8") == '{"active": "Gewerbe"}'

    liste = get_profile()
    assert [(p.name, p.aktiv) for p in liste.profile] == [("Gewerbe", True)]


def test_profil_anlegen_lehnt_duplikat_ab():
    create_profil(ProfilCreateRequest(name="Gewerbe"))
    with pytest.raises(HTTPException) as exc:
        create_profil(ProfilCreateRequest(name="Gewerbe"))
    assert exc.value.status_code == 409


@pytest.mark.parametrize("ungueltig", ["", "../etc", "a/b", "a\\b", "a" * 51])
def test_profil_anlegen_lehnt_ungueltige_namen_ab(ungueltig):
    with pytest.raises(HTTPException) as exc:
        create_profil(ProfilCreateRequest(name=ungueltig))
    assert exc.value.status_code == 422


def test_profil_aktivieren(tmp_path):
    create_profil(ProfilCreateRequest(name="Freiberuflich"))
    create_profil(ProfilCreateRequest(name="Gewerbe"))

    ergebnis = aktiviere_profil("Freiberuflich")

    assert ergebnis.neustart_erforderlich is True
    assert (tmp_path / "profile.json").read_text(encoding="utf-8") == '{"active": "Freiberuflich"}'

    liste = get_profile()
    aktiv = {p.name: p.aktiv for p in liste.profile}
    assert aktiv == {"Freiberuflich": True, "Gewerbe": False}


def test_profil_aktivieren_nicht_existent_gibt_404():
    with pytest.raises(HTTPException) as exc:
        aktiviere_profil("Nichtvorhanden")
    assert exc.value.status_code == 404
