"""
API-Endpunkte für Forderungsmanagement (offene Verrechnungsposten).
"""
from datetime import date as date_type
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Forderung, Journaleintrag, Kategorie, Rechnung
from utils.signatur import signatur_journaleintrag
from .journal import _felder_aus_data, _naechste_belegnr
from .rechnungen import _aktualisiere_zahlungsstatus, _berechne_vorsteuer, _partner_name, _ust_konto
from database.models import Lieferant
from .schemas import JournalEintragCreate

router = APIRouter(prefix="/api/forderungen", tags=["Forderungen"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ForderungCreate(BaseModel):
    typ: str = "lieferantenguthaben"
    betrag: Decimal
    partner_typ: Optional[str] = None
    partner_id: Optional[int] = None
    rechnung_id: Optional[int] = None
    journal_id: Optional[int] = None
    faellig_am: Optional[date_type] = None
    notiz: Optional[str] = None


class ForderungResponse(BaseModel):
    id: int
    typ: str
    status: str
    betrag: Decimal
    waehrung: str
    faellig_am: Optional[date_type] = None
    partner_typ: Optional[str] = None
    partner_id: Optional[int] = None
    rechnung_id: Optional[int] = None
    journal_id: Optional[int] = None
    ausgleich_journal_id: Optional[int] = None
    notiz: Optional[str] = None
    erstellt_am: str

    model_config = {"from_attributes": True}


class AusgleichRequest(BaseModel):
    journal_id: int


class AusbuchenRequest(BaseModel):
    kategorie_id: int
    notiz: Optional[str] = None


class VerrechnenRequest(BaseModel):
    rechnung_id: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ForderungResponse])
def get_forderungen(status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Forderung)
    if status:
        q = q.filter(Forderung.status == status)
    return q.order_by(Forderung.erstellt_am.desc()).all()


@router.get("/offen", response_model=list[ForderungResponse])
def get_offene_forderungen(
    kunde_id: Optional[int] = None,
    lieferant_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Forderung).filter(Forderung.status == "offen")
    if kunde_id is not None:
        q = q.filter(
            Forderung.typ == "kundenguthaben",
            Forderung.partner_typ == "kunde",
            Forderung.partner_id == kunde_id,
        )
    elif lieferant_id is not None:
        q = q.filter(
            Forderung.typ == "lieferantenguthaben",
            Forderung.partner_typ == "lieferant",
            Forderung.partner_id == lieferant_id,
        )
    return q.order_by(Forderung.erstellt_am.desc()).all()


