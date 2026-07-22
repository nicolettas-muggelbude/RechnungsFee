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
    w_idnr: Mapped[str | None] = mapped_column(String(20))
    finanzamt: Mapped[str | None] = mapped_column(String(200))
    voranmeldungsrhythmus: Mapped[str] = mapped_column(String(12), default="quartal", nullable=False)  # monat|quartal
    bundesland: Mapped[str | None] = mapped_column(String(2))  # z.B. BY, NW, BE
    dauerfristverlaengerung_ust: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    est_vorauszahlungen_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gewst_vorauszahlungen_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Status
    ist_kleinunternehmer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bezieht_transferleistungen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Bürgergeld / Transferleistungen (für Anlage EKS)
    geburtsdatum: Mapped[date | None] = mapped_column(Date)
    bg_nummer: Mapped[str | None] = mapped_column(String(50))       # Bedarfsgemeinschaftsnummer
    jobcenter_name: Mapped[str | None] = mapped_column(String(200)) # z.B. "Jobcenter Berlin-Mitte"
    leistungsbescheid_monat: Mapped[str | None] = mapped_column(String(7))  # YYYY-MM – Beginn 6-Monats-Abrechnungszeitraum
    # Lieferschein / Angebote / Proforma / Aufträge
    lieferschein_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    angebote_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    proforma_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    auftraege_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    wiederkehrend_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    buchungsvorlagen_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    lagerführung_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
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
    bezeichnung_des_gewerbes: Mapped[str | None] = mapped_column(String(200))  # Anlage G Z.4: "genaue Bezeichnung des Gewerbes"
    kammer_mitgliedschaft: Mapped[str | None] = mapped_column(String(200))   # z.B. "Rechtsanwaltskammer Berlin"
    # Rechnungs-PDF-Einstellungen
    zahlungshinweis_aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pdf_vorlage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    einleitungstext: Mapped[str | None] = mapped_column(Text)
    # Logo & Mail-Vorlagen
    logo_pfad: Mapped[str | None] = mapped_column(String(500))
    mail_betreff_vorlage: Mapped[str | None] = mapped_column(String(500))
    mail_text_vorlage: Mapped[str | None] = mapped_column(Text)
    mail_betreff_angebot: Mapped[str | None] = mapped_column(String(500))
    mail_text_angebot: Mapped[str | None] = mapped_column(Text)
    mail_betreff_proforma: Mapped[str | None] = mapped_column(String(500))
    mail_text_proforma: Mapped[str | None] = mapped_column(Text)
    mail_betreff_auftrag: Mapped[str | None] = mapped_column(String(500))
    mail_text_auftrag: Mapped[str | None] = mapped_column(Text)
    mail_signatur: Mapped[str | None] = mapped_column(Text)
    # SMTP
    smtp_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    smtp_host: Mapped[str | None] = mapped_column(String(200))
    smtp_port: Mapped[int] = mapped_column(Integer, default=587, server_default="587", nullable=False)
    smtp_ssl: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    smtp_user: Mapped[str | None] = mapped_column(String(200))
    smtp_passwort: Mapped[str | None] = mapped_column(String(500))
    smtp_von_adresse: Mapped[str | None] = mapped_column(String(200))
    unterschrift_bild: Mapped[str | None] = mapped_column(Text)           # base64-PNG
    unterschrift_auf_rechnung: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    standard_zahlungsziel: Mapped[int] = mapped_column(Integer, default=14, server_default="14")
    qr_zahlung_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    standard_skonto_prozent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    standard_skonto_tage: Mapped[int | None] = mapped_column(Integer)
    backup_extern_pfad_1:  Mapped[str | None] = mapped_column(Text)
    backup_extern_pfad_2:  Mapped[str | None] = mapped_column(Text)
    backup_extern_passwort: Mapped[str | None] = mapped_column(Text)
    backup_smb_benutzer:   Mapped[str | None] = mapped_column(Text)
    backup_smb_passwort:   Mapped[str | None] = mapped_column(Text)
    # DATEV-Konfiguration
    datev_beraternummer:   Mapped[str | None] = mapped_column(String(10))
    datev_mandantennummer: Mapped[str | None] = mapped_column(String(10))
    datev_konto_bar:       Mapped[str | None] = mapped_column(String(10))
    datev_konto_bank:      Mapped[str | None] = mapped_column(String(10))
    datev_konto_karte:     Mapped[str | None] = mapped_column(String(10))
    datev_konto_paypal:    Mapped[str | None] = mapped_column(String(10))
    # GuV / §141 AO Buchführungspflicht
    guv_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    # Kontenübersicht (Kategorien-Summenliste mit SKR03/04-Kontonummern)
    kontenuebersicht_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    # Bank CSV-Import
    bank_import_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    bank_import_manuell: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    # Datenübernahme per CSV
    datenmigration_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    # Dashboard-Konfiguration (JSON: widget_order, widget_visibility, quicklinks)
    dashboard_config: Mapped[str | None] = mapped_column(Text)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Konto(Base):
    """Bankkonten und Zahlungsdienstleister des Unternehmens."""
    __tablename__ = "konten"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    anbieter: Mapped[str] = mapped_column(String(100), nullable=False)       # Bank- oder Dienstleistername
    kontoart: Mapped[str] = mapped_column(String(30), default="bank", nullable=False)   # bank|zahlungsdienstleister
    iban: Mapped[str | None] = mapped_column(String(34))                     # nur für kontoart=bank
    bic: Mapped[str | None] = mapped_column(String(11))
    kennung: Mapped[str | None] = mapped_column(String(200))                 # PayPal-E-Mail, Stripe-ID etc.
    kontotyp: Mapped[str] = mapped_column(String(20), default="geschaeftlich", nullable=False)  # geschaeftlich|mischkonto
    ist_standard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    datev_kontonummer: Mapped[str | None] = mapped_column(String(8))  # individuelles DATEV-Gegenkonto (z.B. 1200, 1210)
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
    konto_skr03_default: Mapped[str | None] = mapped_column(String(10))
    konto_skr04_default: Mapped[str | None] = mapped_column(String(10))
    user_modified_skr03: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    user_modified_skr04: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="0")
    eks_kategorie: Mapped[str | None] = mapped_column(String(10))  # B9, A1 etc.
    euer_zeile: Mapped[int | None] = mapped_column(Integer)
    vorsteuer_prozent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=100, nullable=False)
    ust_satz_standard: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 0|7|19
    ist_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    beschreibung: Mapped[str | None] = mapped_column(Text)  # Beispiele / Verwendungshinweis
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    journaleintraege: Mapped[list["Journaleintrag"]] = relationship(back_populates="kategorie")
    rechnungen: Mapped[list["Rechnung"]] = relationship(back_populates="kategorie")
    transaktionen: Mapped[list["BankTransaktion"]] = relationship(back_populates="kategorie")


