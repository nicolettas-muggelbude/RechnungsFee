"""
Issue #604: Empfängername für Überweisungen (EPC-QR-Code, E-Rechnung BT-85).

Seit Oktober 2025 prüfen Banken vor einer Überweisung, ob der Empfängername zum Kontoinhaber
passt (Empfängerüberprüfung / Verification of Payee). Ein Einzelunternehmer mit Firmenname,
dessen Konto auf seinen eigenen Namen läuft, bekam im QR-Code bisher immer den Firmennamen –
die Bank des Kunden meldete dann eine Abweichung.

Der Kontoinhaber wird am Konto gepflegt (Einstellungen → Konten, Spalte konten.kontoinhaber).
Für Rechnungen gilt das Konto mit der Rechnungs-IBAN aus den Stammdaten. Leer = bisheriges
Verhalten: Firmenname, sonst Vor- und Nachname.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session


def _iban_norm(iban: Optional[str]) -> str:
    return (iban or "").replace(" ", "").upper()


def kontoinhaber_fuer_iban(db: Session, iban: Optional[str]) -> str:
    """Gepflegter Kontoinhaber des Kontos mit dieser IBAN, sonst "" (= Standard)."""
    from database.models import Konto

    ziel = _iban_norm(iban)
    if not ziel:
        return ""
    for konto in db.query(Konto).filter(Konto.iban.isnot(None)).all():
        if _iban_norm(konto.iban) == ziel and (konto.kontoinhaber or "").strip():
            return konto.kontoinhaber.strip()
    return ""


def kontoinhaber_von(unternehmen) -> str:
    """Kontoinhaber zur Rechnungs-IBAN eines Unternehmen-ORM-Objekts (Session über das Objekt)."""
    from sqlalchemy.orm import object_session

    if unternehmen is None:
        return ""
    db = object_session(unternehmen)
    return kontoinhaber_fuer_iban(db, unternehmen.iban) if db is not None else ""


def standard_empfaenger(unt: dict) -> str:
    """Bisheriger Empfängername: Firmenname, sonst Vor- und Nachname."""
    return (unt.get("firmenname") or "").strip() or " ".join(
        p for p in [unt.get("vorname"), unt.get("nachname")] if p
    )


def zahlungsempfaenger(unt: dict) -> str:
    """Empfänger im QR-Code. Snapshots ohne Schlüssel (vor #604 finalisiert) behalten den alten Namen."""
    return (unt.get("kontoinhaber") or "").strip() or standard_empfaenger(unt)


def abweichender_kontoinhaber(unt: dict) -> str:
    """Kontoinhaber für die Bankverbindung im PDF – nur wenn gepflegt und vom Firmennamen verschieden."""
    inhaber = (unt.get("kontoinhaber") or "").strip()
    return inhaber if inhaber and inhaber != (unt.get("firmenname") or "").strip() else ""
