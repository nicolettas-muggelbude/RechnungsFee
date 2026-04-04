"""
RechnungsFee - Datenbankmodelle (SQLAlchemy 2.0)

Alle Geldbeträge in NUMERIC(12,2) – kein Float wegen Rundungsfehlern.
GoBD-relevante Tabellen sind unveränderbar (immutable=True + Signatur).
"""

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .connection import Base


# ---------------------------------------------------------------------------
# USt-Sätze (konfigurierbar)
# ---------------------------------------------------------------------------

class UstSatz(Base):
    """Konfigurierbare Mehrwertsteuersätze."""
    __tablename__ = "ust_saetze"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    satz: Mapped[Decimal] = mapped_column(Numeric(5, 2), unique=True, nullable=False)
    bezeichnung: Mapped[str | None] = mapped_column(String(100))
    ist_aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ist_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ist_standard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 0/7/19 – nicht löschbar


# ---------------------------------------------------------------------------
# Stammdaten
# ---------------------------------------------------------------------------

class Unternehmen(Base):
    """Stammdaten des Unternehmens / Selbstständigen (nur 1 Datensatz)."""
    __tablename__ = "unternehmen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firmenname: Mapped[str] = mapped_column(String(200), nullable=False)
    vorname: Mapped[str | None] = mapped_column(String(100))
    nachname: Mapped[str | None] = mapped_column(String(100))
    strasse: Mapped[str] = mapped_column(String(200), nullable=False)
    hausnummer: Mapped[str] = mapped_column(String(20), nullable=False)
    plz: Mapped[str] = mapped_column(String(10), nullable=False)
    ort: Mapped[str] = mapped_column(String(100), nullable=False)
    land: Mapped[str] = mapped_column(String(2), default="DE", nullable=False)
    # Steuerliche Angaben
    steuernummer: Mapped[str | None] = mapped_column(String(30))
    ust_idnr: Mapped[str | None] = mapped_column(String(20))
    finanzamt: Mapped[str | None] = mapped_column(String(200))
    # Status
    ist_kleinunternehmer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bezieht_transferleistungen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Buchführung
    versteuerungsart: Mapped[str] = mapped_column(String(4), default="ist", nullable=False)  # ist|soll
    kontenrahmen: Mapped[str] = mapped_column(String(10), default="SKR03", nullable=False)  # SKR03|SKR04|SKR49
    taetigkeitsart: Mapped[str] = mapped_column(String(20), default="freiberuflich", nullable=False)
    rechtsform: Mapped[str] = mapped_column(String(50), default="Einzelunternehmer", nullable=False)
    eu_handel_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    geschaeftsjahr_beginn: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # Monat 1-12
    # Rechtsangaben
    handelsregister_nr: Mapped[str | None] = mapped_column(String(100))  # z.B. "HRB 215517"
    handelsregister_gericht: Mapped[str | None] = mapped_column(String(100))  # z.B. "Oldenburg"
    # Kontakt
    email: Mapped[str | None] = mapped_column(String(200))
    telefon: Mapped[str | None] = mapped_column(String(50))
    webseite: Mapped[str | None] = mapped_column(String(200))
    # Bank (für Rechnungs-Vorlage)
    iban: Mapped[str | None] = mapped_column(String(34))
    bic: Mapped[str | None] = mapped_column(String(11))
    bank_name: Mapped[str | None] = mapped_column(String(100))
    # Beruf & Kammer
    berufsbezeichnung: Mapped[str | None] = mapped_column(String(100))       # z.B. "Rechtsanwältin"
    kammer_mitgliedschaft: Mapped[str | None] = mapped_column(String(200))   # z.B. "Rechtsanwaltskammer Berlin"
    # Rechnungs-PDF-Einstellungen
    zahlungshinweis_aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pdf_vorlage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Logo & Mail-Vorlagen
    logo_pfad: Mapped[str | None] = mapped_column(String(500))
    mail_betreff_vorlage: Mapped[str | None] = mapped_column(String(500))
    mail_text_vorlage: Mapped[str | None] = mapped_column(Text)
    mail_signatur: Mapped[str | None] = mapped_column(Text)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Konto(Base):
    """Bankkonten des Unternehmens."""
    __tablename__ = "konten"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank: Mapped[str] = mapped_column(String(100), nullable=False)
    iban: Mapped[str] = mapped_column(String(34), unique=True, nullable=False)
    bic: Mapped[str | None] = mapped_column(String(11))
    kontotyp: Mapped[str] = mapped_column(String(20), default="geschaeftlich", nullable=False)  # geschaeftlich|mischkonto|privat
    ist_standard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    transaktionen: Mapped[list["BankTransaktion"]] = relationship(back_populates="konto")
    imports: Mapped[list["BankImport"]] = relationship(back_populates="konto")


