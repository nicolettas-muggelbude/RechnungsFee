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
    vk_netto: Optional[Decimal] = None
    vk_eingabe: str = "brutto"  # netto|brutto - welcher der beiden Preise die eingegebene Wahrheit ist
    ek_netto: Optional[Decimal] = None
    lieferant_id: Optional[int] = None
    lieferanten_artikelnr: Optional[str] = None
    hersteller: Optional[str] = None
    artikelcode: Optional[str] = None
    beschreibung: Optional[str] = None
    gruppe_id: Optional[int] = None
    differenzbesteuerung: bool = False
    # Lagerführung
    lager_aktiv: bool = False
    bestand_aktuell: Optional[Decimal] = None
    mindestbestand: Decimal = Decimal("0")
    minusbestand_erlaubt: bool = False

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

    @field_validator("vk_eingabe")
    @classmethod
    def check_vk_eingabe(cls, v: str) -> str:
        if v not in ("netto", "brutto"):
            raise ValueError("vk_eingabe muss 'netto' oder 'brutto' sein")
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
    vk_netto: Optional[Decimal] = None
    vk_eingabe: Optional[str] = None  # netto|brutto
    ek_netto: Optional[Decimal] = None
    lieferant_id: Optional[int] = None
    lieferanten_artikelnr: Optional[str] = None
    hersteller: Optional[str] = None
    artikelcode: Optional[str] = None
    beschreibung: Optional[str] = None
    gruppe_id: Optional[int] = None
    aktiv: Optional[bool] = None
    differenzbesteuerung: Optional[bool] = None
    # Lagerführung
    lager_aktiv: Optional[bool] = None
    bestand_aktuell: Optional[Decimal] = None
    mindestbestand: Optional[Decimal] = None
    minusbestand_erlaubt: Optional[bool] = None  # None = nicht geändert

    @field_validator("typ")
    @classmethod
    def check_typ(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in GUELTIGE_TYPEN:
            raise ValueError(f"typ muss einer von {sorted(GUELTIGE_TYPEN)} sein")
        return v

    @field_validator("vk_eingabe")
    @classmethod
    def check_vk_eingabe(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("netto", "brutto"):
            raise ValueError("vk_eingabe muss 'netto' oder 'brutto' sein")
        return v


class ArtikelLieferantKurz(BaseModel):
    id: int
    firmenname: str
    lieferantennummer: Optional[str] = None
    model_config = {"from_attributes": True}


class ArtikelGruppeKurz(BaseModel):
    id: int
    name: str
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
    vk_eingabe: str = "brutto"
    ek_netto: Optional[Decimal] = None
    ek_brutto: Optional[Decimal] = None
    lieferant_id: Optional[int] = None
    lieferant: Optional[ArtikelLieferantKurz] = None
    lieferanten_artikelnr: Optional[str] = None
    hersteller: Optional[str] = None
    artikelcode: Optional[str] = None
    beschreibung: Optional[str] = None
    gruppe_id: Optional[int] = None
    gruppe_obj: Optional[ArtikelGruppeKurz] = None
    differenzbesteuerung: bool = False
    # Lagerführung
    lager_aktiv: bool = False
    bestand_aktuell: Decimal = Decimal("0")
    mindestbestand: Decimal = Decimal("0")
    minusbestand_erlaubt: bool = False
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
    ek_brutto: Optional[Decimal] = None
    differenzbesteuerung: bool = False
    lieferant_name: Optional[str] = None
    # Lagerführung – für Bestandswarnung im Rechnungsformular
    beschreibung: Optional[str] = None
    lager_aktiv: bool = False
    bestand_aktuell: Decimal = Decimal("0")
    minusbestand_erlaubt: bool = True
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