class Schnellbuchung(Base):
    """Wiederverwendbare Vorlage für häufige manuelle Journalbuchungen (Issue #256).

    Anders als Buchungsvorlagen (terminiert/automatisch) ist dies ein reiner
    Schnellzugriff im Journal: Kategorie, Zahlungsart und Buchungstext sind
    fest hinterlegt, nur Betrag und Datum werden beim Buchen noch eingegeben.
    """
    __tablename__ = "schnellbuchungen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # Button-Beschriftung, z.B. "Tankquittung"
    art: Mapped[str] = mapped_column(String(10), nullable=False)  # Einnahme|Ausgabe
    kategorie_id: Mapped[int] = mapped_column(ForeignKey("kategorien.id"), nullable=False)
    zahlungsart: Mapped[str] = mapped_column(String(20), nullable=False)  # Bar|Karte|Bank|PayPal
    beschreibung: Mapped[str] = mapped_column(String(500), nullable=False)  # Buchungstext-Vorlage
    reihenfolge: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    kategorie: Mapped["Kategorie"] = relationship()


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
    typ: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)  # journal, rechnung_ausgang, ...
    format: Mapped[str] = mapped_column(String(50), default="YY####", nullable=False)
    naechste_nr: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reset_jaehrlich: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    letztes_jahr: Mapped[int | None] = mapped_column(Integer)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Journal (GoBD-konform, unveränderbar)