# ---------------------------------------------------------------------------
# Kategorien & Buchungslogik
# ---------------------------------------------------------------------------

class Kategorie(Base):
    """Buchungskategorien mit SKR03/SKR04-Konten und EKS-Zuordnung."""
    __tablename__ = "kategorien"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    kontenart: Mapped[str] = mapped_column(String(20), nullable=False)  # Aufwand|Erlös|Privat|Anlage
    konto_skr03: Mapped[str | None] = mapped_column(String(10))
    konto_skr04: Mapped[str | None] = mapped_column(String(10))
    konto_skr49: Mapped[str | None] = mapped_column(String(10))
    eks_kategorie: Mapped[str | None] = mapped_column(String(10))  # B9, A1 etc.
    euer_zeile: Mapped[int | None] = mapped_column(Integer)
    vorsteuer_prozent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100, nullable=False)
    ust_satz_standard: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0|7|19
    ist_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    kassenbucheintraege: Mapped[list["Kassenbucheintrag"]] = relationship(back_populates="kategorie")
    rechnungen: Mapped[list["Rechnung"]] = relationship(back_populates="kategorie")
    transaktionen: Mapped[list["BankTransaktion"]] = relationship(back_populates="kategorie")


# ---------------------------------------------------------------------------
# Nummernkreise
# ---------------------------------------------------------------------------

class Nummernkreis(Base):
    """
    Konfigurierbare Nummernkreise für Belegnummern.
    Format-Vorlage: 'YY####' → '260001', 'YYYY-####' → '2026-0001', 'KB-YY####' → 'KB-260001'
    Y = Jahreszahl-Stelle, # = fortlaufende Nummer (Anzahl # = Stellen mit führenden Nullen).
    """
    __tablename__ = "nummernkreise"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bezeichnung: Mapped[str] = mapped_column(String(100), nullable=False)
    typ: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)  # kassenbuch, rechnung_ausgang, ...
    format: Mapped[str] = mapped_column(String(50), default="YY####", nullable=False)
    naechste_nr: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reset_jaehrlich: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    letztes_jahr: Mapped[int | None] = mapped_column(Integer)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Kassenbuch (GoBD-konform, unveränderbar)
# ---------------------------------------------------------------------------

class Kassenbucheintrag(Base):
    """
    GoBD-konformes Kassenbuch.
    Einträge sind nach Erstellung unveränderbar (immutable=True).
    """
    __tablename__ = "kassenbuch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    datum: Mapped[date] = mapped_column(Date, nullable=False)
    belegnr: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    beschreibung: Mapped[str] = mapped_column(String(500), nullable=False)
    externe_belegnr: Mapped[str | None] = mapped_column(String(100))
    kategorie_id: Mapped[int | None] = mapped_column(ForeignKey("kategorien.id"))
    kunde_id: Mapped[int | None] = mapped_column(ForeignKey("kunden.id"))
    zahlungsart: Mapped[str] = mapped_column(String(20), nullable=False)  # Bar|Karte|Bank|PayPal
    art: Mapped[str] = mapped_column(String(10), nullable=False)  # Einnahme|Ausgabe
    netto_betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ust_satz: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    ust_betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    brutto_betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vorsteuerabzug: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    steuerbefreiung_grund: Mapped[str | None] = mapped_column(String(100))  # z.B. "§19 UStG"
    rechnung_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"))
    # GoBD
    immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signatur: Mapped[str | None] = mapped_column(String(64))
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    erstellt_von: Mapped[str | None] = mapped_column(String(100))

    kategorie: Mapped["Kategorie | None"] = relationship(back_populates="kassenbucheintraege")
    kunde: Mapped["Kunde | None"] = relationship()
    rechnung: Mapped["Rechnung | None"] = relationship(back_populates="kassenbucheintraege")


