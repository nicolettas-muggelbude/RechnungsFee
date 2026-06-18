"""
Mail-Versand via SMTP – Rechnungen, Angebote, Proforma, Aufträge.
"""
import ssl
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr
from typing import Optional

import markdown as md
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db, APP_DATA_DIR
from database.models import Unternehmen, Rechnung, DokumentenPaket, KundeLieferadresse
from utils.pdf_rechnung import generate_rechnung_pdf
from utils.pdf_rechnung_vorlage1 import generate_rechnung_pdf_vorlage1
from utils.zugferd import generate_zugferd_pdf
from utils.pdf_kopie import speichere_original_pdf, lade_original_mit_kopie_stempel

router = APIRouter(prefix="/api/mail", tags=["Mail"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MailSendenRequest(BaseModel):
    an: str
    cc: Optional[str] = None
    betreff: str
    text: str
    rechnung_id: Optional[int] = None
    dokumentenpaket_id: Optional[int] = None


class TestMailRequest(BaseModel):
    an: str


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _smtp_einstellungen(db: Session) -> Unternehmen:
    u = db.query(Unternehmen).first()
    if not u or not u.smtp_aktiv:
        raise HTTPException(400, "SMTP nicht aktiviert")
    if not u.smtp_host or not u.smtp_user or not u.smtp_passwort:
        raise HTTPException(400, "SMTP-Einstellungen unvollständig (Host, Benutzer und Passwort erforderlich)")
    return u


def _pdf_bytes_fuer(rechnung_id: int, db: Session) -> tuple[bytes, str]:
    """Gibt (pdf_bytes, dateiname) zurück."""
    r = db.query(Rechnung).filter(Rechnung.id == rechnung_id).first()
    if not r:
        raise HTTPException(404, "Dokument nicht gefunden")

    u = db.query(Unternehmen).first()
    unt_dict = {c.name: getattr(u, c.name) for c in u.__table__.columns} if u else {}

    if r.lieferadresse_id:
        r._lieferadresse = db.query(KundeLieferadresse).filter(
            KundeLieferadresse.id == r.lieferadresse_id
        ).first()

    _dok = getattr(r, "dokument_typ", "Rechnung") or "Rechnung"
    if _dok == "Auftrag":
        angebot = db.query(Rechnung).filter(
            Rechnung.auftrag_zu_angebot_id == rechnung_id,
            Rechnung.dokument_typ == "Angebot",
        ).first()
        r._quell_angebot_nr = angebot.rechnungsnummer if angebot else None

    ist_netto = r.typ == "ausgang" and r.kunde is not None and r.kunde.zugferd_aktiv
    kunde_zugferd = (
        not r.ist_entwurf and ist_netto and _dok == "Rechnung"
        and u and (u.steuernummer or u.ust_idnr)
    )

    _ist_storno_mail = getattr(r, "storniert", False) and _dok == "Rechnung"
    # Dokumente ohne Original-Archivierung (Auftrag/Angebot/Proforma/Storno: beliebig oft sendbar)
    _kein_archiv = _dok in ("Auftrag", "Angebot", "Proforma") or _ist_storno_mail
    ist_gutschrift = _dok == "Gutschrift"
    gutschrift_erstattet = ist_gutschrift and str(getattr(r, "zahlungsstatus", "offen")) == "bezahlt"
    darf_archiviert = (
        not r.ist_entwurf
        and not _kein_archiv
        and (not ist_gutschrift or gutschrift_erstattet)
    )

    # Kopie: gespeichertes Original laden + Wasserzeichen
    if darf_archiviert and r.original_pdf_pfad:
        kopie_bytes = lade_original_mit_kopie_stempel(APP_DATA_DIR, r.original_pdf_pfad)
        if kopie_bytes:
            nr = (r.rechnungsnummer or str(r.id)).replace("/", "-").replace(" ", "_")
            return kopie_bytes, f"{_dok}_{nr}_Kopie.pdf"

    if kunde_zugferd:
        try:
            pdf_bytes = generate_zugferd_pdf(r, unt_dict)
        except Exception:
            pdf_bytes = generate_rechnung_pdf(r, unt_dict, ist_entwurf=r.ist_entwurf, ist_netto=ist_netto)
    elif u and u.pdf_vorlage == 1:
        pdf_bytes = generate_rechnung_pdf_vorlage1(r, unt_dict, ist_entwurf=r.ist_entwurf, ist_netto=ist_netto)
    else:
        pdf_bytes = generate_rechnung_pdf(r, unt_dict, ist_entwurf=r.ist_entwurf, ist_netto=ist_netto)

    # Original speichern (erste echte Mail)
    if darf_archiviert and not r.original_pdf_pfad:
        rel_pfad = speichere_original_pdf(APP_DATA_DIR, r.id, pdf_bytes)
        r.original_pdf_pfad = rel_pfad
        r.ausgegeben = True
        r.ausgegeben_am = datetime.now()
        db.commit()

    nr = (r.rechnungsnummer or str(r.id)).replace("/", "-").replace(" ", "_")
    prefix = "Stornorechnung" if _ist_storno_mail else _dok
    return pdf_bytes, f"{prefix}_{nr}.pdf"


def _build_message(
    u: Unternehmen,
    an: str,
    cc: Optional[str],
    betreff: str,
    text: str,
    attachments: list[tuple[bytes, str]],
) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    von_adresse = u.smtp_von_adresse or u.smtp_user or ""
    msg["From"] = formataddr((u.firmenname or "", von_adresse))
    msg["To"] = an
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = betreff

    signatur_md = (u.mail_signatur or "").strip()

    # Plain-Text-Teil
    plain = text
    if signatur_md:
        plain += f"\n\n--\n{signatur_md}"

    # HTML-Teil: Text-Body + Markdown-Signatur
    html_body = "<br>\n".join(text.replace("\r\n", "\n").split("\n"))
    sig_html = md.markdown(signatur_md) if signatur_md else ""
    html = (
        "<!DOCTYPE html><html><body "
        'style="font-family:Arial,sans-serif;font-size:14px;color:#333;max-width:700px">'
        f"<p>{html_body}</p>"
    )
    if sig_html:
        html += (
            '<hr style="border:none;border-top:1px solid #ddd;margin:16px 0">'
            f'<div style="font-size:13px;color:#555">{sig_html}</div>'
        )
    html += "</body></html>"

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    for content, filename in attachments:
        part = MIMEApplication(content, Name=filename)
        part["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(part)

    return msg


def _sende(u: Unternehmen, msg: MIMEMultipart, empfaenger: list[str]) -> None:
    port = u.smtp_port or 587
    ctx = ssl.create_default_context()
    try:
        if u.smtp_ssl:
            with smtplib.SMTP_SSL(u.smtp_host, port, context=ctx, timeout=15) as srv:
                srv.login(u.smtp_user, u.smtp_passwort)
                srv.sendmail(msg["From"], empfaenger, msg.as_string())
        else:
            with smtplib.SMTP(u.smtp_host, port, timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ctx)
                srv.ehlo()
                srv.login(u.smtp_user, u.smtp_passwort)
                srv.sendmail(msg["From"], empfaenger, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(400, "SMTP-Authentifizierung fehlgeschlagen – Benutzer oder Passwort prüfen")
    except smtplib.SMTPConnectError:
        raise HTTPException(400, f"Verbindung zu {u.smtp_host}:{port} fehlgeschlagen")
    except smtplib.SMTPException as e:
        raise HTTPException(400, f"SMTP-Fehler: {e}")
    except OSError as e:
        raise HTTPException(400, f"Netzwerkfehler: {e}")


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.post("/senden")
def mail_senden(req: MailSendenRequest, db: Session = Depends(get_db)):
    u = _smtp_einstellungen(db)

    attachments: list[tuple[bytes, str]] = []

    if req.rechnung_id:
        pdf_bytes, dateiname = _pdf_bytes_fuer(req.rechnung_id, db)
        attachments.append((pdf_bytes, dateiname))

    if req.dokumentenpaket_id:
        paket = db.query(DokumentenPaket).filter(DokumentenPaket.id == req.dokumentenpaket_id).first()
        if paket:
            for eintrag in sorted(paket.dateien, key=lambda e: e.sort_order):
                pfad = APP_DATA_DIR / "uploads" / eintrag.beleg.dateiname
                if pfad.exists():
                    attachments.append((pfad.read_bytes(), eintrag.bezeichnung or eintrag.beleg.original_name or eintrag.beleg.dateiname))

    empfaenger = [req.an]
    if req.cc:
        empfaenger.append(req.cc)

    msg = _build_message(u, req.an, req.cc, req.betreff, req.text, attachments)
    _sende(u, msg, empfaenger)
    return {"ok": True}


@router.post("/test")
def test_mail(req: TestMailRequest, db: Session = Depends(get_db)):
    u = _smtp_einstellungen(db)
    msg = _build_message(
        u, req.an, None,
        "RechnungsFee – SMTP-Test",
        "Diese Nachricht bestätigt, dass dein SMTP-Versand funktioniert.",
        [],
    )
    _sende(u, msg, [req.an])
    return {"ok": True}