# ---------------------------------------------------------------------------

class Journaleintrag(Base):
    """
    GoBD-konformes Journal.
    Einträge sind nach Erstellung unveränderbar (immutable=True).
    """
    __tablename__ = "journal"

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
    vorsteuer_betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)  # abziehbarer Anteil (berücksichtigt vorsteuer_prozent der Kategorie, z.B. 70% Bewirtungskosten)
    brutto_betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vorsteuerabzug: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    steuerbefreiung_grund: Mapped[str | None] = mapped_column(String(100))  # z.B. "§19 UStG"
    rechnung_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"))
    beleg_id: Mapped[int | None] = mapped_column(ForeignKey("belege.id"))
    buchungsvorlage_id: Mapped[int | None] = mapped_column(ForeignKey("buchungsvorlagen.id"))
    konto_id: Mapped[int | None] = mapped_column(ForeignKey("konten.id", ondelete="SET NULL"))  # Bankkonto (für DATEV Gegenkonto per Konto)
    # Kontonummern-Snapshot (aus Kategorie zum Buchungszeitpunkt – unveränderbar)
    konto_skr03: Mapped[str | None] = mapped_column(String(10))
    konto_skr04: Mapped[str | None] = mapped_column(String(10))
    # USt-Gegenkonto (1776/1771 bei Einnahme, 1575/1570 bei Ausgabe in SKR03 etc.)
    konto_ust_skr03: Mapped[str | None] = mapped_column(String(10))
    konto_ust_skr04: Mapped[str | None] = mapped_column(String(10))
    # km-Pauschale (optional – für Fahrtkosten Privat-PKW)
    km_anzahl: Mapped[Decimal | None] = mapped_column(Numeric(10, 1))
    # Innergemeinschaftlicher Erwerb §1a UStG: USt (KZ 89/93) + Vorsteuer (KZ 61) getrennt von KZ 66
    ist_ig_erwerb: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Reverse-Charge-Typ: ig_erwerb | 13b_abs1 | 13b_abs2 | NULL (normal)
    ust_sonderfall: Mapped[str | None] = mapped_column(String(20))
    # §25a Differenzbesteuerung: Brutto-Marge (VK − EK) für UStVA KZ 81/83
    marge_25a_brutto: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    # Verknuepft zusammengehoerige Buchungen (Original + Storno + ggf. Neubuchung einer
    # Korrektur) - zeigt auf die id der aeltesten Buchung der Kette (Original). Reine
    # Verknuepfungs-Metadaten, NICHT Teil der GoBD-Signatur (siehe utils/signatur.py).
    gruppe_id: Mapped[int | None] = mapped_column(ForeignKey("journal.id"))
    # GoBD
    immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signatur: Mapped[str | None] = mapped_column(String(64))
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    erstellt_von: Mapped[str | None] = mapped_column(String(100))

    kategorie: Mapped["Kategorie | None"] = relationship(back_populates="journaleintraege")
    kunde: Mapped["Kunde | None"] = relationship()
    rechnung: Mapped["Rechnung | None"] = relationship(back_populates="journaleintraege")