class Tagesabschluss(Base):
    """Kassenbuch-Tagesabschluss (GoBD-konform, unveränderbar)."""
    __tablename__ = "tagesabschluesse"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    datum: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    uhrzeit: Mapped[str] = mapped_column(String(8), nullable=False)  # HH:MM:SS
    anfangsbestand: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    einnahmen_bar: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    ausgaben_bar: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    soll_endbestand: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ist_endbestand: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    differenz: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    differenz_begruendung: Mapped[str | None] = mapped_column(Text)
    differenz_buchungsart: Mapped[str | None] = mapped_column(String(30))  # Privatentnahme|Aufwand|Protokoll
    zaehlung_json: Mapped[str | None] = mapped_column(Text)  # JSON: Münzen/Scheine
    kassenbewegungen_anzahl: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    benutzer: Mapped[str | None] = mapped_column(String(100))
    immutable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signatur: Mapped[str | None] = mapped_column(String(64))
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Kunden & Lieferanten
# ---------------------------------------------------------------------------

class Kunde(Base):
    """Kundenstammdaten."""
    __tablename__ = "kunden"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firmenname: Mapped[str | None] = mapped_column(String(200))
    vorname: Mapped[str | None] = mapped_column(String(100))
    nachname: Mapped[str | None] = mapped_column(String(100))
    strasse: Mapped[str | None] = mapped_column(String(200))
    hausnummer: Mapped[str | None] = mapped_column(String(20))
    plz: Mapped[str | None] = mapped_column(String(10))
    ort: Mapped[str | None] = mapped_column(String(100))
    land: Mapped[str] = mapped_column(String(2), default="DE", nullable=False)
    ust_idnr: Mapped[str | None] = mapped_column(String(20))
    ust_idnr_validiert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ust_idnr_validierung_datum: Mapped[date | None] = mapped_column(Date)
    email: Mapped[str | None] = mapped_column(String(200))
    telefon: Mapped[str | None] = mapped_column(String(50))
    # Vereins-spezifisch (Issue #14)
    ist_verein: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ist_gemeinnuetzig: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bescheinigung_paragraph: Mapped[str | None] = mapped_column(String(50))  # §4 Nr. 21 UStG
    bescheinigung_nummer: Mapped[str | None] = mapped_column(String(100))
    bescheinigung_behoerde: Mapped[str | None] = mapped_column(String(200))
    bescheinigung_gueltig_bis: Mapped[date | None] = mapped_column(Date)
    kundennummer: Mapped[str | None] = mapped_column(String(50))
    notizen: Mapped[str | None] = mapped_column(Text)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    rechnungen: Mapped[list["Rechnung"]] = relationship(back_populates="kunde")


class Lieferant(Base):
    """Lieferantenstammdaten."""
    __tablename__ = "lieferanten"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firmenname: Mapped[str] = mapped_column(String(200), nullable=False)
    vorname: Mapped[str | None] = mapped_column(String(100))
    nachname: Mapped[str | None] = mapped_column(String(100))
    strasse: Mapped[str | None] = mapped_column(String(200))
    hausnummer: Mapped[str | None] = mapped_column(String(20))
    plz: Mapped[str | None] = mapped_column(String(10))
    ort: Mapped[str | None] = mapped_column(String(100))
    land: Mapped[str] = mapped_column(String(2), default="DE", nullable=False)
    ust_idnr: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(200))
    telefon: Mapped[str | None] = mapped_column(String(50))
    lieferantennummer: Mapped[str | None] = mapped_column(String(50))
    notizen: Mapped[str | None] = mapped_column(Text)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    rechnungen: Mapped[list["Rechnung"]] = relationship(back_populates="lieferant")
    artikel: Mapped[list["Artikel"]] = relationship(back_populates="lieferant")


# ---------------------------------------------------------------------------
# Artikelstamm
# ---------------------------------------------------------------------------

