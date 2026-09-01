"""
Pydantic-Schemas für Request/Response-Validierung.
Getrennt von den SQLAlchemy-Models (database/models.py).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, field_validator, model_validator

from .schemas_rechnungen import BelegResponse


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
    bundesland: Optional[str] = None
    dauerfristverlaengerung_ust: bool = False
    est_vorauszahlungen_aktiv: bool = False
    gewst_vorauszahlungen_aktiv: bool = False
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
    bezeichnung_des_gewerbes: Optional[str] = None
    kammer_mitgliedschaft: Optional[str] = None
    zahlungshinweis_aktiv: bool = True
    pdf_vorlage: int = 0
    einleitungstext: Optional[str] = None
    schlusstext: Optional[str] = None
    einleitungstext_angebot: Optional[str] = None
    schlusstext_angebot: Optional[str] = None
    einleitungstext_auftrag: Optional[str] = None
    schlusstext_auftrag: Optional[str] = None
    einleitungstext_proforma: Optional[str] = None
    schlusstext_proforma: Optional[str] = None
    einleitungstext_lieferschein: Optional[str] = None
    schlusstext_lieferschein: Optional[str] = None
    logo_pfad: Optional[str] = None
    mail_betreff_vorlage: Optional[str] = None
    mail_text_vorlage: Optional[str] = None
    mail_betreff_angebot: Optional[str] = None
    mail_text_angebot: Optional[str] = None
    mail_betreff_proforma: Optional[str] = None
    mail_text_proforma: Optional[str] = None
    mail_betreff_auftrag: Optional[str] = None
    mail_text_auftrag: Optional[str] = None
    mail_signatur: Optional[str] = None
    smtp_aktiv: bool = False
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_ssl: bool = False
    smtp_user: Optional[str] = None
    smtp_passwort: Optional[str] = None
    smtp_von_adresse: Optional[str] = None
    smtp_zertifikat_ignorieren: bool = False
    smtp_zertifikat_fingerprint: Optional[str] = None
    thunderbird_aktiv: bool = False
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
    wiederkehrend_aktiv: bool = False
    buchungsvorlagen_aktiv: bool = False
    lagerführung_aktiv: bool = False
    profilmanager_aktiv: bool = False
    backup_extern_pfad_1:   Optional[str] = None
    backup_extern_pfad_2:   Optional[str] = None
    backup_extern_passwort: Optional[str] = None
    backup_smb_benutzer:    Optional[str] = None
    backup_smb_passwort:    Optional[str] = None
    backup_extern_pfad_1_lokal_ok: bool = False
    backup_extern_pfad_2_lokal_ok: bool = False
    datev_beraternummer:    Optional[str] = None
    datev_mandantennummer:  Optional[str] = None
    datev_konto_bar:        Optional[str] = None
    datev_konto_bank:       Optional[str] = None
    datev_konto_karte:      Optional[str] = None
    datev_konto_paypal:     Optional[str] = None
    guv_aktiv: bool = False
    kontenuebersicht_aktiv: bool = False
    bank_import_aktiv: bool = False
    bank_import_manuell: bool = False
    dashboard_config: Optional[str] = None
    datenmigration_aktiv: bool = False

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
    kontotyp: str = "geschaeftlich" # geschaeftlich|mischkonto|privat
    ist_standard: bool = False
    datev_kontonummer: Optional[str] = None  # individuelles DATEV-Gegenkonto (z.B. 1200, 1210)

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
        if v not in ("geschaeftlich", "mischkonto", "privat"):
            raise ValueError("kontotyp muss 'geschaeftlich', 'mischkonto' oder 'privat' sein")
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
    datev_kontonummer: Optional[str] = None
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
    euer_zeile: Optional[int] = None
    euer_zeile_loeschen: bool = False


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
    gruppe_id: Optional[int] = None
    beleg_id: Optional[int] = None
    beleg: Optional[BelegResponse] = None
    # Storno-Status (Issue #321) - bisher nur ueber String-Praefix "STORNO " in der
    # Beschreibung erkennbar; wird jetzt vom Server ausgewertet und mitgeliefert.
    storniert: bool = False               # True wenn eine Gegenbuchung existiert
    storno_belegnr: Optional[str] = None  # Belegnr der Gegenbuchung, falls storniert
    ist_storno: bool = False              # True wenn dieser Eintrag selbst eine Gegenbuchung ist
    storno_von_belegnr: Optional[str] = None  # Belegnr der Originalbuchung, falls ist_storno

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_kunde(cls, obj) -> "JournalEintragResponse":
        data = cls.model_validate(obj)
        if obj.beleg:
            data.beleg = BelegResponse.from_beleg(obj.beleg)
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
    datum: Optional[date] = None  # Storno-Buchungsdatum - Vorgabe: Datum der Originalbuchung (Issue #320)


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
    beleg_id: Optional[int] = None  # vorab hochgeladener Beleg (Issue #310) - Split-Buchungen
    # sind ab Erstellung immutable, ein Beleg kann daher nicht wie bei Einzelbuchungen per
    # separatem Upload NACH der Erstellung angehaengt werden, sondern muss schon beim
    # Anlegen mitgegeben werden.

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
    ust_idnr_validiert: bool = False
    ust_idnr_validierung_datum: Optional[date] = None
    steuernummer_ausland: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    ist_verein: bool = False
    ist_gemeinnuetzig: bool = False
    kundennummer: Optional[str] = None
    debitor_nr: Optional[str] = None
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
    aktiv: bool
    mahnung_gesperrt: bool
    mahnung_warnung: bool
    mahnsperre_bis: Optional[date] = None
    mahnsperre_grund: Optional[str] = None
    erstellt_am: datetime
    aktualisiert_am: datetime

    model_config = {"from_attributes": True}


class MahnsperreSetzenRequest(BaseModel):
    bis: date
    grund: Optional[str] = None


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
    ust_idnr_validiert: bool = False
    ust_idnr_validierung_datum: Optional[date] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    lieferantennummer: Optional[str] = None
    kreditor_nr: Optional[str] = None
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


# ---------------------------------------------------------------------------
# Datenübernahme / CSV-Import
# ---------------------------------------------------------------------------

class ImportVorschauZeile(BaseModel):
    zeile: int
    daten: dict
    status: str          # neu | duplikat | fehler
    duplikat_id: Optional[int] = None
    fehler: Optional[str] = None


class ImportZeileAktion(BaseModel):
    zeile: int
    daten: dict
    aktion: str          # übernehmen | ignorieren | überschreiben
    duplikat_id: Optional[int] = None


class ImportRequest(BaseModel):
    zeilen: List[ImportZeileAktion]


class ImportErgebnis(BaseModel):
    importiert: int
    aktualisiert: int
    ignoriert: int
    fehler: List[dict]


class ImportSpaltenResponse(BaseModel):
    spaltennamen: List[str]        # aus Header oder ["Spalte 1", "Spalte 2", ...]
    vorschau: List[List[str]]      # erste 5 Zeilen als Liste von Zellwerten
    delimiter: str
    encoding: str


class ImportMappingVorlageCreate(BaseModel):
    name: str
    typ: str                       # kunden | lieferanten | artikel | gemischt
    hat_header: bool = True
    mapping_json: str              # JSON: {"col_0": "firmenname", ...}
    typ_erkennung_aktiv: bool = False


class ImportMappingVorlageResponse(ImportMappingVorlageCreate):
    id: int
    erstellt_am: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Mahnwesen (docs/plan-mahnwesen.md, Abschnitt A)
# ---------------------------------------------------------------------------

class MahnstufeBase(BaseModel):
    stufe: int
    bezeichnung: str = "Zahlungserinnerung"
    tage_nach_faelligkeit: int = 7
    tage_nach_vorheriger: int = 14
    betreff_vorlage: Optional[str] = None
    text_vorlage: Optional[str] = None
    mahngebuehr_aktiv: bool = False
    mahngebuehr_privat: Decimal = Decimal("5.00")
    mahngebuehr_gewerblich: Decimal = Decimal("40.00")
    aktiv: bool = True
    anhang_rechnung: bool = False
    anhang_bisherige_mahnungen: bool = False
    anhang_kontokorrent: bool = False


class MahnstufeCreate(MahnstufeBase):
    pass


class MahnstufeUpdate(BaseModel):
    stufe: Optional[int] = None
    bezeichnung: Optional[str] = None
    tage_nach_faelligkeit: Optional[int] = None
    tage_nach_vorheriger: Optional[int] = None
    betreff_vorlage: Optional[str] = None
    text_vorlage: Optional[str] = None
    mahngebuehr_aktiv: Optional[bool] = None
    mahngebuehr_privat: Optional[Decimal] = None
    mahngebuehr_gewerblich: Optional[Decimal] = None
    aktiv: Optional[bool] = None
    anhang_rechnung: Optional[bool] = None
    anhang_bisherige_mahnungen: Optional[bool] = None
    anhang_kontokorrent: Optional[bool] = None


class MahnstufeResponse(MahnstufeBase):
    id: int
    loeschbar: bool = True  # False sobald mind. eine Mahnung diese Stufe per FK referenziert

    model_config = {"from_attributes": True}


class MahnwesenEinstellungenBase(BaseModel):
    aktiv: bool = False
    automation_modus: str = "halb"           # manuell | halb | voll
    versand_mail: bool = True
    versand_pdf: bool = False
    konsolidiert_ab_stufe: int = 2
    kundensperrung_aktiv: bool = False
    # Zweistufig statt eine Schwelle + ein Modus: Warnung ab einer (niedrigeren) Stufe, harte
    # Sperre erst ab einer weiteren (höheren) Stufe - beide unabhängig voneinander optional.
    kundensperrung_warnung_ab_stufe: Optional[int] = None
    kundensperrung_sperrung_ab_stufe: Optional[int] = None
    verzugszinsen_aktiv: bool = False
    verzugszinsen_ab_stufe: int = 2
    basiszinssatz: Decimal = Decimal("2.12")
    verzugszinsen_aufschlag_privat: Decimal = Decimal("5.0")
    verzugszinsen_aufschlag_gewerblich: Decimal = Decimal("9.0")

    @field_validator("automation_modus")
    @classmethod
    def check_automation_modus(cls, v: str) -> str:
        if v not in ("manuell", "halb", "voll"):
            raise ValueError("automation_modus muss manuell, halb oder voll sein")
        return v


class MahnwesenEinstellungenUpdate(MahnwesenEinstellungenBase):
    pass


class MahnwesenEinstellungenResponse(MahnwesenEinstellungenBase):
    id: int
    mahnstufen: List[MahnstufeResponse] = []

    model_config = {"from_attributes": True}


class MahnungFaelligItem(BaseModel):
    rechnung_id: int
    rechnungsnummer: Optional[str] = None
    kunde_id: Optional[int] = None
    kunde_name: str
    faellig_am: Optional[date] = None
    offener_betrag: Decimal
    mahnstufe_aktuell: int
    empfohlene_stufe: int
    empfohlene_stufe_bezeichnung: str


class MahnungVorschauRequest(BaseModel):
    rechnung_ids: List[int] = []
    kunde_id: Optional[int] = None  # nur bei rechnung_ids=[] - reine Gebühren-Eskalation ohne Rechnung
    stufe: Optional[int] = None


class MahnungVorschauPosition(BaseModel):
    rechnung_id: int
    rechnungsnummer: Optional[str] = None
    offener_betrag: Decimal
    tage_ueberfaellig: int


class MahnungVorschauResponse(BaseModel):
    kunde_id: Optional[int] = None
    kunde_name: str
    stufe: int
    bezeichnung: str
    positionen: List[MahnungVorschauPosition]
    offener_betrag_gesamt: Decimal
    mahngebuehr: Decimal
    verzugszinsen: Decimal
    gebuehr_vorperioden: Decimal = Decimal("0")
    gesamtforderung: Decimal
    # Issue #366: Betrag, der beim Anlegen automatisch mit offenen Kundengutschriften
    # verrechnet wird - offener_betrag_gesamt/gesamtforderung sind bereits um diesen Betrag
    # gemindert, das Feld dient nur der Transparenz in der UI.
    gutschrift_verrechnung: Decimal = Decimal("0")


class MahnungErstellenRequest(BaseModel):
    rechnung_ids: List[int] = []
    kunde_id: Optional[int] = None  # nur bei rechnung_ids=[] - reine Gebühren-Eskalation ohne Rechnung
    stufe: Optional[int] = None


class KundenGebuehrZahlungRequest(BaseModel):
    betrag: Decimal
    datum: date
    zahlungsart: str


class MahnungZahlungRequest(BaseModel):
    betrag: Decimal
    datum: date
    zahlungsart: str = "Bank"


class MahnungZahlungPosition(BaseModel):
    rechnung_id: int
    rechnungsnummer: Optional[str] = None
    betrag: Decimal


class MahnungZahlungResponse(BaseModel):
    verteilung: List[MahnungZahlungPosition] = []
    gebuehr_verrechnet: Decimal = Decimal("0")
    kundenguthaben: Decimal = Decimal("0")


class MahnungResponse(BaseModel):
    id: int
    mahnnummer: Optional[str] = None
    kunde_id: Optional[int] = None
    stufe: int
    bezeichnung: Optional[str] = None
    erstellt_am: datetime
    versendet_am: Optional[datetime] = None
    mahngebuehr: Decimal
    verzugszinsen: Decimal
    mahngebuehr_bezahlt: Decimal = Decimal("0")
    verzugszinsen_bezahlt: Decimal = Decimal("0")
    uebernommene_gebuehr_vorperioden: Decimal = Decimal("0")
    uebertragen_in_mahnung_id: Optional[int] = None
    offener_betrag_gesamt: Optional[Decimal] = None
    status: str
    rechnung_ids: List[int] = []

    model_config = {"from_attributes": True}


class MahnungHistorieItem(MahnungResponse):
    kunde_name: str
    kunde_email: Optional[str] = None
    rechnungsnummern: str


class MahnwesenRechnungMini(BaseModel):
    rechnung_id: int
    rechnungsnummer: Optional[str] = None
    faellig_am: Optional[date] = None
    offener_betrag: Decimal
    mahnstufe_aktuell: int
    zahlungserinnerung_faellig: bool  # Stufe 1 (immer 1:1 zur Rechnung) ist jetzt fällig
    letzter_mahnung_status: Optional[str] = None  # entwurf | versendet | None (nie gemahnt)


class MahnwesenKundeUebersicht(BaseModel):
    kunde_id: int
    kunde_name: str
    anzahl_offene_rechnungen: int
    aeltestes_faellig_am: Optional[date] = None
    offener_betrag_gesamt: Decimal
    aktionsfaellig: bool  # ob JETZT eine echte Mahnstufe (>= konsolidiert_ab_stufe) ansteht
    naechste_stufe: Optional[int] = None
    naechste_stufe_bezeichnung: Optional[str] = None
    # Aufschlüsselung über alle Rechnungen des Kunden - ein Kunde kann mehrere dieser
    # Zustände gleichzeitig haben (z.B. 1 versendet, 1 Entwurf, 2 fällig), ein einzelnes
    # "Status"-Label würde das verfälschen (Nutzer-Feedback 2026-08-01).
    anzahl_zahlungserinnerung_faellig: int = 0
    anzahl_entwurf: int = 0
    anzahl_versendet: int = 0
    anzahl_offen: int = 0
    mahnsperre_bis: Optional[date] = None
    mahnsperre_grund: Optional[str] = None
    rechnungen: List[MahnwesenRechnungMini] = []
    # Kunde hat keine offene Rechnung mehr, aber noch offene Mahngebühr/Verzugszinsen aus
    # früheren Mahnungen (Kontokorrent-Konsistenz, Abschnitt E) - offener_betrag_gesamt trägt
    # in diesem Fall die offene Gebühr/Zinsen-Summe statt einer Rechnungssumme, rechnungen ist leer.
    nur_offene_gebuehr: bool = False