class Tagesabschluss(Base):
    """Journal-Tagesabschluss (GoBD-konform, unveränderbar)."""
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
    debitor_nr: Mapped[str | None] = mapped_column(String(20), unique=True)
    z_hd: Mapped[str | None] = mapped_column(String(200))
    notizen: Mapped[str | None] = mapped_column(Text)
    zugferd_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skonto_prozent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    skonto_tage: Mapped[int | None] = mapped_column(Integer)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    rechnungen: Mapped[list["Rechnung"]] = relationship(back_populates="kunde")
    lieferadressen: Mapped[list["KundeLieferadresse"]] = relationship(
        back_populates="kunde", cascade="all, delete-orphan", order_by="KundeLieferadresse.id"
    )
    dokumente: Mapped[list["KundeBeleg"]] = relationship(
        back_populates="kunde", cascade="all, delete-orphan", order_by="KundeBeleg.id"
    )


class KundeBeleg(Base):
    """Dokument am Kundenstammsatz (Vertrag, Bescheinigung, Dokumentation …)."""
    __tablename__ = "kunden_belege"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kunde_id: Mapped[int] = mapped_column(ForeignKey("kunden.id", ondelete="CASCADE"), nullable=False)
    beleg_id: Mapped[int] = mapped_column(ForeignKey("belege.id", ondelete="CASCADE"), nullable=False)
    bezeichnung: Mapped[str | None] = mapped_column(String(200))
    loeschdatum: Mapped[date | None] = mapped_column(Date)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    kunde: Mapped["Kunde"] = relationship(back_populates="dokumente")
    beleg: Mapped["Beleg"] = relationship()


class KundeLieferadresse(Base):
    """Separate Lieferadressen eines Kunden (abweichend von Rechnungsadresse)."""
    __tablename__ = "kunden_lieferadressen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kunde_id: Mapped[int] = mapped_column(ForeignKey("kunden.id"), nullable=False)
    bezeichnung: Mapped[str | None] = mapped_column(String(100))   # z.B. „Lager Nord", „Filiale Berlin"
    z_hd: Mapped[str | None] = mapped_column(String(200))
    strasse: Mapped[str | None] = mapped_column(String(200))
    hausnummer: Mapped[str | None] = mapped_column(String(20))
    plz: Mapped[str | None] = mapped_column(String(10))
    ort: Mapped[str | None] = mapped_column(String(100))
    land: Mapped[str] = mapped_column(String(2), default="DE", nullable=False)
    ist_standard: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    kunde: Mapped["Kunde"] = relationship(back_populates="lieferadressen")


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
    kreditor_nr: Mapped[str | None] = mapped_column(String(20), unique=True)
    z_hd: Mapped[str | None] = mapped_column(String(200))
    notizen: Mapped[str | None] = mapped_column(Text)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    rechnungen: Mapped[list["Rechnung"]] = relationship(back_populates="lieferant")
    artikel: Mapped[list["Artikel"]] = relationship(back_populates="lieferant")


# ---------------------------------------------------------------------------
# Artikelstamm
# ---------------------------------------------------------------------------

class ArtikelGruppe(Base):
    """Warengruppen / Servicegruppen / Fremdleistungsgruppen."""
    __tablename__ = "artikel_gruppen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    typ: Mapped[str] = mapped_column(String(20), nullable=False)   # artikel|dienstleistung|fremdleistung
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    artikel: Mapped[list["Artikel"]] = relationship(back_populates="gruppe_obj")

    __table_args__ = (UniqueConstraint("typ", "name", name="uix_artikel_gruppen_typ_name"),)


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
    gruppe_id: Mapped[int | None] = mapped_column(ForeignKey("artikel_gruppen.id"))
    differenzbesteuerung: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Lagerführung-Light
    lager_aktiv: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    bestand_aktuell: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0, server_default="0", nullable=False)
    mindestbestand: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0, server_default="0", nullable=False)
    minusbestand_erlaubt: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", nullable=False)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    lieferant: Mapped["Lieferant | None"] = relationship(back_populates="artikel")
    gruppe_obj: Mapped["ArtikelGruppe | None"] = relationship(back_populates="artikel")
    positionen: Mapped[list["Rechnungsposition"]] = relationship(back_populates="artikel")


