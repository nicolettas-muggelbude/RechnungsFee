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
    w_idnr: Optional[str] = None
    finanzamt: Optional[str] = None
    voranmeldungsrhythmus: str = "quartal"
    ist_kleinunternehmer: bool = False
    bezieht_transferleistungen: bool = False
    geburtsdatum: Optional[date] = None
    bg_nummer: Optional[str] = None
    jobcenter_name: Optional[str] = None
    leistungsbescheid_monat: Optional[str] = None
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
    berufsbezeichnung: Optional[str] = None
    kammer_mitgliedschaft: Optional[str] = None
    zahlungshinweis_aktiv: bool = True
    pdf_vorlage: int = 0
    logo_pfad: Optional[str] = None
    mail_betreff_vorlage: Optional[str] = None
    mail_text_vorlage: Optional[str] = None
    mail_signatur: Optional[str] = None
    unterschrift_bild: Optional[str] = None
    unterschrift_auf_rechnung: bool = False
    standard_zahlungsziel: int = 14
    qr_zahlung_aktiv: bool = False
    standard_skonto_prozent: Optional[Decimal] = None
    standard_skonto_tage: Optional[int] = None
    lieferschein_aktiv: bool = False
    angebote_aktiv: bool = False
    proforma_aktiv: bool = False
    auftraege_aktiv: bool = False

    @field_validator("versteuerungsart")
    @classmethod
    def check_versteuerungsart(cls, v: str) -> str:
        if v not in ("ist", "soll"):
            raise ValueError("versteuerungsart muss 'ist' oder 'soll' sein")
        return v

    @field_validator("voranmeldungsrhythmus")
    @classmethod
    def check_voranmeldungsrhythmus(cls, v: str) -> str:
        if v not in ("monat", "quartal"):
            raise ValueError("voranmeldungsrhythmus muss 'monat' oder 'quartal' sein")
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
    anbieter: str
    kontoart: str = "bank"          # bank|zahlungsdienstleister
    iban: Optional[str] = None
    bic: Optional[str] = None
    kennung: Optional[str] = None   # PayPal-E-Mail, Stripe-ID etc.
    kontotyp: str = "geschaeftlich" # geschaeftlich|mischkonto
    ist_standard: bool = False

    @model_validator(mode="after")
    def check_felder(self) -> "KontoBase":
        if self.kontoart == "bank":
            if not self.iban:
                raise ValueError("IBAN ist für Bankkonten erforderlich")
            iban = self.iban.replace(" ", "").upper()
            if len(iban) < 15 or len(iban) > 34:
                raise ValueError("IBAN muss zwischen 15 und 34 Zeichen lang sein")
            self.iban = iban
        elif self.kontoart == "zahlungsdienstleister":
            if not self.kennung:
                raise ValueError("Kennung (z.B. E-Mail-Adresse) ist für Zahlungsdienstleister erforderlich")
        return self

    @field_validator("kontoart")
    @classmethod
    def check_kontoart(cls, v: str) -> str:
        if v not in ("bank", "zahlungsdienstleister"):
            raise ValueError("kontoart muss 'bank' oder 'zahlungsdienstleister' sein")
        return v

    @field_validator("kontotyp")
    @classmethod
    def check_kontotyp(cls, v: str) -> str:
        if v not in ("geschaeftlich", "mischkonto"):
            raise ValueError("kontotyp muss 'geschaeftlich' oder 'mischkonto' sein")
        return v


class KontoCreate(KontoBase):
    pass


class KontoUpdate(BaseModel):
    name: Optional[str] = None
    anbieter: Optional[str] = None
    kontoart: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None
    kennung: Optional[str] = None
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
    konto_skr03_default: Optional[str]
    konto_skr04_default: Optional[str]
    user_modified_skr03: bool
    user_modified_skr04: bool
    eks_kategorie: Optional[str]
    euer_zeile: Optional[int]
    vorsteuer_prozent: Decimal
    ust_satz_standard: int
    ist_system: bool
    aktiv: bool
    beschreibung: Optional[str] = None

    model_config = {"from_attributes": True}


class KategorieKontoUpdate(BaseModel):
    konto_skr03: Optional[str] = None
    konto_skr04: Optional[str] = None


class KategorieBeschreibungUpdate(BaseModel):
    beschreibung: Optional[str] = None


class KategorieCreate(BaseModel):
    name: str
    kontenart: str
    konto_skr03: Optional[str] = None
    konto_skr04: Optional[str] = None
    euer_zeile: Optional[int] = None
    eks_kategorie: Optional[str] = None
    vorsteuer_prozent: Decimal = Decimal("100")
    ust_satz_standard: int = 0
    beschreibung: Optional[str] = None

KategorieUpdate = KategorieCreate


