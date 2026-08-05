"""Artikelstamm-API."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Artikel, Lieferant, Nummernkreis, Rechnung, Rechnungsposition, Kunde, UstSatz
from .schemas_artikel import ArtikelCreate, ArtikelUpdate, ArtikelResponse, ArtikelSucheResponse, ArtikelRechnungKurz

router = APIRouter(prefix="/api/artikel", tags=["Artikel"])


def _berechne_preise(
    vk_brutto: Decimal,
    vk_netto: Optional[Decimal],
    vk_eingabe: str,
    ek_netto: Optional[Decimal],
    steuersatz: Decimal,
    differenzbesteuerung: bool = False,
):
    """Berechnet vk_brutto und vk_netto - je nachdem welcher der beiden Preise laut vk_eingabe
    die vom Nutzer eingegebene Wahrheit ist, wird der jeweils andere daraus abgeleitet. Gibt
    (vk_brutto, vk_netto, ek_brutto) zurück.

    Ohne diese Unterscheidung ging beim Runden Präzision verloren: wer 2,94€ netto einträgt,
    bekommt korrekt 3,50€ brutto (2,94 x 1,19 = 3,4986€ -> 3,50€) - eine Rückrechnung
    3,50€ / 1,19 ergibt aber 2,9412€ statt der ursprünglich eingegebenen 2,94€. Beim nächsten
    Speichern "wanderte" der Netto-Preis dadurch vom eingegebenen Wert weg (Nutzer-Feedback
    2026-08-05).

    Bei Differenzbesteuerung (§25a UStG) wird keine USt separat ausgewiesen –
    VK-Brutto ist gleichzeitig der Rechnungspreis (ohne USt-Aufschlag).
    ek_brutto = ek_netto (Ankauf von Privatperson, kein USt-Abzug).

    Der jeweils ABGELEITETE Preis wird NICHT auf 2 Nachkommastellen gerundet, sondern behält
    4 Nachkommastellen (wie rechnungspositionen.netto): würde z.B. bei vk_eingabe="brutto" der
    daraus abgeleitete Netto-Preis auf den Cent gerundet (3,50€ / 1,19 = 2,9412€ -> 2,94€), würde
    eine daraus erstellte Netto-Rechnung bei größeren Mengen spürbar vom eingegebenen Brutto-Preis
    abweichen (2,94€ x 1,19 = 3,4986€, nicht 3,50€). Symmetrisch dazu wird bei vk_eingabe="netto"
    der abgeleitete Brutto-Preis ebenfalls nicht gerundet - sonst weicht umgekehrt eine
    Brutto-Rechnung mit diesem Artikel von einer Netto-Rechnung ab (z.B. 2,94€ netto x 1,19 würde
    auf 3,50€ gerundet, eine Brutto-Rechnung mit 100 Stück ergäbe dann 350,00€ statt der zur
    Netto-Rechnung passenden 349,86€ - Issue #332/#344).
    """
    ek_brutto = None
    if ek_netto is not None:
        ek_brutto = (ek_netto * (1 + steuersatz / 100)).quantize(Decimal("0.01"), ROUND_HALF_UP)

    if differenzbesteuerung:
        # §25a: kein USt-Aufschlag auf den Rechnungspreis
        return vk_brutto, vk_brutto, ek_brutto

    faktor = 1 + steuersatz / 100
    if vk_eingabe == "netto" and vk_netto is not None:
        vk_brutto = (vk_netto * faktor).quantize(Decimal("0.0001"), ROUND_HALF_UP)
    else:
        vk_netto = (vk_brutto / faktor).quantize(Decimal("0.0001"), ROUND_HALF_UP)
    return vk_brutto, vk_netto, ek_brutto


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
    q: str = Query(..., min_length=2, description="Suchbegriff (min. 2 Zeichen)"),
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
            ek_brutto=a.ek_brutto,
            differenzbesteuerung=a.differenzbesteuerung,
            lieferant_name=a.lieferant.firmenname if a.lieferant else None,
            beschreibung=a.beschreibung,
            lager_aktiv=a.lager_aktiv,
            bestand_aktuell=a.bestand_aktuell,
            minusbestand_erlaubt=a.minusbestand_erlaubt,
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


def _prüfe_steuersatz(satz: Decimal, db: Session) -> None:
    erlaubt = {row.satz for row in db.query(UstSatz).filter(UstSatz.ist_aktiv == True).all()}
    if satz not in erlaubt:
        raise HTTPException(
            status_code=422,
            detail=f"Steuersatz {satz}% ist nicht in den aktiven MwSt.-Sätzen vorhanden.",
        )


@router.post("", response_model=ArtikelResponse, status_code=201)
def create_artikel(data: ArtikelCreate, db: Session = Depends(get_db)):
    if not data.differenzbesteuerung:
        _prüfe_steuersatz(data.steuersatz, db)
    vk_brutto, vk_netto, ek_brutto = _berechne_preise(
        data.vk_brutto, data.vk_netto, data.vk_eingabe, data.ek_netto, data.steuersatz, data.differenzbesteuerung
    )
    artikelnummer = _naechste_artikelnummer(db)
    artikel = Artikel(
        artikelnummer=artikelnummer,
        typ=data.typ,
        bezeichnung=data.bezeichnung,
        einheit=data.einheit,
        steuersatz=data.steuersatz,
        vk_brutto=vk_brutto,
        vk_netto=vk_netto,
        vk_eingabe=data.vk_eingabe,
        ek_netto=data.ek_netto,
        ek_brutto=ek_brutto,
        # Dienstleistung = eigene Leistung, kein Einkauf bei einem Lieferanten (Issue #334)
        lieferant_id=data.lieferant_id if data.typ != "dienstleistung" else None,
        lieferanten_artikelnr=data.lieferanten_artikelnr if data.typ != "dienstleistung" else None,
        hersteller=data.hersteller,
        artikelcode=data.artikelcode,
        beschreibung=data.beschreibung,
        gruppe_id=data.gruppe_id,
        differenzbesteuerung=data.differenzbesteuerung,
        lager_aktiv=data.lager_aktiv,
        bestand_aktuell=data.bestand_aktuell if data.bestand_aktuell is not None else Decimal("0"),
        mindestbestand=data.mindestbestand,
        minusbestand_erlaubt=data.minusbestand_erlaubt,
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

    update = data.model_dump(exclude_unset=True)

    differenzbesteuerung = update.get("differenzbesteuerung", artikel.differenzbesteuerung)

    # Dienstleistung = eigene Leistung, kein Einkauf bei einem Lieferanten (Issue #334) - greift
    # auch wenn nur der Typ gewechselt wird, ohne dass lieferant_id im Request enthalten ist.
    if update.get("typ", artikel.typ) == "dienstleistung":
        update["lieferant_id"] = None
        update["lieferanten_artikelnr"] = None

    if "steuersatz" in update and not differenzbesteuerung:
        _prüfe_steuersatz(update["steuersatz"], db)

    # Preise neu berechnen wenn vk_brutto, vk_netto, steuersatz oder differenzbesteuerung geändert wurde
    vk_brutto_in = update.get("vk_brutto", artikel.vk_brutto)
    vk_netto_in = update.get("vk_netto", None)
    vk_eingabe = update.get("vk_eingabe", artikel.vk_eingabe)
    steuersatz = update.get("steuersatz", artikel.steuersatz)
    ek_netto = update.get("ek_netto", artikel.ek_netto)
    vk_brutto, vk_netto, ek_brutto = _berechne_preise(
        vk_brutto_in, vk_netto_in, vk_eingabe, ek_netto, steuersatz, differenzbesteuerung
    )
    update["vk_brutto"] = vk_brutto
    update["vk_netto"] = vk_netto
    update["vk_eingabe"] = vk_eingabe
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
        # pos.brutto ist die Positionssumme (Einzelpreis x Menge, Issue #332) - für die Anzeige
        # "zu welchem Stückpreis wurde der Artikel verkauft" durch die Menge zurückrechnen.
        vk_brutto_stueck = (pos.brutto / pos.menge).quantize(Decimal("0.01"), ROUND_HALF_UP) if pos.menge else pos.brutto
        result.append(ArtikelRechnungKurz(
            rechnung_id=rechnung.id,
            rechnungsnummer=rechnung.rechnungsnummer,
            datum=str(rechnung.datum),
            menge=pos.menge,
            einheit=pos.einheit,
            vk_brutto=vk_brutto_stueck,
            kunde_id=rechnung.kunde_id,
            kunde_name=" ".join(p for p in [kunde.firmenname, kunde.vorname, kunde.nachname] if p) or None if kunde else None,
        ))
    return result


@router.delete("/{artikel_id}", status_code=204)
def delete_artikel(artikel_id: int, db: Session = Depends(get_db)):
    artikel = db.query(Artikel).filter(Artikel.id == artikel_id).first()
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden.")
    links = db.query(Rechnungsposition).filter(Rechnungsposition.artikel_id == artikel_id).count()
    if links > 0:
        raise HTTPException(status_code=409, detail=f"Artikel ist in {links} Rechnung(en) verwendet und kann nicht gelöscht werden.")
    if artikel.lager_aktiv and artikel.bestand_aktuell and artikel.bestand_aktuell != Decimal("0"):
        raise HTTPException(status_code=409, detail=f"Lagerbestand ist {artikel.bestand_aktuell} – bitte zuerst auf 0 setzen.")
    db.delete(artikel)
    db.commit()


@router.patch("/{artikel_id}/archivieren", response_model=ArtikelResponse)
def archiviere_artikel(artikel_id: int, db: Session = Depends(get_db)):
    artikel = db.query(Artikel).filter(Artikel.id == artikel_id).first()
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel nicht gefunden.")
    if artikel.lager_aktiv and artikel.bestand_aktuell and artikel.bestand_aktuell != Decimal("0"):
        raise HTTPException(
            status_code=409,
            detail=f"Artikel kann nicht archiviert werden: Lagerbestand ist {artikel.bestand_aktuell} {artikel.einheit} (muss 0 sein).",
        )
    artikel.aktiv = False
    db.commit()
    db.refresh(artikel)
    return artikel


@router.get("/lagerwarnung/liste", response_model=list[ArtikelResponse])
def get_lagerwarnung(db: Session = Depends(get_db)):
    """Artikel mit aktivierter Lagerführung deren Bestand den Mindestbestand erreicht oder unterschreitet."""
    return (
        db.query(Artikel)
        .filter(
            Artikel.lager_aktiv == True,   # noqa: E712
            Artikel.aktiv == True,          # noqa: E712
            Artikel.bestand_aktuell <= Artikel.mindestbestand,
        )
        .order_by(Artikel.bezeichnung)
        .all()
    )
