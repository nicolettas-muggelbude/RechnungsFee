"""Mahnwesen (docs/plan-mahnwesen.md).

Abschnitt A: globale Einstellungen (Singleton id=1) + konfigurierbare Mahnstufen.
Abschnitt B: Fälligkeits-Prüfung, Vorschau-Berechnung, Mahnung anlegen (Status: Entwurf).
Abschnitt C: Mahnungs-PDF (inline), DIN-5008-Briefkopf, Mail-Versand (api/mail.py).
Eine Mahnung wechselt von "entwurf" zu "versendet", sobald das PDF nicht nur zur Vorschau
(nur_ansehen=true) abgerufen wird - siehe mahnung_pdf_bytes(). Inkasso-Paket und
Vollautomatik folgen mit Abschnitt E/F.
"""

import io
import re as _re
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import (
    Kunde, Mahnstufe, Mahnung, MahnungRechnung, MahnwesenEinstellungen, Nummernkreis, Rechnung, Unternehmen,
)
from .rechnungen import gutschrift_verrechnen, GutschriftVerrechnenRequest
from utils.pdf_inkasso_deckblatt import erstelle_inkasso_deckblatt_pdf
from utils.pdf_kontokorrent import erstelle_kontokorrent_pdf
from utils.pdf_mahnung import erstelle_mahnung_pdf
from .schemas import (
    MahnstufeCreate,
    MahnstufeResponse,
    MahnstufeUpdate,
    MahnungErstellenRequest,
    MahnungFaelligItem,
    MahnungHistorieItem,
    MahnungResponse,
    MahnungVorschauPosition,
    MahnungVorschauRequest,
    MahnungVorschauResponse,
    MahnwesenEinstellungenResponse,
    MahnwesenEinstellungenUpdate,
    MahnsperreSetzenRequest,
    MahnwesenKundeUebersicht,
    MahnwesenRechnungMini,
    KundenGebuehrZahlungRequest,
    MahnungZahlungRequest,
    MahnungZahlungResponse,
)

router = APIRouter(prefix="/api/mahnwesen", tags=["Mahnwesen"])
Q = Decimal("0.01")


def _get_or_create_einstellungen(db: Session) -> MahnwesenEinstellungen:
    einst = db.query(MahnwesenEinstellungen).filter_by(id=1).first()
    if einst is None:
        einst = MahnwesenEinstellungen(id=1)
        db.add(einst)
        db.commit()
        db.refresh(einst)
    return einst


def _mahnstufe_loesch_sperrgrund(db: Session, stufe: Mahnstufe) -> Optional[str]:
    """Gibt None zurück wenn eine Mahnstufe gelöscht werden darf, sonst den Grund wieso nicht.

    Nutzer-Feedback 2026-08-02: "nur neu hinzugefügte Mahnstufen löschbar machen, alle anderen
    sind nicht löschbar" (Standard-Stufen aus dem Seed, system_stufe=1) + Nachfrage danach, ob
    eine selbst angelegte Stufe gefahrlos gelöscht werden kann, wenn sie noch als "ab Stufe X"-
    Schwellenwert (Konsolidierung/Kundensperrung/Verzugszinsen) konfiguriert ist: diese
    Schwellenwerte speichern nur die reine Stufennummer ohne Fremdschlüssel - ein Löschen würde
    die Schwelle sonst lautlos ins Leere zeigen lassen, ohne dass es auffällt.
    """
    if stufe.system_stufe:
        return "Diese Standard-Mahnstufe kann nicht gelöscht werden - nur deaktivieren."
    if db.query(Mahnung.id).filter(Mahnung.mahnstufe_id == stufe.id).first() is not None:
        return "Diese Mahnstufe wurde bereits für Mahnungen verwendet und kann nicht mehr gelöscht werden - nur deaktivieren."
    einst = db.query(MahnwesenEinstellungen).first()
    if einst and stufe.stufe in (
        einst.konsolidiert_ab_stufe,
        einst.kundensperrung_warnung_ab_stufe,
        einst.kundensperrung_sperrung_ab_stufe,
        einst.verzugszinsen_ab_stufe,
    ):
        return (
            "Diese Stufe ist aktuell als Schwellenwert (Konsolidierung, Kundensperrung oder "
            "Verzugszinsen) hinterlegt und kann nicht gelöscht werden - zuerst den Schwellenwert "
            "in den Einstellungen ändern."
        )
    return None


def _mahnstufe_loeschbar(db: Session, stufe: Mahnstufe) -> bool:
    return _mahnstufe_loesch_sperrgrund(db, stufe) is None


@router.get("/einstellungen", response_model=MahnwesenEinstellungenResponse)
def einstellungen_get(db: Session = Depends(get_db)):
    """Lädt die globale Mahnwesen-Konfiguration inkl. aller Mahnstufen (Singleton id=1)."""
    einst = _get_or_create_einstellungen(db)
    stufen = db.query(Mahnstufe).order_by(Mahnstufe.stufe).all()
    for s in stufen:
        s.loeschbar = _mahnstufe_loeschbar(db, s)
    return MahnwesenEinstellungenResponse(
        id=einst.id,
        aktiv=einst.aktiv,
        automation_modus=einst.automation_modus,
        versand_mail=einst.versand_mail,
        versand_pdf=einst.versand_pdf,
        konsolidiert_ab_stufe=einst.konsolidiert_ab_stufe,
        kundensperrung_aktiv=einst.kundensperrung_aktiv,
        kundensperrung_warnung_ab_stufe=einst.kundensperrung_warnung_ab_stufe,
        kundensperrung_sperrung_ab_stufe=einst.kundensperrung_sperrung_ab_stufe,
        verzugszinsen_aktiv=einst.verzugszinsen_aktiv,
        verzugszinsen_ab_stufe=einst.verzugszinsen_ab_stufe,
        basiszinssatz=einst.basiszinssatz,
        verzugszinsen_aufschlag_privat=einst.verzugszinsen_aufschlag_privat,
        verzugszinsen_aufschlag_gewerblich=einst.verzugszinsen_aufschlag_gewerblich,
        mahnstufen=stufen,
    )


@router.put("/einstellungen", response_model=MahnwesenEinstellungenResponse)
def einstellungen_put(data: MahnwesenEinstellungenUpdate, db: Session = Depends(get_db)):
    """Speichert die globale Mahnwesen-Konfiguration."""
    einst = _get_or_create_einstellungen(db)
    updates = data.model_dump(exclude_unset=True)
    # Vollautomatik verschickt beim nächsten App-Start automatisch echte Mahn-Mails - darf nur
    # aktiviert werden, wenn SMTP bereits eingerichtet ist (Nutzer-Vorgabe nach dem live
    # entdeckten Vorfall: sonst könnte "voll" gesetzt werden, ohne dass beim Aktivieren klar
    # wird, dass es erst nach SMTP-Einrichtung tatsächlich verschickt).
    if updates.get("automation_modus") == "voll":
        unternehmen = db.query(Unternehmen).first()
        if not unternehmen or not unternehmen.smtp_aktiv:
            raise HTTPException(
                status_code=422,
                detail="Vollautomatik kann erst aktiviert werden, wenn der Mail-Versand (SMTP) in den Unternehmenseinstellungen eingerichtet ist.",
            )
    for feld, wert in updates.items():
        setattr(einst, feld, wert)
    db.commit()
    db.refresh(einst)
    return einstellungen_get(db)


@router.post("/mahnstufen", response_model=MahnstufeResponse, status_code=201)
def mahnstufe_create(data: MahnstufeCreate, db: Session = Depends(get_db)):
    """Legt eine neue Mahnstufe an.

    Die vom Client übergebene `stufe`-Nummer wird ignoriert: neue Stufen werden immer VOR der
    bisher letzten Stufe eingefügt (unabhängig davon ob diese aktiv ist), damit z. B. "Letzte
    Mahnung vor Inkasso" strukturell immer die letzte bleibt und "ab Stufe X"-Schwellenwerte
    (Konsolidierung/Kundensperrung/Verzugszinsen) nicht durcheinandergeraten (Nutzer-Feedback
    2026-08-02: "Neue Stufen müssen immer vor der letzten angelegt werden").
    """
    bestehende = db.query(Mahnstufe).order_by(Mahnstufe.stufe).all()
    payload = data.model_dump()
    if bestehende:
        letzte = bestehende[-1]
        payload["stufe"] = letzte.stufe
        letzte.stufe += 1
    else:
        payload["stufe"] = 1
    eintrag = Mahnstufe(**payload)
    db.add(eintrag)
    db.commit()
    db.refresh(eintrag)
    eintrag.loeschbar = True  # frisch angelegt, kann noch von keiner Mahnung referenziert sein
    return eintrag


@router.put("/mahnstufen/{stufe_id}", response_model=MahnstufeResponse)
def mahnstufe_update(stufe_id: int, data: MahnstufeUpdate, db: Session = Depends(get_db)):
    """Bearbeitet eine bestehende Mahnstufe."""
    eintrag = db.query(Mahnstufe).filter(Mahnstufe.id == stufe_id).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Mahnstufe nicht gefunden.")
    updates = data.model_dump(exclude_unset=True)
    if updates.get("mahngebuehr_aktiv"):
        erste_stufe = db.query(Mahnstufe).order_by(Mahnstufe.stufe).first()
        if erste_stufe and erste_stufe.id == eintrag.id:
            raise HTTPException(
                status_code=422,
                detail="Auf der ersten Stufe (Zahlungserinnerung) darf keine Mahngebühr berechnet werden.",
            )
    for feld, wert in updates.items():
        setattr(eintrag, feld, wert)
    db.commit()
    db.refresh(eintrag)
    eintrag.loeschbar = _mahnstufe_loeschbar(db, eintrag)
    return eintrag


@router.delete("/mahnstufen/{stufe_id}", status_code=204)
def mahnstufe_delete(stufe_id: int, db: Session = Depends(get_db)):
    """Löscht eine Mahnstufe - nur solange sie nicht system_stufe ist, noch nie für eine Mahnung
    verwendet wurde und nicht als "ab Stufe X"-Schwellenwert konfiguriert ist (siehe
    _mahnstufe_loesch_sperrgrund())."""
    eintrag = db.query(Mahnstufe).filter(Mahnstufe.id == stufe_id).first()
    if not eintrag:
        raise HTTPException(status_code=404, detail="Mahnstufe nicht gefunden.")
    grund = _mahnstufe_loesch_sperrgrund(db, eintrag)
    if grund:
        raise HTTPException(status_code=422, detail=grund)
    db.delete(eintrag)
    db.commit()


# ---------------------------------------------------------------------------
# Fälligkeits-Prüfung, Vorschau, Erstellen (Abschnitt B)
# ---------------------------------------------------------------------------

def _kunde_name(kunde: Optional["Kunde"]) -> str:
    if not kunde:
        return "-"
    return kunde.firmenname or f"{kunde.vorname or ''} {kunde.nachname or ''}".strip() or "-"


def _kunde_ist_gewerblich(kunde: "Kunde") -> bool:
    """Proxy mangels eigenem Kundentyp-Feld: Firmenname gesetzt = gewerblich."""
    return bool(kunde.firmenname and kunde.firmenname.strip())


def _naechste_aktive_stufe(db: Session, aktuelle_stufe: int) -> Optional[Mahnstufe]:
    """Nächsthöhere AKTIVE Stufe - nicht stur 'aktuelle Stufe + 1', da einzelne Stufen
    deaktiviert/gelöscht sein können (z. B. nur Stufe 1+2, danach manuell Inkasso)."""
    return (
        db.query(Mahnstufe)
        .filter(Mahnstufe.stufe > aktuelle_stufe, Mahnstufe.aktiv == True)  # noqa: E712
        .order_by(Mahnstufe.stufe)
        .first()
    )


