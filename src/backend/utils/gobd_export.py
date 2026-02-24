"""
GoBD-Export für Betriebsprüfung (Z3-Datenträgerüberlassung).

Erzeugt ein ZIP-Archiv mit:
  - kassenbuch_journal.csv       IDEA-kompatibles Kassenbuch-Journal
  - tagesabschluesse.csv         Alle Tagesabschlüsse
  - kategorien.csv               Kategorie-Stammdaten
  - kunden.csv                   Kunden-Stammdaten
  - lieferanten.csv              Lieferanten-Stammdaten
  - integritaetspruefung.csv     SHA-256-Signaturprüfung
  - index.xml                    GDPdU-Beschreibungsdatei
  - gobd_pruefbericht.pdf        Zusammenfassender Prüfbericht

CSV-Format: UTF-8 mit BOM, Semikolon-getrennt, Dezimalkomma, Datum DD.MM.YYYY
"""

import io
import zipfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from database.models import (
    Kassenbucheintrag,
    Kategorie,
    Kunde,
    Lieferant,
    Tagesabschluss,
    Unternehmen,
)
from utils.signatur import signatur_kassenbucheintrag, signatur_tagesabschluss


# ---------------------------------------------------------------------------
# Hilfs-Formatierungen (IDEA-kompatibel)
# ---------------------------------------------------------------------------

def _fmt_decimal(val: Any) -> str:
    """Dezimalzahl mit Dezimalkomma, 2 Nachkommastellen."""
    try:
        n = Decimal(str(val))
        formatted = f"{abs(n):.2f}".replace(".", ",")
        return f"-{formatted}" if n < 0 else formatted
    except Exception:
        return "0,00"


def _fmt_date(val: Any) -> str:
    """date/str → DD.MM.YYYY."""
    if isinstance(val, date):
        return val.strftime("%d.%m.%Y")
    try:
        s = str(val)[:10]
        y, m, d_str = s.split("-")
        return f"{d_str}.{m}.{y}"
    except Exception:
        return str(val)


def _fmt_datetime(val: Any) -> str:
    """datetime/str → DD.MM.YYYY HH:MM:SS."""
    if isinstance(val, datetime):
        return val.strftime("%d.%m.%Y %H:%M:%S")
    try:
        s = str(val)
        date_part = s[:10]
        time_part = s[11:19] if len(s) > 10 else "00:00:00"
        y, m, d_str = date_part.split("-")
        return f"{d_str}.{m}.{y} {time_part}"
    except Exception:
        return str(val)


def _fmt_bool(val: Any) -> str:
    """bool → Ja/Nein."""
    return "Ja" if val else "Nein"


def _csv_zelle(wert: str) -> str:
    """Wert semikolon-sicher machen (bei Bedarf in Anführungszeichen)."""
    s = str(wert) if wert is not None else ""
    if ";" in s or '"' in s or "\n" in s:
        s = '"' + s.replace('"', '""') + '"'
    return s


def _make_csv(header: list[str], rows: list[list[str]]) -> bytes:
    """
    Erzeugt CSV-Bytes: UTF-8 mit BOM, Semikolon-getrennt.
    IDEA-kompatibel (Dezimalkomma bereits in den Werten enthalten).
    """
    lines = []
    lines.append(";".join(_csv_zelle(h) for h in header))
    for row in rows:
        lines.append(";".join(_csv_zelle(c) for c in row))
    content = "\n".join(lines) + "\n"
    # UTF-8 BOM für Excel/IDEA-Kompatibilität
    return b"\xef\xbb\xbf" + content.encode("utf-8")


# ---------------------------------------------------------------------------
# Einzelne CSV-Exporte
# ---------------------------------------------------------------------------

