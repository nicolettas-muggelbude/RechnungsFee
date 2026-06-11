"""
Wiederkehrende Ausgangsrechnungen (Abo-Vorlagen).

Beim App-Start prüft _pruefen_intern() ob fällige Vorlagen existieren und
legt automatisch Rechnungs-Entwürfe an. Preisabgleich: hat eine Position
eine artikel_id, wird vk_netto aus dem Artikelstamm geholt; weicht der
gespeicherte Preis ab, bekommt der Entwurf den aktuellen Preis und die
Abweichung wird als Preisaenderung zurückgegeben.
"""

import calendar
import hashlib
import json
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import (
    Artikel,
    Beleg,
    Nummernkreis,
    Rechnung,
    Rechnungsposition,
    Rechnungsvorlage,
    Unternehmen,
)
from api.rechnungen import APP_DATA_DIR, BELEG_DIR, ERLAUBTE_MIME_TYPES

router = APIRouter(prefix="/api/wiederkehrend", tags=["Wiederkehrend"])

Q = Decimal("0.01")
INTERVALLE = {"monatlich", "quartalsweise", "jaehrlich"}


# ---------------------------------------------------------------------------
# Pydantic-Schemas
# ---------------------------------------------------------------------------

class VorlagePosition(BaseModel):
    beschreibung: str
    menge: str = "1.000"
    einheit: str = "Stück"
    netto: str
    ust_satz: str = "0.00"
    artikel_id: Optional[int] = None
    kategorie_id: Optional[int] = None


class VorlageCreate(BaseModel):
    bezeichnung: str
    intervall: str
    naechstes_datum: date
    aktiv: bool = True
    kunde_id: Optional[int] = None
    zahlungsziel_tage: Optional[int] = None
    notizen: Optional[str] = None
    positionen: list[VorlagePosition] = []
    auftrag_id: Optional[int] = None


class VorlageUpdate(BaseModel):
    bezeichnung: Optional[str] = None
    intervall: Optional[str] = None
    naechstes_datum: Optional[date] = None
    aktiv: Optional[bool] = None
    kunde_id: Optional[int] = None
    zahlungsziel_tage: Optional[int] = None
    notizen: Optional[str] = None
    positionen: Optional[list[VorlagePosition]] = None
    auftrag_id: Optional[int] = None


class Preisaenderung(BaseModel):
    beschreibung: str
    artikel_id: int
    preis_vorlage: str
    preis_aktuell: str


class EntwurfErgebnis(BaseModel):
    vorlage_id: int
    vorlage_bezeichnung: str
    rechnung_id: int
    rechnungsnummer: str
    preisaenderungen: list[Preisaenderung]


class VorlageResponse(BaseModel):
    id: int
    bezeichnung: str
    intervall: str
    naechstes_datum: date
    aktiv: bool
    kunde_id: Optional[int]
    kunde_name: Optional[str]
    zahlungsziel_tage: Optional[int]
    notizen: Optional[str]
    positionen: list[VorlagePosition]
    letzte_erstellung: Optional[date]
    erstellte_rechnungen: int
    erstellt_am: datetime
    auftrag_id: Optional[int]
    auftrag_nr: Optional[str]
    beleg_id: Optional[int]
    beleg_name: Optional[str]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _naechstes_datum(von: date, intervall: str) -> date:
    """Rückt naechstes_datum um ein Intervall vor (ohne dateutil-Abhängigkeit)."""
    if intervall in ("monatlich", "quartalsweise"):
        monate = 1 if intervall == "monatlich" else 3
        total = von.month + monate
        jahr = von.year + (total - 1) // 12
        monat = ((total - 1) % 12) + 1
        tag = min(von.day, calendar.monthrange(jahr, monat)[1])
        return date(jahr, monat, tag)
    elif intervall == "jaehrlich":
        try:
            return von.replace(year=von.year + 1)
        except ValueError:  # 29. Feb im Nicht-Schaltjahr
            return date(von.year + 1, 2, 28)
    return von


def _belegnr_aus_format(fmt: str, datum: date, nr: int) -> str:
    s = fmt.replace("YYYY", str(datum.year)).replace("YY", str(datum.year)[-2:])
    stellen = s.count("#")
    if stellen:
        s = s.replace("#" * stellen, str(nr).zfill(stellen))
    return s


