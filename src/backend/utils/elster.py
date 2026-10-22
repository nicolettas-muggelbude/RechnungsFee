r"""ELSTER-Export-Utilities (Stufe 1: Datei-Upload in Mein ELSTER, kein ERiC).

Enthält:
- steuernummer_elster13(): Umrechnung der Landes-Steuernummer ins 13-stellige
  Bundesschema (BUFA-Nr. + "0" + Bezirk + Unterscheidungsnr. + Prüfziffer,
  Schema \d{4}0\d{8} lt. ELSTER-XSD allg_StNrSType).

Quellen: ELSTER-Hilfe themaGlobal=ustva_upload / zmdo_import_eop,
Bundesland-Umrechnungstabelle de.wikipedia.org/wiki/Steuernummer,
Jahresdokumentation UStVA 2026 (ERiC 43.4, Feldliste + Plausi-Regeln),
XSD 2013 (stesie/geierlein).
"""

import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from xml.sax.saxutils import escape

# BUFA-Präfix je Bundesland (erste 4 Stellen = Landespräfix + Finanzamtsnummer).
# Länder mit "prepend": im Landesformat steht der Finanzamtsnummer eine
# Ziffer voran (z. B. HE "0FF/…", TH "151/…"), die vor dem Präfix entfällt;
# beide Schreibweisen werden akzeptiert.
_LAND_TABELLE: dict[str, tuple[str, bool]] = {
    "BW": ("28", False),
    "BY": ("9", False),
    "BE": ("11", False),
    "BB": ("30", True),
    "HB": ("24", False),
    "HH": ("22", False),
    "HE": ("26", True),
    "MV": ("40", True),
    "NI": ("23", False),
    "NW": ("5", False),
    "RP": ("27", False),
    "SL": ("10", True),
    "SN": ("32", True),
    "ST": ("31", True),
    "SH": ("21", False),
    "TH": ("41", True),
}

_TRENNER = re.compile(r"[\s/\-.]+")
_STNR_13 = re.compile(r"\d{4}0\d{8}")


class ElsterExportFehler(ValueError):
    """Export kann nicht erzeugt werden (für 422-Antworten)."""


def steuernummer_elster13(steuernummer: str | None, bundesland: str | None) -> str:
    r"""Rechnet die Landes-Steuernummer in das 13-stellige ELSTER-Format um.

    Akzeptiert die Schreibweisen der Länder ("93/815/08152", "181-815-08155",
    "133/8150/8159") sowie bereits konvertierte 13-stellige Nummern
    (durchgereicht, wenn sie dem Schema \d{4}0\d{8} entsprechen).
    """
    if not bundesland or not bundesland.strip():
        raise ElsterExportFehler(
            "Bundesland fehlt – bitte in den Stammdaten hinterlegen."
        )
    land = bundesland.strip().upper()
    if land not in _LAND_TABELLE:
        raise ElsterExportFehler(f"Unbekanntes Bundesland: {bundesland!r}")

    if not steuernummer or not steuernummer.strip():
        raise ElsterExportFehler(
            "Steuernummer fehlt – bitte in den Stammdaten hinterlegen."
        )
    roh = steuernummer.strip()
    if re.match(r"^[A-Za-z]{2}", roh):
        raise ElsterExportFehler(
            "Das sieht nach einer USt-IdNr aus – ELSTER braucht die lokale "
            "Steuernummer vom Finanzamt, nicht die USt-IdNr."
        )
    ziffern = _TRENNER.sub("", roh)
    if not ziffern.isdigit():
        raise ElsterExportFehler(
            f"Steuernummer {roh!r} enthält ungültige Zeichen – erlaubt sind "
            "Ziffern sowie '/', '-', '.' und Leerzeichen."
        )

    # Bereits konvertiert (13-stellig, "0" an 5. Stelle) → durchreichen
    if len(ziffern) == 13:
        if _STNR_13.fullmatch(ziffern):
            return ziffern
        raise ElsterExportFehler(
            "13-stellige Steuernummer ohne '0' an 5. Stelle – das ist kein "
            "gültiges ELSTER-Bundesschema."
        )

    praefix, prepend = _LAND_TABELLE[land]
    erwartet = 12 - len(praefix)  # 10 Ziffern bei 2-stelligem, 11 bei 1-stelligem Präfix
    if prepend and len(ziffern) == erwartet + 1:
        ziffern = ziffern[1:]
    if len(ziffern) != erwartet:
        raise ElsterExportFehler(
            f"Steuernummer {roh!r} hat für {land} die falsche Länge – "
            f"erwartet werden {erwartet} Ziffern im Landesformat."
        )

    kombiniert = praefix + ziffern
    ergebnis = kombiniert[:4] + "0" + kombiniert[4:]
    if not _STNR_13.fullmatch(ergebnis):
        raise ElsterExportFehler(
            f"Umrechnung von {roh!r} ({land}) ergab kein gültiges "
            "ELSTER-Bundesschema."
        )
    return ergebnis