def export_kassenbuch_csv(db: Session, jahr: int, kontenrahmen: str = "SKR03") -> tuple[bytes, int]:
    """Kassenbuch-Journal als CSV. Gibt (bytes, anzahl_datensaetze) zurück."""
    eintraege = (
        db.query(Kassenbucheintrag)
        .filter(
            Kassenbucheintrag.immutable == True,
        )
        .order_by(Kassenbucheintrag.datum.asc(), Kassenbucheintrag.id.asc())
        .all()
    )
    # Auf Jahr filtern
    eintraege = [e for e in eintraege if e.datum.year == jahr]

    konto_spalte = f"SKR-Konto ({kontenrahmen})"
    header = [
        "Lfd. Nr.", "Datum", "Belegnummer", "Ext. Belegnummer", "Beschreibung",
        "Art", "Zahlungsart", "Kategorie", konto_spalte,
        "Netto-Betrag (EUR)", "USt-Satz (%)", "USt-Betrag (EUR)", "Brutto-Betrag (EUR)",
        "Vorsteuerabzug", "Steuerbefreiung", "Kunde/Lieferant",
        "Signatur (SHA-256)", "Erstellt am",
    ]
    rows = []
    for lfd, e in enumerate(eintraege, 1):
        kat_name = e.kategorie.name if e.kategorie else ""
        konto = ""
        if e.kategorie:
            if kontenrahmen == "SKR04":
                konto = e.kategorie.konto_skr04 or ""
            elif kontenrahmen == "SKR49":
                konto = e.kategorie.konto_skr49 or ""
            else:
                konto = e.kategorie.konto_skr03 or ""

        kunde_name = ""
        if e.kunde:
            teile = []
            if e.kunde.firmenname:
                teile.append(e.kunde.firmenname)
            if e.kunde.vorname or e.kunde.nachname:
                teile.append(f"{e.kunde.vorname or ''} {e.kunde.nachname or ''}".strip())
            kunde_name = ", ".join(t for t in teile if t)

        rows.append([
            str(lfd),
            _fmt_date(e.datum),
            e.belegnr,
            e.externe_belegnr or "",
            e.beschreibung,
            e.art,
            e.zahlungsart,
            kat_name,
            konto,
            _fmt_decimal(e.netto_betrag),
            _fmt_decimal(e.ust_satz),
            _fmt_decimal(e.ust_betrag),
            _fmt_decimal(e.brutto_betrag),
            _fmt_bool(e.vorsteuerabzug),
            e.steuerbefreiung_grund or "",
            kunde_name,
            e.signatur or "",
            _fmt_datetime(e.erstellt_am),
        ])

    return _make_csv(header, rows), len(rows)


def export_tagesabschluesse_csv(db: Session, jahr: int) -> tuple[bytes, int]:
    """Tagesabschlüsse als CSV. Gibt (bytes, anzahl_datensaetze) zurück."""
    abschluesse = (
        db.query(Tagesabschluss)
        .filter(Tagesabschluss.immutable == True)
        .order_by(Tagesabschluss.datum.asc())
        .all()
    )
    abschluesse = [a for a in abschluesse if a.datum.year == jahr]

    header = [
        "Datum", "Uhrzeit", "Anfangsbestand (EUR)", "Einnahmen Bar (EUR)",
        "Ausgaben Bar (EUR)", "Soll-Endbestand (EUR)", "Ist-Endbestand (EUR)",
        "Differenz (EUR)", "Differenz-Buchungsart", "Differenz-Begründung",
        "Kassenbewegungen Anzahl", "Signatur (SHA-256)", "Erstellt am",
    ]
    rows = []
    for a in abschluesse:
        rows.append([
            _fmt_date(a.datum),
            str(a.uhrzeit)[:8],
            _fmt_decimal(a.anfangsbestand),
            _fmt_decimal(a.einnahmen_bar),
            _fmt_decimal(a.ausgaben_bar),
            _fmt_decimal(a.soll_endbestand),
            _fmt_decimal(a.ist_endbestand),
            _fmt_decimal(a.differenz),
            a.differenz_buchungsart or "",
            a.differenz_begruendung or "",
            str(a.kassenbewegungen_anzahl),
            a.signatur or "",
            _fmt_datetime(a.erstellt_am),
        ])

    return _make_csv(header, rows), len(rows)


def export_kategorien_csv(db: Session) -> tuple[bytes, int]:
    """Kategorie-Stammdaten als CSV."""
    kategorien = (
        db.query(Kategorie)
        .order_by(Kategorie.id.asc())
        .all()
    )
    header = [
        "ID", "Name", "Kontenart", "SKR03-Konto", "SKR04-Konto", "SKR49-Konto",
        "EKS-Kategorie", "EÜR-Zeile", "Vorsteuer (%)", "Standard-USt-Satz (%)",
        "Systemkategorie", "Erstellt am",
    ]
    rows = []
    for k in kategorien:
        rows.append([
            str(k.id),
            k.name,
            k.kontenart,
            k.konto_skr03 or "",
            k.konto_skr04 or "",
            k.konto_skr49 or "",
            k.eks_kategorie or "",
            str(k.euer_zeile) if k.euer_zeile is not None else "",
            _fmt_decimal(k.vorsteuer_prozent),
            str(k.ust_satz_standard),
            _fmt_bool(k.ist_system),
            _fmt_datetime(k.erstellt_am),
        ])

    return _make_csv(header, rows), len(rows)