# ---------------------------------------------------------------------------
# Belege (Dateianhänge an Rechnungen und Journaleinträge)
# ---------------------------------------------------------------------------

class Beleg(Base):
    """Dateianhang (PDF, Bild) – verknüpfbar mit Rechnungen und Journaleinträgen."""
    __tablename__ = "belege"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dateiname: Mapped[str] = mapped_column(String(500), nullable=False)         # relativer Pfad im uploads-Verzeichnis
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)     # Dateiname beim Upload
    mime_type: Mapped[str | None] = mapped_column(String(100))
    dateigroesse: Mapped[int | None] = mapped_column(Integer)                   # Bytes
    sha256: Mapped[str | None] = mapped_column(String(64))                      # GoBD: Unveränderlichkeit prüfbar
    hochgeladen_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    beleg_pdfa_pfad: Mapped[str | None] = mapped_column(String(500))            # rel. Pfad PDF/A-3-Version (GoBD-Archiv)


# ---------------------------------------------------------------------------
# Dokumentenpakete (Anhang-Gruppen für Angebote / Auftragsbestätigungen)
# ---------------------------------------------------------------------------

class DokumentenPaket(Base):
    """Wiederverwendbares Paket aus Dokumenten (AGB, DSE, Leistungsverzeichnis …)."""
    __tablename__ = "dokumentenpakete"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    beschreibung: Mapped[str | None] = mapped_column(Text)
    aktiv: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    dateien: Mapped[list["DokumentenPaketBeleg"]] = relationship(
        "DokumentenPaketBeleg", back_populates="paket",
        cascade="all, delete-orphan", order_by="DokumentenPaketBeleg.sort_order"
    )


