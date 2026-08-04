"""
Mail-Versand via SMTP – Rechnungen, Angebote, Proforma, Aufträge.
"""
import hashlib
import socket
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
    mahnung_id: Optional[int] = None


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

    # Netto- oder Bruttorechnung: entscheidet r.eingabemodus (Issue #332), nicht kunde.zugferd_aktiv
    # - sonst interpretiert das PDF den gespeicherten Einzelpreis falsch (siehe rechnungen.py).
    ist_netto = r.typ == "ausgang" and r.eingabemodus == "netto"
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


def _zertifikat_fingerprint(sock) -> str:
    der = sock.getpeercert(binary_form=True)
    return hashlib.sha256(der).hexdigest()


def _pruefe_gepinntes_zertifikat(u: Unternehmen, srv, db: Session) -> None:
    """Trust-on-First-Use (Issue #336): Bei der ersten Verbindung mit aktivem
    smtp_zertifikat_ignorieren wird der Fingerabdruck des präsentierten Zertifikats gespeichert.
    Jede weitere Verbindung muss GENAU dieses Zertifikat zeigen - andernfalls wird abgebrochen,
    BEVOR Zugangsdaten gesendet werden. So bleibt "einmal akzeptieren" auch wirklich sicher:
    ein späterer Man-in-the-Middle-Angriff mit einem anderen (auch selbstsignierten) Zertifikat
    wird erkannt und blockiert, statt wie bei bloßem CERT_NONE unbemerkt durchgelassen zu werden."""
    fp = _zertifikat_fingerprint(srv.sock)
    if not u.smtp_zertifikat_fingerprint:
        u.smtp_zertifikat_fingerprint = fp
        db.commit()
    elif fp != u.smtp_zertifikat_fingerprint:
        raise HTTPException(
            400,
            "Das Zertifikat des Mailservers hat sich geändert! Das kann eine legitime "
            "Zertifikatserneuerung sein - oder ein Angriff auf die Verbindung. Zur Sicherheit "
            "wurde der Versand abgebrochen, bevor Zugangsdaten gesendet wurden. Bitte in den "
            "SMTP-Einstellungen das neue Zertifikat bewusst zurücksetzen (nur wenn du dir "
            "sicher bist, dass die Änderung erwartet ist) und den Versand erneut versuchen.",
        )


def _sende(u: Unternehmen, msg: MIMEMultipart, empfaenger: list[str], db: Session) -> None:
    port = u.smtp_port or 587
    ctx = ssl.create_default_context()
    if u.smtp_zertifikat_ignorieren:
        # Opt-in (Issue #336, z.B. TLS-Interception durch lokale Security-Software mit
        # selbstsigniertem Zertifikat) - die CA-Kettenprüfung entfällt, dafür übernimmt
        # _pruefe_gepinntes_zertifikat() unten die eigentliche Sicherheitsprüfung (TOFU-Pinning).
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        if u.smtp_ssl:
            with smtplib.SMTP_SSL(u.smtp_host, port, context=ctx, timeout=15) as srv:
                if u.smtp_zertifikat_ignorieren:
                    _pruefe_gepinntes_zertifikat(u, srv, db)
                srv.login(u.smtp_user, u.smtp_passwort)
                srv.sendmail(msg["From"], empfaenger, msg.as_string())
        else:
            with smtplib.SMTP(u.smtp_host, port, timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ctx)
                srv.ehlo()
                if u.smtp_zertifikat_ignorieren:
                    _pruefe_gepinntes_zertifikat(u, srv, db)
                srv.login(u.smtp_user, u.smtp_passwort)
                srv.sendmail(msg["From"], empfaenger, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(400, "SMTP-Authentifizierung fehlgeschlagen – Benutzer oder Passwort prüfen")
    except smtplib.SMTPConnectError:
        raise HTTPException(400, f"Verbindung zu {u.smtp_host}:{port} fehlgeschlagen")
    except smtplib.SMTPException as e:
        raise HTTPException(400, f"SMTP-Fehler: {e}")
    # Ab hier: technische OSError-Unterklassen, die von smtplib unverändert durchgereicht werden
    # (z.B. "[Error 11001] getaddrinfo failed" unter Windows) - für Fehlersuche unverständlich,
    # deshalb vor dem generischen OSError-Fallback in verständliche Meldungen übersetzt (Issue #336).
    # ssl.SSLCertVerificationError ist eine Unterklasse von ssl.SSLError, die wiederum eine
    # Unterklasse von OSError ist - muss deshalb vor den allgemeineren Fällen geprüft werden.
    except ssl.SSLCertVerificationError as e:
        selbstsigniert = "self-signed certificate" in str(e)
        grund = "ein selbstsigniertes Zertifikat" if selbstsigniert else "ein nicht vertrauenswürdiges Zertifikat"
        raise HTTPException(
            400,
            f'Zertifikatsprüfung fehlgeschlagen: Der SMTP-Server „{u.smtp_host}" verwendet {grund}, '
            "dem RechnungsFee nicht automatisch vertraut - auch wenn dein E-Mail-Programm oder "
            "Windows die Verbindung akzeptiert (z. B. weil das Zertifikat dort manuell als "
            "vertrauenswürdig hinterlegt wurde). Das kommt häufiger bei einem eigenen/internen "
            "Mailserver vor. Bitte beim E-Mail-Anbieter bzw. der IT nachfragen, ob stattdessen "
            "ein gültiges Zertifikat einer öffentlichen Zertifizierungsstelle verwendet werden kann.",
        )
    except ssl.SSLError as e:
        raise HTTPException(400, f"TLS/SSL-Fehler bei der Verbindung zu {u.smtp_host}:{port}: {e}")
    except socket.gaierror:
        raise HTTPException(
            400,
            f'SMTP-Server „{u.smtp_host}" konnte nicht gefunden werden. Bitte den Servernamen '
            "prüfen (z. B. smtp.gmail.com) sowie die Internetverbindung kontrollieren.",
        )
    except (TimeoutError, socket.timeout):
        raise HTTPException(
            400,
            f"Zeitüberschreitung bei der Verbindung zu {u.smtp_host}:{port}. Bitte Servername, "
            "Port und Firewall/Internetverbindung prüfen.",
        )
    except ConnectionRefusedError:
        raise HTTPException(
            400,
            f"Verbindung zu {u.smtp_host}:{port} wurde abgelehnt. Bitte den Port und die "
            "SSL/TLS-Einstellung prüfen (z. B. Port 465 mit SSL oder 587 mit STARTTLS).",
        )
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

    if req.mahnung_id:
        from database.models import Mahnung
        from api.mahnwesen import mahnung_pdf_bytes, sammle_mahnung_anhaenge
        mahnung = db.query(Mahnung).filter(Mahnung.id == req.mahnung_id).first()
        if not mahnung:
            raise HTTPException(404, "Mahnung nicht gefunden")
        pdf_bytes, dateiname = mahnung_pdf_bytes(db, mahnung)
        attachments.append((pdf_bytes, dateiname))
        # Konfigurierbare Zusatzanhänge je Mahnstufe (Rechnung/bisherige Mahnungen/Kontokorrent,
        # Migration 137) - gilt für manuellen wie automatischen Versand gleichermaßen, da beide
        # über diesen Endpunkt laufen.
        attachments.extend(sammle_mahnung_anhaenge(db, mahnung))

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
    _sende(u, msg, empfaenger, db)
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
    _sende(u, msg, [req.an], db)
    return {"ok": True}
