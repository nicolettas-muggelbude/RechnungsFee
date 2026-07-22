"""
DATEV EXTF Buchungsstapel Export.
Format: Version 700 / Buchungsstapel v9
Modus: EÜR/Zuflussprinzip (eine Zeile pro Journaleintrag)

Sonderfälle:
  ust_sonderfall=ig_erwerb     → BU 19 (19 %) oder 18 (7 %)
  ust_sonderfall=13b_abs2      → BU 94 (19 %) oder 91 (7 %); 13b_abs1 → BU 94
  marge_25a_brutto != NULL     → kein BU-Schlüssel (Automatikkonto 8199/4134), Umsatz = Marge (§25a)
  zahlungsart='Keine'          → übersprungen (kein Gegenkonto)
  fehlendes Sachkonto          → wird exportiert (leer) → DATEV-Importfehler gewollt
  Stornobuchung (STORNO-Prefix) → BU-Schlüssel des Originals (art invertiert, vorsteuerabzug erhalten)
"""

import io
import os
import re
import zipfile
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database.connection import APP_DATA_DIR, get_db
from database.models import Beleg, Journaleintrag, Kategorie, Konto, Kunde, Lieferant, Rechnung, Unternehmen

router = APIRouter(prefix="/api/datev", tags=["DATEV"])

# Buchungsstapel v9 – alle 49 Spaltennamen (Zeile 2 des EXTF)
_COLS = [
    "Umsatz (ohne Soll/Haben-Kz)",
    "Soll/Haben-Kennzeichen",
    "WKZ Umsatz",
    "Kurs",
    "Basisumsatz",
    "WKZ Basisumsatz",
    "Konto",
    "Gegenkonto (ohne BU-Schlüssel)",
    "BU-Schlüssel",
    "Belegdatum",
    "Belegfeld 1",
    "Belegfeld 2",
    "Skonto",
    "Buchungstext",
    "Postensperre",
    "Diverse Adressnummer",
    "Geschäftspartnerbank",
    "Sachverhalt",
    "Zinssperre",
    "Beleglink",
    "Beleginfo - Art 1",
    "Beleginfo - Inhalt 1",
    "Beleginfo - Art 2",
    "Beleginfo - Inhalt 2",
    "Beleginfo - Art 3",
    "Beleginfo - Inhalt 3",
    "Beleginfo - Art 4",
    "Beleginfo - Inhalt 4",
    "Beleginfo - Art 5",
    "Beleginfo - Inhalt 5",
    "Beleginfo - Art 6",
    "Beleginfo - Inhalt 6",
    "Beleginfo - Art 7",
    "Beleginfo - Inhalt 7",
    "Beleginfo - Art 8",
    "Beleginfo - Inhalt 8",
    "KOST1 - Kostenstelle",
    "KOST2 - Kostenstelle",
    "Kost-Menge",
    "EU-Mitgliedsstaat u. UStIdNr.",
    "EU-Steuersatz",
    "Abw. Versteuerungsart",
    "L+L-Identifikation",
    "Buchungslink",
    "Bestellnummer",
    "Belegdatum 2",
    "Relevant§13b UStG",
    "Kreditoren-/Debitorennummer",
    "Technische Identifikation",
]

# Standard-Gegenkonten wenn datev_konto_* nicht konfiguriert
_DEFAULTS: dict[str, dict[str, str]] = {
    "SKR03": {"Bar": "1000", "Bank": "1200", "Karte": "1200", "PayPal": "1361"},
    "SKR04": {"Bar": "1000", "Bank": "1800", "Karte": "1800", "PayPal": "1460"},
    "SKR49": {"Bar": "1000", "Bank": "1800", "Karte": "1800", "PayPal": "1460"},
}

# DATEV-Automatikkonten (Zusatzfunktion AM): kennen ihren Steuersatz eingebaut.
# BU-Schlüssel wäre doppelt → REW00306. Alle anderen Erlöskonten brauchen BU 3/2.
# SKR03 8920–8925: Eigenverbrauch-AM-Konten (Kfz, Licht/Wasser, Waren, Telefon …)
_AM_KONTEN: dict[str, set[str]] = {
    "SKR03": {
        "8100", "8300", "8301", "8400", "8401", "8736", "8850", "8851", "8852",
        "8920", "8921", "8922", "8923", "8924", "8925",
        "8199",  # §25a Differenzbesteuerung (Issue #303)
    },
    "SKR04": {"4100", "4300", "4301", "4400", "4401", "4736", "4134"},
}