def _faellige_naechste_stufe(db: Session, rechnung: Rechnung, heute: date) -> Optional[Mahnstufe]:
    """Gibt die nächste aktive Mahnstufe zurück, wenn die Rechnung dafür fällig ist, sonst None."""
    naechste = _naechste_aktive_stufe(db, rechnung.mahnstufe_aktuell)
    if naechste is None:
        return None
    if rechnung.mahnstufe_aktuell == 0:
        if not rechnung.faellig_am:
            return None
        faellig = rechnung.faellig_am + timedelta(days=naechste.tage_nach_faelligkeit)
        return naechste if faellig <= heute else None
    letzte = (
        db.query(Mahnung)
        .join(MahnungRechnung, MahnungRechnung.mahnung_id == Mahnung.id)
        .filter(MahnungRechnung.rechnung_id == rechnung.id, Mahnung.status == "versendet")
        .order_by(Mahnung.versendet_am.desc())
        .first()
    )
    if letzte is None or letzte.versendet_am is None:
        return None
    faellig = letzte.versendet_am.date() + timedelta(days=naechste.tage_nach_vorheriger)
    return naechste if faellig <= heute else None


def _faellige_naechste_stufe_gebuehr_kunde(db: Session, kunde_id: int, heute: date) -> Optional[Mahnstufe]:
    """Analog zu _faellige_naechste_stufe(), aber für einen Kunden OHNE offene Rechnung, der
    noch eine offene Mahngebühr/Verzugszinsen aus einer früheren Mahnung hat (Kontokorrent-
    Konsistenz - Nutzer-Vorgabe: "Solange der Kontokorrent nicht ausgeglichen ist müssen die
    Mahnstufen weiterlaufen"). Nutzt die höchste noch nicht übertragene, versendete Mahnung mit
    offenem Restbetrag als Basis für den Fälligkeits-Countdown (tage_nach_vorheriger)."""
    from utils.mahngebuehr_verrechnung import _offene_mahnungen_kunde

    kandidaten = [
        m for m in _offene_mahnungen_kunde(db, kunde_id)
        if (m.mahngebuehr - m.mahngebuehr_bezahlt) + (m.verzugszinsen - m.verzugszinsen_bezahlt) > Decimal("0.004")
    ]
    if not kandidaten:
        return None
    letzte = max(kandidaten, key=lambda m: (m.stufe, m.erstellt_am))
    naechste = _naechste_aktive_stufe(db, letzte.stufe)
    if naechste is None or not letzte.versendet_am:
        return None
    faellig = letzte.versendet_am.date() + timedelta(days=naechste.tage_nach_vorheriger)
    return naechste if faellig <= heute else None


@router.get("/faellig", response_model=list[MahnungFaelligItem])
def faellig_liste(db: Session = Depends(get_db)):
    """Ausgangsrechnungen, für die laut Fälligkeits-Logik jetzt eine Mahnung ansteht."""
    heute = date.today()
    rechnungen = (
        db.query(Rechnung)
        .filter(
            Rechnung.typ == "ausgang",
            Rechnung.ist_entwurf == False,  # noqa: E712
            Rechnung.storniert == False,  # noqa: E712
            Rechnung.zahlungsstatus.in_(["offen", "teilweise"]),
            Rechnung.faellig_am.isnot(None),
        )
        .all()
    )
    ergebnisse: list[MahnungFaelligItem] = []
    for r in rechnungen:
        stufe = _faellige_naechste_stufe(db, r, heute)
        if stufe is None:
            continue
        kunde = db.query(Kunde).filter(Kunde.id == r.kunde_id).first() if r.kunde_id else None
        ergebnisse.append(MahnungFaelligItem(
            rechnung_id=r.id,
            rechnungsnummer=r.rechnungsnummer,
            kunde_id=r.kunde_id,
            kunde_name=_kunde_name(kunde),
            faellig_am=r.faellig_am,
            offener_betrag=(r.brutto_gesamt - r.bezahlt_betrag).quantize(Q, ROUND_HALF_UP),
            mahnstufe_aktuell=r.mahnstufe_aktuell,
            empfohlene_stufe=stufe.stufe,
            empfohlene_stufe_bezeichnung=stufe.bezeichnung,
        ))
    return ergebnisse


@router.get("/kunden", response_model=list[MahnwesenKundeUebersicht])
def kunden_uebersicht(db: Session = Depends(get_db)):
    """Eine Zeile pro Kunde mit mahnrelevanten Rechnungen - die Übersichtsliste im Frontend.

    Zahlungserinnerung (Stufe 1) bleibt 1:1 an der einzelnen Rechnung (siehe rechnungen[].
    zahlungserinnerung_faellig); "Mahnungen" (Stufe >= konsolidiert_ab_stufe) sind Sache des
    ganzen Kunden - deren Historie liefert der bereits vorhandene Endpunkt
    GET /kunden/{kunde_id}/mahnungen (kunden.py), hier nur die Zusammenfassung + Rechnungsliste.
    """
    heute = date.today()
    rechnungen = (
        db.query(Rechnung)
        .filter(
            Rechnung.typ == "ausgang",
            Rechnung.dokument_typ == "Rechnung",
            Rechnung.ist_entwurf == False,  # noqa: E712
            Rechnung.storniert == False,  # noqa: E712
            Rechnung.zahlungsstatus.in_(["offen", "teilweise"]),
            Rechnung.faellig_am.isnot(None),
        )
        .all()
    )
    relevant = [r for r in rechnungen if r.faellig_am < heute or r.mahnstufe_aktuell > 0]

    nach_kunde: dict[int, list[Rechnung]] = {}
    for r in relevant:
        if r.kunde_id:
            nach_kunde.setdefault(r.kunde_id, []).append(r)

    einstellungen = _get_or_create_einstellungen(db)
    kunden_by_id = {k.id: k for k in db.query(Kunde).filter(Kunde.id.in_(nach_kunde.keys())).all()}
    alle_stufen_by_wert = {s.stufe: s for s in db.query(Mahnstufe).filter(Mahnstufe.aktiv == True).all()}  # noqa: E712

    # Letzte (höchste Stufe, dann neuestes Datum) nicht-stornierte Mahnung PRO RECHNUNG -
    # nötig für den Breakdown je Kunde (1 versendet / 1 Entwurf / 2 fällig statt einem
    # einzelnen Status, der die anderen Rechnungen verschluckt; Nutzer-Feedback 2026-08-01).
    relevant_ids = [r.id for r in relevant]
    links = (
        db.query(MahnungRechnung, Mahnung)
        .join(Mahnung, Mahnung.id == MahnungRechnung.mahnung_id)
        .filter(MahnungRechnung.rechnung_id.in_(relevant_ids), Mahnung.status != "storniert")
        .all()
    )
    letzte_mahnung_pro_rechnung: dict[int, Mahnung] = {}
    for link, m in links:
        bisher = letzte_mahnung_pro_rechnung.get(link.rechnung_id)
        if bisher is None or (m.stufe, m.erstellt_am) > (bisher.stufe, bisher.erstellt_am):
            letzte_mahnung_pro_rechnung[link.rechnung_id] = m

    ergebnisse: list[MahnwesenKundeUebersicht] = []
    for kunde_id, r_liste in nach_kunde.items():
        kunde_obj = kunden_by_id.get(kunde_id)
        sperre_aktiv = bool(kunde_obj and kunde_obj.mahnsperre_bis and kunde_obj.mahnsperre_bis >= heute)

        rechnungen_mini = []
        faellige_stufen: list[Mahnstufe] = []
        for r in r_liste:
            # Fälligkeit wird IMMER echt berechnet (reine Datumslogik, unverändert) - die
            # Mahnsperre verschiebt keine Fristen, sie blendet nur das Ergebnis für die
            # Dauer der Sperre aus. Läuft die Sperre ab, springt alles sofort auf den Stand
            # an, den es ohne Sperre auch gehabt hätte (Nutzer-Feedback 2026-08-01).
            faellige_stufe = _faellige_naechste_stufe(db, r, heute)
            if faellige_stufe is not None and not sperre_aktiv:
                faellige_stufen.append(faellige_stufe)
            letzte_r = letzte_mahnung_pro_rechnung.get(r.id)
            rechnungen_mini.append(MahnwesenRechnungMini(
                rechnung_id=r.id,
                rechnungsnummer=r.rechnungsnummer,
                faellig_am=r.faellig_am,
                offener_betrag=(r.brutto_gesamt - r.bezahlt_betrag).quantize(Q, ROUND_HALF_UP),
                mahnstufe_aktuell=r.mahnstufe_aktuell,
                zahlungserinnerung_faellig=(not sperre_aktiv and r.mahnstufe_aktuell == 0 and faellige_stufe is not None),
                letzter_mahnung_status=letzte_r.status if letzte_r else None,
            ))

        # "aktionsfaellig" auf Kunden-Ebene meint hier bewusst nur echte Mahnstufen
        # (>= konsolidiert_ab_stufe) - eine fällige Zahlungserinnerung einzelner Rechnungen
        # macht den Kunden als Ganzes noch nicht "aktionsfällig" (Stufe 1 bleibt Rechnungssache).
        #
        # Logikfehler-Fix (Nutzer-Feedback 2026-08-01): eine Rechnung kann ihre EIGENE nächste
        # Stufe auslösen, während eine andere Rechnung desselben Kunden schon eine HÖHERE Stufe
        # erreicht hat (z.B. RE-A schon "2. Mahnung"/Stufe 3, RE-B löst gerade erst ihre eigene
        # "1. Mahnung"/Stufe 2 aus). Ohne Korrektur würde die gemeinsame Mahnung auf Stufe 2
        # zurückfallen - RE-A bekäme scheinbar eine mildere Mahnung als zuvor. Die Zielstufe der
        # Gruppe ist daher IMMER mindestens der bereits erreichte Höchststand der Gruppe (nicht
        # weiter eskaliert, nur "aufgeholt") - echte Weitereskalation kommt weiterhin aus einem
        # tatsächlich ausgelösten höheren Trigger (z.B. RE-A's eigener Stufe-3→4-Termin).
        mahnstufen_faellig = [s for s in faellige_stufen if s.stufe >= einstellungen.konsolidiert_ab_stufe]
        kunde_max_mahnstufe_aktuell = max((r.mahnstufe_aktuell for r in r_liste), default=0)
        if faellige_stufen and kunde_max_mahnstufe_aktuell >= einstellungen.konsolidiert_ab_stufe:
            kandidaten_werte = {s.stufe for s in faellige_stufen} | {kunde_max_mahnstufe_aktuell}
            ziel_wert = max(kandidaten_werte)
            ziel_stufe_obj = alle_stufen_by_wert.get(ziel_wert)
            if ziel_stufe_obj is not None:
                mahnstufen_faellig = [ziel_stufe_obj]
        aktionsfaellig = len(mahnstufen_faellig) > 0
        naechste_stufe = None
        naechste_stufe_bez = None
        if mahnstufen_faellig:
            ziel = max(mahnstufen_faellig, key=lambda s: s.stufe)
            naechste_stufe, naechste_stufe_bez = ziel.stufe, ziel.bezeichnung

        # Jede Rechnung zählt in genau einen Eimer - Priorität: fällig > entwurf > versendet > offen.
        anzahl_faellig = sum(1 for rm in rechnungen_mini if rm.zahlungserinnerung_faellig)
        anzahl_entwurf = sum(1 for rm in rechnungen_mini if not rm.zahlungserinnerung_faellig and rm.letzter_mahnung_status == "entwurf")
        anzahl_versendet = sum(1 for rm in rechnungen_mini if not rm.zahlungserinnerung_faellig and rm.letzter_mahnung_status == "versendet")
        anzahl_offen = len(rechnungen_mini) - anzahl_faellig - anzahl_entwurf - anzahl_versendet

        ergebnisse.append(MahnwesenKundeUebersicht(
            kunde_id=kunde_id,
            kunde_name=_kunde_name(kunden_by_id.get(kunde_id)),
            anzahl_offene_rechnungen=len(r_liste),
            aeltestes_faellig_am=min((r.faellig_am for r in r_liste if r.faellig_am), default=None),
            offener_betrag_gesamt=sum((r.brutto_gesamt - r.bezahlt_betrag for r in r_liste), Decimal("0")).quantize(Q, ROUND_HALF_UP),
            aktionsfaellig=aktionsfaellig,
            naechste_stufe=naechste_stufe,
            naechste_stufe_bezeichnung=naechste_stufe_bez,
            mahnsperre_bis=kunde_obj.mahnsperre_bis if sperre_aktiv else None,
            mahnsperre_grund=kunde_obj.mahnsperre_grund if sperre_aktiv else None,
            anzahl_zahlungserinnerung_faellig=anzahl_faellig,
            anzahl_entwurf=anzahl_entwurf,
            anzahl_versendet=anzahl_versendet,
            anzahl_offen=anzahl_offen,
            rechnungen=sorted(rechnungen_mini, key=lambda rm: rm.faellig_am or heute),
        ))

    # Zweite Passe: Kunden OHNE offene Rechnung, aber mit noch offener Mahngebühr/Verzugszinsen
    # aus einer früheren Mahnung (Kontokorrent-Konsistenz - Nutzer-Vorgabe: "Solange der
    # Kontokorrent nicht ausgeglichen ist müssen die Mahnstufen weiterlaufen... sonst gibt es
    # keine Übereinstimmung mit dem Kontokorrent"). Ausdrücklich NUR bereits gemahnte, noch
    # offene Beträge - eine druckfrische Rechnung ohne eigenen Mahnstatus wird dadurch nicht
    # vorzeitig in den Mahnflow gezogen (Nutzer-Vorgabe).
    from utils.mahngebuehr_verrechnung import offene_mahngebuehr_summe_kunde

    alle_offenen_gebuehr_mahnungen = (
        db.query(Mahnung)
        .filter(Mahnung.status == "versendet", Mahnung.uebertragen_in_mahnung_id.is_(None))
        .all()
    )
    gebuehr_kunde_ids: set[int] = set()
    for m in alle_offenen_gebuehr_mahnungen:
        if not m.kunde_id or m.kunde_id in nach_kunde:
            continue  # hat noch offene Rechnung(en) - bereits oben erfasst
        offen = (m.mahngebuehr - m.mahngebuehr_bezahlt) + (m.verzugszinsen - m.verzugszinsen_bezahlt)
        if offen > Decimal("0.004"):
            gebuehr_kunde_ids.add(m.kunde_id)

    for kunde_id in gebuehr_kunde_ids:
        kunde_obj = db.query(Kunde).filter(Kunde.id == kunde_id).first()
        if not kunde_obj:
            continue
        sperre_aktiv = bool(kunde_obj.mahnsperre_bis and kunde_obj.mahnsperre_bis >= heute)
        offene_gebuehr = offene_mahngebuehr_summe_kunde(db, kunde_id)
        naechste_stufe_obj = None if sperre_aktiv else _faellige_naechste_stufe_gebuehr_kunde(db, kunde_id, heute)
        ergebnisse.append(MahnwesenKundeUebersicht(
            kunde_id=kunde_id,
            kunde_name=_kunde_name(kunde_obj),
            anzahl_offene_rechnungen=0,
            aeltestes_faellig_am=None,
            offener_betrag_gesamt=offene_gebuehr,
            aktionsfaellig=naechste_stufe_obj is not None,
            naechste_stufe=naechste_stufe_obj.stufe if naechste_stufe_obj else None,
            naechste_stufe_bezeichnung=naechste_stufe_obj.bezeichnung if naechste_stufe_obj else None,
            mahnsperre_bis=kunde_obj.mahnsperre_bis if sperre_aktiv else None,
            mahnsperre_grund=kunde_obj.mahnsperre_grund if sperre_aktiv else None,
            rechnungen=[],
            nur_offene_gebuehr=True,
        ))

    return ergebnisse