def export_kunden_csv(db: Session) -> tuple[bytes, int]:
    """Kunden-Stammdaten als CSV."""
    kunden = (
        db.query(Kunde)
        .order_by(Kunde.id.asc())
        .all()
    )
    header = [
        "ID", "Kundennummer", "Firmenname", "Vorname", "Nachname",
        "Straße", "Hausnummer", "PLZ", "Ort", "Land",
        "USt-IdNr.", "E-Mail", "Telefon",
        "Ist Verein", "Ist gemeinnützig",
        "Aktiv", "Erstellt am",
    ]
    rows = []
    for k in kunden:
        rows.append([
            str(k.id),
            k.kundennummer or "",
            k.firmenname or "",
            k.vorname or "",
            k.nachname or "",
            k.strasse or "",
            k.hausnummer or "",
            k.plz or "",
            k.ort or "",
            k.land,
            k.ust_idnr or "",
            k.email or "",
            k.telefon or "",
            _fmt_bool(k.ist_verein),
            _fmt_bool(k.ist_gemeinnuetzig),
            _fmt_bool(k.aktiv),
            _fmt_datetime(k.erstellt_am),
        ])

    return _make_csv(header, rows), len(rows)


def export_lieferanten_csv(db: Session) -> tuple[bytes, int]:
    """Lieferanten-Stammdaten als CSV."""
    lieferanten = (
        db.query(Lieferant)
        .order_by(Lieferant.id.asc())
        .all()
    )
    header = [
        "ID", "Lieferantennummer", "Firmenname", "Vorname", "Nachname",
        "Straße", "Hausnummer", "PLZ", "Ort", "Land",
        "USt-IdNr.", "E-Mail", "Telefon",
        "Aktiv", "Erstellt am",
    ]
    rows = []
    for l in lieferanten:
        rows.append([
            str(l.id),
            l.lieferantennummer or "",
            l.firmenname,
            l.vorname or "",
            l.nachname or "",
            l.strasse or "",
            l.hausnummer or "",
            l.plz or "",
            l.ort or "",
            l.land,
            l.ust_idnr or "",
            l.email or "",
            l.telefon or "",
            _fmt_bool(l.aktiv),
            _fmt_datetime(l.erstellt_am),
        ])

    return _make_csv(header, rows), len(rows)


def export_integritaet_csv(db: Session, jahr: int) -> tuple[bytes, dict]:
    """
    Prüft alle SHA-256-Signaturen und erzeugt Integritäts-CSV.
    Gibt (bytes, stats_dict) zurück.
    stats = {gesamt, gueltig, ungueltig, ohne_signatur}
    """
    eintraege = (
        db.query(Kassenbucheintrag)
        .filter(Kassenbucheintrag.immutable == True)
        .order_by(Kassenbucheintrag.datum.asc(), Kassenbucheintrag.id.asc())
        .all()
    )
    eintraege = [e for e in eintraege if e.datum.year == jahr]

    abschluesse = (
        db.query(Tagesabschluss)
        .filter(Tagesabschluss.immutable == True)
        .order_by(Tagesabschluss.datum.asc())
        .all()
    )
    abschluesse = [a for a in abschluesse if a.datum.year == jahr]

    header = [
        "Datensatz-Typ", "ID", "Datum", "Referenz",
        "Gespeicherte Signatur", "Berechnete Signatur", "Status",
    ]
    rows = []
    gesamt = gueltig = ungueltig = ohne = 0

    for e in eintraege:
        gesamt += 1
        berechnet = signatur_kassenbucheintrag(e)
        if not e.signatur:
            status = "OHNE SIGNATUR"
            ohne += 1
        elif e.signatur == berechnet:
            status = "GÜLTIG"
            gueltig += 1
        else:
            status = "UNGÜLTIG"
            ungueltig += 1
        rows.append([
            "Kassenbucheintrag",
            str(e.id),
            _fmt_date(e.datum),
            e.belegnr,
            e.signatur or "",
            berechnet,
            status,
        ])

    for a in abschluesse:
        gesamt += 1
        berechnet = signatur_tagesabschluss(a)
        if not a.signatur:
            status = "OHNE SIGNATUR"
            ohne += 1
        elif a.signatur == berechnet:
            status = "GÜLTIG"
            gueltig += 1
        else:
            status = "UNGÜLTIG"
            ungueltig += 1
        rows.append([
            "Tagesabschluss",
            str(a.id),
            _fmt_date(a.datum),
            str(a.datum),
            a.signatur or "",
            berechnet,
            status,
        ])

    stats = {
        "gesamt": gesamt,
        "gueltig": gueltig,
        "ungueltig": ungueltig,
        "ohne_signatur": ohne,
    }
    return _make_csv(header, rows), stats