def _fmt(betrag: Decimal) -> str:
    """Betrag im deutschen Format: '1234,56' (Komma, kein Tausender)."""
    return str(abs(betrag).quantize(Decimal("0.01"))).replace(".", ",")


def _bu(j: Journaleintrag, skr: str, konto: Optional[str], db: Optional[Session] = None) -> str:
    sf = j.ust_sonderfall
    if sf == "ig_erwerb":
        # Innergemeinschaftlicher Erwerb §1a UStG (Issue #302)
        return "19" if int(j.ust_satz or 0) >= 19 else "18"
    if sf == "13b_abs2":
        # Bauleistungen §13b Abs. 2 Nr. 4 UStG (Issue #302)
        return "94" if int(j.ust_satz or 0) >= 19 else "91"
    if sf == "13b_abs1":
        return "94"
    if j.marge_25a_brutto is not None:
        # §25a Differenzbesteuerung hat keinen zweistelligen BU-Schlüssel - DATEV erkennt
        # das am Sachkonto (Automatikkonto 8199 SKR03 / 4134 SKR04, siehe Issue #303).
        return ""
    satz = int(j.ust_satz or 0)
    # Stornobuchungen haben art=Gegenteil des Originals (art invertiert).
    # BU-Schlüssel richtet sich nach dem Original → art für BU-Berechnung zurückdrehen.
    is_storno = j.beschreibung.startswith("STORNO ")
    art = ("Ausgabe" if j.art == "Einnahme" else "Einnahme") if is_storno else j.art
    # vorsteuerabzug für BU-Berechnung bestimmen.
    # Alte Stornos (vor v0.3.24) wurden mit vorsteuerabzug=False erstellt; in diesem Fall
    # Original-Buchung per Belegnummer nachschlagen und dessen vorsteuerabzug übernehmen.
    vorsteuerabzug = j.vorsteuerabzug
    if is_storno and not vorsteuerabzug and art == "Ausgabe" and satz > 0 and db:
        m = re.match(r"^STORNO ([^:]+):", j.beschreibung)
        if m:
            orig = db.query(Journaleintrag).filter(Journaleintrag.belegnr == m.group(1)).first()
            if orig:
                vorsteuerabzug = orig.vorsteuerabzug
    if art == "Einnahme":
        if konto in _AM_KONTEN.get(skr, set()):
            # Automatikkonto (AM): Steuersatz eingebaut – BU wäre REW00306
            return ""
        # Kein AM-Konto (z. B. 8910 Eigenverbrauch, 8900 Wertabgaben):
        # USt muss explizit per BU-Schlüssel gesetzt werden (BU 3 = 19 %, BU 2 = 7 %).
        if satz == 19:
            return "3"
        if satz == 7:
            return "2"
    else:
        # Aufwandskonten: Vorsteuer-Schlüssel (BU 9 = 19 %, BU 8 = 7 %)
        if vorsteuerabzug and satz == 19:
            return "9"
        if vorsteuerabzug and satz == 7:
            return "8"
    return ""


def _gegenkonto(j: Journaleintrag, unt: Unternehmen, db: Optional[Session] = None) -> Optional[str]:
    za = j.zahlungsart
    if za == "Keine":
        return None
    if za == "Skonto":
        za = "Bank"

    # Bankkonto mit eigener DATEV-Kontonummer hat Vorrang vor globalem datev_konto_bank
    if za == "Bank" and j.konto_id and db is not None:
        konto = db.query(Konto).filter(Konto.id == j.konto_id).first()
        if konto and konto.datev_kontonummer:
            return konto.datev_kontonummer

    konfig = {
        "Bar":    unt.datev_konto_bar,
        "Bank":   unt.datev_konto_bank,
        "Karte":  unt.datev_konto_karte,
        "PayPal": unt.datev_konto_paypal,
    }
    d = _DEFAULTS.get(unt.kontenrahmen, _DEFAULTS["SKR04"])
    return konfig.get(za) or d.get(za)