@router.put("/kunden/{kunde_id}/sperre", status_code=204)
def mahnsperre_setzen(kunde_id: int, data: MahnsperreSetzenRequest, db: Session = Depends(get_db)):
    """Manuelle, befristete Mahnsperre für einen Kunden (z.B. Kunde ruft an, zahlt in einer
    Woche). Verschiebt keine Fristen - blendet nur bis einschließlich `bis` jede Aktion
    (Zahlungserinnerung wie Mahnung) für diesen Kunden aus; danach läuft alles normal weiter,
    exakt auf dem Stand, den es ohne Sperre auch hätte. Setzen überschreibt eine evtl. bereits
    bestehende Sperre (neues Datum/Grund)."""
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    kunde.mahnsperre_bis = data.bis
    kunde.mahnsperre_grund = data.grund
    db.commit()


@router.delete("/kunden/{kunde_id}/sperre", status_code=204)
def mahnsperre_aufheben(kunde_id: int, db: Session = Depends(get_db)):
    """Hebt eine Mahnsperre vorzeitig auf (z.B. Kunde hat schon vor dem angekündigten Termin gezahlt)."""
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    kunde.mahnsperre_bis = None
    kunde.mahnsperre_grund = None
    db.commit()


@router.post("/kunden/{kunde_id}/gebuehr-zahlung", status_code=201)
def kunden_gebuehr_zahlung(kunde_id: int, data: KundenGebuehrZahlungRequest, db: Session = Depends(get_db)):
    """Bezahlt offene Mahngebühr/Verzugszinsen eines Kunden OHNE dass noch eine Rechnung offen
    sein muss - eigener, kundenweiter Zahlungsweg (Nutzer-Vorgabe: normale Nutzer sollen dafür
    keine freie Journalbuchung anlegen müssen, das würde sie überfordern). Übersteigt der Betrag
    die offene Summe, wird der Rest wie bei den anderen Zahlungswegen als Kundenguthaben erfasst
    statt die Buchung zu blockieren."""
    from database.models import Forderung
    from utils.mahngebuehr_verrechnung import offene_mahngebuehr_summe_kunde, verrechne_mahngebuehren_kunde
    from .journal import _naechste_belegnr

    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    if data.betrag <= Decimal("0"):
        raise HTTPException(status_code=422, detail="Betrag muss größer als 0 sein.")

    offen_vorher = offene_mahngebuehr_summe_kunde(db, kunde_id)
    if offen_vorher <= Decimal("0.004"):
        raise HTTPException(status_code=409, detail="Keine offene Mahngebühr/Verzugszinsen für diesen Kunden vorhanden.")

    rest, erzeugte = verrechne_mahngebuehren_kunde(
        db, kunde_id, data.betrag, data.datum, data.zahlungsart, _naechste_belegnr,
        referenz=_kunde_name(kunde),
    )
    if rest > Decimal("0.004"):
        db.add(Forderung(
            typ="kundenguthaben", betrag=rest, partner_typ="kunde", partner_id=kunde_id,
            journal_id=erzeugte[0] if erzeugte else None,
            notiz=f"Überzahlung Mahngebühr: {_kunde_name(kunde)} · {rest:.2f} €",
        ))
    db.commit()
    return {"verrechnet": (data.betrag - rest).quantize(Q, ROUND_HALF_UP), "kundenguthaben": rest.quantize(Q, ROUND_HALF_UP)}


def verteile_mahnung_zahlung(db: Session, mahnung: Mahnung, betrag: Decimal, datum: date, zahlungsart: str) -> dict:
    """Verteilt eine eingehende Zahlung auf die Rechnungen einer (ggf. konsolidierten) Mahnung.

    Nutzer-Vorgabe 2026-08-02 (Abschnitt E, "Zahlungsverteilung bei konsolidierten Mahnungen"):
    älteste fällige Rechnung zuerst voll auffüllen (FIFO) - jede Rechnung bekommt über
    `zahlung_bar_erstellen()` (api/rechnungen.py, In-Prozess-Aufruf wie an anderen Stellen dieser
    Datei) exakt ihren offenen Betrag, nie mehr, damit dessen eigene Überschuss-Logik nicht
    einspringt und die Aufteilung hier vollständig selbst kontrolliert bleibt. Ein nach allen
    Rechnungen verbleibender Rest (oder der komplette Betrag bei einer rechnungslosen Mahnung,
    `nur_offene_gebuehr`) geht über `verrechne_mahngebuehren_kunde()` gegen offene
    Mahngebühr/Verzugszinsen des Kunden, ein danach noch verbleibender Überschuss wird wie bei
    allen anderen Zahlungswegen als Kundenguthaben erfasst statt die Buchung zu blockieren.

    Von zwei Stellen genutzt: dem manuellen Endpunkt `mahnung_zahlung_erfassen()` (Betrag/Datum
    per Formular) und dem Bank-Import (`bank_import.py::_match_mahnung()` + Aufrufer), der eine
    erkannte Mahnungsnummer im Verwendungszweck automatisch genauso verteilt.

    Gibt zusätzlich `journal_ids` zurück (alle erzeugten Journaleintrag-IDs, in Buchungsreihenfolge)
    - der Bank-Import braucht mindestens eine davon, um `BankTransaktion.journal_id` zu setzen und
    die Transaktion so als "gebucht" zu markieren.
    """
    from database.models import Forderung
    from utils.mahngebuehr_verrechnung import verrechne_mahngebuehren_kunde
    from .journal import _naechste_belegnr
    from .rechnungen import zahlung_bar_erstellen
    from .schemas_rechnungen import BarZahlungCreate

    offene_rechnungen = (
        db.query(Rechnung)
        .join(MahnungRechnung, MahnungRechnung.rechnung_id == Rechnung.id)
        .filter(MahnungRechnung.mahnung_id == mahnung.id)
        .all()
    )
    offene_rechnungen = [r for r in offene_rechnungen if (r.brutto_gesamt - r.bezahlt_betrag) > Decimal("0.004")]
    offene_rechnungen.sort(key=lambda r: r.faellig_am or r.datum)

    rest = betrag.quantize(Q, ROUND_HALF_UP)
    verteilung: list[dict] = []
    journal_ids: list[int] = []
    for rechnung in offene_rechnungen:
        if rest <= Decimal("0.004"):
            break
        offen = rechnung.brutto_gesamt - rechnung.bezahlt_betrag
        teil = min(rest, offen).quantize(Q, ROUND_HALF_UP)
        if teil <= Decimal("0.004"):
            continue
        ergebnis = zahlung_bar_erstellen(
            rechnung_id=rechnung.id,
            data=BarZahlungCreate(betrag=teil, datum=datum, zahlungsart=zahlungsart),
            db=db,
        )
        journal_ids.append(ergebnis.journaleintrag_id)
        verteilung.append({"rechnung_id": rechnung.id, "rechnungsnummer": rechnung.rechnungsnummer, "betrag": teil})
        rest -= teil

    gebuehr_verrechnet = Decimal("0")
    kundenguthaben = Decimal("0")
    if rest > Decimal("0.004") and mahnung.kunde_id:
        vor = rest
        rest, erzeugte = verrechne_mahngebuehren_kunde(
            db, mahnung.kunde_id, rest, datum, zahlungsart, _naechste_belegnr,
            referenz=mahnung.mahnnummer or "",
        )
        journal_ids.extend(erzeugte)
        gebuehr_verrechnet = (vor - rest).quantize(Q, ROUND_HALF_UP)
        if rest > Decimal("0.004"):
            kunde = db.query(Kunde).filter(Kunde.id == mahnung.kunde_id).first()
            db.add(Forderung(
                typ="kundenguthaben", betrag=rest, partner_typ="kunde", partner_id=mahnung.kunde_id,
                journal_id=erzeugte[0] if erzeugte else None,
                notiz=f"Überzahlung Mahnung {mahnung.mahnnummer or mahnung.id}: {_kunde_name(kunde)} · {rest:.2f} €",
            ))
            kundenguthaben = rest.quantize(Q, ROUND_HALF_UP)

    return {"verteilung": verteilung, "gebuehr_verrechnet": gebuehr_verrechnet, "kundenguthaben": kundenguthaben, "journal_ids": journal_ids}


@router.post("/{mahnung_id}/zahlung", response_model=MahnungZahlungResponse, status_code=201)
def mahnung_zahlung_erfassen(mahnung_id: int, data: MahnungZahlungRequest, db: Session = Depends(get_db)):
    """Manueller Endpunkt für `verteile_mahnung_zahlung()` - siehe dort für die eigentliche Logik."""
    mahnung = db.query(Mahnung).filter(Mahnung.id == mahnung_id).first()
    if not mahnung:
        raise HTTPException(status_code=404, detail="Mahnung nicht gefunden.")
    if data.betrag <= Decimal("0"):
        raise HTTPException(status_code=422, detail="Betrag muss größer als 0 sein.")

    ergebnis = verteile_mahnung_zahlung(db, mahnung, data.betrag, data.datum, data.zahlungsart)
    db.commit()
    return ergebnis