class Artikel(Base):
    """Artikel- und Dienstleistungsstammdaten."""
    __tablename__ = "artikel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artikelnummer: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    typ: Mapped[str] = mapped_column(String(20), nullable=False)  # artikel|dienstleistung|fremdleistung
    bezeichnung: Mapped[str] = mapped_column(String(200), nullable=False)
    einheit: Mapped[str] = mapped_column(String(50), nullable=False, default="Stück")
    steuersatz: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=19)
    vk_brutto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vk_netto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ek_netto: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    ek_brutto: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    lieferant_id: Mapped[int | None] = mapped_column(ForeignKey("lieferanten.id"))
    lieferanten_artikelnr: Mapped[str | None] = mapped_column(String(100))
    hersteller: Mapped[str | None] = mapped_column(String(100))
    artikelcode: Mapped[str | None] = mapped_column(String(100))
    beschreibung: Mapped[str | None] = mapped_column(Text)
    kategorie: Mapped[str | None] = mapped_column(String(100))
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    lieferant: Mapped["Lieferant | None"] = relationship(back_populates="artikel")
    positionen: Mapped[list["Rechnungsposition"]] = relationship(back_populates="artikel")


# ---------------------------------------------------------------------------
# Rechnungen
# ---------------------------------------------------------------------------

class Rechnung(Base):
    """Eingangs- und Ausgangsrechnungen."""
    __tablename__ = "rechnungen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    typ: Mapped[str] = mapped_column(String(20), nullable=False)  # eingang|ausgang
    rechnungsnummer: Mapped[str | None] = mapped_column(String(50))
    datum: Mapped[date] = mapped_column(Date, nullable=False)
    faellig_am: Mapped[date | None] = mapped_column(Date)
    # Partner
    kunde_id: Mapped[int | None] = mapped_column(ForeignKey("kunden.id"))
    lieferant_id: Mapped[int | None] = mapped_column(ForeignKey("lieferanten.id"))
    partner_freitext: Mapped[str | None] = mapped_column(String(200))  # Falls kein Stammdatensatz
    # Kategorie
    kategorie_id: Mapped[int | None] = mapped_column(ForeignKey("kategorien.id"))
    # Beträge (Summen, automatisch aus Positionen berechnet)
    netto_gesamt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    ust_gesamt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    brutto_gesamt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    # Zahlung (Zufluss-/Abfluss-Prinzip)
    bezahlt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bezahlt_betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    zahlungsstatus: Mapped[str] = mapped_column(String(20), default="offen", nullable=False)  # offen|teilweise|bezahlt
    zahlungsdatum: Mapped[date | None] = mapped_column(Date)
    konto_id: Mapped[int | None] = mapped_column(ForeignKey("konten.id"))
    # Vorsteuer (nur Eingangsrechnungen)
    vorsteuer_abzugsfaehig: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vorsteuer_prozent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100, nullable=False)
    vorsteuer_betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    # EU / International
    land: Mapped[str] = mapped_column(String(2), default="DE", nullable=False)
    ist_eu_lieferung: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ist_eu_erwerb: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gelangensbestaetigung_vorhanden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Steuerbefreiung
    steuerbefreiung_grund: Mapped[str | None] = mapped_column(String(100))
    # Reverse Charge
    ist_reverse_charge: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Dateianhang
    datei_pfad: Mapped[str | None] = mapped_column(String(500))
    datei_name: Mapped[str | None] = mapped_column(String(200))
    notizen: Mapped[str | None] = mapped_column(Text)
    externe_belegnr: Mapped[str | None] = mapped_column(String(100))  # Lieferanten-Rechnungsnr. (nur Eingang)
    leistungsdatum: Mapped[date | None] = mapped_column(Date)
    # GoBD
    ist_entwurf: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    storniert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ausgegeben: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    kunde: Mapped["Kunde | None"] = relationship(back_populates="rechnungen")
    lieferant: Mapped["Lieferant | None"] = relationship(back_populates="rechnungen")
    kategorie: Mapped["Kategorie | None"] = relationship(back_populates="rechnungen")
    positionen: Mapped[list["Rechnungsposition"]] = relationship(back_populates="rechnung", cascade="all, delete-orphan")
    anlagegueter: Mapped[list["Anlagegut"]] = relationship(back_populates="rechnung")
    kassenbucheintraege: Mapped[list["Kassenbucheintrag"]] = relationship(back_populates="rechnung")


