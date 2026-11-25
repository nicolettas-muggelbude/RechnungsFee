"""
Issue #596: Verlauf je Dokument (Druck, Mailversand, Mahnungen) – sichtbar in der Rechnungsliste
(Spalte „Versand“), in der Detailansicht und im Kunden-/Lieferantenstamm.

Einträge werden nur angehängt. SMTP-Versand protokolliert das Backend selbst (api/mail.py), weil
nur dort feststeht, dass die Mail wirklich rausging. Drucken/PDF öffnen sowie die Übergabe an
Thunderbird oder das Standard-Mailprogramm meldet das Frontend (POST /rechnungen/{id}/verlauf) –
ob die Mail danach tatsächlich verschickt wurde, weiß RechnungsFee dort nicht, deshalb
„mail_uebergeben“ statt „mail_gesendet“.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from database.models import DokumentVerlauf, Mahnung, MahnungRechnung, Rechnung

# Versand des Dokuments selbst (Spalte „Versand“ in der Liste); Mahnungen zählen nicht dazu
VERSAND_ARTEN = ("ausgegeben", "gedruckt", "pdf", "mail_gesendet", "mail_uebergeben")
MAHNUNG_ARTEN = ("mahnung_gesendet", "mahnung_uebergeben", "mahnung_gedruckt")
ARTEN = VERSAND_ARTEN + MAHNUNG_ARTEN
KANAELE = ("druck", "smtp", "thunderbird", "mailprogramm", "unbekannt")


def _kurz(text: str | None, laenge: int = 500) -> str | None:
    text = (text or "").strip()
    return text[:laenge] or None


def protokolliere(
    db: Session, *, art: str, kanal: str, rechnung: Rechnung | None = None,
    kopie: bool = False, empfaenger: str | None = None, betreff: str | None = None,
) -> DokumentVerlauf:
    """Ereignis zu einem Dokument anhängen (ohne commit)."""
    if art not in ARTEN or kanal not in KANAELE:
        raise ValueError(f"unbekannte Verlaufsart/-kanal: {art}/{kanal}")
    e = DokumentVerlauf(
        zeitpunkt=datetime.now(), art=art, kanal=kanal, kopie=kopie,
        rechnung_id=rechnung.id if rechnung else None,
        kunde_id=rechnung.kunde_id if rechnung else None,
        lieferant_id=rechnung.lieferant_id if rechnung else None,
        empfaenger=_kurz(empfaenger), betreff=_kurz(betreff),
    )
    db.add(e)
    return e


def protokolliere_mahnung(
    db: Session, mahnung: Mahnung, *, art: str, kanal: str,
    empfaenger: str | None = None, betreff: str | None = None,
) -> list[DokumentVerlauf]:
    """Ein Eintrag je gemahnter Rechnung – so erscheint die Mahnung im Verlauf jeder Rechnung."""
    if art not in MAHNUNG_ARTEN:
        raise ValueError(f"keine Mahnungs-Verlaufsart: {art}")
    ids = [rid for (rid,) in db.query(MahnungRechnung.rechnung_id)
           .filter(MahnungRechnung.mahnung_id == mahnung.id).all()]
    eintraege = []
    for rid in ids or [None]:
        e = DokumentVerlauf(
            zeitpunkt=datetime.now(), art=art, kanal=kanal, kopie=False,
            rechnung_id=rid, mahnung_id=mahnung.id, kunde_id=mahnung.kunde_id,
            empfaenger=_kurz(empfaenger), betreff=_kurz(betreff),
        )
        db.add(e)
        eintraege.append(e)
    return eintraege


def anonymisiere(db: Session, *, kunde_id: int | None = None, lieferant_id: int | None = None) -> None:
    """DSGVO: Mailadresse, Betreff und Partnerbezug aus dem Verlauf entfernen. Die Ereignisse
    selbst bleiben am Dokument (wann gedruckt/versendet)."""
    werte = {DokumentVerlauf.empfaenger: None, DokumentVerlauf.betreff: None}
    q = db.query(DokumentVerlauf)
    if kunde_id is not None:
        q = q.filter(DokumentVerlauf.kunde_id == kunde_id)
        werte[DokumentVerlauf.kunde_id] = None
    elif lieferant_id is not None:
        q = q.filter(DokumentVerlauf.lieferant_id == lieferant_id)
        werte[DokumentVerlauf.lieferant_id] = None
    else:
        return
    q.update(werte, synchronize_session=False)


def letzter_versand(rechnung: Rechnung) -> DokumentVerlauf | None:
    eintraege = [e for e in (rechnung.verlauf or []) if e.art in VERSAND_ARTEN]
    return eintraege[-1] if eintraege else None