def _naechste_rechnungsnr(datum: date, db: Session) -> str:
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "rechnung_ausgang").first()
    if nk:
        if nk.reset_jaehrlich and nk.letztes_jahr and nk.letztes_jahr != datum.year:
            nk.naechste_nr = 1
        nk.letztes_jahr = datum.year
        nr = nk.naechste_nr
        nk.naechste_nr += 1
        return f"RE-{_belegnr_aus_format(nk.format, datum, nr)}"
    count = db.query(Rechnung).filter(Rechnung.typ == "ausgang").count()
    return f"RE-{str(datum.year)[-2:]}{count + 1:04d}"


def _kunde_name(vorlage: Rechnungsvorlage) -> Optional[str]:
    if not vorlage.kunde:
        return None
    teile = []
    if vorlage.kunde.firmenname:
        teile.append(vorlage.kunde.firmenname)
    if vorlage.kunde.vorname or vorlage.kunde.nachname:
        teile.append(f"{vorlage.kunde.vorname or ''} {vorlage.kunde.nachname or ''}".strip())
    return ", ".join(t for t in teile if t) or None


def _to_response(v: Rechnungsvorlage) -> VorlageResponse:
    positionen = [VorlagePosition(**p) for p in json.loads(v.positionen_json or "[]")]
    return VorlageResponse(
        id=v.id,
        bezeichnung=v.bezeichnung,
        intervall=v.intervall,
        naechstes_datum=v.naechstes_datum,
        aktiv=v.aktiv,
        kunde_id=v.kunde_id,
        kunde_name=_kunde_name(v),
        zahlungsziel_tage=v.zahlungsziel_tage,
        notizen=v.notizen,
        positionen=positionen,
        letzte_erstellung=v.letzte_erstellung,
        erstellte_rechnungen=v.erstellte_rechnungen,
        erstellt_am=v.erstellt_am,
        auftrag_id=v.auftrag_id,
        auftrag_nr=v.auftrag.rechnungsnummer if v.auftrag else None,
        beleg_id=v.beleg_id,
        beleg_name=v.beleg.original_name if v.beleg else None,
    )


def _set_auftrag_laufend(auftrag: Rechnung) -> None:
    """Setzt Auftrag-Status auf 'laufend' wenn noch nicht abgeschlossen/storniert."""
    if auftrag.auftrag_status not in ("abgeschlossen", "storniert"):
        auftrag.auftrag_status = "laufend"


def _revert_auftrag_status(auftrag_id: int, db: Session) -> None:
    """Setzt Auftrag-Status zurück wenn keine aktiven Vorlagen mehr existieren."""
    hat_aktive = db.query(Rechnungsvorlage).filter(
        Rechnungsvorlage.auftrag_id == auftrag_id,
        Rechnungsvorlage.aktiv == True,  # noqa: E712
    ).first()
    if hat_aktive:
        return
    auftrag = db.query(Rechnung).filter(Rechnung.id == auftrag_id).first()
    if auftrag and auftrag.auftrag_status == "laufend":
        auftrag.auftrag_status = "in_bearbeitung"