class Rechnungsposition(Base):
    """Einzelpositionen einer Rechnung (für Mischrechnungen mit verschiedenen Steuersätzen)."""
    __tablename__ = "rechnungspositionen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rechnung_id: Mapped[int] = mapped_column(ForeignKey("rechnungen.id", ondelete="CASCADE"), nullable=False)
    artikel_id: Mapped[int | None] = mapped_column(ForeignKey("artikel.id"))
    position_nr: Mapped[int] = mapped_column(Integer, nullable=False)
    beschreibung: Mapped[str] = mapped_column(String(500), nullable=False)
    menge: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=1, nullable=False)
    einheit: Mapped[str] = mapped_column(String(20), default="Stück", nullable=False)
    netto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ust_satz: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    ust_betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    brutto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    rechnung: Mapped["Rechnung"] = relationship(back_populates="positionen")
    artikel: Mapped["Artikel | None"] = relationship(back_populates="positionen")

    __table_args__ = (
        UniqueConstraint("rechnung_id", "position_nr", name="uq_rechnung_position"),
    )


# ---------------------------------------------------------------------------
# Bank-Integration
# ---------------------------------------------------------------------------

class BankTemplate(Base):
    """CSV-Import-Vorlagen für verschiedene Banken."""
    __tablename__ = "bank_templates"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # z.B. "sparkasse-lzo-mt940"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    bank: Mapped[str] = mapped_column(String(100), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # MT940|CAMT|Standard
    delimiter: Mapped[str] = mapped_column(String(5), default=";", nullable=False)
    encoding: Mapped[str] = mapped_column(String(20), default="UTF-8", nullable=False)
    decimal_separator: Mapped[str] = mapped_column(String(1), default=",", nullable=False)
    date_format: Mapped[str] = mapped_column(String(20), default="DD.MM.YYYY", nullable=False)
    skip_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    column_mapping: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    ist_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    autor: Mapped[str | None] = mapped_column(String(100))
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    imports: Mapped[list["BankImport"]] = relationship(back_populates="template")


class BankImport(Base):
    """Protokoll jedes CSV-Imports."""
    __tablename__ = "bank_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    konto_id: Mapped[int] = mapped_column(ForeignKey("konten.id"), nullable=False)
    template_id: Mapped[str] = mapped_column(ForeignKey("bank_templates.id"), nullable=False)
    dateiname: Mapped[str] = mapped_column(String(200), nullable=False)
    anzahl_zeilen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    erfolg: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fehler: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplikate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    importiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    konto: Mapped["Konto"] = relationship(back_populates="imports")
    template: Mapped["BankTemplate"] = relationship(back_populates="imports")
    transaktionen: Mapped[list["BankTransaktion"]] = relationship(back_populates="import_")


class BankTransaktion(Base):
    """Importierte Bank-Transaktion."""
    __tablename__ = "bank_transaktionen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    konto_id: Mapped[int] = mapped_column(ForeignKey("konten.id"), nullable=False)
    import_id: Mapped[int] = mapped_column(ForeignKey("bank_imports.id"), nullable=False)
    datum: Mapped[date] = mapped_column(Date, nullable=False)
    valuta: Mapped[date | None] = mapped_column(Date)
    buchungstext: Mapped[str | None] = mapped_column(String(500))
    verwendungszweck: Mapped[str | None] = mapped_column(Text)
    partner_name: Mapped[str | None] = mapped_column(String(200))
    partner_iban: Mapped[str | None] = mapped_column(String(34))
    betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    waehrung: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    saldo: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    # Klassifizierung (Mischkonto)
    ist_geschaeftlich: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ist_privatentnahme: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ist_einlage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_vorschlag: Mapped[str | None] = mapped_column(String(20))
    user_ueberschrieben: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Zuordnung
    kategorie_id: Mapped[int | None] = mapped_column(ForeignKey("kategorien.id"))
    rechnung_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"))
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    konto: Mapped["Konto"] = relationship(back_populates="transaktionen")
    import_: Mapped["BankImport"] = relationship(back_populates="transaktionen")
    kategorie: Mapped["Kategorie | None"] = relationship(back_populates="transaktionen")