@router.post("/kunden/{kunde_id}/entsperren", status_code=204)
def kundensperrung_aufheben(kunde_id: int, db: Session = Depends(get_db)):
    """Hebt Warnung UND harte Sperre manuell auf - z.B. nach Zahlungseingang oder individueller
    Absprache. Erneut fällig, sobald wieder eine Mahnstufe die jeweilige Schwelle erreicht
    (siehe erstellen())."""
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    kunde.mahnung_gesperrt = False
    kunde.mahnung_warnung = False
    db.commit()


def pruefe_kundensperre(db: Session, kunde_id: Optional[int], typ: str) -> None:
    """Wirft eine 403, wenn für diesen Kunden ein neues Ausgangsdokument (Angebot, Auftrag,
    Proforma, Lieferschein, Rechnung) wegen harter Kundensperrung nicht angelegt werden darf.

    Nur kunden.mahnung_gesperrt (die höhere, "Sperrung"-Schwelle) blockiert hier; die niedrigere
    "Warnung"-Schwelle (kunden.mahnung_warnung) blockiert bewusst nichts - das Frontend zeigt dort
    nur einen Hinweis (siehe RechnungForm).
    """
    if typ != "ausgang" or not kunde_id:
        return
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if kunde and kunde.mahnung_gesperrt:
        raise HTTPException(
            status_code=403,
            detail=f"{_kunde_name(kunde)} ist wegen ausstehender Mahnungen für neue Dokumente gesperrt.",
        )


def _verzugszinsen_fuer_betrag(
    einstellungen: MahnwesenEinstellungen, gewerblich: bool, betrag: Decimal,
    faellig_am: date, bis_datum: date,
) -> Decimal:
    """§288 BGB Verzugszinsen für `betrag`, Zeitraum faellig_am → bis_datum (exklusiv Tag 0)."""
    tage = (bis_datum - faellig_am).days
    if tage <= 0:
        return Decimal("0.00")
    aufschlag = (
        einstellungen.verzugszinsen_aufschlag_gewerblich if gewerblich
        else einstellungen.verzugszinsen_aufschlag_privat
    )
    jahreszins = (einstellungen.basiszinssatz + aufschlag) / Decimal("100")
    return (betrag * jahreszins * Decimal(tage) / Decimal("365")).quantize(Q, ROUND_HALF_UP)


def finalisiere_verzugszinsen_bei_zahlung(db: Session, rechnung: Rechnung, zahlungsdatum: date) -> None:
    """Wird aufgerufen, sobald eine Ausgangsrechnung vollständig bezahlt ist (siehe
    _aktualisiere_zahlungsstatus() in api/rechnungen.py). §288 BGB: Verzugszinsen laufen bis zur
    tatsächlichen Zahlung, nicht nur bis zum Tag, an dem zufällig die letzte Mahnung erstellt
    wurde - ohne diese Einfrierung würde die gespeicherte Zinsberechnung einer offenen Mahnung
    die Tage zwischen Mahnungs-Erstellung und tatsächlicher Zahlung schlicht verlieren.

    Bewusst nur für NICHT konsolidierte Mahnungen (genau eine verknüpfte Rechnung) - bei einer
    konsolidierten Mahnung ist der Zinsanteil je Rechnung am gespeicherten mahnung.verzugszinsen
    nicht sauber trennbar, ohne die Buchung nachträglich aufzuspalten (gleiche Einschränkung wie
    offene_mahngebuehr_summe() in utils/mahngebuehr_verrechnung.py)."""
    if rechnung.typ != "ausgang" or not rechnung.faellig_am:
        return
    einstellungen = _get_or_create_einstellungen(db)
    if not einstellungen.verzugszinsen_aktiv:
        return

    links = db.query(MahnungRechnung).filter(MahnungRechnung.rechnung_id == rechnung.id).all()
    kunde: Optional[Kunde] = None
    for link in links:
        anzahl_verknuepft = db.query(MahnungRechnung).filter(MahnungRechnung.mahnung_id == link.mahnung_id).count()
        if anzahl_verknuepft != 1:
            continue
        mahnung = db.query(Mahnung).filter(
            Mahnung.id == link.mahnung_id, Mahnung.status == "versendet",
            Mahnung.uebertragen_in_mahnung_id.is_(None),
        ).first()
        if not mahnung:
            continue
        stufe = db.query(Mahnstufe).filter(Mahnstufe.id == mahnung.mahnstufe_id).first()
        if not stufe or stufe.stufe < einstellungen.verzugszinsen_ab_stufe:
            continue
        if kunde is None:
            kunde = db.query(Kunde).filter(Kunde.id == rechnung.kunde_id).first()
        gewerblich = _kunde_ist_gewerblich(kunde) if kunde else False
        neu = _verzugszinsen_fuer_betrag(
            einstellungen, gewerblich, rechnung.brutto_gesamt, rechnung.faellig_am, zahlungsdatum,
        )
        if neu > mahnung.verzugszinsen:
            mahnung.verzugszinsen = neu


def _offene_gebuehr_vorperioden_kunde(db: Session, kunde_id: int) -> tuple[Decimal, Decimal, list[Mahnung]]:
    """Noch offene Mahngebühr/Verzugszinsen aller VERSENDETEN, noch nicht übertragenen Mahnungen
    eines Kunden - unabhängig davon, ob die ursprüngliche Rechnung inzwischen bezahlt ist (Nutzer-
    Vorgabe: "Solange offene Beträge vorhanden sind muss es auch in die nächste Mahnstufe gehen...
    sonst gibt es keine Übereinstimmung mit dem Kontokorrent"). Gibt (gebuehr_summe, zinsen_summe,
    betroffene_mahnungen) zurück - getrennt nach Kategorie, damit die aufnehmende Mahnung die
    Beträge korrekt in ihre eigenen mahngebuehr/verzugszinsen-Felder einrechnen kann."""
    mahnungen = (
        db.query(Mahnung)
        .filter(
            Mahnung.kunde_id == kunde_id,
            Mahnung.status == "versendet",
            Mahnung.uebertragen_in_mahnung_id.is_(None),
        )
        .all()
    )
    gebuehr_summe = Decimal("0")
    zinsen_summe = Decimal("0")
    betroffene: list[Mahnung] = []
    for m in mahnungen:
        offen_gebuehr = (m.mahngebuehr or Decimal("0")) - (m.mahngebuehr_bezahlt or Decimal("0"))
        offen_zinsen = (m.verzugszinsen or Decimal("0")) - (m.verzugszinsen_bezahlt or Decimal("0"))
        if offen_gebuehr > Decimal("0.004") or offen_zinsen > Decimal("0.004"):
            gebuehr_summe += max(offen_gebuehr, Decimal("0"))
            zinsen_summe += max(offen_zinsen, Decimal("0"))
            betroffene.append(m)
    return gebuehr_summe.quantize(Q, ROUND_HALF_UP), zinsen_summe.quantize(Q, ROUND_HALF_UP), betroffene