class DokumentenPaketBeleg(Base):
    """Eintrag eines Belegs in einem Dokumentenpaket."""
    __tablename__ = "dokumentenpaket_belege"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paket_id: Mapped[int] = mapped_column(Integer, ForeignKey("dokumentenpakete.id", ondelete="CASCADE"), nullable=False)
    beleg_id: Mapped[int] = mapped_column(Integer, ForeignKey("belege.id", ondelete="CASCADE"), nullable=False)
    bezeichnung: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    paket: Mapped["DokumentenPaket"] = relationship("DokumentenPaket", back_populates="dateien")
    beleg: Mapped["Beleg"] = relationship("Beleg")


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
    partner_strasse: Mapped[str | None] = mapped_column(String(200))
    partner_hausnummer: Mapped[str | None] = mapped_column(String(20))
    partner_plz: Mapped[str | None] = mapped_column(String(20))
    partner_ort: Mapped[str | None] = mapped_column(String(200))
    partner_land: Mapped[str | None] = mapped_column(String(2))
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
    beleg_id: Mapped[int | None] = mapped_column(ForeignKey("belege.id"))
    notizen: Mapped[str | None] = mapped_column(Text)
    externe_belegnr: Mapped[str | None] = mapped_column(String(100))  # Lieferanten-Rechnungsnr. (nur Eingang)
    leistung_von: Mapped[date | None] = mapped_column(Date)
    leistung_bis: Mapped[date | None] = mapped_column(Date)
    # Einleitungstext (überschreibt globalen Text aus unternehmen.einleitungstext)
    einleitungstext: Mapped[str | None] = mapped_column(Text)
    # Rabatt
    rabatt_prozent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False, server_default="0")
    rabatt_betrag: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Skonto
    skonto_prozent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    skonto_tage: Mapped[int | None] = mapped_column(Integer)
    # GoBD
    ist_entwurf: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    immutable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    storniert: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ueberzahlung_anerkannt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    storno_grund: Mapped[str | None] = mapped_column(String(500))
    storno_datum: Mapped[date | None] = mapped_column(Date, nullable=True)
    storno_rechnungsnummer: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ausgegeben: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ausgegeben_am: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    original_pdf_pfad: Mapped[str | None] = mapped_column(String(500))
    absender_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Gutschrift / Lieferschein
    dokument_typ: Mapped[str] = mapped_column(String(20), default="Rechnung", nullable=False, server_default="Rechnung")
    gutschrift_zu_rechnung_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)
    lieferschein_zu_rechnung_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)
    lieferadresse_id: Mapped[int | None] = mapped_column(ForeignKey("kunden_lieferadressen.id"), nullable=True)
    # Angebote
    angebot_status: Mapped[str | None] = mapped_column(String(20), default="offen")   # offen|akzeptiert|abgelehnt|abgelaufen
    gueltig_bis: Mapped[date | None] = mapped_column(Date)
    dokumentenpaket_id: Mapped[int | None] = mapped_column(ForeignKey("dokumentenpakete.id"), nullable=True)
    rechnung_zu_angebot_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)
    lieferschein_zu_angebot_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)
    # Proforma: gespeichert auf dem Angebot (welche Proforma daraus entstand) und auf der Proforma (welche Rechnung)
    proforma_zu_angebot_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)
    rechnung_zu_proforma_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)
    # Aufträge
    auftrag_status: Mapped[str | None] = mapped_column(String(20))  # offen|in_bearbeitung|abgeschlossen|storniert
    vorlage_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungsvorlagen.id", ondelete="SET NULL"), nullable=True)
    buchungsvorlage_id: Mapped[int | None] = mapped_column(ForeignKey("buchungsvorlagen.id", ondelete="SET NULL"), nullable=True)
    auftrag_zu_angebot_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)   # auf Angebot: welcher Auftrag entstand
    rechnung_zu_auftrag_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)  # auf Auftrag: welche Rechnung entstand
    lieferschein_zu_auftrag_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)
    proforma_zu_auftrag_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"), nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    kunde: Mapped["Kunde | None"] = relationship(back_populates="rechnungen")
    lieferant: Mapped["Lieferant | None"] = relationship(back_populates="rechnungen")
    kategorie: Mapped["Kategorie | None"] = relationship(back_populates="rechnungen")
    beleg: Mapped["Beleg | None"] = relationship(foreign_keys=[beleg_id])
    positionen: Mapped[list["Rechnungsposition"]] = relationship(back_populates="rechnung", cascade="all, delete-orphan")
    journaleintraege: Mapped[list["Journaleintrag"]] = relationship(back_populates="rechnung")


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
    netto: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    rabatt_prozent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"), nullable=False, server_default="0")
    ust_satz: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    ust_betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    brutto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    differenzbesteuerung: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ek_netto_25a: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))  # EK-Preis zum Zeitpunkt der Rechnung
    ust_satz_25a: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))   # nominaler USt-Satz (19/7) für Margensteuer

    kategorie_id: Mapped[int | None] = mapped_column(ForeignKey("kategorien.id"))

    rechnung: Mapped["Rechnung"] = relationship(back_populates="positionen")
    artikel: Mapped["Artikel | None"] = relationship(back_populates="positionen")

    __table_args__ = (
        UniqueConstraint("rechnung_id", "position_nr", name="uq_rechnung_position"),
    )


# ---------------------------------------------------------------------------
# Wiederkehrende Ausgangsrechnungen
# ---------------------------------------------------------------------------