class AutoFilterRegel(Base):
    """Automatische Klassifizierungsregeln für Bank-Transaktionen."""
    __tablename__ = "auto_filter_regeln"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partner_pattern: Mapped[str | None] = mapped_column(String(200))  # SQL LIKE, z.B. "%Amazon%"
    verwendungszweck_pattern: Mapped[str | None] = mapped_column(String(200))
    vorschlag: Mapped[str] = mapped_column(String(20), nullable=False)  # geschaeftlich|privat|privatentnahme
    kategorie_id: Mapped[int | None] = mapped_column(ForeignKey("kategorien.id"))
    prioritaet: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# Anlagevermögen / AfA
# ---------------------------------------------------------------------------

class Anlagegut(Base):
    """Anlagevermögen für AfA-Berechnung."""
    __tablename__ = "anlagegueter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bezeichnung: Mapped[str] = mapped_column(String(200), nullable=False)
    anschaffungsdatum: Mapped[date] = mapped_column(Date, nullable=False)
    anschaffungskosten_netto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    nutzungsdauer_jahre: Mapped[int] = mapped_column(Integer, nullable=False)
    afa_methode: Mapped[str] = mapped_column(String(20), default="linear", nullable=False)  # linear|degressiv
    afa_jahresbetrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    restbuchwert: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vollstaendig_abgeschrieben: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rechnung_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"))
    notizen: Mapped[str | None] = mapped_column(Text)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    rechnung: Mapped["Rechnung | None"] = relationship(back_populates="anlagegueter")


# ---------------------------------------------------------------------------
# Steuerexporte
# ---------------------------------------------------------------------------

class UstvaExport(Base):
    """Gespeicherte UStVA-Daten pro Zeitraum."""
    __tablename__ = "ustva_exporte"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zeitraum: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM oder YYYY-QN
    zeitraum_typ: Mapped[str] = mapped_column(String(20), default="monatlich", nullable=False)
    # Kennziffern
    kz_81: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # Umsätze 19%
    kz_83: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # USt 19%
    kz_86: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # Umsätze 7%
    kz_88: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # USt 7%
    kz_41: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # EU-Lieferungen
    kz_89: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # EU-Erwerb
    kz_93: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # USt aus EU-Erwerb
    kz_61: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # Vorsteuer EU-Erwerb
    kz_66: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)   # Vorsteuer Inland
    zahllast: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    daten_json: Mapped[str | None] = mapped_column(Text)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("zeitraum", name="uq_ustva_zeitraum"),
    )


class EksExport(Base):
    """Anlage EKS Export-Protokoll."""
    __tablename__ = "eks_exporte"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zeitraum_von: Mapped[date] = mapped_column(Date, nullable=False)
    zeitraum_bis: Mapped[date] = mapped_column(Date, nullable=False)
    art: Mapped[str] = mapped_column(String(20), default="vorlaeufig", nullable=False)  # vorlaeufig|abschliessend
    datei_pfad: Mapped[str | None] = mapped_column(String(500))
    daten_json: Mapped[str | None] = mapped_column(Text)
    exportiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EuerExport(Base):
    """EÜR Export-Protokoll."""
    __tablename__ = "euer_exporte"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jahr: Mapped[int] = mapped_column(Integer, nullable=False)
    einnahmen_gesamt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    ausgaben_gesamt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    afa_gesamt: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    gewinn: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    export_format: Mapped[str] = mapped_column(String(20), default="csv", nullable=False)
    datei_pfad: Mapped[str | None] = mapped_column(String(500))
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DatevExportLog(Base):
    """DATEV-Export Protokoll."""
    __tablename__ = "datev_export_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zeitraum_von: Mapped[date] = mapped_column(Date, nullable=False)
    zeitraum_bis: Mapped[date] = mapped_column(Date, nullable=False)
    anzahl_buchungen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    datei_pfad: Mapped[str | None] = mapped_column(String(500))
    exportiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ---------------------------------------------------------------------------
# EU-Stammdaten
# ---------------------------------------------------------------------------

class EuLand(Base):
    """EU-Mitgliedsstaaten für EU-Handel."""
    __tablename__ = "eu_laender"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)  # DE, FR, AT ...
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    mwst_satz_standard: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    mwst_satz_reduziert: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ust_idnr_format: Mapped[str | None] = mapped_column(String(50))  # Regex-Muster