def _erstelle_entwurf(vorlage: Rechnungsvorlage, db: Session) -> tuple[int, str, list[dict]]:
    """Erstellt Rechnungs-Entwurf aus Vorlage. Gibt (id, nummer, preisaenderungen) zurück."""
    unt = db.query(Unternehmen).first()
    ist_kleinunternehmer = unt.ist_kleinunternehmer if unt else False
    zt = vorlage.zahlungsziel_tage
    if zt is None and unt:
        zt = int(getattr(unt, "standard_zahlungsziel", 14) or 14)

    rechnungsdatum = vorlage.naechstes_datum
    rechnungsnummer = _naechste_rechnungsnr(rechnungsdatum, db)

    rechnung = Rechnung(
        typ="ausgang",
        rechnungsnummer=rechnungsnummer,
        datum=rechnungsdatum,
        faellig_am=rechnungsdatum + timedelta(days=zt) if zt else None,
        kunde_id=vorlage.kunde_id,
        notizen=vorlage.notizen,
        ist_entwurf=True,
        dokument_typ="Rechnung",
        bezahlt=False,
        bezahlt_betrag=Decimal("0.00"),
        zahlungsstatus="offen",
        netto_gesamt=Decimal("0.00"),
        ust_gesamt=Decimal("0.00"),
        brutto_gesamt=Decimal("0.00"),
    )
    db.add(rechnung)
    db.flush()

    positionen_raw: list[dict] = json.loads(vorlage.positionen_json or "[]")
    preisaenderungen: list[dict] = []
    netto_sum = Decimal("0.00")
    ust_sum = Decimal("0.00")

    for i, p in enumerate(positionen_raw, start=1):
        netto = Decimal(str(p.get("netto", "0"))).quantize(Q, ROUND_HALF_UP)
        ust_satz = Decimal(str(p.get("ust_satz", "0")))
        artikel_id = p.get("artikel_id")

        # Preisabgleich mit aktuellem Artikelstamm
        if artikel_id:
            art = db.query(Artikel).filter(Artikel.id == artikel_id).first()
            if art and art.vk_netto.quantize(Q) != netto:
                preisaenderungen.append({
                    "beschreibung": p.get("beschreibung", ""),
                    "artikel_id": artikel_id,
                    "preis_vorlage": str(netto),
                    "preis_aktuell": str(art.vk_netto),
                })
                netto = art.vk_netto.quantize(Q, ROUND_HALF_UP)
                ust_satz = art.steuersatz

        if ist_kleinunternehmer or ust_satz == 0:
            ust_betrag = Decimal("0.00")
            brutto = netto
            ust_satz = Decimal("0")
        else:
            ust_betrag = (netto * ust_satz / 100).quantize(Q, ROUND_HALF_UP)
            brutto = netto + ust_betrag

        menge = Decimal(str(p.get("menge", "1"))).quantize(Decimal("0.001"), ROUND_HALF_UP)
        db.add(Rechnungsposition(
            rechnung_id=rechnung.id,
            artikel_id=artikel_id,
            kategorie_id=p.get("kategorie_id"),
            position_nr=i,
            beschreibung=p.get("beschreibung", ""),
            menge=menge,
            einheit=p.get("einheit", "Stück"),
            netto=netto,
            ust_satz=ust_satz,
            ust_betrag=ust_betrag,
            brutto=brutto,
        ))
        netto_sum += netto * menge
        ust_sum += ust_betrag * menge

    rechnung.netto_gesamt = netto_sum.quantize(Q, ROUND_HALF_UP)
    rechnung.ust_gesamt = ust_sum.quantize(Q, ROUND_HALF_UP)
    rechnung.brutto_gesamt = (rechnung.netto_gesamt + rechnung.ust_gesamt).quantize(Q, ROUND_HALF_UP)
    db.commit()
    db.refresh(rechnung)
    return rechnung.id, rechnungsnummer, preisaenderungen


def pruefen_intern(db: Session) -> list[dict]:
    """
    Prüft alle aktiven Vorlagen und erstellt fällige Entwürfe.
    Wird beim App-Start aus main.py aufgerufen.
    Gibt Liste der erstellten Ergebnisse zurück.
    """
    heute = date.today()
    vorlagen = (
        db.query(Rechnungsvorlage)
        .filter(Rechnungsvorlage.aktiv == True, Rechnungsvorlage.naechstes_datum <= heute)  # noqa: E712
        .all()
    )
    ergebnisse = []
    for v in vorlagen:
        rid, rnr, pa = _erstelle_entwurf(v, db)
        v.naechstes_datum = _naechstes_datum(v.naechstes_datum, v.intervall)
        v.letzte_erstellung = heute
        v.erstellte_rechnungen = (v.erstellte_rechnungen or 0) + 1
        db.commit()
        ergebnisse.append({
            "vorlage_id": v.id,
            "vorlage_bezeichnung": v.bezeichnung,
            "rechnung_id": rid,
            "rechnungsnummer": rnr,
            "preisaenderungen": pa,
        })
    return ergebnisse


# ---------------------------------------------------------------------------
# CRUD-Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[VorlageResponse])
def liste_vorlagen(db: Session = Depends(get_db)):
    vorlagen = db.query(Rechnungsvorlage).order_by(Rechnungsvorlage.bezeichnung).all()
    return [_to_response(v) for v in vorlagen]