def _berechne_mahnung(
    db: Session, rechnung_ids: list[int], stufe_nr: Optional[int], einstellungen: MahnwesenEinstellungen,
) -> tuple[Kunde, Mahnstufe, list[Rechnung], Decimal, Decimal, Decimal]:
    """Ermittelt Kunde, Zielstufe, offene Rechnungen, offenen Gesamtbetrag, Mahngebühr, Verzugszinsen.

    Gemeinsame Berechnung für /vorschau und /erstellen, damit beide garantiert dasselbe liefern.
    """
    rechnungen = db.query(Rechnung).filter(Rechnung.id.in_(rechnung_ids)).all()
    if not rechnungen:
        raise HTTPException(status_code=404, detail="Keine Rechnungen gefunden.")
    kunde_ids = {r.kunde_id for r in rechnungen}
    if len(kunde_ids) > 1:
        raise HTTPException(status_code=422, detail="Alle Rechnungen müssen zum selben Kunden gehören.")
    kunde = db.query(Kunde).filter(Kunde.id == rechnungen[0].kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    if kunde.mahnsperre_bis and kunde.mahnsperre_bis >= date.today():
        raise HTTPException(
            status_code=422,
            detail=f"Kunde hat eine Mahnsperre bis {kunde.mahnsperre_bis.strftime('%d.%m.%Y')}.",
        )

    if stufe_nr is not None:
        stufe = db.query(Mahnstufe).filter(Mahnstufe.stufe == stufe_nr, Mahnstufe.aktiv == True).first()  # noqa: E712
        if not stufe:
            raise HTTPException(status_code=404, detail=f"Aktive Mahnstufe {stufe_nr} nicht gefunden.")
    else:
        # Wie in kunden_uebersicht(): der Kunde kann bereits offene Rechnungen mit einer
        # höheren Stufe haben als die hier übergebenen rechnung_ids - die Baseline darf nicht
        # dahinter zurückfallen. Aktuell ruft das Frontend erstellen()/vorschau() immer mit
        # explizitem stufe_nr auf (dieser Zweig ist der generische Fallback für künftige
        # Aufrufer, z.B. Abschnitt F Vollautomatik).
        alle_offenen_kunde = db.query(Rechnung).filter(
            Rechnung.kunde_id == kunde.id,
            Rechnung.typ == "ausgang",
            Rechnung.dokument_typ == "Rechnung",
            Rechnung.ist_entwurf == False,  # noqa: E712
            Rechnung.storniert == False,  # noqa: E712
            Rechnung.zahlungsstatus.in_(["offen", "teilweise"]),
        ).all()
        aktuelle = max(
            (r.mahnstufe_aktuell for r in rechnungen),
            default=0,
        )
        aktuelle = max(aktuelle, max((r.mahnstufe_aktuell for r in alle_offenen_kunde), default=0))
        stufe = _naechste_aktive_stufe(db, aktuelle)
        if not stufe:
            raise HTTPException(status_code=422, detail="Keine weitere aktive Mahnstufe vorhanden.")

    # Ab konsolidiert_ab_stufe (Standard: Stufe 2, "echte" Mahnung statt Zahlungserinnerung)
    # werden automatisch ALLE offenen Rechnungen des Kunden einbezogen - unabhängig davon,
    # welche/wie viele rechnung_ids ursprünglich übergeben wurden. Stufe 1 bleibt bewusst
    # immer 1:1 zur einzelnen Rechnung (Plan-Vorgabe).
    if stufe.stufe >= einstellungen.konsolidiert_ab_stufe:
        alle_offenen = (
            db.query(Rechnung)
            .filter(
                Rechnung.kunde_id == kunde.id,
                Rechnung.typ == "ausgang",
                Rechnung.dokument_typ == "Rechnung",
                Rechnung.ist_entwurf == False,  # noqa: E712
                Rechnung.storniert == False,  # noqa: E712
                Rechnung.zahlungsstatus.in_(["offen", "teilweise"]),
            )
            .all()
        )
        if alle_offenen:
            rechnungen = alle_offenen

    gewerblich = _kunde_ist_gewerblich(kunde)
    offener_betrag_gesamt = sum(
        (r.brutto_gesamt - r.bezahlt_betrag for r in rechnungen), Decimal("0")
    ).quantize(Q, ROUND_HALF_UP)

    mahngebuehr = Decimal("0.00")
    if stufe.mahngebuehr_aktiv:
        mahngebuehr = stufe.mahngebuehr_gewerblich if gewerblich else stufe.mahngebuehr_privat

    verzugszinsen = Decimal("0.00")
    if einstellungen.verzugszinsen_aktiv and stufe.stufe >= einstellungen.verzugszinsen_ab_stufe:
        heute = date.today()
        for r in rechnungen:
            if not r.faellig_am:
                continue
            betrag = r.brutto_gesamt - r.bezahlt_betrag
            verzugszinsen += _verzugszinsen_fuer_betrag(einstellungen, gewerblich, betrag, r.faellig_am, heute)

    return kunde, stufe, rechnungen, offener_betrag_gesamt, mahngebuehr, verzugszinsen


def _berechne_mahnung_gebuehr_only(
    db: Session, kunde_id: int, stufe_nr: Optional[int], einstellungen: MahnwesenEinstellungen,
) -> tuple[Kunde, Mahnstufe, Decimal, Decimal, list[Mahnung]]:
    """Wie _berechne_mahnung(), aber für einen Kunden OHNE offene Rechnung - reine Eskalation
    der noch offenen Mahngebühr/Verzugszinsen aus früheren Mahnungen (Kontokorrent-Konsistenz).

    KEINE neue Mahngebühr, KEINE neue Verzugszinsen-Berechnung (Nutzer-Vorgabe: Gebühr-auf-Gebühr
    ist rechtlich riskant, Zinsen laufen nach Zahlung der Hauptforderung nicht automatisch
    weiter) - trägt ausschließlich den bereits eingefrorenen Betrag weiter."""
    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    if kunde.mahnsperre_bis and kunde.mahnsperre_bis >= date.today():
        raise HTTPException(
            status_code=422,
            detail=f"Kunde hat eine Mahnsperre bis {kunde.mahnsperre_bis.strftime('%d.%m.%Y')}.",
        )

    from utils.mahngebuehr_verrechnung import _offene_mahnungen_kunde

    vorperioden_gebuehr, vorperioden_zinsen, vorperioden_mahnungen = _offene_gebuehr_vorperioden_kunde(db, kunde_id)
    if vorperioden_gebuehr <= Decimal("0.004") and vorperioden_zinsen <= Decimal("0.004"):
        raise HTTPException(status_code=422, detail="Keine offene Mahngebühr/Verzugszinsen für diesen Kunden vorhanden.")

    if stufe_nr is not None:
        stufe = db.query(Mahnstufe).filter(Mahnstufe.stufe == stufe_nr, Mahnstufe.aktiv == True).first()  # noqa: E712
        if not stufe:
            raise HTTPException(status_code=404, detail=f"Aktive Mahnstufe {stufe_nr} nicht gefunden.")
    else:
        aktuelle = max((m.stufe for m in _offene_mahnungen_kunde(db, kunde_id)), default=0)
        stufe = _naechste_aktive_stufe(db, aktuelle)
        if not stufe:
            raise HTTPException(status_code=422, detail="Keine weitere aktive Mahnstufe vorhanden.")

    return kunde, stufe, vorperioden_gebuehr, vorperioden_zinsen, vorperioden_mahnungen


def _offene_ausgangsgutschriften_kunde(db: Session, kunde_id: int) -> list[Rechnung]:
    """Offene (nicht vollständig verrechnete) Kundengutschriften eines Kunden, älteste zuerst -
    Grundlage der automatischen Gutschriften-Verrechnung vor einer Mahnung (Issue #366)."""
    return (
        db.query(Rechnung)
        .filter(
            Rechnung.kunde_id == kunde_id,
            Rechnung.typ == "ausgang",
            Rechnung.dokument_typ == "Gutschrift",
            Rechnung.ist_entwurf == False,  # noqa: E712
            Rechnung.storniert == False,  # noqa: E712
            Rechnung.zahlungsstatus.in_(["offen", "teilweise"]),
        )
        .order_by(Rechnung.datum.asc())
        .all()
    )


def _gutschrift_verrechnung_vorschau(db: Session, kunde_id: int, rechnungen: list[Rechnung]) -> Decimal:
    """Rein informative (nicht buchende) Berechnung für /vorschau: wie viel von
    offener_betrag_gesamt automatisch durch offene Kundengutschriften verrechnet würde.
    Muss side-effect-frei bleiben - /vorschau darf keine Buchung auslösen (siehe
    _berechne_mahnung()-Docstring: "Gemeinsame Berechnung für /vorschau und /erstellen")."""
    gutschriften = _offene_ausgangsgutschriften_kunde(db, kunde_id)
    if not gutschriften:
        return Decimal("0.00")
    verfuegbar = sum(
        (abs(g.brutto_gesamt - (g.bezahlt_betrag or Decimal("0"))) for g in gutschriften), Decimal("0"),
    )
    offen = sum((r.brutto_gesamt - r.bezahlt_betrag for r in rechnungen), Decimal("0"))
    return min(verfuegbar, offen).quantize(Q, ROUND_HALF_UP)


def _verrechne_offene_gutschriften_vor_mahnung(db: Session, rechnungen: list[Rechnung]) -> None:
    """Bucht die automatische Verrechnung offener Kundengutschriften gegen die mahnrelevanten
    Rechnungen (Issue #366, Nutzer-Vorgabe "automatisch mindern") - echte Buchung über
    gutschrift_verrechnen(), NICHT nur eine Anzeige-Korrektur. Nur in /erstellen aufgerufen,
    nie in _berechne_mahnung()/vorschau() (siehe _gutschrift_verrechnung_vorschau()-Docstring).
    Aktualisiert die übergebenen Rechnung-Objekte in-place (gleiche Session/Identity Map)."""
    kunde_ids = {r.kunde_id for r in rechnungen if r.kunde_id}
    for kunde_id in kunde_ids:
        gutschriften = _offene_ausgangsgutschriften_kunde(db, kunde_id)
        if not gutschriften:
            continue
        ziel_rechnungen = [
            r for r in rechnungen
            if r.kunde_id == kunde_id
            and r.dokument_typ == "Rechnung"
            and r.zahlungsstatus in ("offen", "teilweise")
        ]
        for gs in gutschriften:
            for ziel in ziel_rechnungen:
                gs_rest = abs(gs.brutto_gesamt - (gs.bezahlt_betrag or Decimal("0")))
                if gs_rest <= Decimal("0.004"):
                    break
                ziel_rest = ziel.brutto_gesamt - (ziel.bezahlt_betrag or Decimal("0"))
                if ziel_rest <= Decimal("0.004"):
                    continue
                gutschrift_verrechnen(gs.id, GutschriftVerrechnenRequest(rechnung_id=ziel.id), db)


@router.post("/vorschau", response_model=MahnungVorschauResponse)
def vorschau(data: MahnungVorschauRequest, db: Session = Depends(get_db)):
    """Berechnet Mahngebühr/Verzugszinsen für eine (ggf. konsolidierte) Mahnung, ohne zu speichern."""
    einstellungen = _get_or_create_einstellungen(db)

    if not data.rechnung_ids:
        if not data.kunde_id:
            raise HTTPException(status_code=422, detail="rechnung_ids oder kunde_id erforderlich.")
        kunde, stufe, vorperioden_gebuehr, vorperioden_zinsen, _ = _berechne_mahnung_gebuehr_only(
            db, data.kunde_id, data.stufe, einstellungen
        )
        gesamt = (vorperioden_gebuehr + vorperioden_zinsen).quantize(Q, ROUND_HALF_UP)
        return MahnungVorschauResponse(
            kunde_id=kunde.id, kunde_name=_kunde_name(kunde), stufe=stufe.stufe, bezeichnung=stufe.bezeichnung,
            positionen=[], offener_betrag_gesamt=Decimal("0.00"),
            mahngebuehr=vorperioden_gebuehr, verzugszinsen=vorperioden_zinsen,
            gebuehr_vorperioden=gesamt, gesamtforderung=gesamt,
        )

    kunde, stufe, rechnungen, offener_betrag_gesamt, mahngebuehr, verzugszinsen = _berechne_mahnung(
        db, data.rechnung_ids, data.stufe, einstellungen
    )
    vorperioden_gebuehr, vorperioden_zinsen, _ = _offene_gebuehr_vorperioden_kunde(db, kunde.id)
    heute = date.today()
    positionen = [
        MahnungVorschauPosition(
            rechnung_id=r.id,
            rechnungsnummer=r.rechnungsnummer,
            offener_betrag=(r.brutto_gesamt - r.bezahlt_betrag).quantize(Q, ROUND_HALF_UP),
            tage_ueberfaellig=max((heute - r.faellig_am).days, 0) if r.faellig_am else 0,
        )
        for r in rechnungen
    ]
    gebuehr_vorperioden = (vorperioden_gebuehr + vorperioden_zinsen).quantize(Q, ROUND_HALF_UP)
    gutschrift_verrechnung = _gutschrift_verrechnung_vorschau(db, kunde.id, rechnungen)
    offener_betrag_netto = (offener_betrag_gesamt - gutschrift_verrechnung).quantize(Q, ROUND_HALF_UP)
    return MahnungVorschauResponse(
        kunde_id=kunde.id,
        kunde_name=_kunde_name(kunde),
        stufe=stufe.stufe,
        bezeichnung=stufe.bezeichnung,
        positionen=positionen,
        offener_betrag_gesamt=offener_betrag_netto,
        mahngebuehr=(mahngebuehr + vorperioden_gebuehr).quantize(Q, ROUND_HALF_UP),
        verzugszinsen=(verzugszinsen + vorperioden_zinsen).quantize(Q, ROUND_HALF_UP),
        gebuehr_vorperioden=gebuehr_vorperioden,
        gesamtforderung=(offener_betrag_netto + mahngebuehr + verzugszinsen + gebuehr_vorperioden).quantize(Q, ROUND_HALF_UP),
        gutschrift_verrechnung=gutschrift_verrechnung,
    )


def _naechste_mahnnummer(db: Session, datum: date) -> str:
    """Mahnnummer aus dem Nummernkreis 'mahnung' (analog zu den Belegnummer-Helfern in rechnungen.py)."""
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "mahnung").first()
    if not nk:
        count = db.query(Mahnung).count()
        return f"MHN-{str(datum.year)[-2:]}{count + 1:04d}"
    if nk.reset_jaehrlich and nk.letztes_jahr and datum.year > nk.letztes_jahr:
        nk.naechste_nr = 1
    if not nk.letztes_jahr or datum.year > nk.letztes_jahr:
        nk.letztes_jahr = datum.year

    def _format(nr: int) -> str:
        year_2 = str(datum.year)[-2:]
        result = nk.format.replace("YY", year_2).replace("JJ", year_2)
        return _re.sub(r"#+", lambda m: str(nr).zfill(len(m.group())), result)

    nr = nk.naechste_nr
    nk.naechste_nr += 1
    candidate = _format(nr)
    while db.query(Mahnung).filter(Mahnung.mahnnummer == candidate).first():
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        candidate = _format(nr)
    return candidate


def _erstellen_gebuehr_only(
    db: Session, kunde_id: int, stufe_nr: Optional[int], einstellungen: MahnwesenEinstellungen,
) -> MahnungResponse:
    """Reine Eskalations-Mahnung ohne Rechnung - trägt nur die bereits eingefrorene, noch offene
    Mahngebühr/Verzugszinsen aus älteren Mahnungen weiter (Kontokorrent-Konsistenz), OHNE neue
    Gebühr oder neue Verzugszinsen (siehe _berechne_mahnung_gebuehr_only())."""
    kunde, stufe, vorperioden_gebuehr, vorperioden_zinsen, vorperioden_mahnungen = _berechne_mahnung_gebuehr_only(
        db, kunde_id, stufe_nr, einstellungen
    )
    heute = date.today()
    gesamt = (vorperioden_gebuehr + vorperioden_zinsen).quantize(Q, ROUND_HALF_UP)
    mahnung = Mahnung(
        mahnnummer=_naechste_mahnnummer(db, heute),
        kunde_id=kunde.id,
        mahnstufe_id=stufe.id,
        stufe=stufe.stufe,
        bezeichnung=stufe.bezeichnung,
        mahngebuehr=vorperioden_gebuehr,
        verzugszinsen=vorperioden_zinsen,
        uebernommene_gebuehr_vorperioden=gesamt,
        offener_betrag_gesamt=gesamt,
        status="entwurf",
    )
    db.add(mahnung)
    db.flush()
    for alte in vorperioden_mahnungen:
        alte.uebertragen_in_mahnung_id = mahnung.id

    if einstellungen.kundensperrung_aktiv:
        if (
            einstellungen.kundensperrung_sperrung_ab_stufe is not None
            and stufe.stufe >= einstellungen.kundensperrung_sperrung_ab_stufe
        ):
            kunde.mahnung_gesperrt = True
        if (
            einstellungen.kundensperrung_warnung_ab_stufe is not None
            and stufe.stufe >= einstellungen.kundensperrung_warnung_ab_stufe
        ):
            kunde.mahnung_warnung = True

    db.commit()
    db.refresh(mahnung)
    return MahnungResponse(
        id=mahnung.id, mahnnummer=mahnung.mahnnummer, kunde_id=mahnung.kunde_id,
        stufe=mahnung.stufe, bezeichnung=mahnung.bezeichnung, erstellt_am=mahnung.erstellt_am,
        versendet_am=mahnung.versendet_am, mahngebuehr=mahnung.mahngebuehr,
        verzugszinsen=mahnung.verzugszinsen,
        uebernommene_gebuehr_vorperioden=mahnung.uebernommene_gebuehr_vorperioden,
        offener_betrag_gesamt=mahnung.offener_betrag_gesamt,
        status=mahnung.status, rechnung_ids=[],
    )


