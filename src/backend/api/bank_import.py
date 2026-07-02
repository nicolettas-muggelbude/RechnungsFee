"""
API-Endpunkte für Bank-CSV-Import.
"""

import hashlib
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import (
    BankImport, BankTemplate, BankTransaktion, Forderung, Journaleintrag,
    Kategorie, Konto, Kunde, Lieferant, Rechnung, Unternehmen,
)
from utils.bank_csv_parser import (
    detect_delimiter,
    detect_encoding,
    extract_konto_iban,
    find_best_template,
    parse_csv_mit_template,
)
from utils.signatur import signatur_journaleintrag
from .journal import _felder_aus_data, _naechste_belegnr
from .rechnungen import _aktualisiere_zahlungsstatus, _berechne_vorsteuer, _partner_name, _ust_konto
from .schemas import JournalEintragCreate

router = APIRouter(prefix="/api/bank-import", tags=["Bank-Import"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TransaktionVorschau(BaseModel):
    datum: date
    valuta: Optional[date] = None
    buchungstext: Optional[str] = None
    verwendungszweck: Optional[str] = None
    partner_name: Optional[str] = None
    partner_iban: Optional[str] = None
    betrag: Decimal
    waehrung: str = "EUR"
    saldo: Optional[Decimal] = None
    referenz: Optional[str] = None
    dedupe_hash: str
    ist_duplikat: bool = False


class VorschauResponse(BaseModel):
    erkanntes_template: Optional[str] = None
    template_name: Optional[str] = None
    encoding: str
    konto_iban: Optional[str] = None          # aus CSV-Header extrahierte eigene IBAN
    erkanntes_konto_id: Optional[int] = None  # passendes Konto im System (None = nicht gefunden)
    transaktionen: list[TransaktionVorschau]


class ImportiereRequest(BaseModel):
    konto_id: int
    template_id: str
    dateiname: str
    transaktionen: list[TransaktionVorschau]


class ImportiereResponse(BaseModel):
    import_id: int
    erfolg: int
    duplikate: int
    fehler: int


class BankImportResponse(BaseModel):
    id: int
    konto_id: int
    template_id: str
    dateiname: str
    anzahl_zeilen: int
    erfolg: int
    fehler: int
    duplikate: int
    importiert_am: str

    model_config = {"from_attributes": True}


class RechnungKurzinfo(BaseModel):
    rechnungsnummer: str
    partner: str
    brutto_gesamt: Decimal
    gebuchter_betrag: Decimal


class BankTransaktionResponse(BaseModel):
    id: int
    import_id: int
    konto_id: int
    datum: date
    valuta: Optional[date] = None
    buchungstext: Optional[str] = None
    verwendungszweck: Optional[str] = None
    partner_name: Optional[str] = None
    partner_iban: Optional[str] = None
    betrag: Decimal
    waehrung: str
    saldo: Optional[Decimal] = None
    ist_geschaeftlich: bool
    ist_privatentnahme: bool
    ist_einlage: bool
    ist_rueckerstattung: bool = False
    auto_vorschlag: Optional[str] = None
    user_ueberschrieben: bool
    kategorie_id: Optional[int] = None
    rechnung_id: Optional[int] = None
    journal_id: Optional[int] = None
    forderung_id: Optional[int] = None
    dedupe_hash: Optional[str] = None
    rechnung_info: Optional[RechnungKurzinfo] = None

    model_config = {"from_attributes": True}


class BuchungsRequest(BaseModel):
    rechnung_id: Optional[int] = None
    betrag_zu_buchen: Optional[Decimal] = None


class AbgleichVorschlag(BaseModel):
    rechnung_id: int
    rechnungsnummer: str
    externe_belegnr: Optional[str] = None
    partner: str
    datum: date
    brutto_gesamt: Decimal
    restbetrag: Decimal
    score: int
    betrag_match: bool
    nummer_match: bool
    name_match: bool


class TransaktionKlassifizierung(BaseModel):
    ist_geschaeftlich: bool = True
    ist_privatentnahme: bool = False
    ist_einlage: bool = False
    kategorie_id: Optional[int] = None


class AutoBuchenResult(BaseModel):
    gebucht: int
    offen: int
    import_id: Optional[int] = None
    forderungen: int
    fehler: int


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _dedupe_hash(tx: dict) -> str:
    raw = f"{tx.get('datum')}|{tx.get('betrag')}|{tx.get('partner_iban') or ''}|{tx.get('verwendungszweck') or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _vorhandene_hashes(db: Session, konto_id: int) -> set[str]:
    rows = db.execute(
        text("SELECT dedupe_hash FROM bank_transaktionen WHERE konto_id = :kid AND dedupe_hash IS NOT NULL"),
        {"kid": konto_id},
    ).fetchall()
    return {r[0] for r in rows}


def _betrag_match(rechnung: Rechnung, tx_betrag: Decimal) -> bool:
    restbetrag = abs(rechnung.brutto_gesamt - rechnung.bezahlt_betrag)
    return abs(restbetrag - abs(tx_betrag)) <= Decimal("0.02")


def _nummer_match(rechnung: Rechnung, verwendungszweck: str | None) -> bool:
    if not verwendungszweck:
        return False
    vwz = verwendungszweck.upper()
    if rechnung.rechnungsnummer and rechnung.rechnungsnummer.upper() in vwz:
        return True
    if rechnung.externe_belegnr and rechnung.externe_belegnr.upper() in vwz:
        return True
    return False


def _name_match(partner_rechnung: str, partner_tx: str | None) -> bool:
    if not partner_tx:
        return False
    a = partner_rechnung.lower().strip()
    b = partner_tx.lower().strip()
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    words_a = {w for w in a.split() if len(w) >= 3}
    words_b = {w for w in b.split() if len(w) >= 3}
    return bool(words_a & words_b)


def _abgleich_score(rechnung: Rechnung, tx: BankTransaktion) -> tuple[int, bool, bool, bool]:
    """Gibt (score, betrag_match, nummer_match, name_match) zurück."""
    bm = _betrag_match(rechnung, tx.betrag)
    nm = _nummer_match(rechnung, tx.verwendungszweck)
    nam = _name_match(_partner_name(rechnung), tx.partner_name)
    return int(bm) + int(nm) + int(nam), bm, nm, nam


_RUECKERSTATTUNG_KEYWORDS = {"erstattung", "rueckerstattung", "rückerstattung", "refund", "rueck", "rück"}


def _match_kundenguthaben(
    db: Session,
    tx: BankTransaktion,
) -> Optional[Forderung]:
    """Sucht ein offenes Kundenguthaben das zur ausgehenden Transaktion passt.

    Matching-Kriterien (mind. eines muss zutreffen):
    1. Betrag ±0,02 € + Kundenname-Overlap im partner_name der Transaktion
    2. Betrag ±0,02 € + Keyword (ERSTATTUNG, RUECKERSTATTUNG, …) im Verwendungszweck
    """
    if tx.betrag >= 0:
        return None

    tx_abs = abs(tx.betrag)

    kandidaten = (
        db.query(Forderung)
        .filter(
            Forderung.typ == "kundenguthaben",
            Forderung.status == "offen",
            Forderung.betrag.between(tx_abs - Decimal("0.02"), tx_abs + Decimal("0.02")),
        )
        .all()
    )

    if not kandidaten:
        return None

    verwendung_lower = (tx.verwendungszweck or "").lower().replace("-", "")
    hat_keyword = any(kw in verwendung_lower for kw in _RUECKERSTATTUNG_KEYWORDS)

    for f in kandidaten:
        # Kundenname aus verknüpfter Rechnung holen
        if f.rechnung_id:
            rechnung = db.query(Rechnung).filter(Rechnung.id == f.rechnung_id).first()
            if rechnung and rechnung.kunde_id:
                kunde = db.query(Kunde).filter(Kunde.id == rechnung.kunde_id).first()
                if kunde:
                    kunde_name = (kunde.firma or f"{kunde.vorname or ''} {kunde.nachname or ''}").strip()
                    if _name_match(kunde_name, tx.partner_name):
                        return f

        # Fallback: Keyword im Verwendungszweck reicht auch ohne Namens-Match
        if hat_keyword:
            return f

    return None


def _match_lieferantenguthaben(
    db: Session,
    tx: BankTransaktion,
) -> Optional[Forderung]:
    """Sucht ein offenes Lieferantenguthaben das zur eingehenden Transaktion passt.

    Matching: Betrag ±0,02 € + Lieferantenname-Overlap ODER Keyword im Verwendungszweck.
    """
    if tx.betrag <= 0:
        return None

    kandidaten = (
        db.query(Forderung)
        .filter(
            Forderung.typ == "lieferantenguthaben",
            Forderung.status == "offen",
            Forderung.betrag.between(tx.betrag - Decimal("0.02"), tx.betrag + Decimal("0.02")),
        )
        .all()
    )

    if not kandidaten:
        return None

    verwendung_lower = (tx.verwendungszweck or "").lower().replace("-", "")
    hat_keyword = any(kw in verwendung_lower for kw in _RUECKERSTATTUNG_KEYWORDS)

    for f in kandidaten:
        if f.rechnung_id:
            rechnung = db.query(Rechnung).filter(Rechnung.id == f.rechnung_id).first()
            if rechnung and rechnung.lieferant_id:
                lieferant = db.query(Lieferant).filter(Lieferant.id == rechnung.lieferant_id).first()
                if lieferant:
                    lieferant_name = (lieferant.firma or f"{lieferant.vorname or ''} {lieferant.nachname or ''}").strip()
                    if _name_match(lieferant_name, tx.partner_name):
                        return f

        if hat_keyword:
            return f

    return None


def _buche_pfad_a(
    db: Session,
    tx: BankTransaktion,
    rechnung: Rechnung,
    betrag_zu_buchen: Optional[Decimal] = None,
    unternehmen: Optional[Unternehmen] = None,
) -> tuple[Journaleintrag, Optional[Forderung]]:
    """Bucht Transaktion gegen Rechnung. Bei Überzahlung: Split + Forderung (Lieferanten-/Kundenguthaben)."""
    if unternehmen is None:
        unternehmen = db.query(Unternehmen).first()

    restbetrag = abs(rechnung.brutto_gesamt - rechnung.bezahlt_betrag)
    art = "Einnahme" if rechnung.typ == "ausgang" else "Ausgabe"
    tx_abs = abs(tx.betrag)

    if betrag_zu_buchen is None:
        # Bei Überzahlung immer nur den Restbetrag buchen – Surplus wird als Guthaben erfasst
        betrag_zu_buchen = restbetrag if tx_abs > restbetrag + Decimal("0.02") else tx_abs

    steuerbefreiung_grund = "§19 UStG" if (unternehmen and unternehmen.ist_kleinunternehmer) else None
    ust_satz = Decimal("0")
    kat_id = None

    if not (unternehmen and unternehmen.ist_kleinunternehmer) and rechnung.positionen:
        gruppen_brutto: dict[int, Decimal] = {}
        kat_gruppen: dict[int | None, Decimal] = {}
        for pos in rechnung.positionen:
            s = int(pos.ust_satz_25a if pos.differenzbesteuerung and pos.ust_satz_25a else pos.ust_satz)
            gruppen_brutto[s] = gruppen_brutto.get(s, Decimal("0")) + pos.brutto
            kat_gruppen[pos.kategorie_id] = kat_gruppen.get(pos.kategorie_id, Decimal("0")) + pos.brutto
        dom_satz = max(gruppen_brutto, key=lambda s: gruppen_brutto[s])
        ust_satz = Decimal(str(dom_satz))
        kat_id = max(kat_gruppen, key=lambda k: kat_gruppen[k] if k is not None else Decimal("0"))

    kat = db.query(Kategorie).filter(Kategorie.id == kat_id).first() if kat_id else None
    konto_ust_skr03, konto_ust_skr04 = _ust_konto(art, ust_satz) if ust_satz > 0 else (None, None)

    if ust_satz > 0:
        netto = (betrag_zu_buchen * 100 / (100 + ust_satz)).quantize(Decimal("0.01"), ROUND_HALF_UP)
        ust_betrag = (betrag_zu_buchen - netto).quantize(Decimal("0.01"), ROUND_HALF_UP)
    else:
        netto = betrag_zu_buchen
        ust_betrag = Decimal("0.00")

    vst_abzug = art == "Ausgabe" and ust_satz > 0
    eintrag = Journaleintrag(
        datum=tx.datum,
        belegnr=_naechste_belegnr(db, tx.datum),
        beschreibung=f"Zahlung {rechnung.rechnungsnummer}: {_partner_name(rechnung)}",
        kategorie_id=kat_id,
        konto_skr03=kat.konto_skr03 if kat else None,
        konto_skr04=kat.konto_skr04 if kat else None,
        konto_ust_skr03=konto_ust_skr03,
        konto_ust_skr04=konto_ust_skr04,
        zahlungsart="Bank",
        art=art,
        netto_betrag=netto,
        ust_satz=ust_satz,
        ust_betrag=ust_betrag,
        vorsteuer_betrag=_berechne_vorsteuer(ust_betrag, vst_abzug, kat),
        brutto_betrag=betrag_zu_buchen,
        vorsteuerabzug=vst_abzug,
        steuerbefreiung_grund=steuerbefreiung_grund,
        rechnung_id=rechnung.id,
        konto_id=tx.konto_id,
        immutable=True,
    )
    eintrag.signatur = signatur_journaleintrag(eintrag)
    db.add(eintrag)
    db.flush()

    tx.rechnung_id = rechnung.id
    tx.journal_id = eintrag.id
    _aktualisiere_zahlungsstatus(rechnung)

    # Guthaben bei Überzahlung: Lieferantenguthaben (Eingang) oder Kundenguthaben (Ausgang)
    forderung = None
    surplus = tx_abs - betrag_zu_buchen
    if surplus > Decimal("0.02"):
        if rechnung.typ == "eingang":
            forderung = Forderung(
                typ="lieferantenguthaben",
                betrag=surplus,
                partner_typ="lieferant",
                partner_id=rechnung.lieferant_id,
                rechnung_id=rechnung.id,
                journal_id=eintrag.id,
                notiz=f"Überzahlung: {_partner_name(rechnung)} · {surplus:.2f} €",
            )
        else:
            forderung = Forderung(
                typ="kundenguthaben",
                betrag=surplus,
                partner_typ="kunde",
                partner_id=rechnung.kunde_id,
                rechnung_id=rechnung.id,
                journal_id=eintrag.id,
                notiz=f"Überzahlung: {_partner_name(rechnung)} · {surplus:.2f} €",
            )
        db.add(forderung)
        db.flush()

    return eintrag, forderung


def _buche_pfad_b(db: Session, tx: BankTransaktion) -> Journaleintrag:
    """Freie Buchung ohne Rechnungsbezug – Kategorie muss gesetzt sein."""
    art = "Einnahme" if tx.betrag > 0 else "Ausgabe"
    brutto = abs(tx.betrag)
    teile = [t for t in [tx.partner_name, tx.verwendungszweck] if t]
    beschreibung = " / ".join(teile)[:255] or "Bank-Transaktion"

    journal_data = JournalEintragCreate(
        datum=tx.datum,
        beschreibung=beschreibung,
        kategorie_id=tx.kategorie_id,
        zahlungsart="Bank",
        art=art,
        brutto_betrag=brutto,
        ust_satz=Decimal("0"),
        vorsteuerabzug=True,
    )
    felder = _felder_aus_data(journal_data, db)
    belegnr = _naechste_belegnr(db, tx.datum)
    eintrag = Journaleintrag(belegnr=belegnr, konto_id=tx.konto_id, immutable=False, **felder)
    eintrag.signatur = signatur_journaleintrag(eintrag)
    db.add(eintrag)
    db.flush()
    tx.journal_id = eintrag.id
    return eintrag


def _enriche_tx(tx: BankTransaktion, rechnungen_map: dict, journale_map: dict) -> BankTransaktionResponse:
    """Reichert eine BankTransaktion mit Rechnung-Kurzinfo an."""
    resp = BankTransaktionResponse.model_validate(tx)
    if tx.rechnung_id and tx.rechnung_id in rechnungen_map:
        r = rechnungen_map[tx.rechnung_id]
        j = journale_map.get(tx.journal_id) if tx.journal_id else None
        resp.rechnung_info = RechnungKurzinfo(
            rechnungsnummer=r.rechnungsnummer or "?",
            partner=_partner_name(r),
            brutto_gesamt=r.brutto_gesamt,
            gebuchter_betrag=j.brutto_betrag if j else abs(tx.betrag),
        )
    return resp


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/vorschau", response_model=VorschauResponse)
async def vorschau_import(
    datei: UploadFile = File(...),
    konto_id: Optional[int] = Form(None),
    template_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    if konto_id is not None and not db.query(Konto).filter(Konto.id == konto_id).first():
        raise HTTPException(status_code=404, detail="Konto nicht gefunden.")

    raw = await datei.read()
    templates = db.query(BankTemplate).all()

    if template_id:
        template = db.query(BankTemplate).filter(BankTemplate.id == template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template nicht gefunden.")
    else:
        enc = detect_encoding(raw)
        text_content = raw.decode(enc, errors="replace")
        delim = detect_delimiter(text_content)
        import csv as csv_mod
        lines = text_content.splitlines()
        reader = csv_mod.reader(lines[:1], delimiter=delim, quotechar='"')
        header = next(reader, [])
        template = find_best_template(header, templates)

    if not template:
        raise HTTPException(
            status_code=422,
            detail="Kein passendes Template gefunden. Bitte Template manuell auswählen.",
        )

    # IBAN aus CSV-Header extrahieren und Konto im System suchen
    konto_iban = extract_konto_iban(raw, template)
    erkanntes_konto_id = konto_id  # übernehmen falls manuell übergeben

    if konto_iban and konto_id is None:
        konto = db.query(Konto).filter(
            Konto.iban == konto_iban,
            Konto.aktiv == True,
        ).first()
        if konto:
            erkanntes_konto_id = konto.id

    transaktionen, enc = parse_csv_mit_template(raw, template)
    hashes = _vorhandene_hashes(db, erkanntes_konto_id) if erkanntes_konto_id else set()

    result = []
    for tx in transaktionen:
        h = _dedupe_hash(tx)
        result.append(TransaktionVorschau(
            datum=tx["datum"],
            valuta=tx.get("valuta"),
            buchungstext=tx.get("buchungstext"),
            verwendungszweck=tx.get("verwendungszweck"),
            partner_name=tx.get("partner_name"),
            partner_iban=tx.get("partner_iban"),
            betrag=tx["betrag"],
            waehrung=tx.get("waehrung", "EUR"),
            saldo=tx.get("saldo"),
            referenz=tx.get("referenz"),
            dedupe_hash=h,
            ist_duplikat=h in hashes,
        ))

    return VorschauResponse(
        erkanntes_template=template.id,
        template_name=template.name,
        encoding=enc,
        konto_iban=konto_iban,
        erkanntes_konto_id=erkanntes_konto_id,
        transaktionen=result,
    )


@router.post("/importieren", response_model=ImportiereResponse, status_code=201)
def importieren(data: ImportiereRequest, db: Session = Depends(get_db)):
    if not db.query(Konto).filter(Konto.id == data.konto_id).first():
        raise HTTPException(status_code=404, detail="Konto nicht gefunden.")
    if not db.query(BankTemplate).filter(BankTemplate.id == data.template_id).first():
        raise HTTPException(status_code=404, detail="Template nicht gefunden.")

    hashes = _vorhandene_hashes(db, data.konto_id)

    bank_import = BankImport(
        konto_id=data.konto_id,
        template_id=data.template_id,
        dateiname=data.dateiname,
        anzahl_zeilen=len(data.transaktionen),
    )
    db.add(bank_import)
    db.flush()

    erfolg = duplikate = fehler = 0

    for tx in data.transaktionen:
        if tx.dedupe_hash in hashes:
            duplikate += 1
            continue
        try:
            bt = BankTransaktion(
                konto_id=data.konto_id,
                import_id=bank_import.id,
                datum=tx.datum,
                valuta=tx.valuta,
                buchungstext=tx.buchungstext,
                verwendungszweck=tx.verwendungszweck,
                partner_name=tx.partner_name,
                partner_iban=tx.partner_iban,
                betrag=tx.betrag,
                waehrung=tx.waehrung,
                saldo=tx.saldo,
                dedupe_hash=tx.dedupe_hash,
            )
            db.add(bt)
            db.flush()
            hashes.add(tx.dedupe_hash)
            erfolg += 1
        except Exception:
            db.rollback()
            fehler += 1

    bank_import.erfolg = erfolg
    bank_import.duplikate = duplikate
    bank_import.fehler = fehler
    db.commit()

    return ImportiereResponse(
        import_id=bank_import.id,
        erfolg=erfolg,
        duplikate=duplikate,
        fehler=fehler,
    )


@router.post("/{konto_id}/auto-buchen", response_model=AutoBuchenResult)
def auto_buchen(konto_id: int, import_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Batch: pending Transaktionen des aktuellen Imports abgleichen und eindeutige Treffer buchen."""
    if not db.query(Konto).filter(Konto.id == konto_id).first():
        raise HTTPException(status_code=404, detail="Konto nicht gefunden.")

    q = (
        db.query(BankTransaktion)
        .filter(
            BankTransaktion.konto_id == konto_id,
            BankTransaktion.ist_geschaeftlich == True,
            BankTransaktion.ist_privatentnahme == False,
            BankTransaktion.ist_einlage == False,
            BankTransaktion.journal_id == None,
        )
    )
    if import_id is not None:
        q = q.filter(BankTransaktion.import_id == import_id)
    pending = q.order_by(BankTransaktion.datum.asc()).all()

    unternehmen = db.query(Unternehmen).first()
    gebucht = offen = forderungen = fehler = 0

    for tx in pending:
        try:
            # Ausgehende Zahlung: Kundenguthaben-Rückerstattung erkennen
            guthaben = _match_kundenguthaben(db, tx)
            if guthaben:
                guthaben.status = "ausgeglichen"
                tx.ist_rueckerstattung = True
                gebucht += 1
                continue

            # Eingehende Zahlung: Lieferantenguthaben-Rückerstattung erkennen
            lguthaben = _match_lieferantenguthaben(db, tx)
            if lguthaben:
                lguthaben.status = "ausgeglichen"
                tx.ist_rueckerstattung = True
                gebucht += 1
                continue

            rechnung_typ = "ausgang" if tx.betrag > 0 else "eingang"
            offene = db.query(Rechnung).filter(
                Rechnung.ist_entwurf == False,
                Rechnung.storniert == False,
                Rechnung.zahlungsstatus != "bezahlt",
                Rechnung.dokument_typ == "Rechnung",
                Rechnung.typ == rechnung_typ,
            ).all()

            score3_treffer = [r for r in offene if _abgleich_score(r, tx)[0] == 3]

            if len(score3_treffer) == 1:
                _, forderung = _buche_pfad_a(db, tx, score3_treffer[0], unternehmen=unternehmen)
                gebucht += 1
                if forderung:
                    forderungen += 1
            elif tx.kategorie_id:
                _buche_pfad_b(db, tx)
                gebucht += 1
            else:
                offen += 1
        except Exception:
            fehler += 1

    db.commit()
    return AutoBuchenResult(gebucht=gebucht, offen=offen, forderungen=forderungen, fehler=fehler, import_id=import_id)


@router.get("/{konto_id}", response_model=list[BankTransaktionResponse])
def get_transaktionen(
    konto_id: int,
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if not db.query(Konto).filter(Konto.id == konto_id).first():
        raise HTTPException(status_code=404, detail="Konto nicht gefunden.")

    txs = (
        db.query(BankTransaktion)
        .filter(BankTransaktion.konto_id == konto_id)
        .order_by(BankTransaktion.datum.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    rechnung_ids = [tx.rechnung_id for tx in txs if tx.rechnung_id]
    journal_ids = [tx.journal_id for tx in txs if tx.journal_id and tx.rechnung_id]

    rechnungen_map = {r.id: r for r in db.query(Rechnung).filter(Rechnung.id.in_(rechnung_ids)).all()} if rechnung_ids else {}
    journale_map = {j.id: j for j in db.query(Journaleintrag).filter(Journaleintrag.id.in_(journal_ids)).all()} if journal_ids else {}

    return [_enriche_tx(tx, rechnungen_map, journale_map) for tx in txs]


@router.patch("/transaktion/{tx_id}", response_model=BankTransaktionResponse)
def klassifiziere_transaktion(
    tx_id: int,
    data: TransaktionKlassifizierung,
    db: Session = Depends(get_db),
):
    tx = db.query(BankTransaktion).filter(BankTransaktion.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaktion nicht gefunden.")
    tx.ist_geschaeftlich = data.ist_geschaeftlich
    tx.ist_privatentnahme = data.ist_privatentnahme
    tx.ist_einlage = data.ist_einlage
    tx.kategorie_id = data.kategorie_id
    tx.user_ueberschrieben = True
    db.commit()
    db.refresh(tx)
    return _enriche_tx(tx, {}, {})


@router.delete("/import/{import_id}", status_code=204)
def loesche_import(import_id: int, db: Session = Depends(get_db)):
    bank_import = db.query(BankImport).filter(BankImport.id == import_id).first()
    if not bank_import:
        raise HTTPException(status_code=404, detail="Import nicht gefunden.")
    db.query(BankTransaktion).filter(BankTransaktion.import_id == import_id).delete()
    db.delete(bank_import)
    db.commit()


@router.get("/transaktion/{tx_id}/abgleich", response_model=list[AbgleichVorschlag])
def abgleich_transaktion(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(BankTransaktion).filter(BankTransaktion.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaktion nicht gefunden.")

    rechnung_typ = "ausgang" if tx.betrag > 0 else "eingang"
    offene = db.query(Rechnung).filter(
        Rechnung.ist_entwurf == False,
        Rechnung.storniert == False,
        Rechnung.zahlungsstatus != "bezahlt",
        Rechnung.dokument_typ == "Rechnung",
        Rechnung.typ == rechnung_typ,
    ).all()

    vorschlaege = []
    for rechnung in offene:
        score, bm, nm, nam = _abgleich_score(rechnung, tx)
        if score >= 1:
            restbetrag = rechnung.brutto_gesamt - rechnung.bezahlt_betrag
            vorschlaege.append(AbgleichVorschlag(
                rechnung_id=rechnung.id,
                rechnungsnummer=rechnung.rechnungsnummer or "?",
                externe_belegnr=rechnung.externe_belegnr or None,
                partner=_partner_name(rechnung),
                datum=rechnung.datum,
                brutto_gesamt=rechnung.brutto_gesamt,
                restbetrag=restbetrag,
                score=score,
                betrag_match=bm,
                nummer_match=nm,
                name_match=nam,
            ))

    vorschlaege.sort(key=lambda v: v.score, reverse=True)
    return vorschlaege


@router.post("/transaktion/{tx_id}/buchen", response_model=BankTransaktionResponse, status_code=201)
def buche_transaktion(
    tx_id: int,
    data: BuchungsRequest = Body(...),
    db: Session = Depends(get_db),
):
    """Einzelne Transaktion manuell buchen."""
    tx = db.query(BankTransaktion).filter(BankTransaktion.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaktion nicht gefunden.")
    if not tx.ist_geschaeftlich:
        raise HTTPException(status_code=409, detail="nicht_geschaeftlich")
    if tx.journal_id:
        raise HTTPException(status_code=409, detail="bereits_gebucht")

    forderung = None
    if data.rechnung_id:
        rechnung = db.query(Rechnung).filter(Rechnung.id == data.rechnung_id).first()
        if not rechnung:
            raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
        if rechnung.ist_entwurf:
            raise HTTPException(status_code=409, detail="Entwürfe können nicht kassiert werden.")
        if rechnung.storniert:
            raise HTTPException(status_code=409, detail="Stornierte Rechnungen können nicht bezahlt werden.")
        restbetrag = abs(rechnung.brutto_gesamt - rechnung.bezahlt_betrag)
        if restbetrag <= Decimal("0.004"):
            raise HTTPException(status_code=409, detail="Rechnung ist bereits vollständig bezahlt.")

        _, forderung = _buche_pfad_a(db, tx, rechnung, data.betrag_zu_buchen)
    else:
        if not tx.kategorie_id:
            raise HTTPException(status_code=422, detail="keine_kategorie")
        _buche_pfad_b(db, tx)

    db.commit()
    db.refresh(tx)

    resp = _enriche_tx(tx, {}, {})
    if tx.rechnung_id:
        r = db.query(Rechnung).filter(Rechnung.id == tx.rechnung_id).first()
        j = db.query(Journaleintrag).filter(Journaleintrag.id == tx.journal_id).first() if tx.journal_id else None
        if r:
            resp.rechnung_info = RechnungKurzinfo(
                rechnungsnummer=r.rechnungsnummer or "?",
                partner=_partner_name(r),
                brutto_gesamt=r.brutto_gesamt,
                gebuchter_betrag=j.brutto_betrag if j else abs(tx.betrag),
            )
    if forderung:
        resp.forderung_id = forderung.id

    return resp
