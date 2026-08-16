"""
Regressionstest für Issue #348 (macOS-Datenpfad).

Bug: database/connection.py unterschied nur Windows vs. "alles andere" - der else-Zweig
nutzte fälschlich die Linux-XDG-Konvention (~/.local/share/RechnungsFee) auch unter
macOS, statt ~/Library/Application Support/RechnungsFee. Bestehende macOS-Installationen
mit Daten im alten Pfad werden beim ersten Start nach dem Fix einmalig automatisch
migriert (Ordner verschoben), damit sie ihre Datenbank nicht scheinbar verlieren.
"""
from pathlib import Path

from database.connection import _resolve_app_data_dir


def test_windows_nutzt_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    ergebnis = _resolve_app_data_dir("Windows", tmp_path)
    assert ergebnis == tmp_path / "Roaming" / "RechnungsFee"


def test_linux_nutzt_xdg_share(tmp_path):
    ergebnis = _resolve_app_data_dir("Linux", tmp_path)
    assert ergebnis == tmp_path / ".local" / "share" / "RechnungsFee"


def test_macos_ohne_bestehende_daten_nutzt_application_support(tmp_path):
    ergebnis = _resolve_app_data_dir("Darwin", tmp_path)
    assert ergebnis == tmp_path / "Library" / "Application Support" / "RechnungsFee"
    # Keine alten Daten vorhanden -> nichts zu verschieben, Zielordner selbst wird von
    # dieser Funktion bewusst NICHT angelegt (das macht der Aufrufer via mkdir).
    assert not ergebnis.exists()


def test_macos_migriert_bestehende_daten_aus_altem_linux_pfad(tmp_path):
    alter_pfad = tmp_path / ".local" / "share" / "RechnungsFee"
    alter_pfad.mkdir(parents=True)
    (alter_pfad / "rechnungsfee.db").write_bytes(b"echte-datenbank-bytes")
    (alter_pfad / "uploads").mkdir()
    (alter_pfad / "uploads" / "beleg.pdf").write_bytes(b"pdf-inhalt")

    ergebnis = _resolve_app_data_dir("Darwin", tmp_path)

    assert ergebnis == tmp_path / "Library" / "Application Support" / "RechnungsFee"
    assert (ergebnis / "rechnungsfee.db").read_bytes() == b"echte-datenbank-bytes"
    assert (ergebnis / "uploads" / "beleg.pdf").read_bytes() == b"pdf-inhalt"
    assert not alter_pfad.exists()


def test_macos_ueberschreibt_bereits_migrierten_ordner_nicht(tmp_path):
    alter_pfad = tmp_path / ".local" / "share" / "RechnungsFee"
    alter_pfad.mkdir(parents=True)
    (alter_pfad / "rechnungsfee.db").write_bytes(b"alte-db")

    neuer_pfad = tmp_path / "Library" / "Application Support" / "RechnungsFee"
    neuer_pfad.mkdir(parents=True)
    (neuer_pfad / "rechnungsfee.db").write_bytes(b"bereits-migrierte-db")

    ergebnis = _resolve_app_data_dir("Darwin", tmp_path)

    assert ergebnis == neuer_pfad
    assert (neuer_pfad / "rechnungsfee.db").read_bytes() == b"bereits-migrierte-db"
    # Alter Ordner bleibt unangetastet, da am Ziel schon eine DB liegt
    assert (alter_pfad / "rechnungsfee.db").read_bytes() == b"alte-db"