@router.post("/erstellen", response_model=MahnungResponse, status_code=201)
def erstellen(data: MahnungErstellenRequest, db: Session = Depends(get_db)):
    """Legt eine Mahnung (Status: Entwurf) für eine oder mehrere Rechnungen desselben Kunden an.

    Setzt rechnungen.mahnstufe_aktuell bereits beim Entwurf hoch (nicht erst beim Versand) -
    sonst empfiehlt /faellig für dieselbe Rechnung wieder dieselbe Stufe und es entstehen
    Doppel-Entwürfe. Wird der Entwurf per DELETE verworfen, wird die Stufe zurückgesetzt.
    """
    einstellungen = _get_or_create_einstellungen(db)

    if not data.rechnung_ids:
        if not data.kunde_id:
            raise HTTPException(status_code=422, detail="rechnung_ids oder kunde_id erforderlich.")
        return _erstellen_gebuehr_only(db, data.kunde_id, data.stufe, einstellungen)

    # Offene Kundengutschriften automatisch verrechnen, BEVOR der Mahnbetrag berechnet wird
    # (Issue #366, Nutzer-Vorgabe "automatisch mindern") - reduziert rechnung.bezahlt_betrag
    # der betroffenen Rechnungen direkt in der DB, sodass _berechne_mahnung() (dieselbe
    # Funktion wie in /vorschau) den bereits geminderten Betrag automatisch korrekt liefert,
    # ohne dort selbst etwas Buchendes anfassen zu müssen. Defensiv abgesichert: schlägt die
    # Verrechnung aus einem unerwarteten Grund fehl, darf das die eigentliche Mahnungserstellung
    # nicht blockieren - dann läuft sie wie bisher ohne automatische Verrechnung weiter.
    vorab_rechnungen = db.query(Rechnung).filter(Rechnung.id.in_(data.rechnung_ids)).all()
    try:
        _verrechne_offene_gutschriften_vor_mahnung(db, vorab_rechnungen)
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Automatische Gutschriften-Verrechnung vor Mahnung fehlgeschlagen (rechnung_ids=%s)",
            data.rechnung_ids, exc_info=True,
        )

    kunde, stufe, rechnungen, offener_betrag_gesamt, mahngebuehr, verzugszinsen = _berechne_mahnung(
        db, data.rechnung_ids, data.stufe, einstellungen
    )

    # Kundenweite Übernahme offener Gebühr/Zinsen aus älteren, noch nicht übertragenen Mahnungen
    # (Abschnitt E) - siehe _offene_gebuehr_vorperioden_kunde(). Muss mit der neuen Mahnung
    # übereinstimmen, egal ob deren ursprüngliche Rechnung inzwischen bezahlt ist.
    vorperioden_gebuehr, vorperioden_zinsen, vorperioden_mahnungen = _offene_gebuehr_vorperioden_kunde(db, kunde.id)

    heute = date.today()
    mahnung = Mahnung(
        mahnnummer=_naechste_mahnnummer(db, heute),
        kunde_id=kunde.id,
        mahnstufe_id=stufe.id,
        stufe=stufe.stufe,
        bezeichnung=stufe.bezeichnung,
        mahngebuehr=(mahngebuehr + vorperioden_gebuehr).quantize(Q, ROUND_HALF_UP),
        verzugszinsen=(verzugszinsen + vorperioden_zinsen).quantize(Q, ROUND_HALF_UP),
        uebernommene_gebuehr_vorperioden=(vorperioden_gebuehr + vorperioden_zinsen).quantize(Q, ROUND_HALF_UP),
        offener_betrag_gesamt=(offener_betrag_gesamt + mahngebuehr + verzugszinsen + vorperioden_gebuehr + vorperioden_zinsen).quantize(Q, ROUND_HALF_UP),
        status="entwurf",
    )
    db.add(mahnung)
    db.flush()
    for alte in vorperioden_mahnungen:
        alte.uebertragen_in_mahnung_id = mahnung.id
    for r in rechnungen:
        db.add(MahnungRechnung(
            mahnung_id=mahnung.id,
            rechnung_id=r.id,
            offener_betrag=(r.brutto_gesamt - r.bezahlt_betrag).quantize(Q, ROUND_HALF_UP),
        ))
        if stufe.stufe > r.mahnstufe_aktuell:
            r.mahnstufe_aktuell = stufe.stufe

    # Kundensperrung (Abschnitt E) - schon beim Anlegen des Entwurfs, nicht erst beim Versand
    # (explizite Nutzer-Vorgabe). Zweistufig: eine (niedrigere) Stufe löst nur eine Warnung aus,
    # eine weitere (höhere) Stufe die harte Sperre - beide Schwellen unabhängig voneinander
    # optional und unabhängig voneinander gesetzt/geprüft (Nutzer-Vorgabe: "Wenn ich für eine
    # Mahnstufe erst eine Warnung haben möchte, möchte ich vielleicht bei der nächsten Mahnstufe
    # eine Kundensperre").
    if einstellungen.kundensperrung_aktiv:
        if (
            einstellungen.kundensperrung_sperrung_ab_stufe is not None
            and stufe.stufe >= einstellungen.kundensperrung_sperrung_ab_stufe
        ):
            kunde.mahnung_gesperrt = True
        if (
            einstellungen.kundensperrung_warnung_ab_stufe is not None
            and stufe.stufe >= einstellungen.kundensperrung_warnung_ab_stufe
        ):
            kunde.mahnung_warnung = True

    db.commit()
    db.refresh(mahnung)
    return MahnungResponse(
        id=mahnung.id, mahnnummer=mahnung.mahnnummer, kunde_id=mahnung.kunde_id,
        stufe=mahnung.stufe, bezeichnung=mahnung.bezeichnung, erstellt_am=mahnung.erstellt_am,
        versendet_am=mahnung.versendet_am, mahngebuehr=mahnung.mahngebuehr,
        verzugszinsen=mahnung.verzugszinsen,
        uebernommene_gebuehr_vorperioden=mahnung.uebernommene_gebuehr_vorperioden,
        offener_betrag_gesamt=mahnung.offener_betrag_gesamt,
        status=mahnung.status, rechnung_ids=[r.id for r in rechnungen],
    )


@router.delete("/{mahnung_id}", status_code=204)
def mahnung_loeschen(mahnung_id: int, db: Session = Depends(get_db)):
    """Löscht einen Mahnungs-Entwurf und setzt rechnungen.mahnstufe_aktuell wieder zurück.

    Nur im Status 'entwurf' möglich - eine versendete Mahnung ist ein zugestelltes Dokument
    und wird (analog zu Rechnungen) nicht gelöscht, sondern in Abschnitt E/F storniert.
    """
    mahnung = db.query(Mahnung).filter(Mahnung.id == mahnung_id).first()
    if not mahnung:
        raise HTTPException(status_code=404, detail="Mahnung nicht gefunden.")
    if mahnung.status != "entwurf":
        raise HTTPException(status_code=422, detail="Nur Entwürfe können gelöscht werden.")

    betroffene_rechnung_ids = [
        rid for (rid,) in db.query(MahnungRechnung.rechnung_id).filter(MahnungRechnung.mahnung_id == mahnung_id).all()
    ]
    kunde_id = mahnung.kunde_id
    db.delete(mahnung)
    db.flush()

    for rid in betroffene_rechnung_ids:
        rechnung = db.query(Rechnung).filter(Rechnung.id == rid).first()
        if not rechnung:
            continue
        hoechste_verbleibende = (
            db.query(Mahnung.stufe)
            .join(MahnungRechnung, MahnungRechnung.mahnung_id == Mahnung.id)
            .filter(MahnungRechnung.rechnung_id == rid)
            .order_by(Mahnung.stufe.desc())
            .first()
        )
        rechnung.mahnstufe_aktuell = hoechste_verbleibende[0] if hoechste_verbleibende else 0

    # Ohne expliziten flush() liest die folgende max_verbleibend-Abfrage noch den alten
    # mahnstufe_aktuell-Wert (Bug gefunden 2026-08-02: Rückbau der Kundensperrung lief dadurch
    # immer einen Schritt versetzt - reagierte erst auf das VORLETZTE statt das letzte Löschen).
    db.flush()

    # Kundensperrung/-warnung zurücknehmen, falls der gelöschte Entwurf der einzige Grund dafür
    # war (symmetrisch zum mahnstufe_aktuell-Reset oben) - beide Schwellen unabhängig prüfen.
    if kunde_id and (
        db.query(Kunde).filter(Kunde.id == kunde_id, (Kunde.mahnung_gesperrt == True) | (Kunde.mahnung_warnung == True)).first()  # noqa: E712
    ):
        kunde_obj = db.query(Kunde).filter(Kunde.id == kunde_id).first()
        einstellungen = _get_or_create_einstellungen(db)
        max_verbleibend = db.query(Rechnung.mahnstufe_aktuell).filter(
            Rechnung.kunde_id == kunde_id,
        ).order_by(Rechnung.mahnstufe_aktuell.desc()).first()
        max_verbleibend = max_verbleibend[0] if max_verbleibend else 0
        if kunde_obj.mahnung_gesperrt and (
            einstellungen.kundensperrung_sperrung_ab_stufe is None
            or max_verbleibend < einstellungen.kundensperrung_sperrung_ab_stufe
        ):
            kunde_obj.mahnung_gesperrt = False
        if kunde_obj.mahnung_warnung and (
            einstellungen.kundensperrung_warnung_ab_stufe is None
            or max_verbleibend < einstellungen.kundensperrung_warnung_ab_stufe
        ):
            kunde_obj.mahnung_warnung = False

    db.commit()


@router.get("/mahnungen", response_model=list[MahnungHistorieItem])
def mahnungen_liste(status: Optional[str] = None, db: Session = Depends(get_db)):
    """Historie aller Mahnungen - unabhängig von der aktuellen Fälligkeits-Warteschlange."""
    q = db.query(Mahnung)
    if status:
        q = q.filter(Mahnung.status == status)
    mahnungen = q.order_by(Mahnung.erstellt_am.desc()).all()
    if not mahnungen:
        return []

    links = db.query(MahnungRechnung).filter(MahnungRechnung.mahnung_id.in_([m.id for m in mahnungen])).all()
    rechnung_ids_by_mahnung: dict[int, list[int]] = {}
    for link in links:
        rechnung_ids_by_mahnung.setdefault(link.mahnung_id, []).append(link.rechnung_id)
    alle_rechnung_ids = {rid for ids in rechnung_ids_by_mahnung.values() for rid in ids}
    rechnungen_by_id = {r.id: r for r in db.query(Rechnung).filter(Rechnung.id.in_(alle_rechnung_ids)).all()}
    kunden_by_id = {
        k.id: k for k in db.query(Kunde).filter(Kunde.id.in_({m.kunde_id for m in mahnungen if m.kunde_id})).all()
    }

    ergebnisse = []
    for m in mahnungen:
        rids = rechnung_ids_by_mahnung.get(m.id, [])
        nummern = ", ".join(
            rechnungen_by_id[rid].rechnungsnummer for rid in rids
            if rid in rechnungen_by_id and rechnungen_by_id[rid].rechnungsnummer
        )
        kunde = kunden_by_id.get(m.kunde_id)
        ergebnisse.append(MahnungHistorieItem(
            id=m.id, mahnnummer=m.mahnnummer, kunde_id=m.kunde_id, stufe=m.stufe,
            bezeichnung=m.bezeichnung, erstellt_am=m.erstellt_am, versendet_am=m.versendet_am,
            mahngebuehr=m.mahngebuehr, verzugszinsen=m.verzugszinsen,
            mahngebuehr_bezahlt=m.mahngebuehr_bezahlt, verzugszinsen_bezahlt=m.verzugszinsen_bezahlt,
            uebernommene_gebuehr_vorperioden=m.uebernommene_gebuehr_vorperioden,
            uebertragen_in_mahnung_id=m.uebertragen_in_mahnung_id,
            offener_betrag_gesamt=m.offener_betrag_gesamt, status=m.status, rechnung_ids=rids,
            kunde_name=_kunde_name(kunde),
            kunde_email=kunde.email if kunde else None,
            rechnungsnummern=nummern,
        ))
    return ergebnisse