@router.post("", response_model=VorlageResponse, status_code=201)
def erstelle_vorlage(data: VorlageCreate, db: Session = Depends(get_db)):
    if data.intervall not in INTERVALLE:
        raise HTTPException(400, f"intervall muss einer von {sorted(INTERVALLE)} sein.")
    if data.auftrag_id:
        auftrag = db.query(Rechnung).filter(Rechnung.id == data.auftrag_id).first()
        if not auftrag or auftrag.dokument_typ != "Auftrag":
            raise HTTPException(404, "Auftrag nicht gefunden.")
    v = Rechnungsvorlage(
        bezeichnung=data.bezeichnung,
        intervall=data.intervall,
        naechstes_datum=data.naechstes_datum,
        aktiv=data.aktiv,
        kunde_id=data.kunde_id,
        zahlungsziel_tage=data.zahlungsziel_tage,
        notizen=data.notizen,
        positionen_json=json.dumps([p.model_dump() for p in data.positionen], default=str),
        auftrag_id=data.auftrag_id,
    )
    db.add(v)
    db.flush()
    if data.auftrag_id and data.aktiv:
        _set_auftrag_laufend(auftrag)
    db.commit()
    db.refresh(v)
    return _to_response(v)


@router.get("/{vorlage_id}", response_model=VorlageResponse)
def get_vorlage(vorlage_id: int, db: Session = Depends(get_db)):
    v = db.query(Rechnungsvorlage).filter(Rechnungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden.")
    return _to_response(v)


@router.put("/{vorlage_id}", response_model=VorlageResponse)
def aktualisiere_vorlage(vorlage_id: int, data: VorlageUpdate, db: Session = Depends(get_db)):
    v = db.query(Rechnungsvorlage).filter(Rechnungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden.")
    if data.bezeichnung is not None:
        v.bezeichnung = data.bezeichnung
    if data.intervall is not None:
        if data.intervall not in INTERVALLE:
            raise HTTPException(400, f"intervall muss einer von {sorted(INTERVALLE)} sein.")
        v.intervall = data.intervall
    if data.naechstes_datum is not None:
        v.naechstes_datum = data.naechstes_datum
    alter_auftrag_id = v.auftrag_id
    if data.aktiv is not None:
        war_aktiv = v.aktiv
        v.aktiv = data.aktiv
        if war_aktiv and not data.aktiv and v.auftrag_id:
            _revert_auftrag_status(v.auftrag_id, db)
        elif not war_aktiv and data.aktiv and v.auftrag_id:
            auftrag = db.query(Rechnung).filter(Rechnung.id == v.auftrag_id).first()
            if auftrag:
                _set_auftrag_laufend(auftrag)
    if data.kunde_id is not None:
        v.kunde_id = data.kunde_id
    if data.zahlungsziel_tage is not None:
        v.zahlungsziel_tage = data.zahlungsziel_tage
    if data.notizen is not None:
        v.notizen = data.notizen
    if data.positionen is not None:
        v.positionen_json = json.dumps([p.model_dump() for p in data.positionen], default=str)
    if data.auftrag_id is not None:
        if data.auftrag_id != v.auftrag_id:
            # Alten Auftrag-Status ggf. zurücksetzen
            if alter_auftrag_id:
                _revert_auftrag_status(alter_auftrag_id, db)
            if data.auftrag_id > 0:
                neuer_auftrag = db.query(Rechnung).filter(Rechnung.id == data.auftrag_id).first()
                if not neuer_auftrag or neuer_auftrag.dokument_typ != "Auftrag":
                    raise HTTPException(404, "Auftrag nicht gefunden.")
                v.auftrag_id = data.auftrag_id
                if v.aktiv:
                    _set_auftrag_laufend(neuer_auftrag)
            else:
                v.auftrag_id = None
    db.commit()
    db.refresh(v)
    return _to_response(v)


@router.delete("/{vorlage_id}", status_code=204)
def loesche_vorlage(vorlage_id: int, db: Session = Depends(get_db)):
    v = db.query(Rechnungsvorlage).filter(Rechnungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden.")
    auftrag_id = v.auftrag_id
    db.delete(v)
    db.flush()
    if auftrag_id:
        _revert_auftrag_status(auftrag_id, db)
    db.commit()


@router.post("/pruefen", response_model=list[EntwurfErgebnis])
def pruefen(db: Session = Depends(get_db)):
    """Erstellt Entwürfe für alle fälligen Vorlagen. Frontend ruft das beim Start auf."""
    ergebnisse = pruefen_intern(db)
    return [
        EntwurfErgebnis(
            vorlage_id=e["vorlage_id"],
            vorlage_bezeichnung=e["vorlage_bezeichnung"],
            rechnung_id=e["rechnung_id"],
            rechnungsnummer=e["rechnungsnummer"],
            preisaenderungen=[Preisaenderung(**p) for p in e["preisaenderungen"]],
        )
        for e in ergebnisse
    ]


@router.post("/{vorlage_id}/jetzt", response_model=EntwurfErgebnis)
def entwurf_jetzt(vorlage_id: int, db: Session = Depends(get_db)):
    """Erstellt sofort einen Entwurf aus der Vorlage (manuell, ohne Datumscheck)."""
    v = db.query(Rechnungsvorlage).filter(Rechnungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden.")
    rid, rnr, pa = _erstelle_entwurf(v, db)
    v.naechstes_datum = _naechstes_datum(v.naechstes_datum, v.intervall)
    v.letzte_erstellung = date.today()
    v.erstellte_rechnungen = (v.erstellte_rechnungen or 0) + 1
    db.commit()
    return EntwurfErgebnis(
        vorlage_id=v.id,
        vorlage_bezeichnung=v.bezeichnung,
        rechnung_id=rid,
        rechnungsnummer=rnr,
        preisaenderungen=[Preisaenderung(**p) for p in pa],
    )


@router.post("/{vorlage_id}/preise-sync", response_model=VorlageResponse)
def preise_synchronisieren(vorlage_id: int, db: Session = Depends(get_db)):
    """Aktualisiert alle Artikel-Preise in der Vorlage auf aktuelle vk_netto-Werte."""
    v = db.query(Rechnungsvorlage).filter(Rechnungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden.")
    positionen: list[dict] = json.loads(v.positionen_json or "[]")
    for p in positionen:
        if p.get("artikel_id"):
            art = db.query(Artikel).filter(Artikel.id == p["artikel_id"]).first()
            if art:
                p["netto"] = str(art.vk_netto)
                p["ust_satz"] = str(art.steuersatz)
    v.positionen_json = json.dumps(positionen, default=str)
    db.commit()
    db.refresh(v)
    return _to_response(v)


@router.post("/{vorlage_id}/vertrag", response_model=VorlageResponse)
async def upload_vertrag(vorlage_id: int, datei: UploadFile = File(...), db: Session = Depends(get_db)):
    """Vertrag-PDF an eine Vorlage hängen (ersetzt vorherigen Vertrag)."""
    v = db.query(Rechnungsvorlage).filter(Rechnungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden.")
    mime = datei.content_type or ""
    if mime not in ERLAUBTE_MIME_TYPES:
        raise HTTPException(422, f"Dateityp '{mime}' nicht erlaubt. Erlaubt: PDF, JPEG, PNG, TIFF.")
    inhalt = await datei.read()
    sha256 = hashlib.sha256(inhalt).hexdigest()
    jetzt = datetime.now()
    ziel_dir = BELEG_DIR / str(jetzt.year) / jetzt.strftime("%m")
    ziel_dir.mkdir(parents=True, exist_ok=True)
    original = Path(datei.filename or "vertrag")
    stem = original.stem[:50]
    suffix = original.suffix.lower() or ".bin"
    dateiname_lokal = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    rel_pfad = f"belege/{jetzt.year}/{jetzt.strftime('%m')}/{dateiname_lokal}"
    (ziel_dir / dateiname_lokal).write_bytes(inhalt)
    if v.beleg_id:
        alter_beleg = db.query(Beleg).filter(Beleg.id == v.beleg_id).first()
        if alter_beleg:
            alter_pfad = APP_DATA_DIR / "uploads" / alter_beleg.dateiname
            if alter_pfad.exists():
                alter_pfad.unlink()
            db.delete(alter_beleg)
    beleg = Beleg(
        dateiname=rel_pfad,
        original_name=datei.filename or "vertrag",
        mime_type=mime,
        dateigroesse=len(inhalt),
        sha256=sha256,
    )
    db.add(beleg)
    db.flush()
    v.beleg_id = beleg.id
    db.commit()
    db.refresh(v)
    return _to_response(v)


@router.delete("/{vorlage_id}/vertrag", response_model=VorlageResponse)
def loesche_vertrag(vorlage_id: int, db: Session = Depends(get_db)):
    """Vertrag-PDF von Vorlage entfernen."""
    v = db.query(Rechnungsvorlage).filter(Rechnungsvorlage.id == vorlage_id).first()
    if not v:
        raise HTTPException(404, "Vorlage nicht gefunden.")
    if v.beleg_id:
        beleg = db.query(Beleg).filter(Beleg.id == v.beleg_id).first()
        if beleg:
            pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
            if pfad.exists():
                pfad.unlink()
            db.delete(beleg)
        v.beleg_id = None
    db.commit()
    db.refresh(v)
    return _to_response(v)