def _sachkonto(j: Journaleintrag, skr: str, db: Optional[Session] = None) -> Optional[str]:
    # 1. Snapshot auf dem Journaleintrag
    konto = (j.konto_skr03 if skr == "SKR03" else j.konto_skr04) or None
    if konto:
        return konto
    # 2. Aktuelles Konto aus der verknüpften Kategorie (ältere Einträge ohne Snapshot)
    if j.kategorie:
        k = (j.kategorie.konto_skr03 if skr == "SKR03" else j.kategorie.konto_skr04) or None
        if k:
            return k
    # 3. Fallback für RE-Zahlungen mit fehlender Kategorie-Kontonummer:
    #    Erlöskonto aus den Positionen der verknüpften Rechnung ermitteln.
    #    Betrifft Einträge deren Erlös-Kategorie kein SKR-Konto eingetragen hat
    #    (z. B. selbst angelegte „Erlöse 19%"-Kategorie ohne DATEV-Zuordnung).
    if db and j.rechnung_id and j.art == "Einnahme":
        re = db.query(Rechnung).filter(Rechnung.id == j.rechnung_id).first()
        if re and re.typ == "ausgang" and re.positionen:
            satz_summen: dict[int, Decimal] = {}
            for pos in re.positionen:
                satz = int(pos.ust_satz or 0)
                satz_summen[satz] = satz_summen.get(satz, Decimal("0")) + (pos.netto or Decimal("0"))
            dom_satz = max(satz_summen, key=lambda s: satz_summen[s]) if satz_summen else 19
            namen = {19: "Betriebseinnahmen", 7: "Betriebseinnahmen (7%)", 0: "Betriebseinnahmen (0%)"}
            kat = db.query(Kategorie).filter(
                Kategorie.name == namen.get(dom_satz, "Betriebseinnahmen"),
                Kategorie.aktiv == True,  # noqa: E712
            ).first()
            if kat:
                k = (kat.konto_skr03 if skr == "SKR03" else kat.konto_skr04) or None
                if k:
                    return k
    return None


def _zeile1(unt: Unternehmen, von: date, bis: date) -> str:
    """EXTF-Verwaltungssatz (Zeile 1) – 31 Felder gemäß DATEV EXTF-Spezifikation v700."""
    ts = datetime.now()
    jetzt = ts.strftime("%Y%m%d%H%M%S") + f"{ts.microsecond // 1000:03d}"  # 17 Stellen
    wj_start = date(von.year, unt.geschaeftsjahr_beginn, 1)
    teile = [
        '"EXTF"',                               # 1:  Kennzeichen
        "700",                                  # 2:  Versionsnummer
        "21",                                   # 3:  Datenkategorie (21 = Buchungsstapel)
        '"Buchungsstapel"',                     # 4:  Formatname
        "9",                                    # 5:  Formatversion
        jetzt,                                  # 6:  Erzeugt am (17 Stellen YYYYMMDDHHmmssSSS)
        "",                                     # 7:  Importiert am (leer, wird von DATEV gefüllt)
        '"RE"',                                 # 8:  Herkunft (2 Zeichen)
        "",                                     # 9:  Exportiert von
        "",                                     # 10: Importiert von (leer beim Export)
        unt.datev_beraternummer or "1001",      # 11: Beraternummer
        unt.datev_mandantennummer or "1",       # 12: Mandantennummer
        wj_start.strftime("%Y%m%d"),            # 13: WJ-Beginn (YYYYMMDD)
        "4",                                    # 14: Sachkontonummernlänge
        von.strftime("%Y%m%d"),                 # 15: Datum von
        bis.strftime("%Y%m%d"),                 # 16: Datum bis
        "",                                     # 17: Bezeichnung (max 30 Zeichen)
        "",                                     # 18: Diktat-Kürzel (max 2 Zeichen)
        "1",                                    # 19: Buchungstyp (1 = Finanzbuchhaltung)
        "",                                     # 20: Rechnungslegungszweck (leer)
        "0",                                    # 21: Festschreibung (0 = nicht festschreiben)
        '"EUR"',                                # 22: WKZ (ISO 4217)
        "",                                     # 23: Reserviert
        "",                                     # 24: Derivatskennzeichen
        "",                                     # 25: Reserviert
        "",                                     # 26: Reserviert
        "",                                     # 27: SKR (optional)
        "",                                     # 28: Branchenlösungs-ID
        "",                                     # 29: Reserviert
        "",                                     # 30: Reserviert
        "",                                     # 31: Anwendungsinformation
    ]
    return ";".join(teile)