# ---------------------------------------------------------------------------
# UStVA-XML (Nutzdaten für den Upload in Mein ELSTER)
# ---------------------------------------------------------------------------

# ELSTER-Typ GeldBetragOhneCent (Bemessungsgrundlagen, volle Euro nach §123 AO);
# alle übrigen Kennzahlen sind GeldBetragMitCent.
KZ_BEMESSUNGSGRUNDLAGE = frozenset({"21", "41", "43", "45", "46", "81", "84", "86", "87", "89", "90", "93", "95"})

# Kz09 ist laut XSD Pflicht, wird beim Mein-ELSTER-Upload aber ausdrücklich
# ignoriert (offizielle Hilfe, Ausschlussliste). RechnungsFee hat keine
# ERiC-Hersteller-ID → neutraler 5-stelliger Platzhalter.
_KZ09_PLATZHALTER = "00000"

_USTVA_NS = "http://finkonsens.de/elster/elsteranmeldung/ustva/v{jahr}"


def _e(text: object | None, max_len: int) -> str:
    """Auf XSD-maxLength kürzen und XML-escapen (Kürzen vor Escapen!)."""
    return escape(str(text or "").strip()[:max_len])


def _format_kz(nr: str, wert: Decimal) -> str:
    # "+ 0" normalisiert -0 – das ELSTER-Muster verbietet ein Minus ohne Ziffer ≠ 0
    stellen = Decimal("1") if nr in KZ_BEMESSUNGSGRUNDLAGE else Decimal("0.01")
    return str(wert.quantize(stellen, ROUND_HALF_UP) + 0)


def build_ustva_xml(
    *,
    zeitraum: str,
    steuernummer13: str,
    unternehmen,
    kz_werte: dict[str, Decimal],
) -> bytes:
    """Baut die UStVA-Nutzdaten-XML für den Upload in Mein ELSTER (kein ERiC).

    zeitraum: "YYYY-MM" (Monat) oder "YYYY-QN" (Quartal).
    kz_werte: ELSTER-Kennziffer → Betrag; die Rundung nach ELSTER-Typ
        (Bemessungsgrundlagen volle Euro, Steuerbeträge centgenau) übernimmt
        der Builder – ungerundete Werte dürfen übergeben werden.
        Kz83 (verbleibende Steuer) ist Pflicht und wird ggf. mit 0.00 gesetzt.
    """
    if not _STNR_13.fullmatch(steuernummer13 or ""):
        raise ElsterExportFehler(
            f"Steuernummer nicht im 13-stelligen ELSTER-Format: {steuernummer13!r}"
        )

    if "-Q" in zeitraum:
        jahr_s, q = zeitraum.split("-Q")
        zr = f"4{int(q)}"
    else:
        jahr_s, monat = zeitraum.split("-")
        zr = f"{int(monat):02d}"
    jahr = int(jahr_s)

    name = unternehmen.firmenname or " ".join(
        p for p in (unternehmen.vorname, unternehmen.nachname) if p
    )
    strasse_komplett = " ".join(
        p for p in (unternehmen.strasse, unternehmen.hausnummer) if p
    ).strip()

    # DatenLieferant Name/Strasse/PLZ/Ort sind Pflichtfelder (XSD minLength=1)
    fehlend = [
        bezeichnung
        for bezeichnung, wert in (
            ("Name", name), ("Straße", unternehmen.strasse),
            ("PLZ", unternehmen.plz), ("Ort", unternehmen.ort),
        )
        if not (wert or "").strip()
    ]
    if fehlend:
        raise ElsterExportFehler(
            "Für den ELSTER-Export fehlen Angaben in den Stammdaten: "
            + ", ".join(fehlend) + " – bitte ergänzen."
        )

    kz_werte = dict(kz_werte)
    kz_werte.setdefault("83", Decimal("0.00"))
    kz_teile = [f"      <Kz09>{_KZ09_PLATZHALTER}</Kz09>"]
    for nr in sorted(kz_werte):
        wert = kz_werte[nr]
        if nr != "83" and wert == 0:
            continue  # 0-Kennziffern werden nicht übertragen
        kz_teile.append(f"      <Kz{nr}>{_format_kz(nr, wert)}</Kz{nr}>")

    zeilen = [
        '<?xml version="1.0" encoding="ISO-8859-15" standalone="no"?>',
        f'<Anmeldungssteuern xmlns="{_USTVA_NS.format(jahr=jahr)}" version="{jahr}">',
        f"  <Erstellungsdatum>{date.today():%Y%m%d}</Erstellungsdatum>",
        "  <DatenLieferant>",
        f"    <Name>{_e(name, 45)}</Name>",
        f"    <Strasse>{_e(strasse_komplett, 30)}</Strasse>",
        f"    <PLZ>{_e(unternehmen.plz, 12)}</PLZ>",
        f"    <Ort>{_e(unternehmen.ort, 30)}</Ort>",
    ]
    if unternehmen.telefon:
        zeilen.append(f"    <Telefon>{_e(unternehmen.telefon, 20)}</Telefon>")
    if unternehmen.email:
        zeilen.append(f"    <Email>{_e(unternehmen.email, 70)}</Email>")
    zeilen += [
        "  </DatenLieferant>",
        "  <Steuerfall>",
        "    <Umsatzsteuervoranmeldung>",
        f"      <Jahr>{jahr}</Jahr>",
        f"      <Zeitraum>{zr}</Zeitraum>",
        f"      <Steuernummer>{steuernummer13}</Steuernummer>",
        *kz_teile,
        "    </Umsatzsteuervoranmeldung>",
        "  </Steuerfall>",
        "</Anmeldungssteuern>",
    ]
    # ISO-8859-15-nicht darstellbare Zeichen (z. B. „—“, Emoji) als numerische
    # XML-Entitäten (&#NNN;) schreiben – valide XML, ELSTER dekodiert korrekt.
    return "\n".join(zeilen).encode("iso-8859-15", errors="xmlcharrefreplace")


