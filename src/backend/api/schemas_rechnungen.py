"""
Pydantic-Schemas für Rechnungen (Eingang + Ausgang).
Getrennt von schemas.py wegen Umfang.
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from pydantic import BaseModel, field_validator, model_validator


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

    @field_validator("netto")
    @classmethod
    def check_netto(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("netto muss positiv sein")
        return v

    @field_validator("ust_satz")
    @classmethod
    def check_ust_satz(cls, v: Decimal) -> Decimal:
        if v not in (Decimal("0"), Decimal("7"), Decimal("19")):
            raise ValueError("ust_satz muss 0, 7 oder 19 sein")
        return v

    @field_validator("menge")
    @classmethod
    def check_menge(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("menge muss positiv sein")
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

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Rechnung
# ---------------------------------------------------------------------------

class RechnungCreate(BaseModel):
    typ: str  # eingang|ausgang
    rechnungsnummer: Optional[str] = None
    datum: date
    leistungsdatum: Optional[date] = None
    faellig_am: Optional[date] = None
    kunde_id: Optional[int] = None
    lieferant_id: Optional[int] = None
    partner_freitext: Optional[str] = None
    kategorie_id: Optional[int] = None
    notizen: Optional[str] = None
    externe_belegnr: Optional[str] = None
    ist_entwurf: bool = True
    positionen: List[RechnungspositionCreate]

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
    leistungsdatum: Optional[date] = None
    faellig_am: Optional[date] = None
    kunde_id: Optional[int] = None
    lieferant_id: Optional[int] = None
    partner_freitext: Optional[str] = None
    kategorie_id: Optional[int] = None
    notizen: Optional[str] = None
    externe_belegnr: Optional[str] = None
    ist_entwurf: Optional[bool] = None
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
    leistungsdatum: Optional[date]
    ist_entwurf: bool
    ausgegeben: bool
    positionen: List[RechnungspositionResponse] = []
    zahlungen: List[ZahlungKompakt] = []
    immutable: bool
    storniert: bool
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
            for e in obj.kassenbucheintraege
        ]
        return data


# ---------------------------------------------------------------------------
# Bar-Zahlung
# ---------------------------------------------------------------------------

class BarZahlungCreate(BaseModel):
    betrag: Optional[Decimal] = None  # None = Restbetrag
    datum: date
    zahlungsart: str = "Bar"  # Bar|Karte|PayPal|Bank
    beschreibung: Optional[str] = None

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
    kassenbucheintrag_id: int
    kassenbucheintrag_belegnr: str
    rechnung: RechnungResponse