class Rechnungsvorlage(Base):
    """Vorlage für wiederkehrende Ausgangsrechnungen (Abo-Modell)."""
    __tablename__ = "rechnungsvorlagen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bezeichnung: Mapped[str] = mapped_column(String(200), nullable=False)
    intervall: Mapped[str] = mapped_column(String(20), nullable=False)  # monatlich|quartalsweise|jaehrlich
    naechstes_datum: Mapped[date] = mapped_column(Date, nullable=False)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    beendet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    kunde_id: Mapped[int | None] = mapped_column(ForeignKey("kunden.id", ondelete="SET NULL"))
    zahlungsziel_tage: Mapped[int | None] = mapped_column(Integer)  # NULL = Unternehmens-Standard
    notizen: Mapped[str | None] = mapped_column(Text)
    positionen_json: Mapped[str] = mapped_column(Text, nullable=False, server_default="[]")
    letzte_erstellung: Mapped[date | None] = mapped_column(Date)
    erstellte_rechnungen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    auftrag_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id", ondelete="SET NULL"))
    beleg_id: Mapped[int | None] = mapped_column(ForeignKey("belege.id", ondelete="SET NULL"))

    kunde: Mapped["Kunde | None"] = relationship(foreign_keys=[kunde_id])
    auftrag: Mapped["Rechnung | None"] = relationship(foreign_keys=[auftrag_id])
    beleg: Mapped["Beleg | None"] = relationship(foreign_keys=[beleg_id])


class Anlagegut(Base):
    """Wirtschaftsgut im Anlagevermögen (Anlage AVEÜR – Abschreibungsplan)."""
    __tablename__ = "anlageverzeichnis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bezeichnung: Mapped[str] = mapped_column(String(200), nullable=False)
    typ: Mapped[str] = mapped_column(String(20), default="sonstig", nullable=False)  # kfz | edv | sonstig
    kaufdatum: Mapped[date] = mapped_column(Date, nullable=False)
    kaufpreis_netto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    nutzungsdauer_jahre: Mapped[int] = mapped_column(Integer, nullable=False)
    afa_methode: Mapped[str] = mapped_column(String(20), default="linear", nullable=False)
    kennzeichen: Mapped[str | None] = mapped_column(String(20))          # KFZ
    privat_anteil_prozent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    verkauft_am: Mapped[date | None] = mapped_column(Date)
    notizen: Mapped[str | None] = mapped_column(Text)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Buchungsvorlage(Base):
    """Vorlage für wiederkehrende Journal-Buchungen (Miete, Leasing, Abonnements)."""
    __tablename__ = "buchungsvorlagen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bezeichnung: Mapped[str] = mapped_column(String(200), nullable=False)
    lieferant_id: Mapped[int | None] = mapped_column(ForeignKey("lieferanten.id", ondelete="SET NULL"))
    kategorie_id: Mapped[int | None] = mapped_column(ForeignKey("kategorien.id", ondelete="SET NULL"))
    konto_id: Mapped[int | None] = mapped_column(ForeignKey("konten.id", ondelete="SET NULL"))
    betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ist_brutto: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ust_satz: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    intervall: Mapped[str] = mapped_column(String(20), nullable=False)  # monatlich|quartalsweise|jaehrlich
    naechstes_datum: Mapped[date] = mapped_column(Date, nullable=False)
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    modus: Mapped[str] = mapped_column(String(20), default="direkt", nullable=False)  # direkt|beleg
    art: Mapped[str] = mapped_column(String(20), default="Ausgabe", server_default="Ausgabe", nullable=False)  # Einnahme|Ausgabe
    notizen: Mapped[str | None] = mapped_column(Text)
    beleg_id: Mapped[int | None] = mapped_column(ForeignKey("belege.id", ondelete="SET NULL"))
    letzte_buchung: Mapped[date | None] = mapped_column(Date)
    erstellte_buchungen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lieferant: Mapped["Lieferant | None"] = relationship(foreign_keys=[lieferant_id])
    kategorie: Mapped["Kategorie | None"] = relationship(foreign_keys=[kategorie_id])
    konto: Mapped["Konto | None"] = relationship(foreign_keys=[konto_id])
    beleg: Mapped["Beleg | None"] = relationship(foreign_keys=[beleg_id])


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
    ist_rueckerstattung: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_vorschlag: Mapped[str | None] = mapped_column(String(20))
    user_ueberschrieben: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dedupe_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    # Zuordnung
    kategorie_id: Mapped[int | None] = mapped_column(ForeignKey("kategorien.id"))
    rechnung_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id"))
    journal_id: Mapped[int | None] = mapped_column(ForeignKey("journal.id", ondelete="SET NULL"))
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


