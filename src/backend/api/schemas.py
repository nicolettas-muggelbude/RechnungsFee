"""
Pydantic-Schemas für Request/Response-Validierung.
Getrennt von den SQLAlchemy-Models (database/models.py).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
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
    handelsregister_nr: Optional[str] = None
    handelsregister_gericht: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    bank_name: Optional[str] = None
    logo_pfad: Optional[str] = None
    mail_betreff_vorlage: Optional[str] = None
    mail_text_vorlage: Optional[str] = None
    mail_signatur: Optional[str] = None

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
    ust_satz_standard: int
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


# ---------------------------------------------------------------------------
# Kassenbuch
# ---------------------------------------------------------------------------

class KassenbuchEintragCreate(BaseModel):
    datum: date
    beschreibung: str
    kategorie_id: Optional[int] = None
    kunde_id: Optional[int] = None
    zahlungsart: str = "Bar"  # Bar|Karte|Bank|PayPal
    art: str  # Einnahme|Ausgabe
    brutto_betrag: Decimal
    ust_satz: Decimal = Decimal("0")
    vorsteuerabzug: bool = False
    externe_belegnr: Optional[str] = None

    @field_validator("zahlungsart")
    @classmethod
    def check_zahlungsart(cls, v: str) -> str:
        if v not in ("Bar", "Karte", "Bank", "PayPal"):
            raise ValueError("zahlungsart muss Bar, Karte, Bank oder PayPal sein")
        return v

    @field_validator("art")
    @classmethod
    def check_art(cls, v: str) -> str:
        if v not in ("Einnahme", "Ausgabe"):
            raise ValueError("art muss Einnahme oder Ausgabe sein")
        return v

    @field_validator("brutto_betrag")
    @classmethod
    def check_betrag(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("brutto_betrag muss positiv sein")
        return v


class KassenbuchEintragResponse(BaseModel):
    id: int
    datum: date
    belegnr: str
    beschreibung: str
    kategorie_id: Optional[int]
    kategorie_kontenart: Optional[str] = None  # Erlös|Aufwand|Privat|Anlage
    kunde_id: Optional[int]
    kunde_name: Optional[str] = None   # aus Relationship befüllt
    kunde_email: Optional[str] = None
    zahlungsart: str
    art: str
    netto_betrag: Decimal
    ust_satz: Decimal
    ust_betrag: Decimal
    brutto_betrag: Decimal
    vorsteuerabzug: bool
    steuerbefreiung_grund: Optional[str]
    externe_belegnr: Optional[str] = None
    immutable: bool
    erstellt_am: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_kunde(cls, obj) -> "KassenbuchEintragResponse":
        data = cls.model_validate(obj)
        if obj.kunde:
            parts = [obj.kunde.firmenname or "", obj.kunde.vorname or "", obj.kunde.nachname or ""]
            data.kunde_name = " ".join(p for p in parts if p) or None
            data.kunde_email = obj.kunde.email
        if obj.kategorie:
            data.kategorie_kontenart = obj.kategorie.kontenart
        return data


class StornoRequest(BaseModel):
    grund: str


class SplitPosition(BaseModel):
    beschreibung: str
    kategorie_id: Optional[int] = None
    brutto_betrag: Decimal
    ust_satz: Decimal = Decimal("0")
    vorsteuerabzug: bool = False

    @field_validator("brutto_betrag")
    @classmethod
    def check_betrag(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("brutto_betrag muss positiv sein")
        return v


class SplitBuchungCreate(BaseModel):
    datum: date
    art: str
    zahlungsart: str = "Bar"
    externe_belegnr: Optional[str] = None
    kunde_id: Optional[int] = None
    positionen: List[SplitPosition]

    @field_validator("art")
    @classmethod
    def check_art(cls, v: str) -> str:
        if v not in ("Einnahme", "Ausgabe"):
            raise ValueError("art muss Einnahme oder Ausgabe sein")
        return v

    @field_validator("zahlungsart")
    @classmethod
    def check_zahlungsart(cls, v: str) -> str:
        if v not in ("Bar", "Karte", "Bank", "PayPal"):
            raise ValueError("zahlungsart muss Bar, Karte, Bank oder PayPal sein")
        return v

    @field_validator("positionen")
    @classmethod
    def check_positionen(cls, v: List[SplitPosition]) -> List[SplitPosition]:
        if len(v) < 2:
            raise ValueError("Mindestens 2 Positionen erforderlich")
        return v


class MonatsUebersicht(BaseModel):
    monat: str  # YYYY-MM
    einnahmen: Decimal
    ausgaben: Decimal
    saldo: Decimal
    anzahl_buchungen: int


# ---------------------------------------------------------------------------
# Tagesabschluss
# ---------------------------------------------------------------------------

class TagesabschlussCreate(BaseModel):
    datum: date
    ist_endbestand: Decimal
    zaehlung_json: Optional[str] = None  # JSON: Scheine/Münzen-Zählung
    differenz_begruendung: Optional[str] = None
    differenz_buchungsart: Optional[str] = None  # Privatentnahme|Aufwand|Protokoll


class TagesabschlussResponse(BaseModel):
    id: int
    datum: date
    uhrzeit: str
    anfangsbestand: Decimal
    einnahmen_bar: Decimal
    ausgaben_bar: Decimal
    soll_endbestand: Decimal
    ist_endbestand: Decimal
    differenz: Decimal
    differenz_begruendung: Optional[str]
    differenz_buchungsart: Optional[str]
    zaehlung_json: Optional[str]
    kassenbewegungen_anzahl: int
    immutable: bool
    signatur: Optional[str] = None
    erstellt_am: datetime

    model_config = {"from_attributes": True}


class TagesabschlussVorschau(BaseModel):
    datum: date
    anfangsbestand: Decimal
    einnahmen_bar: Decimal
    ausgaben_bar: Decimal
    soll_endbestand: Decimal
    kassenbewegungen_anzahl: int


# ---------------------------------------------------------------------------
# Kunden
# ---------------------------------------------------------------------------

class KundeBase(BaseModel):
    firmenname: Optional[str] = None
    vorname: Optional[str] = None
    nachname: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    land: str = "DE"
    ust_idnr: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    ist_verein: bool = False
    ist_gemeinnuetzig: bool = False
    kundennummer: Optional[str] = None
    notizen: Optional[str] = None


class KundeCreate(KundeBase):
    pass


class KundeUpdate(KundeBase):
    aktiv: Optional[bool] = None


class KundeResponse(KundeBase):
    id: int
    ust_idnr_validiert: bool
    aktiv: bool
    erstellt_am: datetime
    aktualisiert_am: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Lieferanten
# ---------------------------------------------------------------------------

class LieferantBase(BaseModel):
    firmenname: str
    vorname: Optional[str] = None
    nachname: Optional[str] = None
    strasse: Optional[str] = None
    hausnummer: Optional[str] = None
    plz: Optional[str] = None
    ort: Optional[str] = None
    land: str = "DE"
    ust_idnr: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    lieferantennummer: Optional[str] = None
    notizen: Optional[str] = None


class LieferantCreate(LieferantBase):
    pass


class LieferantUpdate(LieferantBase):
    firmenname: Optional[str] = None
    aktiv: Optional[bool] = None


class LieferantResponse(LieferantBase):
    id: int
    aktiv: bool
    erstellt_am: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Nummernkreise
# ---------------------------------------------------------------------------

class NummernkreisUpdate(BaseModel):
    bezeichnung: Optional[str] = None
    format: Optional[str] = None
    naechste_nr: Optional[int] = None
    reset_jaehrlich: Optional[bool] = None
    aktiv: Optional[bool] = None

    @field_validator("format")
    @classmethod
    def check_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if "#" not in v:
            raise ValueError("Format muss mindestens ein '#' als Nummernplatzhalter enthalten")
        return v

    @field_validator("naechste_nr")
    @classmethod
    def check_naechste_nr(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("naechste_nr muss >= 1 sein")
        return v


class NummernkreisResponse(BaseModel):
    id: int
    bezeichnung: str
    typ: str
    format: str
    naechste_nr: int
    reset_jaehrlich: bool
    letztes_jahr: Optional[int]
    aktiv: bool
    vorschau: Optional[str] = None  # wird im Router befüllt

    model_config = {"from_attributes": True}
