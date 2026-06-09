"""
Pydantic-Schemas für Rechnungen (Eingang + Ausgang).
Getrennt von schemas.py wegen Umfang.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Beleg
# ---------------------------------------------------------------------------

class BelegResponse(BaseModel):
    id: int
    dateiname: str
    original_name: str
    mime_type: Optional[str]
    dateigroesse: Optional[int]
    sha256: Optional[str]
    hochgeladen_am: datetime
    pdfa_verfuegbar: bool = False

    model_config = {"from_attributes": True}

    @classmethod
    def from_beleg(cls, beleg) -> "BelegResponse":
        return cls(
            id=beleg.id,
            dateiname=beleg.dateiname,
            original_name=beleg.original_name,
            mime_type=beleg.mime_type,
            dateigroesse=beleg.dateigroesse,
            sha256=beleg.sha256,
            hochgeladen_am=beleg.hochgeladen_am,
            pdfa_verfuegbar=bool(beleg.beleg_pdfa_pfad),
        )


# ---------------------------------------------------------------------------
# Rechnungspositionen
# ---------------------------------------------------------------------------

class RechnungspositionCreate(BaseModel):
    beschreibung: str
    menge: Decimal = Decimal("1.000")
    einheit: str = "Stück"
    netto: Decimal
    ust_satz: Decimal = Decimal("0")
    artikel_id: Optional[int] = None
    kategorie_id: Optional[int] = None
    differenzbesteuerung: bool = False

    @field_validator("ust_satz")
    @classmethod
    def check_ust_satz(cls, v: Decimal) -> Decimal:
        if v < Decimal("0") or v > Decimal("100"):
            raise ValueError("ust_satz muss zwischen 0 und 100 liegen")
        return v

    @field_validator("menge")
    @classmethod
    def check_menge(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("menge darf nicht 0 sein")
        return v


class RechnungspositionResponse(BaseModel):
    id: int
    artikel_id: Optional[int] = None
    artikel_typ: Optional[str] = None
    kategorie_id: Optional[int] = None
    position_nr: int
    beschreibung: str
    menge: Decimal
    einheit: str
    netto: Decimal
    ust_satz: Decimal
    ust_betrag: Decimal
    brutto: Decimal
    differenzbesteuerung: bool = False

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Rechnung
# ---------------------------------------------------------------------------

class RechnungCreate(BaseModel):
    typ: str  # eingang|ausgang
    rechnungsnummer: Optional[str] = None
    datum: date
    leistung_von: Optional[date] = None
    leistung_bis: Optional[date] = None
    faellig_am: Optional[date] = None
    kunde_id: Optional[int] = None
    lieferant_id: Optional[int] = None
    partner_freitext: Optional[str] = None
    kategorie_id: Optional[int] = None
    notizen: Optional[str] = None
    externe_belegnr: Optional[str] = None
    ist_entwurf: bool = True
    skonto_prozent: Optional[Decimal] = None
    skonto_tage: Optional[int] = None
    dokument_typ: str = "Rechnung"
    lieferadresse_id: Optional[int] = None
    gueltig_bis: Optional[date] = None
    dokumentenpaket_id: Optional[int] = None
    positionen: List[RechnungspositionCreate]

    @field_validator("dokument_typ")
    @classmethod
    def check_dokument_typ(cls, v: str) -> str:
        if v not in ("Rechnung", "Gutschrift", "Lieferschein", "Angebot", "Proforma"):
            raise ValueError("dokument_typ muss 'Rechnung', 'Gutschrift', 'Lieferschein', 'Angebot' oder 'Proforma' sein")
        return v

    @model_validator(mode="after")
    def check_leistungszeitraum(self) -> "RechnungCreate":
        if self.leistung_bis and self.leistung_von and self.leistung_bis < self.leistung_von:
            raise ValueError("leistung_bis darf nicht vor leistung_von liegen")
        return self

    @model_validator(mode="after")
    def check_netto_positionen(self) -> "RechnungCreate":
        if self.dokument_typ not in ("Lieferschein", "Angebot", "Proforma"):
            for pos in self.positionen:
                if pos.netto == 0:
                    raise ValueError("Position netto darf nicht 0 sein")
        return self

    # Direkt-Übernahme aus XML-Import – überschreibt die berechneten Gesamtbeträge
    netto_gesamt_override: Optional[Decimal] = None
    ust_gesamt_override: Optional[Decimal] = None
    brutto_gesamt_override: Optional[Decimal] = None

    @field_validator("typ")
    @classmethod
    def check_typ(cls, v: str) -> str:
        if v not in ("eingang", "ausgang"):
            raise ValueError("typ muss 'eingang' oder 'ausgang' sein")
        return v

    @field_validator("positionen")
    @classmethod
    def check_positionen(cls, v: List[RechnungspositionCreate]) -> List[RechnungspositionCreate]:
        if not v:
            raise ValueError("Mindestens eine Position erforderlich")
        return v

    @model_validator(mode="after")
    def check_partner(self) -> "RechnungCreate":
        if self.typ == "ausgang" and not self.kunde_id and not self.partner_freitext:
            raise ValueError("Ausgangsrechnung benötigt einen Kunden oder partner_freitext")
        if self.typ == "eingang" and not self.lieferant_id and not self.partner_freitext:
            raise ValueError("Eingangsrechnung benötigt einen Lieferanten oder partner_freitext")
        return self


class RechnungUpdate(BaseModel):
    rechnungsnummer: Optional[str] = None
    datum: Optional[date] = None
    leistung_von: Optional[date] = None
    leistung_bis: Optional[date] = None
    faellig_am: Optional[date] = None
    kunde_id: Optional[int] = None
    lieferant_id: Optional[int] = None
    partner_freitext: Optional[str] = None
    kategorie_id: Optional[int] = None
    notizen: Optional[str] = None
    externe_belegnr: Optional[str] = None
    ist_entwurf: Optional[bool] = None
    skonto_prozent: Optional[Decimal] = None
    skonto_tage: Optional[int] = None
    gueltig_bis: Optional[date] = None
    dokumentenpaket_id: Optional[int] = None
    positionen: Optional[List[RechnungspositionCreate]] = None


# Kompakte Zahlungsinfo für die Rechnung-Response
class ZahlungKompakt(BaseModel):
    id: int
    belegnr: str
    datum: date
    brutto_betrag: Decimal
    art: str
    zahlungsart: str

    model_config = {"from_attributes": True}


class RechnungResponse(BaseModel):
    id: int
    typ: str
    rechnungsnummer: Optional[str]
    datum: date
    faellig_am: Optional[date]
    kunde_id: Optional[int]
    kunde_name: Optional[str] = None
    kunde_email: Optional[str] = None
    lieferant_id: Optional[int]
    lieferant_name: Optional[str] = None
    lieferant_email: Optional[str] = None
    partner_freitext: Optional[str]
    kategorie_id: Optional[int]
    netto_gesamt: Decimal
    ust_gesamt: Decimal
    brutto_gesamt: Decimal
    bezahlt: bool
    bezahlt_betrag: Decimal
    zahlungsstatus: str
    zahlungsdatum: Optional[date]
    notizen: Optional[str]
    externe_belegnr: Optional[str]
    leistung_von: Optional[date]
    leistung_bis: Optional[date]
    skonto_prozent: Optional[Decimal] = None
    skonto_tage: Optional[int] = None
    ist_entwurf: bool
    ausgegeben: bool
    positionen: List[RechnungspositionResponse] = []
    zahlungen: List[ZahlungKompakt] = []
    beleg: Optional[BelegResponse] = None
    immutable: bool
    storniert: bool
    storno_grund: Optional[str] = None
    dokument_typ: str = "Rechnung"
    gutschrift_zu_rechnung_id: Optional[int] = None
    gutschrift_zu_rechnung_nr: Optional[str] = None  # wird in from_orm_extended befüllt
    lieferschein_zu_rechnung_id: Optional[int] = None
    lieferschein_rechnung_ist_entwurf: Optional[bool] = None  # wird in from_orm_extended befüllt
    lieferschein_zu_rechnung_nr: Optional[str] = None  # wird in from_orm_extended befüllt
    hat_lieferschein: bool = False      # wird in from_orm_extended befüllt
    lieferschein_anzahl: int = 0        # wird in from_orm_extended befüllt
    linked_lieferschein_id: Optional[int] = None   # nur bei genau 1 Lieferschein
    linked_lieferschein_nr: Optional[str] = None   # nur bei genau 1 Lieferschein
    lieferadresse_id: Optional[int] = None
    lieferadresse_text: Optional[str] = None  # wird in from_orm_extended befüllt
    # Angebote
    angebot_status: Optional[str] = None
    gueltig_bis: Optional[date] = None
    dokumentenpaket_id: Optional[int] = None
    rechnung_zu_angebot_id: Optional[int] = None
    rechnung_zu_angebot_nr: Optional[str] = None  # wird in from_orm_extended befüllt
    lieferschein_zu_angebot_id: Optional[int] = None
    lieferschein_zu_angebot_nr: Optional[str] = None  # wird in from_orm_extended befüllt
    # Proforma: auf Angebot → welche Proforma daraus entstand
    proforma_zu_angebot_id: Optional[int] = None
    proforma_zu_angebot_nr: Optional[str] = None  # wird in from_orm_extended befüllt
    # Proforma: auf Proforma → welche Rechnung daraus entstand + aus welchem Angebot
    rechnung_zu_proforma_id: Optional[int] = None
    rechnung_zu_proforma_nr: Optional[str] = None  # wird in from_orm_extended befüllt
    angebot_zu_proforma_id: Optional[int] = None   # wird in from_orm_extended befüllt
    angebot_zu_proforma_nr: Optional[str] = None   # wird in from_orm_extended befüllt
    erstellt_am: datetime
    aktualisiert_am: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_extended(cls, obj) -> "RechnungResponse":
        data = cls.model_validate(obj)
        for pos_data, pos_orm in zip(data.positionen, obj.positionen):
            if pos_orm.artikel:
                pos_data.artikel_typ = pos_orm.artikel.typ
        if obj.kunde:
            parts = [obj.kunde.firmenname or "", obj.kunde.vorname or "", obj.kunde.nachname or ""]
            data.kunde_name = " ".join(p for p in parts if p) or None
            data.kunde_email = obj.kunde.email
        if obj.lieferant:
            parts = [obj.lieferant.firmenname or "", obj.lieferant.vorname or "", obj.lieferant.nachname or ""]
            data.lieferant_name = " ".join(p for p in parts if p) or None
            data.lieferant_email = obj.lieferant.email
        data.zahlungen = [
            ZahlungKompakt(
                id=e.id,
                belegnr=e.belegnr,
                datum=e.datum,
                brutto_betrag=e.brutto_betrag,
                art=e.art,
                zahlungsart=e.zahlungsart,
            )
            for e in obj.journaleintraege
        ]
        if obj.beleg_id and hasattr(obj, "beleg") and obj.beleg:
            data.beleg = BelegResponse.from_beleg(obj.beleg)
        if obj.gutschrift_zu_rechnung_id and hasattr(obj, "_gutschrift_original_nr"):
            data.gutschrift_zu_rechnung_nr = obj._gutschrift_original_nr
        if obj.lieferadresse_id and hasattr(obj, "_lieferadresse"):
            la = obj._lieferadresse
            if la:
                teile = [la.bezeichnung, la.z_hd,
                         " ".join(filter(None, [la.strasse, la.hausnummer])),
                         " ".join(filter(None, [la.plz, la.ort]))]
                data.lieferadresse_text = "\n".join(t for t in teile if t)
        if obj.lieferschein_zu_rechnung_id:
            try:
                from sqlalchemy import inspect as _sa_inspect
                session = _sa_inspect(obj).session
                if session:
                    linked = session.get(obj.__class__, obj.lieferschein_zu_rechnung_id)
                    if linked:
                        data.lieferschein_rechnung_ist_entwurf = linked.ist_entwurf
                        data.lieferschein_zu_rechnung_nr = linked.rechnungsnummer
            except Exception:
                pass
        try:
            from sqlalchemy import inspect as _sa_inspect
            session = _sa_inspect(obj).session
            if session:
                ls_list = session.query(obj.__class__).filter(
                    obj.__class__.lieferschein_zu_rechnung_id == obj.id,
                    obj.__class__.dokument_typ == "Lieferschein",
                    obj.__class__.storniert == False,
                ).all()
                if ls_list:
                    data.hat_lieferschein = True
                    data.lieferschein_anzahl = len(ls_list)
                    if len(ls_list) == 1:
                        data.linked_lieferschein_id = ls_list[0].id
                        data.linked_lieferschein_nr = ls_list[0].rechnungsnummer
        except Exception:
            pass
        # Rechnungsnummer der aus dem Angebot erstellten Rechnung
        if obj.rechnung_zu_angebot_id:
            try:
                from sqlalchemy import inspect as _sa_inspect
                session = _sa_inspect(obj).session
                if session:
                    linked_re = session.get(obj.__class__, obj.rechnung_zu_angebot_id)
                    if linked_re:
                        data.rechnung_zu_angebot_nr = linked_re.rechnungsnummer
            except Exception:
                pass
        if obj.lieferschein_zu_angebot_id:
            try:
                from sqlalchemy import inspect as _sa_inspect
                session = _sa_inspect(obj).session
                if session:
                    linked_ls = session.get(obj.__class__, obj.lieferschein_zu_angebot_id)
                    if linked_ls:
                        data.lieferschein_zu_angebot_nr = linked_ls.rechnungsnummer
            except Exception:
                pass
        # Proforma-Links auflösen
        if obj.proforma_zu_angebot_id:
            try:
                from sqlalchemy import inspect as _sa_inspect
                session = _sa_inspect(obj).session
                if session:
                    linked_pf = session.get(obj.__class__, obj.proforma_zu_angebot_id)
                    if linked_pf:
                        data.proforma_zu_angebot_nr = linked_pf.rechnungsnummer
            except Exception:
                pass
        if obj.rechnung_zu_proforma_id:
            try:
                from sqlalchemy import inspect as _sa_inspect
                session = _sa_inspect(obj).session
                if session:
                    linked_re = session.get(obj.__class__, obj.rechnung_zu_proforma_id)
                    if linked_re:
                        data.rechnung_zu_proforma_nr = linked_re.rechnungsnummer
            except Exception:
                pass
        # Bei Proforma: Eltern-Angebot ermitteln (Angebot, das proforma_zu_angebot_id == this.id hat)
        if getattr(obj, "dokument_typ", None) == "Proforma":
            try:
                from sqlalchemy import inspect as _sa_inspect
                session = _sa_inspect(obj).session
                if session:
                    eltern_ang = session.query(obj.__class__).filter(
                        obj.__class__.proforma_zu_angebot_id == obj.id,
                        obj.__class__.dokument_typ == "Angebot",
                    ).first()
                    if eltern_ang:
                        data.angebot_zu_proforma_id = eltern_ang.id
                        data.angebot_zu_proforma_nr = eltern_ang.rechnungsnummer
            except Exception:
                pass
        return data


# ---------------------------------------------------------------------------
# Analyse-Ergebnis (Stufe 2 – ZUGFeRD/XRechnung-Import)
# ---------------------------------------------------------------------------

class AnalysePositionResponse(BaseModel):
    beschreibung: str
    menge: str
    einheit: str
    netto: str
    ust_satz: str
    artikel_nr: Optional[str] = None


class AnalyseFelder(BaseModel):
    externe_belegnr: Optional[str] = None
    datum: Optional[str] = None
    faellig_am: Optional[str] = None
    gesamt_netto: Optional[str] = None
    gesamt_ust: Optional[str] = None
    gesamt_brutto: Optional[str] = None
    ust_satz: Optional[str] = None
    lieferant_name: Optional[str] = None
    lieferant_ust_id: Optional[str] = None
    lieferant_email: Optional[str] = None
    lieferant_strasse: Optional[str] = None
    lieferant_plz: Optional[str] = None
    lieferant_ort: Optional[str] = None
    konfidenz: Dict[str, str] = {}


class LieferantVorschlag(BaseModel):
    id: int
    name: str
    score: float


class AnalyseResponse(BaseModel):
    format: str   # zugferd | xrechnung | pdf | unbekannt
    felder: AnalyseFelder
    positionen: List[AnalysePositionResponse]
    warnungen: List[str]
    positionen_modus: str = "netto"   # "netto" | "brutto"
    temp_url: Optional[str] = None
    temp_path: Optional[str] = None
    lieferant_vorschlaege: List[LieferantVorschlag] = []


# ---------------------------------------------------------------------------
# Bar-Zahlung
# ---------------------------------------------------------------------------

class ZahlungSplitPosition(BaseModel):
    kategorie_id: int
    betrag: Decimal  # Brutto-Anteil dieser Split-Position
    beschreibung: str  # Positionsbeschreibung aus der Rechnungsposition

    @field_validator("betrag")
    @classmethod
    def check_betrag(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("betrag muss positiv sein")
        return v


class BarZahlungCreate(BaseModel):
    betrag: Optional[Decimal] = None  # None = Restbetrag
    datum: date
    zahlungsart: str = "Bar"  # Bar|Karte|PayPal|Bank
    beschreibung: Optional[str] = None
    kategorie_id: Optional[int] = None  # Pflicht für Eingangsrechnungen (ohne Split), wird beim Endpoint geprüft
    split: Optional[List["ZahlungSplitPosition"]] = None  # Split: ersetzt kategorie_id, Summe muss betrag ergeben
    skonto_betrag: Optional[Decimal] = None  # Skontobetrag wenn Skonto gewährt wird

    @field_validator("zahlungsart")
    @classmethod
    def check_zahlungsart(cls, v: str) -> str:
        if v not in ("Bar", "Karte", "PayPal", "Bank"):
            raise ValueError("zahlungsart muss Bar, Karte, PayPal oder Bank sein")
        return v

    @field_validator("betrag")
    @classmethod
    def check_betrag(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("betrag muss positiv sein")
        return v


class BarZahlungResult(BaseModel):
    journaleintrag_id: int
    journaleintrag_belegnr: str
    rechnung: RechnungResponse
