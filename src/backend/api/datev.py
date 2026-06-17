"""
DATEV EXTF Buchungsstapel Export.
Format: Version 700 / Buchungsstapel v9
Modus: EÜR/Zuflussprinzip (eine Zeile pro Journaleintrag)

Sonderfälle:
  ust_sonderfall=ig_erwerb     → BU 89 (19 %) oder 93 (7 %)
  ust_sonderfall=13b_abs1/abs2 → BU 94
  marge_25a_brutto != NULL     → BU 57, Umsatz = Marge (§25a)
  zahlungsart='Keine'          → übersprungen (kein Gegenkonto)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import Journaleintrag, Kategorie, Rechnung, Unternehmen

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
    },
    "SKR04": {"4100", "4300", "4301", "4400", "4401", "4736"},
}


def _fmt(betrag: Decimal) -> str:
    """Betrag im deutschen Format: '1234,56' (Komma, kein Tausender)."""
    return str(abs(betrag).quantize(Decimal("0.01"))).replace(".", ",")


def _bu(j: Journaleintrag, skr: str, konto: Optional[str]) -> str:
    sf = j.ust_sonderfall
    if sf == "ig_erwerb":
        return "89" if int(j.ust_satz or 0) >= 19 else "93"
    if sf in ("13b_abs1", "13b_abs2"):
        return "94"
    if j.marge_25a_brutto is not None:
        return "57"
    satz = int(j.ust_satz or 0)
    if j.art == "Einnahme":
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
        if j.vorsteuerabzug and satz == 19:
            return "9"
        if j.vorsteuerabzug and satz == 7:
            return "8"
    return ""


def _gegenkonto(j: Journaleintrag, unt: Unternehmen) -> Optional[str]:
    konfig = {
        "Bar":    unt.datev_konto_bar,
        "Bank":   unt.datev_konto_bank,
        "Karte":  unt.datev_konto_karte,
        "PayPal": unt.datev_konto_paypal,
    }
    za = j.zahlungsart
    if za == "Keine":
        return None
    # Skonto hat keinen eigenen Kassenkontext → Bank als Gegenkonto
    if za == "Skonto":
        za = "Bank"
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
    db: Session = Depends(get_db),
):
    """DATEV EXTF Buchungsstapel für den angegebenen Zeitraum als CSV."""
    unt = db.query(Unternehmen).first()
    if not unt:
        raise HTTPException(status_code=404, detail="Keine Unternehmensdaten")

    eintraege = (
        db.query(Journaleintrag)
        .filter(Journaleintrag.datum >= von, Journaleintrag.datum <= bis)
        .order_by(Journaleintrag.datum, Journaleintrag.id)
        .all()
    )

    skr = unt.kontenrahmen
    zeilen: list[str] = [_zeile1(unt, von, bis)]
    uebersprungen = 0

    for j in eintraege:
        konto = _sachkonto(j, skr, db)
        gegenkonto = _gegenkonto(j, unt)

        if not konto or not gegenkonto:
            uebersprungen += 1
            continue

        betrag = j.marge_25a_brutto if j.marge_25a_brutto is not None else j.netto_betrag
        sh = "H" if j.art == "Einnahme" else "S"
        belegfeld1 = (j.externe_belegnr or j.belegnr)[:12]
        buchungstext = j.beschreibung[:60]

        row = [
            _fmt(betrag),       # 1: Umsatz
            sh,                  # 2: S/H
            "EUR",               # 3: WKZ
            "", "", "",          # 4-6: leer
            konto,               # 7: Konto
            gegenkonto,          # 8: Gegenkonto
            _bu(j, skr, konto),  # 9: BU-Schlüssel
            j.datum.strftime("%d%m"),  # 10: Belegdatum DDMM
            belegfeld1,          # 11: Belegfeld 1
            "",                  # 12: Belegfeld 2
            "",                  # 13: Skonto
            buchungstext,        # 14: Buchungstext
        ] + [""] * 35           # 15-49: leer

        zeilen.append(";".join(row))

    inhalt = "\r\n".join(zeilen)
    bom = b"\xef\xbb\xbf"
    data = bom + inhalt.encode("utf-8")

    dateiname = f"DATEV_Buchungsstapel_{von.strftime('%Y%m%d')}_{bis.strftime('%Y%m%d')}.csv"
    headers = {
        "Content-Disposition": f'attachment; filename="{dateiname}"',
        "X-Datev-Eintraege": str(len(eintraege) - uebersprungen),
        "X-Datev-Uebersprungen": str(uebersprungen),
    }
    return StreamingResponse(iter([data]), media_type="text/csv; charset=utf-8", headers=headers)
