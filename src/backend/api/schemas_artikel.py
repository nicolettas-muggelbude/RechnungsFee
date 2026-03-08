"""Pydantic-Schemas für den Artikelstamm."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


GUELTIGE_TYPEN = {"artikel", "dienstleistung", "fremdleistung"}


class ArtikelCreate(BaseModel):
    typ: str
    bezeichnung: str
    einheit: str = "Stück"
    steuersatz: Decimal = Decimal("19")
    vk_brutto: Decimal
    ek_netto: Optional[Decimal] = None
    lieferant_id: Optional[int] = None
    lieferanten_artikelnr: Optional[str] = None
    hersteller: Optional[str] = None
    artikelcode: Optional[str] = None
    beschreibung: Optional[str] = None
    kategorie: Optional[str] = None

    @field_validator("typ")
    @classmethod
    def check_typ(cls, v: str) -> str:
        if v not in GUELTIGE_TYPEN:
            raise ValueError(f"typ muss einer von {sorted(GUELTIGE_TYPEN)} sein")
        return v

    @field_validator("vk_brutto")
    @classmethod
    def check_vk(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("vk_brutto muss positiv sein")
        return v

    @field_validator("steuersatz")
    @classmethod
    def check_steuersatz(cls, v: Decimal) -> Decimal:
        if v not in (Decimal("0"), Decimal("7"), Decimal("19")):
            raise ValueError("steuersatz muss 0, 7 oder 19 sein")
        return v

    @model_validator(mode="after")
    def check_fremdleistung(self) -> "ArtikelCreate":
        if self.typ == "fremdleistung" and not self.lieferant_id:
            raise ValueError("Fremdleistung erfordert einen Lieferanten")
        return self


class ArtikelUpdate(BaseModel):
    typ: Optional[str] = None
    bezeichnung: Optional[str] = None
    einheit: Optional[str] = None
    steuersatz: Optional[Decimal] = None
    vk_brutto: Optional[Decimal] = None
    ek_netto: Optional[Decimal] = None
    lieferant_id: Optional[int] = None
    lieferanten_artikelnr: Optional[str] = None
    hersteller: Optional[str] = None
    artikelcode: Optional[str] = None
    beschreibung: Optional[str] = None
    kategorie: Optional[str] = None
    aktiv: Optional[bool] = None

    @field_validator("typ")
    @classmethod
    def check_typ(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in GUELTIGE_TYPEN:
            raise ValueError(f"typ muss einer von {sorted(GUELTIGE_TYPEN)} sein")
        return v


class ArtikelLieferantKurz(BaseModel):
    id: int
    firmenname: str
    lieferantennummer: Optional[str] = None
    model_config = {"from_attributes": True}


class ArtikelResponse(BaseModel):
    id: int
    artikelnummer: str
    typ: str
    bezeichnung: str
    einheit: str
    steuersatz: Decimal
    vk_brutto: Decimal
    vk_netto: Decimal
    ek_netto: Optional[Decimal] = None
    ek_brutto: Optional[Decimal] = None
    lieferant_id: Optional[int] = None
    lieferant: Optional[ArtikelLieferantKurz] = None
    lieferanten_artikelnr: Optional[str] = None
    hersteller: Optional[str] = None
    artikelcode: Optional[str] = None
    beschreibung: Optional[str] = None
    kategorie: Optional[str] = None
    aktiv: bool
    erstellt_am: datetime
    aktualisiert_am: datetime
    model_config = {"from_attributes": True}


class ArtikelSucheResponse(BaseModel):
    """Kompaktes Schema für Autocomplete in Rechnungspositionen."""
    id: int
    artikelnummer: str
    typ: str
    bezeichnung: str
    einheit: str
    steuersatz: Decimal
    vk_brutto: Decimal
    vk_netto: Decimal
    lieferant_name: Optional[str] = None
    model_config = {"from_attributes": True}


class ArtikelRechnungKurz(BaseModel):
    """Rechnung in der ein Artikel vorkommt – für das Detail-Panel."""
    rechnung_id: int
    rechnungsnummer: Optional[str]
    datum: str
    menge: Decimal
    einheit: str
    vk_brutto: Decimal
    kunde_id: Optional[int]
    kunde_name: Optional[str]
    model_config = {"from_attributes": True}