# ---------------------------------------------------------------------------
# Setup-Status (wird beim Start abgefragt)
# ---------------------------------------------------------------------------

class SetupStatus(BaseModel):
    ist_eingerichtet: bool
    hat_unternehmen: bool
    hat_konto: bool
    hat_kategorien: bool


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------

class JournalEintragCreate(BaseModel):
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
    km_anzahl: Optional[Decimal] = None  # Fahrtkosten Privat-PKW: EÜR=km×0,30 gespeichert, EKS rechnet km×0,10
    ist_ig_erwerb: bool = False  # veraltet – wird zu ust_sonderfall='ig_erwerb' migriert
    ust_sonderfall: Optional[str] = None  # ig_erwerb | 13b_abs1 | 13b_abs2 | None

    @field_validator("zahlungsart")
    @classmethod
    def check_zahlungsart(cls, v: str) -> str:
        if v not in ("Bar", "Karte", "Bank", "PayPal", "Keine"):
            raise ValueError("zahlungsart muss Bar, Karte, Bank, PayPal oder Keine sein")
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


class JournalEintragResponse(BaseModel):
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
    rechnung_id: Optional[int] = None
    rechnung_nr: Optional[str] = None
    konto_skr03: Optional[str] = None
    konto_skr04: Optional[str] = None
    konto_ust_skr03: Optional[str] = None
    konto_ust_skr04: Optional[str] = None
    immutable: bool
    erstellt_am: datetime
    km_anzahl: Optional[Decimal] = None
    ist_ig_erwerb: bool = False
    ust_sonderfall: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_kunde(cls, obj) -> "JournalEintragResponse":
        data = cls.model_validate(obj)
        if obj.kunde:
            parts = [obj.kunde.firmenname or "", obj.kunde.vorname or "", obj.kunde.nachname or ""]
            data.kunde_name = " ".join(p for p in parts if p) or None
            data.kunde_email = obj.kunde.email
        if obj.kategorie:
            data.kategorie_kontenart = obj.kategorie.kontenart
        if obj.rechnung:
            data.rechnung_nr = obj.rechnung.rechnungsnummer
        return data


class StornoRequest(BaseModel):
    grund: str


class SplitPosition(BaseModel):
    beschreibung: str
    kategorie_id: Optional[int] = None
    brutto_betrag: Decimal
    ust_satz: Decimal = Decimal("0")
    vorsteuerabzug: bool = False
    ist_ig_erwerb: bool = False
    ust_sonderfall: Optional[str] = None

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
        if v not in ("Bar", "Karte", "Bank", "PayPal", "Keine"):
            raise ValueError("zahlungsart muss Bar, Karte, Bank, PayPal oder Keine sein")
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
    z_hd: Optional[str] = None
    notizen: Optional[str] = None
    zugferd_aktiv: bool = False
    skonto_prozent: Optional[Decimal] = None
    skonto_tage: Optional[int] = None


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
    z_hd: Optional[str] = None
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


# ---------------------------------------------------------------------------
# EKS-Einstellungen
# ---------------------------------------------------------------------------

class EksEinstellungenBase(BaseModel):
    taetigkeitsart_text: Optional[str] = None
    taetigkeitsbeginn: Optional[str] = None
    taetigkeitsende: Optional[str] = None
    wohnung_gewerblich: bool = False
    gewerbliche_raeume: Optional[str] = None
    gewerbliche_flaeche: Optional[str] = None
    produkte_kostenfrei: bool = False
    personal_beschaeftigt: bool = False
    anzahl_beschaeftigte: Optional[str] = None
    weiteres_personal: bool = False
    anzahl_weiteres_personal: Optional[str] = None
    personal_ab: Optional[str] = None
    umsatzsteuerpflichtig: bool = False
    zuschuss_erhalten: bool = False
    zuschuss_beantragt: bool = False
    darlehen: bool = False
    darlehen_hoehe: Optional[str] = None
    darlehen_eingang: Optional[str] = None
    darlehen_rueckzahlung_ab: Optional[str] = None
    darlehen_tilgung: Optional[str] = None
    darlehen_ausgaben_art: Optional[str] = None
    darlehen_ausgaben_hoehe: Optional[str] = None
    kind_ausserhalb: bool = False
    unterhalt: bool = False
    fahrten_betriebsstaette: bool = False
    km_einfach: Optional[str] = None
    arbeitstage_pro_woche: Optional[str] = None
    mehraufwand_verpflegung: bool = False
    arbeitstage_verpflegung: Optional[str] = None


class EksEinstellungenCreate(EksEinstellungenBase):
    pass


class EksEinstellungenResponse(EksEinstellungenBase):
    id: int
    aktualisiert_am: datetime

    model_config = {"from_attributes": True}