# ---------------------------------------------------------------------------
# Statistiken sammeln
# ---------------------------------------------------------------------------

def _sammle_statistiken(db: Session, jahr: int) -> dict:
    """Sammelt alle Kennzahlen für den PDF-Bericht."""
    from sqlalchemy import extract, func

    # Kassenbuch
    eintraege = (
        db.query(Kassenbucheintrag)
        .filter(
            Kassenbucheintrag.immutable == True,
            extract("year", Kassenbucheintrag.datum) == jahr,
        )
        .all()
    )

    anzahl_buchungen = len(eintraege)
    einnahmen_gesamt = sum(
        Decimal(str(e.brutto_betrag)) for e in eintraege if e.art == "Einnahme"
    )
    ausgaben_gesamt = sum(
        Decimal(str(e.brutto_betrag)) for e in eintraege if e.art == "Ausgabe"
    )
    stornos = sum(1 for e in eintraege if e.beschreibung.startswith("STORNO:"))
    saldo = einnahmen_gesamt - ausgaben_gesamt

    # USt-Aufschlüsselung
    ust_19 = sum(
        Decimal(str(e.ust_betrag))
        for e in eintraege
        if e.art == "Einnahme" and int(float(str(e.ust_satz))) == 19
    )
    ust_7 = sum(
        Decimal(str(e.ust_betrag))
        for e in eintraege
        if e.art == "Einnahme" and int(float(str(e.ust_satz))) == 7
    )
    netto_19 = sum(
        Decimal(str(e.netto_betrag))
        for e in eintraege
        if e.art == "Einnahme" and int(float(str(e.ust_satz))) == 19
    )
    netto_7 = sum(
        Decimal(str(e.netto_betrag))
        for e in eintraege
        if e.art == "Einnahme" and int(float(str(e.ust_satz))) == 7
    )
    steuerfrei = sum(
        Decimal(str(e.brutto_betrag))
        for e in eintraege
        if e.art == "Einnahme" and int(float(str(e.ust_satz))) == 0
    )
    vorsteuer = sum(
        Decimal(str(e.ust_betrag))
        for e in eintraege
        if e.art == "Ausgabe" and e.vorsteuerabzug
    )

    # Tagesabschlüsse
    abschluesse = (
        db.query(Tagesabschluss)
        .filter(
            Tagesabschluss.immutable == True,
            extract("year", Tagesabschluss.datum) == jahr,
        )
        .all()
    )
    anzahl_abschluesse = len(abschluesse)
    abschluesse_mit_differenz = sum(
        1 for a in abschluesse if abs(float(str(a.differenz))) > 0.005
    )
    gesamtdifferenz = sum(Decimal(str(a.differenz)) for a in abschluesse)

    return {
        "jahr": jahr,
        "exportdatum": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
        # Buchungen
        "anzahl_buchungen": anzahl_buchungen,
        "einnahmen_gesamt": einnahmen_gesamt,
        "ausgaben_gesamt": ausgaben_gesamt,
        "stornos": stornos,
        "saldo": saldo,
        # USt
        "ust_19": ust_19,
        "ust_7": ust_7,
        "netto_19": netto_19,
        "netto_7": netto_7,
        "steuerfrei": steuerfrei,
        "vorsteuer": vorsteuer,
        # Tagesabschlüsse
        "anzahl_abschluesse": anzahl_abschluesse,
        "abschluesse_mit_differenz": abschluesse_mit_differenz,
        "gesamtdifferenz": gesamtdifferenz,
    }


# ---------------------------------------------------------------------------
# GDPdU index.xml
# ---------------------------------------------------------------------------

