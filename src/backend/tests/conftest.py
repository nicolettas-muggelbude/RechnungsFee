import sys
from pathlib import Path

# Backend-Verzeichnis zum Suchpfad hinzufügen, damit alle Module importierbar sind
sys.path.insert(0, str(Path(__file__).parent.parent))

import keyring
import pytest
from keyring.backend import KeyringBackend


class SpeicherSchluesselbund(KeyringBackend):
    """Schlüsselbund im Speicher – Tests dürfen nie den echten des Rechners anfassen (F6)."""
    priority = 1

    def __init__(self):
        super().__init__()
        self.eintraege: dict[tuple[str, str], str] = {}

    def get_password(self, service, username):
        return self.eintraege.get((service, username))

    def set_password(self, service, username, password):
        self.eintraege[(service, username)] = password

    def delete_password(self, service, username):
        from keyring.errors import PasswordDeleteError
        if self.eintraege.pop((service, username), None) is None:
            raise PasswordDeleteError("nicht vorhanden")


@pytest.fixture(autouse=True)
def schluesselbund(tmp_path_factory, monkeypatch):
    from utils import geheimnisse
    vorher = keyring.get_keyring()
    kr = SpeicherSchluesselbund()
    keyring.set_keyring(kr)
    monkeypatch.setattr(geheimnisse, "DATEN_DIR", tmp_path_factory.mktemp("profil"))
    monkeypatch.delenv("RECHNUNGSFEE_KEIN_SCHLUESSELBUND", raising=False)
    yield kr
    keyring.set_keyring(vorher)
