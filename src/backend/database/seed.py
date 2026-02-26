"""
Startwerte für die Datenbank:
- Standard-Kategorien (SKR03/SKR04 + EKS-Zuordnung)
- EU-Mitgliedsstaaten
"""

from sqlalchemy.orm import Session
from .models import Kategorie, EuLand, Nummernkreis


STANDARD_KATEGORIEN = [
    # --- Einnahmen ---
    {"name": "Betriebseinnahmen",          "kontenart": "Erlös",   "konto_skr03": "8400", "konto_skr04": "4400", "eks_kategorie": "A1",  "euer_zeile": 11, "vorsteuer_prozent": 0,   "ust_satz_standard": 19},
    {"name": "Betriebseinnahmen (7%)",     "kontenart": "Erlös",   "konto_skr03": "8300", "konto_skr04": "4300", "eks_kategorie": "A1",  "euer_zeile": 12, "vorsteuer_prozent": 0,   "ust_satz_standard": 7},
    {"name": "Betriebseinnahmen (0%)",     "kontenart": "Erlös",   "konto_skr03": "8100", "konto_skr04": "4100", "eks_kategorie": "A1",  "euer_zeile": 14, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
    {"name": "Kleinunternehmer-Einnahmen", "kontenart": "Erlös",   "konto_skr03": "8100", "konto_skr04": "4100", "eks_kategorie": "A1",  "euer_zeile": 14, "vorsteuer_prozent": 0,   "ust_satz_standard": 0},
    {"name": "Privateinlage",              "kontenart": "Privat",  "konto_skr03": "1890", "konto_skr04": "2100", "eks_kategorie": None,  "euer_zeile": None, "vorsteuer_prozent": 0,  "ust_satz_standard": 0},
    # --- Ausgaben: Büro & Verwaltung ---
    {"name": "Büromaterial",              "kontenart": "Aufwand", "konto_skr03": "4910", "konto_skr04": "6815", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Büroausstattung",           "kontenart": "Aufwand", "konto_skr03": "4920", "konto_skr04": "6820", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Porto & Versand",           "kontenart": "Aufwand", "konto_skr03": "4930", "konto_skr04": "6825", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Telefon & Internet",        "kontenart": "Aufwand", "konto_skr03": "4920", "konto_skr04": "6820", "eks_kategorie": "B10", "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Software & Abonnements",    "kontenart": "Aufwand", "konto_skr03": "4940", "konto_skr04": "6831", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Steuerberatung",            "kontenart": "Aufwand", "konto_skr03": "4960", "konto_skr04": "6835", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Rechts- & Beratungskosten","kontenart": "Aufwand", "konto_skr03": "4970", "konto_skr04": "6840", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Buchführungskosten",        "kontenart": "Aufwand", "konto_skr03": "4975", "konto_skr04": "6845", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    # --- Ausgaben: Raumkosten ---
    {"name": "Miete Büro",               "kontenart": "Aufwand", "konto_skr03": "4210", "konto_skr04": "6310", "eks_kategorie": "B5",  "euer_zeile": 46, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Nebenkosten Büro",         "kontenart": "Aufwand", "konto_skr03": "4230", "konto_skr04": "6320", "eks_kategorie": "B5",  "euer_zeile": 46, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Arbeitszimmer (anteilig)", "kontenart": "Aufwand", "konto_skr03": "4215", "konto_skr04": "6315", "eks_kategorie": "B5",  "euer_zeile": 46, "vorsteuer_prozent": 0,    "ust_satz_standard": 0},
    # --- Ausgaben: KFZ ---
    {"name": "KFZ-Kosten",              "kontenart": "Aufwand", "konto_skr03": "4530", "konto_skr04": "6520", "eks_kategorie": "B7",  "euer_zeile": 48, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "KFZ-Versicherung",        "kontenart": "Aufwand", "konto_skr03": "4360", "konto_skr04": "6430", "eks_kategorie": "B7",  "euer_zeile": 48, "vorsteuer_prozent": 0,    "ust_satz_standard": 0},
    {"name": "Reisekosten",             "kontenart": "Aufwand", "konto_skr03": "4660", "konto_skr04": "6640", "eks_kategorie": "B8",  "euer_zeile": 49, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    # --- Ausgaben: Wareneinkauf ---
    {"name": "Wareneinkauf",              "kontenart": "Aufwand", "konto_skr03": "3000", "konto_skr04": "5000", "eks_kategorie": "B1",  "euer_zeile": 26, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Wareneinkauf (7%)",         "kontenart": "Aufwand", "konto_skr03": "3000", "konto_skr04": "5000", "eks_kategorie": "B1",  "euer_zeile": 26, "vorsteuer_prozent": 100,  "ust_satz_standard": 7},
    # --- Ausgaben: Personal ---
    {"name": "Löhne & Gehälter",        "kontenart": "Aufwand", "konto_skr03": "4120", "konto_skr04": "6010", "eks_kategorie": "B3",  "euer_zeile": 44, "vorsteuer_prozent": 0,    "ust_satz_standard": 0},
    {"name": "Fremdleistungen",         "kontenart": "Aufwand", "konto_skr03": "3100", "konto_skr04": "5900", "eks_kategorie": "B4",  "euer_zeile": 45, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    # --- Ausgaben: Marketing ---
    {"name": "Werbung & Marketing",     "kontenart": "Aufwand", "konto_skr03": "4600", "konto_skr04": "6600", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Bewirtungskosten",        "kontenart": "Aufwand", "konto_skr03": "4650", "konto_skr04": "6620", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 70,   "ust_satz_standard": 19},
    # --- Ausgaben: Fortbildung ---
    {"name": "Fortbildung & Fachliteratur", "kontenart": "Aufwand", "konto_skr03": "4945", "konto_skr04": "6820", "eks_kategorie": "B9", "euer_zeile": 40, "vorsteuer_prozent": 100, "ust_satz_standard": 19},
    # --- Ausgaben: Versicherungen ---
    {"name": "Betriebsversicherungen",  "kontenart": "Aufwand", "konto_skr03": "4360", "konto_skr04": "6430", "eks_kategorie": "B6",  "euer_zeile": 47, "vorsteuer_prozent": 0,    "ust_satz_standard": 0},
    {"name": "Berufsgenossenschaft",    "kontenart": "Aufwand", "konto_skr03": "4380", "konto_skr04": "6450", "eks_kategorie": "B6",  "euer_zeile": 47, "vorsteuer_prozent": 0,    "ust_satz_standard": 0},
    # --- Ausgaben: Bankkosten ---
    {"name": "Bankgebühren",            "kontenart": "Aufwand", "konto_skr03": "4970", "konto_skr04": "6855", "eks_kategorie": "B9",  "euer_zeile": 50, "vorsteuer_prozent": 0,    "ust_satz_standard": 0},
    # --- Ausgaben: Sonstiges ---
    {"name": "Sonstige Betriebsausgaben","kontenart": "Aufwand","konto_skr03": "4980", "konto_skr04": "6880", "eks_kategorie": "B18", "euer_zeile": 50, "vorsteuer_prozent": 100,  "ust_satz_standard": 19},
    {"name": "Privatentnahme",           "kontenart": "Privat", "konto_skr03": "1800", "konto_skr04": "2010", "eks_kategorie": None,  "euer_zeile": None, "vorsteuer_prozent": 0,  "ust_satz_standard": 0},
    # --- Anlagevermögen ---
    {"name": "Anlagevermögen (Kauf)",    "kontenart": "Anlage", "konto_skr03": "0400", "konto_skr04": "0400", "eks_kategorie": "C1",  "euer_zeile": None, "vorsteuer_prozent": 100, "ust_satz_standard": 19},
    {"name": "Geringwertige Wirtschaftsgüter (GWG)", "kontenart": "Aufwand", "konto_skr03": "0480", "konto_skr04": "0680", "eks_kategorie": "B9", "euer_zeile": 50, "vorsteuer_prozent": 100, "ust_satz_standard": 19},
]

EU_LAENDER = [
    {"code": "AT", "name": "Österreich",       "mwst_satz_standard": 20, "mwst_satz_reduziert": 10,  "ust_idnr_format": "ATU[0-9]{8}"},
    {"code": "BE", "name": "Belgien",           "mwst_satz_standard": 21, "mwst_satz_reduziert": 6,   "ust_idnr_format": "BE[0-9]{10}"},
    {"code": "BG", "name": "Bulgarien",         "mwst_satz_standard": 20, "mwst_satz_reduziert": 9,   "ust_idnr_format": "BG[0-9]{9,10}"},
    {"code": "CY", "name": "Zypern",            "mwst_satz_standard": 19, "mwst_satz_reduziert": 5,   "ust_idnr_format": "CY[0-9]{8}[A-Z]"},
    {"code": "CZ", "name": "Tschechien",        "mwst_satz_standard": 21, "mwst_satz_reduziert": 12,  "ust_idnr_format": "CZ[0-9]{8,10}"},
    {"code": "DE", "name": "Deutschland",       "mwst_satz_standard": 19, "mwst_satz_reduziert": 7,   "ust_idnr_format": "DE[0-9]{9}"},
    {"code": "DK", "name": "Dänemark",          "mwst_satz_standard": 25, "mwst_satz_reduziert": None,"ust_idnr_format": "DK[0-9]{8}"},
    {"code": "EE", "name": "Estland",           "mwst_satz_standard": 22, "mwst_satz_reduziert": 9,   "ust_idnr_format": "EE[0-9]{9}"},
    {"code": "ES", "name": "Spanien",           "mwst_satz_standard": 21, "mwst_satz_reduziert": 10,  "ust_idnr_format": "ES[A-Z0-9][0-9]{7}[A-Z0-9]"},
    {"code": "FI", "name": "Finnland",          "mwst_satz_standard": 25, "mwst_satz_reduziert": 10,  "ust_idnr_format": "FI[0-9]{8}"},
    {"code": "FR", "name": "Frankreich",        "mwst_satz_standard": 20, "mwst_satz_reduziert": 5,   "ust_idnr_format": "FR[A-Z0-9]{2}[0-9]{9}"},
    {"code": "GR", "name": "Griechenland",      "mwst_satz_standard": 24, "mwst_satz_reduziert": 13,  "ust_idnr_format": "EL[0-9]{9}"},
    {"code": "HR", "name": "Kroatien",          "mwst_satz_standard": 25, "mwst_satz_reduziert": 13,  "ust_idnr_format": "HR[0-9]{11}"},
    {"code": "HU", "name": "Ungarn",            "mwst_satz_standard": 27, "mwst_satz_reduziert": 18,  "ust_idnr_format": "HU[0-9]{8}"},
    {"code": "IE", "name": "Irland",            "mwst_satz_standard": 23, "mwst_satz_reduziert": 9,   "ust_idnr_format": "IE[0-9]{7}[A-Z]{1,2}"},
    {"code": "IT", "name": "Italien",           "mwst_satz_standard": 22, "mwst_satz_reduziert": 10,  "ust_idnr_format": "IT[0-9]{11}"},
    {"code": "LT", "name": "Litauen",           "mwst_satz_standard": 21, "mwst_satz_reduziert": 9,   "ust_idnr_format": "LT([0-9]{9}|[0-9]{12})"},
    {"code": "LU", "name": "Luxemburg",         "mwst_satz_standard": 17, "mwst_satz_reduziert": 8,   "ust_idnr_format": "LU[0-9]{8}"},
    {"code": "LV", "name": "Lettland",          "mwst_satz_standard": 21, "mwst_satz_reduziert": 12,  "ust_idnr_format": "LV[0-9]{11}"},
    {"code": "MT", "name": "Malta",             "mwst_satz_standard": 18, "mwst_satz_reduziert": 5,   "ust_idnr_format": "MT[0-9]{8}"},
    {"code": "NL", "name": "Niederlande",       "mwst_satz_standard": 21, "mwst_satz_reduziert": 9,   "ust_idnr_format": "NL[0-9]{9}B[0-9]{2}"},
    {"code": "PL", "name": "Polen",             "mwst_satz_standard": 23, "mwst_satz_reduziert": 8,   "ust_idnr_format": "PL[0-9]{10}"},
    {"code": "PT", "name": "Portugal",          "mwst_satz_standard": 23, "mwst_satz_reduziert": 13,  "ust_idnr_format": "PT[0-9]{9}"},
    {"code": "RO", "name": "Rumänien",          "mwst_satz_standard": 19, "mwst_satz_reduziert": 9,   "ust_idnr_format": "RO[0-9]{2,10}"},
    {"code": "SE", "name": "Schweden",          "mwst_satz_standard": 25, "mwst_satz_reduziert": 12,  "ust_idnr_format": "SE[0-9]{12}"},
    {"code": "SI", "name": "Slowenien",         "mwst_satz_standard": 22, "mwst_satz_reduziert": 9,   "ust_idnr_format": "SI[0-9]{8}"},
    {"code": "SK", "name": "Slowakei",          "mwst_satz_standard": 20, "mwst_satz_reduziert": 10,  "ust_idnr_format": "SK[0-9]{10}"},
]


def seed_kategorien(db: Session) -> None:
    if db.query(Kategorie).count() > 0:
        return
    for data in STANDARD_KATEGORIEN:
        db.add(Kategorie(**data))
    db.commit()


def seed_eu_laender(db: Session) -> None:
    if db.query(EuLand).count() > 0:
        return
    for data in EU_LAENDER:
        db.add(EuLand(**data))
    db.commit()


def seed_nummernkreise(db: Session) -> None:
    typen = {nk.typ for nk in db.query(Nummernkreis).all()}
    neue = []
    if "kassenbuch" not in typen:
        neue.append(Nummernkreis(
            bezeichnung="Kassenbuch",
            typ="kassenbuch",
            format="YY####",
            naechste_nr=1,
            reset_jaehrlich=True,
        ))
    if "rechnung_ausgang" not in typen:
        neue.append(Nummernkreis(
            bezeichnung="Ausgangsrechnungen",
            typ="rechnung_ausgang",
            format="YY####",
            naechste_nr=1,
            reset_jaehrlich=True,
        ))
    if "rechnung_eingang" not in typen:
        neue.append(Nummernkreis(
            bezeichnung="Eingangsrechnungen",
            typ="rechnung_eingang",
            format="YY####",
            naechste_nr=1,
            reset_jaehrlich=True,
        ))
    if "kunde" not in typen:
        neue.append(Nummernkreis(
            bezeichnung="Kundennummern",
            typ="kunde",
            format="KD-####",
            naechste_nr=1,
            reset_jaehrlich=False,
        ))
    if "lieferant" not in typen:
        neue.append(Nummernkreis(
            bezeichnung="Lieferantennummern",
            typ="lieferant",
            format="LI-####",
            naechste_nr=1,
            reset_jaehrlich=False,
        ))
    if neue:
        for nk in neue:
            db.add(nk)
        db.commit()


def run_all_seeds(db: Session) -> None:
    seed_kategorien(db)
    seed_eu_laender(db)
    seed_nummernkreise(db)