def _generate_index_xml(unternehmen: dict, jahr: int, stats: dict, datei_infos: list[dict]) -> bytes:
    """
    GDPdU-angelehnte Beschreibungsdatei (index.xml).
    Listet alle CSV-Dateien mit ihrer Struktur auf.
    """
    exportdatum = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    firmenname = unternehmen.get("firmenname", "")
    steuernr = unternehmen.get("steuernummer") or unternehmen.get("ust_idnr") or ""

    datei_elemente = ""
    for info in datei_infos:
        datei_elemente += f"""
    <Datei>
      <Name>{info['name']}</Name>
      <Beschreibung>{info['beschreibung']}</Beschreibung>
      <Datensaetze>{info['anzahl']}</Datensaetze>
      <Format>CSV;UTF-8-BOM;Semikolon</Format>
    </Datei>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<GoBD-Export xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <Version>1.0</Version>
  <Exportdatum>{exportdatum}</Exportdatum>
  <Zeitraum>
    <Von>{jahr}-01-01</Von>
    <Bis>{jahr}-12-31</Bis>
  </Zeitraum>
  <Unternehmen>
    <Name>{firmenname}</Name>
    <Steuernummer>{steuernr}</Steuernummer>
  </Unternehmen>
  <Software>
    <Name>RechnungsFee</Name>
    <Version>0.1</Version>
  </Software>
  <Dateien>{datei_elemente}
  </Dateien>
  <Pruefwerte>
    <AnzahlBuchungen>{stats.get('anzahl_buchungen', 0)}</AnzahlBuchungen>
    <AnzahlTagesabschluesse>{stats.get('anzahl_abschluesse', 0)}</AnzahlTagesabschluesse>
  </Pruefwerte>
</GoBD-Export>
"""
    return xml.encode("utf-8")


# ---------------------------------------------------------------------------
# Haupt-Funktion: ZIP zusammenstellen
# ---------------------------------------------------------------------------

def generate_gobd_zip(db: Session, jahr: int) -> bytes:
    """
    Erzeugt das vollständige GoBD-Export-ZIP für das angegebene Jahr.
    Gibt ZIP-Bytes zurück.
    """
    # Unternehmensdaten
    unt = db.query(Unternehmen).first()
    unt_dict: dict = {}
    if unt:
        unt_dict = {
            "firmenname": unt.firmenname,
            "vorname": unt.vorname or "",
            "nachname": unt.nachname or "",
            "strasse": unt.strasse,
            "hausnummer": unt.hausnummer,
            "plz": unt.plz,
            "ort": unt.ort,
            "steuernummer": unt.steuernummer or "",
            "ust_idnr": unt.ust_idnr or "",
            "finanzamt": unt.finanzamt or "",
            "ist_kleinunternehmer": unt.ist_kleinunternehmer,
            "kontenrahmen": unt.kontenrahmen,
        }
    kontenrahmen = unt_dict.get("kontenrahmen", "SKR03")

    # CSVs erzeugen
    kb_csv, kb_anzahl = export_kassenbuch_csv(db, jahr, kontenrahmen)
    ta_csv, ta_anzahl = export_tagesabschluesse_csv(db, jahr)
    kat_csv, kat_anzahl = export_kategorien_csv(db)
    kd_csv, kd_anzahl = export_kunden_csv(db)
    lf_csv, lf_anzahl = export_lieferanten_csv(db)
    integ_csv, integ_stats = export_integritaet_csv(db, jahr)

    # Statistiken
    stats = _sammle_statistiken(db, jahr)
    stats["integritaet"] = integ_stats

    datei_infos = [
        {"name": "kassenbuch_journal.csv",   "beschreibung": "Kassenbuch-Journal (alle immutable Einträge)", "anzahl": kb_anzahl},
        {"name": "tagesabschluesse.csv",     "beschreibung": "Tagesabschlüsse",                              "anzahl": ta_anzahl},
        {"name": "kategorien.csv",           "beschreibung": "Kategorie-Stammdaten",                         "anzahl": kat_anzahl},
        {"name": "kunden.csv",               "beschreibung": "Kunden-Stammdaten",                            "anzahl": kd_anzahl},
        {"name": "lieferanten.csv",          "beschreibung": "Lieferanten-Stammdaten",                       "anzahl": lf_anzahl},
        {"name": "integritaetspruefung.csv", "beschreibung": "SHA-256-Signaturprüfung aller Datensätze",     "anzahl": integ_stats["gesamt"]},
    ]

    index_xml = _generate_index_xml(unt_dict, jahr, stats, datei_infos)

    # PDF
    from utils.pdf_gobd_bericht import generate_gobd_bericht_pdf
    pdf_bytes = generate_gobd_bericht_pdf(unt_dict, jahr, stats, datei_infos)

    # ZIP zusammenstellen
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.xml",                  index_xml)
        zf.writestr("kassenbuch_journal.csv",     kb_csv)
        zf.writestr("tagesabschluesse.csv",       ta_csv)
        zf.writestr("kategorien.csv",             kat_csv)
        zf.writestr("kunden.csv",                 kd_csv)
        zf.writestr("lieferanten.csv",            lf_csv)
        zf.writestr("integritaetspruefung.csv",   integ_csv)
        zf.writestr("gobd_pruefbericht.pdf",      pdf_bytes)

    return zip_buffer.getvalue()