# ---------------------------------------------------------------------------
# ZM-CSV (Meldelisten-Import in Mein ELSTER)
# ---------------------------------------------------------------------------

# Offizielle Schnittstelle (themaGlobal=zmdo_import_eop): CSV-Version 3.0,
# Excel-Version 3.2.1, UTF-8, Komma-getrennt, Summe als ganze Euro-Zahl.
# RechnungsFee-Kennzeichen → ELSTER-Code: intern "D" (§13b-Dienstleistung)
# ist bei ELSTER "S" (sonstige Leistung); "D" ist dort das Dreiecksgeschäft.
# Seit Issue #456 liefert api/zm.py direkt "S"; "D" bleibt als Altwert erlaubt.
_ZM_KENNZEICHEN = {"L": "L", "S": "S", "D": "S"}
_UST_IDNR_RE = re.compile(r"^[A-Z]{2}[0-9A-Z+*]{5,12}$")


def build_zm_csv(positionen) -> bytes:
    """Baut die ZM-Meldeliste als CSV für den Import in Mein ELSTER.

    positionen: Objekte mit .ust_idnr (inkl. Länderkennzeichen), .betrag
    (Decimal) und .kennzeichen ("L" ig. Lieferung / "D" ig. Dienstleistung
    §13b – wird zu ELSTER-"S" gemappt).
    """
    zeilen = [
        "#v3.0",
        "#ve3.2.1",
        "Umsatzsteuer-Identifikationsnummer (USt-IdNr.),Summe (Euro),Art der Leistung",
    ]
    fehler: list[str] = []
    for pos in positionen:
        ust_idnr = (pos.ust_idnr or "").strip().upper()
        if not _UST_IDNR_RE.fullmatch(ust_idnr):
            fehler.append(pos.ust_idnr or "<leer>")
            continue
        code = _ZM_KENNZEICHEN.get(pos.kennzeichen)
        if code is None:
            raise ElsterExportFehler(
                f"Unbekanntes ZM-Kennzeichen: {pos.kennzeichen!r}"
            )
        summe = pos.betrag.quantize(Decimal("1"), rounding="ROUND_HALF_UP")
        zeilen.append(f"{ust_idnr},{int(summe)},{code}")

    if fehler:
        raise ElsterExportFehler(
            "Fehlende oder ungültige USt-IdNr. bei: "
            + ", ".join(fehler)
            + " – bitte beim Kunden in den Stammdaten hinterlegen."
        )
    if len(zeilen) == 3:
        raise ElsterExportFehler(
            "Keine meldepflichtigen Positionen im Zeitraum – die ZM entfällt."
        )
    return ("\n".join(zeilen) + "\n").encode("utf-8")