class Forderung(Base):
    """Offene Verrechnungsposten – Fundament für Forderungsmanagement."""
    __tablename__ = "forderungen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    typ: Mapped[str] = mapped_column(String(50), default="lieferantenguthaben", nullable=False)
    # offen | ausgeglichen | ausgebucht
    status: Mapped[str] = mapped_column(String(20), default="offen", nullable=False)
    betrag: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    waehrung: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    faellig_am: Mapped[date | None] = mapped_column(Date, nullable=True)
    # partner_typ: lieferant | kunde (kein FK-Constraint für Flexibilität)
    partner_typ: Mapped[str | None] = mapped_column(String(20), nullable=True)
    partner_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rechnung_id: Mapped[int | None] = mapped_column(ForeignKey("rechnungen.id", ondelete="SET NULL"), nullable=True)
    # journal_id: Buchung die den Posten erzeugt hat
    journal_id: Mapped[int | None] = mapped_column(ForeignKey("journal.id", ondelete="SET NULL"), nullable=True)
    # ausgleich_journal_id: gesetzt bei Ausgleich oder Ausbuchen
    ausgleich_journal_id: Mapped[int | None] = mapped_column(ForeignKey("journal.id", ondelete="SET NULL"), nullable=True)
    notiz: Mapped[str | None] = mapped_column(Text, nullable=True)
    erstellt_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())



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


# ---------------------------------------------------------------------------
# EKS-Einstellungen (Singleton)
# ---------------------------------------------------------------------------

class EksEinstellungen(Base):
    """Persistente EKS-Formularfelder Abschnitte D / F / Seite 9 (Singleton id=1)."""
    __tablename__ = "eks_einstellungen"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    taetigkeitsart_text: Mapped[str | None] = mapped_column(String(200))
    taetigkeitsbeginn: Mapped[str | None] = mapped_column(String(7))
    taetigkeitsende: Mapped[str | None] = mapped_column(String(7))
    wohnung_gewerblich: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    gewerbliche_raeume: Mapped[str | None] = mapped_column(String(10))
    gewerbliche_flaeche: Mapped[str | None] = mapped_column(String(20))
    produkte_kostenfrei: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    personal_beschaeftigt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anzahl_beschaeftigte: Mapped[str | None] = mapped_column(String(10))
    weiteres_personal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    anzahl_weiteres_personal: Mapped[str | None] = mapped_column(String(10))
    personal_ab: Mapped[str | None] = mapped_column(String(10))
    umsatzsteuerpflichtig: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    zuschuss_erhalten: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    zuschuss_beantragt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    darlehen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    darlehen_hoehe: Mapped[str | None] = mapped_column(String(20))
    darlehen_eingang: Mapped[str | None] = mapped_column(String(10))
    darlehen_rueckzahlung_ab: Mapped[str | None] = mapped_column(String(10))
    darlehen_tilgung: Mapped[str | None] = mapped_column(String(20))
    darlehen_ausgaben_art: Mapped[str | None] = mapped_column(String(200))
    darlehen_ausgaben_hoehe: Mapped[str | None] = mapped_column(String(20))
    kind_ausserhalb: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    unterhalt: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fahrten_betriebsstaette: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    km_einfach: Mapped[str | None] = mapped_column(String(10))
    arbeitstage_pro_woche: Mapped[str | None] = mapped_column(String(5))
    mehraufwand_verpflegung: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    arbeitstage_verpflegung: Mapped[str | None] = mapped_column(String(5))
    aktualisiert_am: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
