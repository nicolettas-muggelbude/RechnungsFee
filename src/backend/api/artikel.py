"""Artikelstamm-API."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Artikel, Lieferant, Nummernkreis, Rechnung, Rechnungsposition, Kunde
from .schemas_artikel import ArtikelCreate, ArtikelUpdate, ArtikelResponse, ArtikelSucheResponse, ArtikelRechnungKurz

router = APIRouter(prefix="/api/artikel", tags=["Artikel"])


def _berechne_preise(vk_brutto: Decimal, ek_netto: Optional[Decimal], steuersatz: Decimal):
    """Berechnet vk_netto und ek_brutto aus den Eingabewerten."""
    faktor = 1 + steuersatz / 100
    vk_netto = (vk_brutto / faktor).quantize(Decimal("0.01"), ROUND_HALF_UP)
    ek_brutto = None
    if ek_netto is not None:
        ek_brutto = (ek_netto * faktor).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return vk_netto, ek_brutto


def _naechste_artikelnummer(db: Session) -> str:
    nk = db.query(Nummernkreis).filter(Nummernkreis.typ == "artikel").first()
    if not nk:
        count = db.query(Artikel).count()
        return f"ART-{count + 1:04d}"
    nr = nk.naechste_nr
    nk.naechste_nr += 1
    # Format: ART-#### → einfaches Replace der #
    result = nk.format
    result = result.replace("####", f"{nr:04d}")
    result = result.replace("###", f"{nr:03d}")
    result = result.replace("##", f"{nr:02d}")
    result = result.replace("#", str(nr))
    return result


@router.get("/suche", response_model=list[ArtikelSucheResponse])
def suche_artikel(
    q: str = Query(..., min_length=3, description="Suchbegriff (min. 3 Zeichen)"),
    db: Session = Depends(get_db),
):
    """Volltextsuche in Artikelnummer, Bezeichnung und Lieferantenname."""
    qlike = f"%{q}%"
    treffer = (
        db.query(Artikel)
        .outerjoin(Lieferant, Artikel.lieferant_id == Lieferant.id)
        .filter(
            Artikel.aktiv == True,
            (
                Artikel.artikelnummer.ilike(qlike)
                | Artikel.bezeichnung.ilike(qlike)
                | Lieferant.firmenname.ilike(qlike)
            ),
        )
        .order_by(Artikel.bezeichnung)
        .limit(20)
        .all()
    )
    result = []
    for a in treffer:
        result.append(ArtikelSucheResponse(
            id=a.id,
            artikelnummer=a.artikelnummer,
            typ=a.typ,
            bezeichnung=a.bezeichnung,
            einheit=a.einheit,
            steuersatz=a.steuersatz,
            vk_brutto=a.vk_brutto,
            vk_netto=a.vk_netto,
            lieferant_name=a.lieferant.firmenname if a.lieferant else None,
        ))
    return result


@router.get("", response_model=list[ArtikelResponse])
def list_artikel(
    aktiv: Optional[bool] = Query(None),
    typ: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Artikel)
    if aktiv is not None:
        q = q.filter(Artikel.aktiv == aktiv)
    if typ:
        q = q.filter(Artikel.typ == typ)
    return q.order_by(Artikel.bezeichnung).all()


@router.post("", response_model=ArtikelResponse, status_code=201)
def create_artikel(data: ArtikelCreate, db: Session = Depends(get_db)):
    vk_netto, ek_brutto = _berechne_preise(data.vk_brutto, data.ek_netto, data.steuersatz)
    artikelnummer = _naechste_artikelnummer(db)
    artikel = Artikel(
        artikelnummer=artikelnummer,
        typ=data.typ,
        bezeichnung=data.bezeichnung,
        einheit=data.einheit,
        steuersatz=data.steuersatz,
        vk_brutto=data.vk_brutto,
        vk_netto=vk_netto,
        ek_netto=data.ek_netto,
        ek_brutto=ek_brutto,
        lieferant_id=data.lieferant_id,
        lieferanten_artikelnr=data.lieferanten_artikelnr,
        hersteller=data.hersteller,
        artikelcode=data.artikelcode,
        beschreibung=data.beschreibung,
        kategorie=data.kategorie,
    )
    db.add(artikel)
    db.commit()
    db.refresh(artikel)
    return artikel


@router.get("/{artikel_id}", response_model=ArtikelResponse)
def get_artikel(artikel_id: int, db: Session = Depends(get_db)):
    artikel = db.query(Artikel).filter(Artikel.id == artikel_id).first()
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden.")
    return artikel


@router.put("/{artikel_id}", response_model=ArtikelResponse)
def update_artikel(artikel_id: int, data: ArtikelUpdate, db: Session = Depends(get_db)):
    artikel = db.query(Artikel).filter(Artikel.id == artikel_id).first()
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden.")

    update = data.model_dump(exclude_none=True)

    # Preise neu berechnen wenn vk_brutto oder steuersatz geändert wurde
    vk_brutto = update.get("vk_brutto", artikel.vk_brutto)
    steuersatz = update.get("steuersatz", artikel.steuersatz)
    ek_netto = update.get("ek_netto", artikel.ek_netto)
    vk_netto, ek_brutto = _berechne_preise(vk_brutto, ek_netto, steuersatz)
    update["vk_netto"] = vk_netto
    if ek_brutto is not None or "ek_netto" in update:
        update["ek_brutto"] = ek_brutto

    for k, v in update.items():
        setattr(artikel, k, v)
    db.commit()
    db.refresh(artikel)
    return artikel


@router.get("/{artikel_id}/rechnungen", response_model=list[ArtikelRechnungKurz])
def get_artikel_rechnungen(artikel_id: int, db: Session = Depends(get_db)):
    """Alle Rechnungen in denen dieser Artikel vorkommt, inkl. Kundeninfo."""
    artikel = db.query(Artikel).filter(Artikel.id == artikel_id).first()
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden.")

    positionen = (
        db.query(Rechnungsposition)
        .filter(Rechnungsposition.artikel_id == artikel_id)
        .join(Rechnung, Rechnungsposition.rechnung_id == Rechnung.id)
        .all()
    )

    result = []
    for pos in positionen:
        rechnung = pos.rechnung
        kunde = db.query(Kunde).filter(Kunde.id == rechnung.kunde_id).first() if rechnung.kunde_id else None
        result.append(ArtikelRechnungKurz(
            rechnung_id=rechnung.id,
            rechnungsnummer=rechnung.rechnungsnummer,
            datum=str(rechnung.datum),
            menge=pos.menge,
            einheit=pos.einheit,
            vk_brutto=pos.brutto,
            kunde_id=rechnung.kunde_id,
            kunde_name=kunde.firmenname if kunde else None,
        ))
    return result
