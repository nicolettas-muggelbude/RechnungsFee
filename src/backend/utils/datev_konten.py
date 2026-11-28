"""
DATEV-Finanzkonten für eigene Konten (Bank, PayPal und andere Zahlungsdienstleister).

Jedes Konto unter Einstellungen → Konten bekommt beim Anlegen die nächste freie Nummer aus dem
Bankbereich des Kontenrahmens („Bank“, „Bank 1“ … „Bank 5“ laut DATEV-Kontenrahmen 2026). So
landet jedes Konto im DATEV-Export auf einem eigenen Finanzkonto, auch ohne Vorwissen. Das
Steuerbüro kann eine andere Nummer vorgeben, dann wird sie am Konto eingetragen.
"""
from typing import Optional

from sqlalchemy.orm import Session

from database.models import Konto, Unternehmen
from database.seed import GELDTRANSIT_KONTEN

FINANZKONTEN: dict[str, list[str]] = {
    "SKR03": ["1200", "1210", "1220", "1230", "1240", "1250"],
    "SKR04": ["1800", "1810", "1820", "1830", "1840", "1850"],
}


def kontenrahmen(db: Session) -> str:
    unt = db.query(Unternehmen).first()
    rahmen = (unt.kontenrahmen if unt else None) or "SKR03"
    return "SKR03" if rahmen == "SKR03" else "SKR04"  # SKR49 nutzt wie im Export die SKR04-Nummern


def _rahmen(rahmen: Optional[str]) -> str:
    return "SKR03" if (rahmen or "SKR03") == "SKR03" else "SKR04"


def finanzkonten_umstellen(db: Session, alt: Optional[str], neu: Optional[str]) -> int:
    """Kontenrahmen gewechselt: Kontonummern aus dem Bankbereich des alten Rahmens auf dieselbe
    Position im neuen Rahmen umstellen (SKR03 1200 → SKR04 1800, 1210 → 1810 …). Sonst bliebe z. B.
    1200 stehen - in SKR04 „Forderungen aus Lieferungen und Leistungen“. Eigene Nummern außerhalb
    des Bankbereichs bleiben unverändert. Ist die Zielnummer schon von einem anderen Konto belegt,
    bekommt das Konto die nächste freie. Gibt die Zahl der umgestellten Konten zurück."""
    von, nach = _rahmen(alt), _rahmen(neu)
    if von == nach:
        return 0
    konten = db.query(Konto).all()
    umzustellen = [k for k in konten if (k.datev_kontonummer or "").strip() in FINANZKONTEN[von]]
    bleibt = {(k.datev_kontonummer or "").strip() for k in konten if k not in umzustellen} - {""}
    vergeben: set[str] = set()
    for k in sorted(umzustellen, key=lambda k: FINANZKONTEN[von].index(k.datev_kontonummer.strip())):
        ziel = FINANZKONTEN[nach][FINANZKONTEN[von].index(k.datev_kontonummer.strip())]
        if ziel in bleibt or ziel in vergeben:
            ziel = next((n for n in FINANZKONTEN[nach] if n not in bleibt and n not in vergeben), None)
        k.datev_kontonummer = ziel
        if ziel:
            vergeben.add(ziel)
    return len(umzustellen)


def geldtransit_konto(rahmen: str) -> str:
    return GELDTRANSIT_KONTEN["SKR03" if rahmen == "SKR03" else "SKR04"]


def naechste_freie_kontonummer(db: Session, kontoart: str = "bank",
                               ausser_konto_id: Optional[int] = None) -> Optional[str]:
    """Vorschlag für die DATEV-Nummer eines Kontos.

    1. Hat das Steuerbüro global eine Nummer für diese Art eingetragen (datev_konto_bank bzw.
       datev_konto_paypal) und nutzt sie noch kein anderes Konto, gehört sie zu diesem Konto -
       so buchen Journal und Bank-Import auf dieselbe Nummer.
    2. Sonst die erste freie Nummer aus dem Bankbereich. Belegt sind die Nummern aller Konten
       (auch inaktiver), die global eingetragenen Nummern und Geldtransit.
    None, wenn alle Nummern vergeben sind."""
    rahmen = kontenrahmen(db)
    unt = db.query(Unternehmen).first()
    q = db.query(Konto.datev_kontonummer).filter(Konto.datev_kontonummer.isnot(None))
    if ausser_konto_id is not None:
        q = q.filter(Konto.id != ausser_konto_id)
    an_konten = {(n or "").strip() for (n,) in q.all()} - {""}

    eigene_globale = (unt.datev_konto_paypal if kontoart == "zahlungsdienstleister" else unt.datev_konto_bank) if unt else None
    if eigene_globale and eigene_globale.strip() not in an_konten:
        return eigene_globale.strip()

    belegt = set(an_konten) | {geldtransit_konto(rahmen)}
    if unt:
        belegt |= {(n or "").strip() for n in (unt.datev_konto_bank, unt.datev_konto_karte,
                                                 unt.datev_konto_paypal, unt.datev_konto_bar)} - {""}
    return next((n for n in FINANZKONTEN[rahmen] if n not in belegt), None)