# ---------------------------------------------------------------------------
# Mahnungs-PDF (Abschnitt C)
# ---------------------------------------------------------------------------

_STANDARD_MAHNTEXT = (
    "Sehr geehrte Damen und Herren,\n\n"
    "für die unten aufgeführte(n) Rechnung(en) konnten wir bislang keinen Zahlungseingang "
    "feststellen. Bitte begleichen Sie den offenen Betrag umgehend.\n\n"
    "Falls Sie bereits gezahlt haben, betrachten Sie dieses Schreiben als gegenstandslos.\n\n"
    "Mit freundlichen Grüßen"
)


def _euro_str(v) -> str:
    d = Decimal(str(v or 0))
    s = f"{abs(d):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"−{s}" if d < 0 else s


def _mahntext_rendern(
    vorlage: Optional[str], kunde: Kunde, mahnung: Mahnung, rechnungsnummern: str,
    offener_betrag_gesamt: Decimal, gesamtforderung: Decimal, datum: date,
) -> str:
    text = vorlage or _STANDARD_MAHNTEXT
    ersetzungen = {
        "{rechnungsnummer}": rechnungsnummern,
        "{offener_betrag}": _euro_str(offener_betrag_gesamt),
        "{mahngebuehr}": _euro_str(mahnung.mahngebuehr),
        "{verzugszinsen}": _euro_str(mahnung.verzugszinsen),
        "{gesamtforderung}": _euro_str(gesamtforderung),
        "{bezeichnung}": mahnung.bezeichnung or "",
        "{stufe}": str(mahnung.stufe),
        "{kunde}": _kunde_name(kunde),
        "{firmenname}": kunde.firmenname or "",
        "{datum}": datum.strftime("%d.%m.%Y"),
    }
    for platzhalter, wert in ersetzungen.items():
        text = text.replace(platzhalter, wert)
    return text


def mahnung_pdf_bytes(db: Session, mahnung: Mahnung, nur_ansehen: bool = False) -> tuple[bytes, str]:
    """Erzeugt das Mahnungs-PDF und gibt (bytes, dateiname) zurück.

    nur_ansehen=True: reine Vorschau, Status bleibt unverändert (analog rechnungen.py
    ?nur_ansehen=true). Sonst gilt die Mahnung ab hier als zugestellt - GET /pdf (Drucken/
    Ansehen-Klick ohne den Parameter) sowie der Mail-Versand (api/mail.py) laufen beide
    hierüber, damit "entwurf" konsistent zu "versendet" wird, sobald der Entwurf das
    erste Mal wirklich das Haus verlässt (Feedback: ein geöffneter/gedruckter Entwurf
    darf danach nicht mehr folgenlos gelöscht werden können).
    """
    kunde = db.query(Kunde).filter(Kunde.id == mahnung.kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    unt = db.query(Unternehmen).first()
    unt_dict = {c.name: getattr(unt, c.name) for c in unt.__table__.columns} if unt else {}

    links = db.query(MahnungRechnung).filter(MahnungRechnung.mahnung_id == mahnung.id).all()
    rechnungen_by_id = {
        r.id: r for r in db.query(Rechnung).filter(Rechnung.id.in_([l.rechnung_id for l in links])).all()
    }
    positionen = []
    for link in links:
        r = rechnungen_by_id.get(link.rechnung_id)
        positionen.append({
            "rechnungsnummer": r.rechnungsnummer if r else None,
            "rechnungsdatum": str(r.datum) if r and r.datum else None,
            "faellig_am": str(r.faellig_am) if r and r.faellig_am else None,
            "offener_betrag": link.offener_betrag,
        })

    offener_betrag_gesamt = sum((p["offener_betrag"] or Decimal("0")) for p in positionen)
    gesamtforderung = offener_betrag_gesamt + (mahnung.mahngebuehr or 0) + (mahnung.verzugszinsen or 0)
    rechnungsnummern = ", ".join(p["rechnungsnummer"] for p in positionen if p["rechnungsnummer"])

    stufe_obj = db.query(Mahnstufe).filter(Mahnstufe.id == mahnung.mahnstufe_id).first()
    mahntext = _mahntext_rendern(
        stufe_obj.text_vorlage if stufe_obj else None, kunde, mahnung, rechnungsnummern,
        offener_betrag_gesamt, gesamtforderung, mahnung.erstellt_am.date(),
    )

    pdf_bytes = erstelle_mahnung_pdf(
        unternehmen=unt_dict,
        kunde=kunde,
        mahnnummer=mahnung.mahnnummer or "",
        bezeichnung=mahnung.bezeichnung or "",
        datum=str(mahnung.erstellt_am.date()),
        mahntext=mahntext,
        positionen=positionen,
        offener_betrag_gesamt=offener_betrag_gesamt,
        mahngebuehr=mahnung.mahngebuehr,
        verzugszinsen=mahnung.verzugszinsen,
        gebuehr_vorperioden=mahnung.uebernommene_gebuehr_vorperioden,
    )

    if not nur_ansehen and mahnung.status == "entwurf":
        mahnung.status = "versendet"
        mahnung.versendet_am = datetime.now()
        db.commit()

    dateiname = f"{mahnung.mahnnummer or 'Mahnung'}.pdf"
    return pdf_bytes, dateiname


def sammle_mahnung_anhaenge(db: Session, mahnung: Mahnung) -> list[tuple[bytes, str]]:
    """Zusätzliche Dokumentanhänge für den Mail-Versand dieser Mahnung, je nach Konfiguration
    ihrer Mahnstufe (Migration 137, Nutzer-Feedback: "Unter Einstellungen will ich für jede
    Mahnstufe festlegen können welche Dokumente ich anhängen möchte. Rechnung, Bisherige
    Mahnungen, Kontokorrent ab erste gemahnte Rechnung."). Rein additiv zum Haupt-PDF, jeder
    Anhang-Typ läuft in einem eigenen try/except - ein fehlgeschlagener Zusatzanhang darf den
    eigentlichen Mahnungs-Versand nie verhindern."""
    stufe = db.query(Mahnstufe).filter(Mahnstufe.id == mahnung.mahnstufe_id).first()
    if not stufe or not mahnung.kunde_id:
        return []
    anhaenge: list[tuple[bytes, str]] = []

    if stufe.anhang_rechnung:
        from api.rechnungen import rechnung_als_pdf
        links = db.query(MahnungRechnung.rechnung_id).filter(MahnungRechnung.mahnung_id == mahnung.id).all()
        for (rid,) in links:
            r = db.query(Rechnung).filter(Rechnung.id == rid).first()
            if not r:
                continue
            try:
                resp = rechnung_als_pdf(rechnung_id=rid, db=db)
                nr = (r.rechnungsnummer or str(rid)).replace("/", "-").replace(" ", "_")
                anhaenge.append((resp.body, f"Rechnung_{nr}.pdf"))
            except Exception:
                import logging
                logging.getLogger(__name__).warning("Mahnung-Anhang Rechnung %s fehlgeschlagen", rid, exc_info=True)

    if stufe.anhang_bisherige_mahnungen:
        bisherige = (
            db.query(Mahnung)
            .filter(
                Mahnung.kunde_id == mahnung.kunde_id, Mahnung.status == "versendet",
                Mahnung.id != mahnung.id, Mahnung.erstellt_am < mahnung.erstellt_am,
            )
            .order_by(Mahnung.erstellt_am)
            .all()
        )
        for alte in bisherige:
            try:
                pdf_bytes, dateiname = mahnung_pdf_bytes(db, alte, nur_ansehen=True)
                anhaenge.append((pdf_bytes, dateiname))
            except Exception:
                import logging
                logging.getLogger(__name__).warning("Mahnung-Anhang bisherige Mahnung %s fehlgeschlagen", alte.id, exc_info=True)

    if stufe.anhang_kontokorrent:
        try:
            from api.kunden import _kontokorrent_bewegungen
            kunde = db.query(Kunde).filter(Kunde.id == mahnung.kunde_id).first()
            if kunde:
                erste_mahnung = (
                    db.query(Mahnung)
                    .filter(Mahnung.kunde_id == mahnung.kunde_id, Mahnung.status == "versendet")
                    .order_by(Mahnung.erstellt_am)
                    .first()
                )
                von = erste_mahnung.erstellt_am.date() if erste_mahnung else mahnung.erstellt_am.date()
                heute = date.today()
                bewegungen, partner_name = _kontokorrent_bewegungen(kunde.id, von, heute, db)
                unt_dict = _unt_dict(db)
                adresse = [z for z in [
                    " ".join(filter(None, [kunde.strasse, kunde.hausnummer])),
                    " ".join(filter(None, [kunde.plz, kunde.ort])),
                ] if z.strip()]
                kk_bytes = erstelle_kontokorrent_pdf(
                    unternehmen=unt_dict, partner_name=partner_name, von=str(von), bis=str(heute),
                    bewegungen=bewegungen, partner_nr=kunde.debitor_nr, partner_adresse=adresse,
                    nr_label="Debitorennr.",
                )
                anhaenge.append((kk_bytes, f"Kontokorrent_{partner_name.replace(' ', '_')}.pdf"))
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Mahnung-Anhang Kontokorrent fehlgeschlagen (Mahnung %s)", mahnung.id, exc_info=True)

    return anhaenge


@router.get("/{mahnung_id}/pdf")
def mahnung_pdf(mahnung_id: int, nur_ansehen: bool = False, download: bool = False, db: Session = Depends(get_db)):
    """Mahnungs-PDF – inline (Standard) oder als Datei-Download für den Mail-Ohne-SMTP-Fallback.

    download=True setzt bewusst NICHT nur_ansehen - der Download dient dazu, die PDF manuell an
    eine Mail anzuhängen, gilt also genauso als "verlässt das Haus" wie Drucken/SMTP-Versand.
    """
    mahnung = db.query(Mahnung).filter(Mahnung.id == mahnung_id).first()
    if not mahnung:
        raise HTTPException(status_code=404, detail="Mahnung nicht gefunden.")
    pdf_bytes, dateiname = mahnung_pdf_bytes(db, mahnung, nur_ansehen=nur_ansehen)
    disposition = "attachment" if download else "inline"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{dateiname}"'},
    )


# ---------------------------------------------------------------------------
# Inkasso-Paket (Abschnitt E)
# ---------------------------------------------------------------------------

def _unt_dict(db: Session) -> dict:
    unt = db.query(Unternehmen).first()
    return {c.name: getattr(unt, c.name) for c in unt.__table__.columns} if unt else {}


