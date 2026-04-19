"""
API für Rechnungsvorlagen: Demo-PDF und Vorlagen-Liste.
"""
from decimal import Decimal
from datetime import date
from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Unternehmen
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1

router = APIRouter(prefix="/api/pdf-vorlagen", tags=["PDF-Vorlagen"])

# Registry aller verfügbaren Vorlagen
VORLAGEN = [
    {
        "id": 0,
        "name": "Standard",
        "beschreibung": "DIN 5008-Layout · Spalten: Beschreibung, Menge, Einheit, Netto, MwSt, Brutto · für alle Unternehmensformen",
    },
    {
        "id": 1,
        "name": "Sandra grün – Nur für Kleinunternehmer",
        "beschreibung": "Nur für Kleinunternehmer (§ 19 UStG) · Grünes Design · Spalten: Datum, Beschreibung, Saldo · Überweisungsblock mit IBAN",
    },
]


def _demo_rechnung(unt: dict) -> Any:
    """Erzeugt eine Muster-Rechnung mit Dummy-Daten für die Vorschau."""
    pos1 = SimpleNamespace(
        position_nr=1,
        beschreibung="Webdesign – Startseite", menge=Decimal("1"), einheit="Pauschal",
        netto=Decimal("800.00"), ust_satz=Decimal("0" if unt.get("ist_kleinunternehmer") else "19"),
        ust_betrag=Decimal("0" if unt.get("ist_kleinunternehmer") else "152.00"),
        brutto=Decimal("800.00" if unt.get("ist_kleinunternehmer") else "952.00"),
    )
    pos2 = SimpleNamespace(
        position_nr=2,
        beschreibung="Logo-Erstellung und CI-Konzept", menge=Decimal("1"), einheit="Pauschal",
        netto=Decimal("300.00"), ust_satz=Decimal("0" if unt.get("ist_kleinunternehmer") else "19"),
        ust_betrag=Decimal("0" if unt.get("ist_kleinunternehmer") else "57.00"),
        brutto=Decimal("300.00" if unt.get("ist_kleinunternehmer") else "357.00"),
    )
    pos3 = SimpleNamespace(
        position_nr=3,
        beschreibung="Technischer Support (3 Stunden)", menge=Decimal("3"), einheit="Std",
        netto=Decimal("180.00"), ust_satz=Decimal("0" if unt.get("ist_kleinunternehmer") else "19"),
        ust_betrag=Decimal("0" if unt.get("ist_kleinunternehmer") else "34.20"),
        brutto=Decimal("180.00" if unt.get("ist_kleinunternehmer") else "214.20"),
    )
    kunde = SimpleNamespace(
        firmenname="Musterfirma GmbH", vorname="Max", nachname="Mustermann",
        strasse="Musterstraße", hausnummer="12", plz="10115", ort="Berlin", land="DE",
    )
    brutto = Decimal("1280.00" if unt.get("ist_kleinunternehmer") else "1523.20")
    netto  = Decimal("1280.00")
    ust    = Decimal("0.00" if unt.get("ist_kleinunternehmer") else "243.20")
    return SimpleNamespace(
        typ="ausgang",
        rechnungsnummer="RE-2024-0042",
        datum=date(2024, 3, 15),
        leistungsdatum=date(2024, 3, 10),
        faellig_am=date(2024, 4, 14),
        netto_gesamt=netto,
        ust_gesamt=ust,
        brutto_gesamt=brutto,
        zahlungsstatus="offen",
        kassenbucheintraege=[],
        positionen=[pos1, pos2, pos3],
        kunde=kunde,
        lieferant=None,
        partner_freitext=None,
        notizen=None,
        ausgegeben=False,
        ist_entwurf=False,
        storniert=False,
    )


def _unt_dict(unternehmen: Unternehmen | None) -> dict:
    """Unternehmen-Objekt → dict für PDF-Generator."""
    if unternehmen is None:
        return {
            "firmenname": "Musterfirma", "vorname": "", "nachname": "",
            "strasse": "Musterstraße", "hausnummer": "1", "plz": "12345", "ort": "Musterstadt",
            "land": "DE", "steuernummer": "12/345/67890", "ust_idnr": "",
            "finanzamt": "", "handelsregister_nr": "", "handelsregister_gericht": "",
            "telefon": "+49 30 123456", "email": "info@musterfirma.de", "webseite": "www.musterfirma.de",
            "iban": "DE89 3704 0044 0532 0130 00", "bic": "COBADEFFXXX", "bank_name": "Musterbank",
            "logo_pfad": "", "berufsbezeichnung": "", "kammer_mitgliedschaft": "",
            "rechtsform": "Einzelunternehmen", "ist_kleinunternehmer": True,
            "zahlungshinweis_aktiv": True, "qr_zahlung_aktiv": True,
        }
    return {
        "firmenname":              unternehmen.firmenname or "",
        "vorname":                 unternehmen.vorname or "",
        "nachname":                unternehmen.nachname or "",
        "strasse":                 unternehmen.strasse or "",
        "hausnummer":              unternehmen.hausnummer or "",
        "plz":                     unternehmen.plz or "",
        "ort":                     unternehmen.ort or "",
        "land":                    unternehmen.land or "DE",
        "steuernummer":            unternehmen.steuernummer or "",
        "ust_idnr":                unternehmen.ust_idnr or "",
        "finanzamt":               unternehmen.finanzamt or "",
        "handelsregister_nr":      unternehmen.handelsregister_nr or "",
        "handelsregister_gericht": unternehmen.handelsregister_gericht or "",
        "telefon":                 unternehmen.telefon or "",
        "email":                   unternehmen.email or "",
        "webseite":                unternehmen.webseite or "",
        "iban":                    unternehmen.iban or "",
        "bic":                     unternehmen.bic or "",
        "bank_name":               unternehmen.bank_name or "",
        "logo_pfad":               unternehmen.logo_pfad or "",
        "berufsbezeichnung":       unternehmen.berufsbezeichnung or "",
        "kammer_mitgliedschaft":   unternehmen.kammer_mitgliedschaft or "",
        "rechtsform":              getattr(unternehmen, "rechtsform", "") or "",
        "ist_kleinunternehmer":    unternehmen.ist_kleinunternehmer or False,
        "zahlungshinweis_aktiv":   unternehmen.zahlungshinweis_aktiv,
        "qr_zahlung_aktiv":        unternehmen.qr_zahlung_aktiv or False,
        "unterschrift_bild":       unternehmen.unterschrift_bild or "",
        "unterschrift_auf_rechnung": unternehmen.unterschrift_auf_rechnung or False,
    }


@router.get("")
def list_vorlagen():
    """Liste aller verfügbaren Rechnungsvorlagen."""
    return VORLAGEN


@router.get("/demo")
def demo_pdf(vorlage: int = 0, db: Session = Depends(get_db)):
    """Demo-PDF einer Vorlage mit echten Stammdaten und Dummy-Rechnung."""
    unternehmen = db.query(Unternehmen).first()
    unt_dict = _unt_dict(unternehmen)
    rechnung = _demo_rechnung(unt_dict)

    if vorlage == 1:
        pdf_bytes = generate_rechnung_pdf_vorlage1(rechnung, unt_dict, ist_kopie=False)
    else:
        pdf_bytes = generate_rechnung_pdf(rechnung, unt_dict, ist_kopie=False)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="Vorschau_Vorlage_{vorlage}.pdf"'},
    )