@router.get("/buchungsstapel")
def datev_buchungsstapel(
    von: date = Query(..., description="Startdatum YYYY-MM-DD"),
    bis: date = Query(..., description="Enddatum YYYY-MM-DD"),
    mit_belegen: bool = Query(True, description="Belege als ZIP mitexportieren (Belege/-Ordner, benannt nach Belegnummer)"),
    db: Session = Depends(get_db),
):
    """DATEV EXTF Buchungsstapel für den angegebenen Zeitraum als CSV (mit_belegen=false)
    oder als ZIP mit CSV + zugehörigen Belegen im Belege/-Ordner (Standard)."""
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(status_code=404, detail="Keine Unternehmensdaten")

    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .order_by(Journaleintrag.datum, Journaleintrag.id)
        .all()
    )

    # Lookup-Maps für Spalte 48: Kreditoren-/Debitorennummer
    kunde_ids = {j.kunde_id for j in eintraege if j.kunde_id}
    rechnung_ids_set = {j.rechnung_id for j in eintraege if j.rechnung_id}
    debitor_map: dict[int, str] = {
        k.id: k.debitor_nr
        for k in db.query(Kunde).filter(Kunde.id.in_(kunde_ids)).all()
        if k.debitor_nr
    }
    rechnung_lieferant: dict[int, int] = {
        r.id: r.lieferant_id
        for r in db.query(Rechnung).filter(Rechnung.id.in_(rechnung_ids_set)).all()
        if r.lieferant_id
    }
    lieferant_ids = set(rechnung_lieferant.values())
    kreditor_map: dict[int, str] = {
        lf.id: lf.kreditor_nr
        for lf in db.query(Lieferant).filter(Lieferant.id.in_(lieferant_ids)).all()
        if lf.kreditor_nr
    }

    # Belege je Journaleintrag einmalig ermitteln (journal.beleg_id oder ueber die
    # verknuepfte Rechnung rechnung.beleg_id) - dieselbe Zuordnung wird sowohl fuer
    # die Beleglink-Spalte (20) der CSV als auch fuer die Datei im ZIP verwendet,
    # damit beide immer exakt uebereinstimmen.
    beleg_info: dict[int, tuple[Beleg, str]] = {}
    if mit_belegen:
        for j in eintraege:
            beleg_id = j.beleg_id
            if not beleg_id and j.rechnung_id:
                rechnung_obj = db.query(Rechnung).filter(Rechnung.id == j.rechnung_id).first()
                if rechnung_obj and rechnung_obj.beleg_id:
                    beleg_id = rechnung_obj.beleg_id
            if not beleg_id:
                continue
            beleg = db.query(Beleg).filter(Beleg.id == beleg_id).first()
            if not beleg:
                continue
            # Dateiname = Belegnummer (Belegfeld 1) - muss nicht sein (DATEV verknuepft
            # ueber den Beleglink-Wert, nicht den Dateinamen), ist aber fuer Menschen
            # nachvollziehbar und eindeutig innerhalb dieses Exports.
            if beleg.beleg_pdfa_pfad:
                dateiname = f"{j.belegnr}.pdf"
            else:
                extension = os.path.splitext(beleg.original_name)[1] or ".pdf"
                dateiname = f"{j.belegnr}{extension}"
            beleg_info[j.id] = (beleg, dateiname)

    skr = unt.kontenrahmen
    zeilen: list[str] = [_zeile1(unt, von, bis), ";".join(_COLS)]
    uebersprungen = 0
    leer_konto = 0

    for j in eintraege:
        konto = _sachkonto(j, skr, db)
        gegenkonto = _gegenkonto(j, unt, db)

        if not gegenkonto:
            # zahlungsart='Keine' → kein Zahlungskonto, Buchung nicht exportierbar
            uebersprungen += 1
            continue
        if not konto:
            # Kein Sachkonto ermittelbar → leeres Konto exportieren.
            # DATEV gibt einen Importfehler, der Steuerberater kann die Buchung sehen und korrigieren.
            konto = ""
            leer_konto += 1

        betrag = j.marge_25a_brutto if j.marge_25a_brutto is not None else j.netto_betrag
        sh = "H" if j.art == "Einnahme" else "S"
        belegfeld1 = (j.externe_belegnr or j.belegnr)[:12]
        buchungstext = j.beschreibung[:60]

        # Spalte 48: Kreditoren-/Debitorennummer
        personenkonto = ""
        if j.art == "Einnahme" and j.kunde_id:
            personenkonto = debitor_map.get(j.kunde_id, "")
        elif j.art == "Ausgabe" and j.rechnung_id:
            lf_id = rechnung_lieferant.get(j.rechnung_id)
            if lf_id:
                personenkonto = kreditor_map.get(lf_id, "")

        leere_felder = [""] * 35    # Felder 15–49
        if j.id in beleg_info:
            leere_felder[5] = beleg_info[j.id][1]     # Feld 20: Beleglink (Index 20-15=5)
        leere_felder[33] = personenkonto              # Feld 48 (Index 47-14=33)

        row = [
            _fmt(betrag),       # 1: Umsatz
            sh,                  # 2: S/H
            "EUR",               # 3: WKZ
            "", "", "",          # 4-6: leer
            konto,               # 7: Konto
            gegenkonto,          # 8: Gegenkonto
            _bu(j, skr, konto, db),  # 9: BU-Schlüssel
            j.datum.strftime("%d%m"),  # 10: Belegdatum DDMM
            belegfeld1,          # 11: Belegfeld 1
            "",                  # 12: Belegfeld 2
            "",                  # 13: Skonto
            buchungstext,        # 14: Buchungstext
        ] + leere_felder        # 15-49

        zeilen.append(";".join(row))

    inhalt = "\r\n".join(zeilen)
    bom = b"\xef\xbb\xbf"
    data = bom + inhalt.encode("utf-8")

    zeitraum_suffix = f"{von.strftime('%Y%m%d')}_{bis.strftime('%Y%m%d')}"
    zaehl_headers = {
        "X-Datev-Eintraege": str(len(eintraege) - uebersprungen),
        "X-Datev-Uebersprungen": str(uebersprungen),
        "X-Datev-LeerKonto": str(leer_konto),
    }

    if not mit_belegen:
        headers = {"Content-Disposition": 'attachment; filename="EXTF_Buchungsstapel.csv"', **zaehl_headers}
        return StreamingResponse(iter([data]), media_type="text/csv; charset=utf-8", headers=headers)

    # ZIP schreiben: CSV + Belege-Dateien, exakt dieselbe Zuordnung wie in beleg_info
    # (Spalte 20 der CSV) - Dateiname und Beleglink stimmen dadurch garantiert ueberein.
    belege_gefunden = 0
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("EXTF_Buchungsstapel.csv", data)

        geschrieben: set[str] = set()
        for beleg, dateiname in beleg_info.values():
            if dateiname in geschrieben:
                continue

            if beleg.beleg_pdfa_pfad:
                pdfa_pfad = APP_DATA_DIR / "uploads" / beleg.beleg_pdfa_pfad
                if pdfa_pfad.exists():
                    zf.write(str(pdfa_pfad), f"Belege/{dateiname}")
                    geschrieben.add(dateiname)
                    belege_gefunden += 1
                    continue

            orig_pfad = APP_DATA_DIR / "uploads" / beleg.dateiname
            if orig_pfad.exists():
                zf.write(str(orig_pfad), f"Belege/{dateiname}")
                geschrieben.add(dateiname)
                belege_gefunden += 1

    dateiname = f"DATEV_Buchungsstapel_{zeitraum_suffix}.zip"
    headers = {
        "Content-Disposition": f'attachment; filename="{dateiname}"',
        "X-Datev-Belege": str(belege_gefunden),
        **zaehl_headers,
    }
    return StreamingResponse(iter([zip_buffer.getvalue()]), media_type="application/zip", headers=headers)