def generate_inkasso_zip(db: Session, kunde_id: int) -> tuple[bytes, str]:
    """Baut das Inkasso-Paket eines Kunden: Deckblatt, Kontokorrent, alle offenen Rechnungs-PDFs
    und alle versendeten Mahnungs-PDFs, gebündelt als ZIP. Rein lesend (nur_ansehen bei den
    Mahnungs-PDFs, keine Status-/Archiv-Änderung bei den Rechnungs-PDFs außer dem normalen
    Erstarchivierungs-Fall - identisch zum regulären PDF-Abruf, siehe rechnung_als_pdf())."""
    from api.kunden import _kontokorrent_bewegungen
    from api.rechnungen import rechnung_als_pdf

    kunde = db.query(Kunde).filter(Kunde.id == kunde_id).first()
    if not kunde:
        raise HTTPException(status_code=404, detail="Kunde nicht gefunden.")
    kunde_name = _kunde_name(kunde)

    offene_rechnungen = (
        db.query(Rechnung)
        .filter(
            Rechnung.kunde_id == kunde_id,
            Rechnung.typ == "ausgang",
            Rechnung.dokument_typ == "Rechnung",
            Rechnung.ist_entwurf == False,  # noqa: E712
            Rechnung.storniert == False,  # noqa: E712
            Rechnung.zahlungsstatus != "bezahlt",
        )
        .order_by(Rechnung.datum)
        .all()
    )

    versendete_mahnungen = (
        db.query(Mahnung)
        .filter(Mahnung.kunde_id == kunde_id, Mahnung.status == "versendet")
        .order_by(Mahnung.erstellt_am)
        .all()
    )
    if not versendete_mahnungen:
        raise HTTPException(
            status_code=404,
            detail="Für diesen Kunden wurde noch keine Mahnung versendet - ein Inkasso-Paket ist erst danach sinnvoll.",
        )
    # Kunde ohne offene Rechnung, aber noch offener Mahngebühr (Kontokorrent-Konsistenz,
    # Abschnitt E) - Inkasso-Paket bleibt trotzdem nutzbar, nur ohne Rechnungs-PDFs.
    if not offene_rechnungen and not any(
        (m.mahngebuehr - m.mahngebuehr_bezahlt) + (m.verzugszinsen - m.verzugszinsen_bezahlt) > Decimal("0.004")
        for m in versendete_mahnungen
    ):
        raise HTTPException(status_code=404, detail="Keine offenen Rechnungen oder Mahngebühr für ein Inkasso-Paket vorhanden.")

    heute = date.today()
    unt_dict = _unt_dict(db)

    # Kontokorrent (ab ältester offener Rechnung bzw. ältester Mahnung bis heute)
    von = min(r.datum for r in offene_rechnungen) if offene_rechnungen else min(
        (m.erstellt_am.date() for m in versendete_mahnungen), default=heute
    )
    bewegungen, partner_name = _kontokorrent_bewegungen(kunde_id, von, heute, db)
    adresse = [z for z in [
        " ".join(filter(None, [kunde.strasse, kunde.hausnummer])),
        " ".join(filter(None, [kunde.plz, kunde.ort])),
    ] if z.strip()]
    kontokorrent_bytes = erstelle_kontokorrent_pdf(
        unternehmen=unt_dict, partner_name=partner_name, von=str(von), bis=str(heute),
        bewegungen=bewegungen, partner_nr=kunde.debitor_nr, partner_adresse=adresse,
        nr_label="Debitorennr.",
    )

    # Rechnungs-PDFs (identische Erzeugung wie regulärer Einzel-Abruf - Original-Archiv/Kopie-Stempel greift)
    rechnung_pdfs: list[tuple[str, bytes]] = []
    rechnungen_deckblatt: list[dict] = []
    for r in offene_rechnungen:
        resp = rechnung_als_pdf(rechnung_id=r.id, db=db)
        nr = (r.rechnungsnummer or str(r.id)).replace("/", "-").replace(" ", "_")
        rechnung_pdfs.append((f"rechnungen/{nr}.pdf", resp.body))
        rechnungen_deckblatt.append({
            "rechnungsnummer": r.rechnungsnummer,
            "datum": str(r.datum),
            "faellig_am": str(r.faellig_am) if r.faellig_am else None,
            "brutto_gesamt": r.brutto_gesamt,
            "offener_betrag": r.brutto_gesamt - (r.bezahlt_betrag or Decimal("0")),
            "tage_ueberfaellig": (heute - r.faellig_am).days if r.faellig_am else "—",
        })

    # Mahnungs-PDFs (nur_ansehen=True - reiner Nachdruck fürs Paket, keine Statusänderung nötig,
    # die Mahnungen sind ohnehin schon versendet)
    mahnung_pdfs: list[tuple[str, bytes]] = []
    mahnungen_deckblatt: list[dict] = []
    for m in versendete_mahnungen:
        pdf_bytes, dateiname = mahnung_pdf_bytes(db, m, nur_ansehen=True)
        mahnung_pdfs.append((f"mahnungen/{dateiname}", pdf_bytes))
        mahnungen_deckblatt.append({
            "mahnnummer": m.mahnnummer,
            "bezeichnung": m.bezeichnung,
            "stufe": m.stufe,
            "versendet_am": str(m.versendet_am.date()) if m.versendet_am else None,
            "gesamtforderung": (m.offener_betrag_gesamt or Decimal("0")) + (m.mahngebuehr or Decimal("0")) + (m.verzugszinsen or Decimal("0")),
        })

    dateiliste = ["00_Deckblatt.pdf", "01_Kontokorrent.pdf"] + [n for n, _ in rechnung_pdfs] + [n for n, _ in mahnung_pdfs]
    deckblatt_bytes = erstelle_inkasso_deckblatt_pdf(
        unternehmen=unt_dict, kunde_name=kunde_name, erstellt_am=heute.strftime("%d.%m.%Y"),
        offene_rechnungen=rechnungen_deckblatt, mahnungen=mahnungen_deckblatt, dateiliste=dateiliste,
    )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("00_Deckblatt.pdf", deckblatt_bytes)
        zf.writestr("01_Kontokorrent.pdf", kontokorrent_bytes)
        for name, data in rechnung_pdfs:
            zf.writestr(name, data)
        for name, data in mahnung_pdfs:
            zf.writestr(name, data)

    dateiname = f"Inkasso_{kunde_name.replace(' ', '_')}_{heute.isoformat()}.zip"
    return zip_buffer.getvalue(), dateiname


@router.get("/kunden/{kunde_id}/inkasso-paket")
def inkasso_paket(kunde_id: int, db: Session = Depends(get_db)):
    """ZIP-Download: Deckblatt, Kontokorrent, alle offenen Rechnungs-PDFs und alle versendeten
    Mahnungs-PDFs eines Kunden - fertig zusammengestellte Unterlagen für Inkassobüro/Anwalt."""
    zip_bytes, dateiname = generate_inkasso_zip(db, kunde_id)
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )


# ---------------------------------------------------------------------------
# Abschnitt F: Automatisierung (opt-in, Startup-Hook analog api/wiederkehrend.py)
# ---------------------------------------------------------------------------

_MAIL_BETREFF_VORLAGE = "{bezeichnung} – Rechnung {rechnungsnummer}"
_MAIL_TEXT_VORLAGE = (
    "Guten Tag {kunde},\n\nanbei erhalten Sie unser Schreiben „{bezeichnung}\" zu Rechnung {rechnungsnummer}.\n\n"
    "Bitte entnehmen Sie die Details dem beigefügten PDF.\n\nMit freundlichen Grüßen\n{firmenname}"
)


def _mail_platzhalter(vorlage: str, bezeichnung: str, rechnungsnummern: str, kunde_name: str, firmenname: str) -> str:
    return (
        vorlage.replace("{bezeichnung}", bezeichnung or "Mahnung")
        .replace("{rechnungsnummer}", rechnungsnummern or "—")
        .replace("{kunde}", kunde_name)
        .replace("{firmenname}", firmenname)
    )


def automatik_lauf(db: Session) -> list[dict]:
    """Wird beim App-Start aufgerufen (main.py, analog api.wiederkehrend.pruefen_intern()) - legt
    bei automation_modus 'halb'/'voll' automatisch fällige Mahnungs-Entwürfe an. Bei 'manuell'
    (Default) passiert nichts. Jeder Fall läuft einzeln in einem eigenen try/except - ein Fehler
    bei einem Kunden bricht die anderen nicht ab und blockiert nie den App-Start.

    'voll' versendet zusätzlich ALLE offenen Entwürfe per Mail - nicht nur die in diesem Lauf neu
    erzeugten, sondern auch bereits vorher bestehende (z.B. während einer früheren Phase mit
    'manuell'/'halb' manuell angelegte, aber nie verschickte Entwürfe). Eine Umstellung auf 'voll'
    holt solche liegen gebliebenen Entwürfe also nach (Nutzer-Vorgabe: "Bestehende Entwürfe können
    versendet werden"). Bereits VERSENDETE Mahnungen werden nie erneut angefasst - der Versand
    läuft ausschließlich über `status == 'entwurf'`, das per DB-Query ermittelt wird, nicht über
    eine In-Memory-Liste der in diesem Lauf neu erzeugten IDs (Nutzer-Vorgabe: "Es darf nur nichts
    noch mal versendet werden was bereits gesendet ist" - genau dieser Status ist die Garantie
    dafür, unabhängig davon wann/wie der Entwurf entstanden ist)."""
    einstellungen = _get_or_create_einstellungen(db)
    if not einstellungen.aktiv or einstellungen.automation_modus == "manuell":
        return []

    unternehmen = db.query(Unternehmen).first()
    # "voll" darf laut einstellungen_put() ohnehin nur mit smtp_aktiv=True gesetzt werden - die
    # Prüfung hier ist zusätzliche Absicherung für den Fall, dass SMTP NACH dem Aktivieren wieder
    # deaktiviert wurde (Automatik läuft dann weiter, versendet aber nichts mehr, kein Fehler).
    kann_mailen = bool(
        einstellungen.automation_modus == "voll" and einstellungen.versand_mail
        and unternehmen and unternehmen.smtp_aktiv
    )

    ergebnisse: list[dict] = []
    kunden = kunden_uebersicht(db)
    for kunde in kunden:
        # Zahlungserinnerung (Stufe 1, immer 1:1 pro Rechnung) - unabhängig von aktionsfaellig
        # (das bezieht sich nur auf echte Mahnstufen ab konsolidiert_ab_stufe, siehe
        # kunden_uebersicht()).
        for rm in kunde.rechnungen:
            if not rm.zahlungserinnerung_faellig:
                continue
            try:
                mahnung = erstellen(MahnungErstellenRequest(rechnung_ids=[rm.rechnung_id]), db)
                ergebnisse.append({"kunde_id": kunde.kunde_id, "mahnung_id": mahnung.id, "stufe": mahnung.stufe, "neu_angelegt": True})
            except Exception:
                import logging
                logging.getLogger(__name__).warning("Mahnwesen-Automatik: Zahlungserinnerung für Rechnung %s fehlgeschlagen", rm.rechnung_id, exc_info=True)

        if not kunde.aktionsfaellig:
            continue
        try:
            if kunde.nur_offene_gebuehr:
                mahnung = erstellen(MahnungErstellenRequest(rechnung_ids=[], kunde_id=kunde.kunde_id, stufe=kunde.naechste_stufe), db)
            else:
                mahnung = erstellen(MahnungErstellenRequest(rechnung_ids=[kunde.rechnungen[0].rechnung_id], stufe=kunde.naechste_stufe), db)
            ergebnisse.append({"kunde_id": kunde.kunde_id, "mahnung_id": mahnung.id, "stufe": mahnung.stufe, "neu_angelegt": True})
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Mahnwesen-Automatik: Mahnstufe für Kunde %s fehlgeschlagen", kunde.kunde_id, exc_info=True)

    if not kann_mailen:
        return ergebnisse

    # Alle offenen Entwürfe versenden - neu erzeugte UND bereits vorher bestehende. status prüft
    # dabei live gegen die DB, nicht gegen eine In-Memory-Liste, damit garantiert nichts bereits
    # Versendetes erneut angefasst wird.
    from api.mail import mail_senden, MailSendenRequest

    offene_entwuerfe = db.query(Mahnung).filter(Mahnung.status == "entwurf").all()
    for mahnung in offene_entwuerfe:
        kunde_obj = db.query(Kunde).filter(Kunde.id == mahnung.kunde_id).first()
        if not kunde_obj or not kunde_obj.email:
            continue
        try:
            links = db.query(MahnungRechnung.rechnung_id).filter(MahnungRechnung.mahnung_id == mahnung.id).all()
            nummern = ", ".join(
                r.rechnungsnummer for r in db.query(Rechnung).filter(Rechnung.id.in_([rid for (rid,) in links])).all()
                if r.rechnungsnummer
            )
            kunde_name = _kunde_name(kunde_obj)
            betreff = _mail_platzhalter(_MAIL_BETREFF_VORLAGE, mahnung.bezeichnung or "", nummern, kunde_name, unternehmen.firmenname or "")
            text = _mail_platzhalter(_MAIL_TEXT_VORLAGE, mahnung.bezeichnung or "", nummern, kunde_name, unternehmen.firmenname or "")
            mail_senden(MailSendenRequest(an=kunde_obj.email, betreff=betreff, text=text, mahnung_id=mahnung.id), db)
            treffer = next((e for e in ergebnisse if e["mahnung_id"] == mahnung.id), None)
            if treffer:
                treffer["versendet"] = True
            else:
                ergebnisse.append({"kunde_id": mahnung.kunde_id, "mahnung_id": mahnung.id, "stufe": mahnung.stufe, "neu_angelegt": False, "versendet": True})
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Mahnwesen-Automatik: Mail-Versand für Mahnung %s fehlgeschlagen", mahnung.id, exc_info=True)

    return ergebnisse
