"""
Pydantic-Schemas für Request/Response-Validierung.
Getrennt von den SQLAlchemy-Models (database/models.py).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Unternehmen
# ---------------------------------------------------------------------------

class UnternehmenBase(BaseModel):
    firmenname: str
    vorname: Optional[str] = None
    nachname: Optional[str] = None
    strasse: str
    hausnummer: str
    plz: str
    ort: str
    land: str = "DE"
    steuernummer: Optional[str] = None
    ust_idnr: Optional[str] = None
    finanzamt: Optional[str] = None
    ist_kleinunternehmer: bool = False
    bezieht_transferleistungen: bool = False
    versteuerungsart: str = "ist"
    kontenrahmen: str = "SKR03"
    taetigkeitsart: str = "freiberuflich"
    rechtsform: str = "Einzelunternehmer"
    eu_handel_aktiv: bool = False
    geschaeftsjahr_beginn: int = 1
    email: Optional[str] = None
    telefon: Optional[str] = None
    webseite: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_name: Optional[str] = None

    @field_validator("versteuerungsart")
    @classmethod
    def check_versteuerungsart(cls, v: str) -> str:
        if v not in ("ist", "soll"):
            raise ValueError("versteuerungsart muss 'ist' oder 'soll' sein")
        return v

    @field_validator("kontenrahmen")
    @classmethod
    def check_kontenrahmen(cls, v: str) -> str:
        if v not in ("SKR03", "SKR04", "SKR49"):
            raise ValueError("kontenrahmen muss SKR03, SKR04 oder SKR49 sein")
        return v

    @field_validator("geschaeftsjahr_beginn")
    @classmethod
    def check_geschaeftsjahr(cls, v: int) -> int:
        if not 1 <= v <= 12:
            raise ValueError("geschaeftsjahr_beginn muss zwischen 1 und 12 liegen")
        return v


class UnternehmenCreate(UnternehmenBase):
    pass


class UnternehmenUpdate(UnternehmenBase):
    # Alle Felder optional beim Update
    firmenname: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None


class UnternehmenResponse(UnternehmenBase):
    id: int
    erstellt_am: datetime
    aktualisiert_am: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Konten
# ---------------------------------------------------------------------------

class KontoBase(BaseModel):
    name: str
    bank: str
    iban: str
    bic: Optional[str] = None
    kontotyp: str = "geschaeftlich"
    ist_standard: bool = False

    @field_validator("iban")
    @classmethod
    def check_iban(cls, v: str) -> str:
        iban = v.replace(" ", "").upper()
        if len(iban) < 15 or len(iban) > 34:
            raise ValueError("IBAN muss zwischen 15 und 34 Zeichen lang sein")
        return iban

    @field_validator("kontotyp")
    @classmethod
    def check_kontotyp(cls, v: str) -> str:
        if v not in ("geschaeftlich", "mischkonto", "privat"):
            raise ValueError("kontotyp muss 'geschaeftlich', 'mischkonto' oder 'privat' sein")
        return v


class KontoCreate(KontoBase):
    pass


class KontoUpdate(BaseModel):
    name: Optional[str] = None
    bank: Optional[str] = None
    bic: Optional[str] = None
    kontotyp: Optional[str] = None
    ist_standard: Optional[bool] = None
    aktiv: Optional[bool] = None


class KontoResponse(KontoBase):
    id: int
    aktiv: bool
    erstellt_am: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Kategorien
# ---------------------------------------------------------------------------

class KategorieResponse(BaseModel):
    id: int
    name: str
    kontenart: str
    konto_skr03: Optional[str]
    konto_skr04: Optional[str]
    konto_skr49: Optional[str]
    eks_kategorie: Optional[str]
    euer_zeile: Optional[int]
    vorsteuer_prozent: Decimal
    ist_system: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Setup-Status (wird beim Start abgefragt)
# ---------------------------------------------------------------------------

class SetupStatus(BaseModel):
    ist_eingerichtet: bool
    hat_unternehmen: bool
    hat_konto: bool
    hat_kategorien: bool