@router.post("", response_model=ForderungResponse, status_code=201)
def create_forderung(data: ForderungCreate, db: Session = Depends(get_db)):
    f = Forderung(
        typ=data.typ,
        betrag=data.betrag,
        partner_typ=data.partner_typ,
        partner_id=data.partner_id,
        rechnung_id=data.rechnung_id,
        journal_id=data.journal_id,
        faellig_am=data.faellig_am,
        notiz=data.notiz,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


@router.patch("/{forderung_id}/ausgleichen", response_model=ForderungResponse)
def forderung_ausgleichen(
    forderung_id: int,
    data: AusgleichRequest,
    db: Session = Depends(get_db),
):
    """Forderung mit einem bestehenden Journal-Eintrag (Rücküberweisung) ausgleichen."""
    f = db.query(Forderung).filter(Forderung.id == forderung_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Forderung nicht gefunden.")
    if f.status != "offen":
        raise HTTPException(status_code=409, detail="Forderung ist nicht offen.")
    f.status = "ausgeglichen"
    f.ausgleich_journal_id = data.journal_id
    db.commit()
    db.refresh(f)
    return f


@router.patch("/{forderung_id}/ausbuchen", response_model=ForderungResponse)
def forderung_ausbuchen(
    forderung_id: int,
    data: AusbuchenRequest,
    db: Session = Depends(get_db),
):
    """Forderungsausfall buchen – legt Journal-Eintrag an und schließt den Posten."""
    f = db.query(Forderung).filter(Forderung.id == forderung_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Forderung nicht gefunden.")
    if f.status != "offen":
        raise HTTPException(status_code=409, detail="Forderung ist nicht offen.")

    kat = db.query(Kategorie).filter(Kategorie.id == data.kategorie_id).first()
    if not kat:
        raise HTTPException(status_code=404, detail="Kategorie nicht gefunden.")

    beschreibung = data.notiz or f"Forderungsausfall Lieferantenguthaben #{f.id}"
    journal_data = JournalEintragCreate(
        datum=date_type.today(),
        beschreibung=beschreibung,
        kategorie_id=data.kategorie_id,
        zahlungsart="Keine",
        art="Ausgabe",
        brutto_betrag=f.betrag,
        ust_satz=Decimal("0"),
        vorsteuerabzug=False,
    )
    felder = _felder_aus_data(journal_data, db)
    belegnr = _naechste_belegnr(db, date_type.today())
    eintrag = Journaleintrag(belegnr=belegnr, immutable=False, **felder)
    eintrag.signatur = signatur_journaleintrag(eintrag)
    db.add(eintrag)
    db.flush()

    f.status = "ausgebucht"
    f.ausgleich_journal_id = eintrag.id
    if data.notiz:
        f.notiz = data.notiz
    db.commit()
    db.refresh(f)
    return f


@router.post("/{forderung_id}/verrechnen", response_model=ForderungResponse)
def forderung_verrechnen(
    forderung_id: int,
    data: VerrechnenRequest,
    db: Session = Depends(get_db),
):
    """Kunden- oder Lieferantenguthaben als Teilzahlung auf eine offene Rechnung anrechnen."""
    f = db.query(Forderung).filter(Forderung.id == forderung_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Forderung nicht gefunden.")
    if f.status != "offen":
        raise HTTPException(status_code=409, detail="Forderung ist nicht offen.")
    if f.typ not in ("kundenguthaben", "lieferantenguthaben"):
        raise HTTPException(status_code=400, detail="Nur Kunden- oder Lieferantenguthaben können verrechnet werden.")

    rechnung = db.query(Rechnung).filter(Rechnung.id == data.rechnung_id).first()
    if not rechnung:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    if rechnung.storniert:
        raise HTTPException(status_code=400, detail="Stornierte Rechnung.")

    # Richtungs-Prüfung: Kundenguthaben → Ausgangsrechnung, Lieferantenguthaben → Eingangsrechnung
    if f.typ == "kundenguthaben":
        if rechnung.typ != "ausgang":
            raise HTTPException(status_code=400, detail="Kundenguthaben nur gegen Ausgangsrechnungen.")
        if rechnung.kunde_id != f.partner_id:
            raise HTTPException(status_code=400, detail="Kunde stimmt nicht mit Forderung überein.")
    else:
        if rechnung.typ != "eingang":
            raise HTTPException(status_code=400, detail="Lieferantenguthaben nur gegen Eingangsrechnungen.")
        if rechnung.lieferant_id != f.partner_id:
            raise HTTPException(status_code=400, detail="Lieferant stimmt nicht mit Forderung überein.")

    restbetrag = abs(rechnung.brutto_gesamt - rechnung.bezahlt_betrag)
    if restbetrag <= Decimal("0.004"):
        raise HTTPException(status_code=400, detail="Rechnung ist bereits vollständig bezahlt.")

    betrag = min(f.betrag, restbetrag)

    # USt anteilig wie bei normaler Teilzahlung
    ust_satz = Decimal("0")
    kat_id = None
    if rechnung.positionen:
        gruppen: dict[int, Decimal] = {}
        kat_gruppen: dict[int | None, Decimal] = {}
        for pos in rechnung.positionen:
            s = int(pos.ust_satz_25a if pos.differenzbesteuerung and pos.ust_satz_25a else pos.ust_satz)
            gruppen[s] = gruppen.get(s, Decimal("0")) + pos.brutto
            kat_gruppen[pos.kategorie_id] = kat_gruppen.get(pos.kategorie_id, Decimal("0")) + pos.brutto
        ust_satz = Decimal(str(max(gruppen, key=lambda s: gruppen[s])))
        kat_id = max(kat_gruppen, key=lambda k: kat_gruppen[k] if k is not None else Decimal("0"))

    ist_einnahme = f.typ == "kundenguthaben"
    art = "Einnahme" if ist_einnahme else "Ausgabe"
    bezeichnung = "Kundenguthaben" if ist_einnahme else "Lieferantenguthaben"
    vst_abzug = not ist_einnahme and ust_satz > 0

    kat = db.query(Kategorie).filter(Kategorie.id == kat_id).first() if kat_id else None
    konto_ust_skr03, konto_ust_skr04 = _ust_konto(art, ust_satz) if ust_satz > 0 else (None, None)

    if ust_satz > 0:
        netto = (betrag * 100 / (100 + ust_satz)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        ust_betrag = (betrag - netto).quantize(Decimal("0.01"), ROUND_HALF_UP)
    else:
        netto = betrag
        ust_betrag = Decimal("0.00")

    eintrag = Journaleintrag(
        datum=date_type.today(),
        belegnr=_naechste_belegnr(db, date_type.today()),
        beschreibung=f"Verrechnung {bezeichnung}: {_partner_name(rechnung)}",
        kategorie_id=kat_id,
        konto_skr03=kat.konto_skr03 if kat else None,
        konto_skr04=kat.konto_skr04 if kat else None,
        konto_ust_skr03=konto_ust_skr03,
        konto_ust_skr04=konto_ust_skr04,
        zahlungsart="Verrechnung",
        art=art,
        netto_betrag=netto,
        ust_satz=ust_satz,
        ust_betrag=ust_betrag,
        vorsteuer_betrag=_berechne_vorsteuer(ust_betrag, vst_abzug, kat),
        brutto_betrag=betrag,
        vorsteuerabzug=vst_abzug,
        rechnung_id=rechnung.id,
        immutable=True,
    )
    eintrag.signatur = signatur_journaleintrag(eintrag)
    db.add(eintrag)
    db.flush()

    rechnung.bezahlt_betrag = (rechnung.bezahlt_betrag or Decimal("0")) + betrag
    _aktualisiere_zahlungsstatus(rechnung)

    # Forderung schließen oder Restbetrag reduzieren
    if f.betrag <= betrag + Decimal("0.004"):
        f.status = "ausgeglichen"
        f.ausgleich_journal_id = eintrag.id
    else:
        f.betrag = f.betrag - betrag

    db.commit()
    db.refresh(f)
    return f
