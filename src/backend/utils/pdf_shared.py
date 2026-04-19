"""
Gemeinsame Hilfsfunktionen für alle Rechnungs-PDF-Vorlagen.
Neue Vorlagen importieren von hier – nie direkt im Template implementieren.
"""

import base64
from io import BytesIO
from typing import Optional


def embed_unterschrift(pdf, unt: dict, x: float, w: float = 50, h: float = 18) -> None:
    """Digitale Unterschrift ins PDF einbetten, falls hinterlegt und aktiviert.

    Aufruf am Ende von render(), nach Notizen:
        embed_unterschrift(self, unt, L_MARGIN)
    """
    b64 = unt.get("unterschrift_bild") or ""
    if not b64 or not unt.get("unterschrift_auf_rechnung"):
        return
    try:
        raw = b64.split(",", 1)[-1]
        img_bytes = base64.b64decode(raw)
        pdf.ln(6)
        pdf.image(BytesIO(img_bytes), x=x, y=pdf.get_y(), w=w, h=h)
        pdf.ln(h + 2)
    except Exception:
        pass


def epc_qr_bytes(
    iban: str,
    bic: str,
    empfaenger: str,
    betrag_euro: float,
    verwendungszweck: str,
) -> Optional[bytes]:
    """EPC-QR-Code (GiroCode) als PNG-Bytes erzeugen.

    Folgt dem European Payments Council EPC069-12 Standard v2.
    Wird von allen deutschen Banking-Apps gescannt.
    Gibt None zurück wenn qrcode nicht verfügbar oder Daten unvollständig.
    """
    if not iban or not empfaenger:
        return None
    try:
        import segno

        content = "\n".join([
            "BCD",
            "002",
            "2",
            "SCT",
            (bic or "")[:11],
            empfaenger[:70],
            iban.replace(" ", "")[:34],
            f"EUR{betrag_euro:.2f}",
            "",
            "",
            (verwendungszweck or "")[:140],
        ])
        qr = segno.make(content, error="m")
        buf = BytesIO()
        qr.save(buf, kind="png", scale=10, border=1)
        return buf.getvalue()
    except Exception:
        return None


def build_hr_zeile(unt: dict) -> str:
    """Handelsregistereintrag für die Fußzeile.

    Der gespeicherte Wert enthält bereits die Abteilung (z.B. 'HRA 12345'
    oder 'HRB 215517') – kein Präfix hinzufügen.
    """
    nr  = unt.get("handelsregister_nr") or ""
    ger = unt.get("handelsregister_gericht") or ""
    if not nr:
        return ""
    return nr + (f", {ger}" if ger else "")
