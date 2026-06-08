"""
Anlage EKS – Einkommenserklärung für Selbstständige (Jobcenter/Bürgergeld).
Feldcodes und -bezeichnungen entsprechen dem offiziellen Formular (04/2025).

Vorläufige EKS:  Prognose = Vorjahres-Halbjahr (abschliessend) ÷ 6.
Abschließende EKS: Echte Journalsummen pro Monat.
"""

import calendar as cal_mod
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import EksEinstellungen, EksExport, Journaleintrag, Kategorie, Unternehmen
from utils.pdf_eks import generate_eks_pdf

router = APIRouter(prefix="/api/eks", tags=["EKS"])

# ---------------------------------------------------------------------------
# EKS-Feldliste – Reihenfolge und Codes wie im offiziellen Formular 04/2025
# (tabelle, code, bezeichnung, auto_berechenbar_aus_journal, negativ)
# negativ=True: Feld wird vom B-Gesamt ABGEZOGEN (z.B. Privatanteil Betriebs-KFZ)
# ---------------------------------------------------------------------------

EKS_FELDER_META = [
    # ── Tabelle A: Betriebseinnahmen ──────────────────────────────────────
    ("A", "A1",    "Betriebseinnahmen",                                        True,  False),
    ("A", "A2",    "Privatentnahmen von Waren",                                True,  False),
    ("A", "A3",    "Sonstige betriebliche Einnahmen",                          True,  False),
    ("A", "A4",    "Zuwendungen von Dritten",                                  True,  False),
    ("A", "A5_1",  "Vereinnahmte Umsatzsteuer",                                True,  False),
    ("A", "A5_2",  "Umsatzsteuer auf Privatentnahmen von Waren",               True,  False),
    ("A", "A5_3",  "Vom Finanzamt erstattete Umsatzsteuer",                    True,  False),
    # ── Tabelle B Teil 1: Betriebsausgaben ───────────────────────────────
    ("B", "B1",    "Wareneinkauf",                                              True,  False),
    ("B", "B2_1",  "Personalkosten – Vollzeitbeschäftigte",                    True,  False),
    ("B", "B2_2",  "Personalkosten – Teilzeitbeschäftigte",                    False, False),
    ("B", "B2_3",  "Personalkosten – geringfügig Beschäftigte",                True,  False),
    ("B", "B2_4",  "Personalkosten – mithelfende Familienangehörige",          False, False),
    ("B", "B3",    "Betriebliche Raumkosten",                                   True,  False),
    ("B", "B4",    "Betriebliche Versicherungen / Beiträge",                   True,  False),
    ("B", "B5",    "Kosten für Werbung",                                        True,  False),
    # ── Tabelle B Teil 2 ─────────────────────────────────────────────────
    ("B", "B6_1",  "Betriebliches KFZ – Steuern",                              True,  False),
    ("B", "B6_2",  "Betriebliches KFZ – Versicherung",                         True,  False),
    ("B", "B6_3",  "Betriebliches KFZ – laufende Betriebskosten",              True,  False),
    ("B", "B6_4",  "Betriebliches KFZ – Reparaturkosten",                      False, False),
    ("B", "B6_4_priv", "  ↳ abzgl. privat gefahrene Kilometer (0,10 €/km)",   False, True),   # Abzug: Privatanteil Betriebs-KFZ
    ("B", "B6_5",  "Privates KFZ – betriebliche Fahrten (0,10 €/km)",          True,  False),  # auto aus journal.km_anzahl
    ("B", "B7_1",  "Reisekosten – Übernachtungskosten",                        True,  False),
    ("B", "B7_2",  "Reisekosten – Reisenebenkosten",                           False, False),
    ("B", "B7_3",  "Reisekosten – Öffentliche Verkehrsmittel",                 False, False),
    ("B", "B8",    "Investitionen",                                              True,  False),
    ("B", "B9",    "Investitionen aus Zuwendungen Dritter",                    False, False),
    ("B", "B10",   "Büromaterial einschließlich Porto",                         True,  False),
    # ── Tabelle B Teil 3 ─────────────────────────────────────────────────
    ("B", "B11",   "Telefonkosten",                                              True,  False),
    ("B", "B12",   "Beratungskosten",                                            True,  False),
    ("B", "B13",   "Fortbildungskosten",                                         True,  False),
    ("B", "B14_1", "Sonstige – Reparaturkosten Anlagevermögen",                False, False),
    ("B", "B14_2", "Sonstige – Miete Einrichtung",                             False, False),
    ("B", "B14_3", "Sonstige – Nebenkosten des Geldverkehrs",                  True,  False),
    ("B", "B14_4", "Sonstige – Betriebliche Abfallbeseitigung",                False, False),
    ("B", "B14_5", "Sonstige – weitere Betriebsausgaben",                      True,  False),
    ("B", "B15",   "Schuldzinsen aus Anlagevermögen",                           True,  False),
    ("B", "B16",   "Tilgung bestehender betrieblicher Darlehen",               True,  False),
    ("B", "B17",   "Gezahlte Vorsteuer",                                         False, False),
    ("B", "B18",   "An das Finanzamt gezahlte Umsatzsteuer",                   True,  False),
    # ── Tabelle C: Absetzungen vom Einkommen ─────────────────────────────
    ("C", "C1",    "Einkommensteuervorauszahlungen / -nachzahlungen",          True,  False),
    ("C", "C2",    "Pflichtbeiträge Kranken-/Pflege-/Rentenversicherung",      True,  False),
    ("C", "C3",    "Private Kranken-/Pflegeversicherung (freiwillig)",         True,  False),
    ("C", "C4",    "Beiträge zur Rentenversicherung",                           True,  False),
    ("C", "C5",    "Kapitalbildende Lebensversicherung",                        False, False),
    ("C", "C6",    "Beiträge zu Versorgungseinrichtungen",                      False, False),
    ("C", "C7",    "Kfz-Haftpflichtversicherung",                               False, False),
    ("C", "C8",    "Weitere gesetzlich vorgeschriebene Versicherungen",         False, False),
    ("C", "C9",    "Geförderte Altersvorsorge / Riester (§ 82 EStG)",          True,  False),
    ("C", "C10",   "Sonstige Absetzungsmöglichkeiten",                          False, False),
]

ALLE_CODES = [code for _, code, _, _, _ in EKS_FELDER_META]
A_CODES    = [code for t, code, _, _, _ in EKS_FELDER_META if t == "A"]
B_CODES    = [code for t, code, _, _, _ in EKS_FELDER_META if t == "B"]
C_CODES    = [code for t, code, _, _, _ in EKS_FELDER_META if t == "C"]
# B6_4_priv ist Abzugsposten – nicht in B_CODES für Spaltensummen (kein Journaleintrag)
B_CODES_SUMME = [code for t, code, _, _, negativ in EKS_FELDER_META if t == "B" and not negativ]


class EksPdfRequest(BaseModel):
    zeitraum_von: date
    zeitraum_bis: date
    art: str = "abschliessend"
    felder: dict[str, str]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _halbjahr_grenzen(monat_datum: date) -> tuple[date, date]:
    y = monat_datum.year
    if monat_datum.month <= 6:
        return date(y, 1, 1), date(y, 6, 30)
    return date(y, 7, 1), date(y, 12, 31)


def _monatsgrenzen(start: date) -> list[tuple[date, date, str]]:
    """Gibt Liste von 6 (von, bis, 'YYYY-MM') für aufeinanderfolgende Monate ab start."""
    ergebnis = []
    for i in range(6):
        total = start.month - 1 + i
        y = start.year + total // 12
        m = total % 12 + 1
        letzter = cal_mod.monthrange(y, m)[1]
        ergebnis.append((date(y, m, 1), date(y, m, letzter), f"{y}-{m:02d}"))
    return ergebnis


def _journal_summen_pro_monat(von: date, bis: date, db: Session) -> dict[str, str]:
    # Storno-Einträge haben art='Ausgabe' aber eks_kategorie eines A-Codes.
    # Daher getrennte Abfragen: Einnahmen (+) und Ausgaben (−) pro Kategorie.
    def _abfrage(art: str):
        return (
            db.query(
                Kategorie.eks_kategorie,
                func.sum(Journaleintrag.netto_betrag).label("netto_summe"),
                func.sum(Journaleintrag.brutto_betrag).label("brutto_summe"),
                func.sum(Journaleintrag.ust_betrag).label("ust_summe"),
            )
            .join(Journaleintrag.kategorie)
            .filter(
                Journaleintrag.datum >= von,
                Journaleintrag.datum <= bis,
                Kategorie.eks_kategorie.isnot(None),
                Journaleintrag.art == art,
            )
            .group_by(Kategorie.eks_kategorie)
            .all()
        )

    ein_rows = _abfrage("Einnahme")
    aus_rows = _abfrage("Ausgabe")

    # (netto, brutto, ust) pro Kategorie
    ein = {r.eks_kategorie: (Decimal(str(r.netto_summe or 0)), Decimal(str(r.brutto_summe or 0)), Decimal(str(r.ust_summe or 0))) for r in ein_rows}
    aus = {r.eks_kategorie: (Decimal(str(r.netto_summe or 0)), Decimal(str(r.brutto_summe or 0)), Decimal(str(r.ust_summe or 0))) for r in aus_rows}

    result: dict[str, str] = {}

    # A-Codes: Netto-Einnahmen − Netto-Storni (A5_1 addiert USt separat → zusammen = brutto)
    for code in A_CODES:
        e_n = ein.get(code, (Decimal("0"), Decimal("0"), Decimal("0")))[0]
        a_n = aus.get(code, (Decimal("0"), Decimal("0"), Decimal("0")))[0]
        net = (e_n - a_n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if net:
            result[code] = str(net)

    # B/C-Codes: Brutto-Ausgaben − Brutto-Storni
    for code in B_CODES + C_CODES:
        a_b = aus.get(code, (Decimal("0"), Decimal("0"), Decimal("0")))[1]
        e_b = ein.get(code, (Decimal("0"), Decimal("0"), Decimal("0")))[1]
        net = (a_b - e_b).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if net:
            result[code] = str(net)

    # B6_5: Privat-PKW betriebliche Fahrten – EKS-Rate 0,10 €/km (nicht 0,30 EÜR)
    b6_5_eintraege = (
        db.query(Journaleintrag.km_anzahl, Journaleintrag.brutto_betrag)
        .join(Journaleintrag.kategorie)
        .filter(
            Journaleintrag.datum >= von,
            Journaleintrag.datum <= bis,
            Kategorie.eks_kategorie == "B6_5",
        )
        .all()
    )
    if b6_5_eintraege:
        b6_5_total = Decimal("0")
        for e in b6_5_eintraege:
            if e.km_anzahl is not None:
                b6_5_total += Decimal(str(e.km_anzahl)) * Decimal("0.10")
            else:
                b6_5_total += Decimal(str(e.brutto_betrag))
        result["B6_5"] = str(b6_5_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    # A5_1: vereinnahmte USt netto (Einnahmen-USt − Storni-USt) automatisch ableiten
    # A5_2: USt auf Eigenverbrauch von Waren (A2) automatisch ableiten
    ust_a1 = sum(
        ein.get(code, (Decimal("0"), Decimal("0"), Decimal("0")))[2] - aus.get(code, (Decimal("0"), Decimal("0"), Decimal("0")))[2]
        for code in ("A1", "A3", "A4")
    )
    ust_a2 = (
        ein.get("A2", (Decimal("0"), Decimal("0"), Decimal("0")))[2]
        - aus.get("A2", (Decimal("0"), Decimal("0"), Decimal("0")))[2]
    )
    if ust_a1:
        existing = Decimal(result.get("A5_1", "0"))
        result["A5_1"] = str((existing + ust_a1).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    if ust_a2:
        existing = Decimal(result.get("A5_2", "0"))
        result["A5_2"] = str((existing + ust_a2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return result


def _zeilensummen(werte_pro_monat: dict, monate_keys: list[str]) -> dict[str, str]:
    result = {}
    for code in ALLE_CODES:
        s = sum(Decimal(werte_pro_monat.get(mk, {}).get(code, "0")) for mk in monate_keys)
        result[code] = str(s.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return result


def _spaltensummen(werte_pro_monat: dict, monate_keys: list[str], codes: list[str]) -> dict[str, str]:
    result = {}
    for mk in monate_keys:
        s = sum(Decimal(werte_pro_monat.get(mk, {}).get(c, "0")) for c in codes)
        result[mk] = str(s.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return result


# ---------------------------------------------------------------------------
# Endpunkte
# ---------------------------------------------------------------------------

@router.get("/halbjahr")
def eks_halbjahr(
    start: date = Query(..., description="Erster Tag des ersten Monats"),
    art: str = Query("abschliessend"),
    db: Session = Depends(get_db),
):
    """Berechnet EKS für 6 aufeinanderfolgende Monate (Bewilligungszeitraum)."""
    monate = _monatsgrenzen(start)
    monate_keys = [mk for _, _, mk in monate]
    quelle = None

    if art == "vorlaeufig":
        hj_von, hj_bis = _halbjahr_grenzen(start)
        vj_von = date(hj_von.year - 1, hj_von.month, hj_von.day)
        vj_bis = date(hj_bis.year - 1, hj_bis.month, hj_bis.day)

        exports_vj = (
            db.query(EksExport)
            .filter(
                EksExport.art == "abschliessend",
                EksExport.zeitraum_von >= vj_von,
                EksExport.zeitraum_bis <= vj_bis,
            )
            .all()
        )

        if not exports_vj:
            werte_pro_monat = {mk: {} for mk in monate_keys}
        else:
            summen: dict[str, Decimal] = {}
            for exp in exports_vj:
                rohdaten = json.loads(exp.daten_json or "{}")
                # daten_json kann Halbjahr-Format {"zeilensummen": {...}} oder Alt-Format sein
                if "zeilensummen" in rohdaten:
                    quell_werte = rohdaten["zeilensummen"]
                else:
                    quell_werte = rohdaten
                for code in ALLE_CODES:
                    summen[code] = summen.get(code, Decimal("0")) + Decimal(str(quell_werte.get(code, "0")))

            werte_pro_monat = {
                mk: {
                    code: str(
                        (summen.get(code, Decimal("0")) / 6)
                        .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    )
                    for code in ALLE_CODES
                }
                for mk in monate_keys
            }
            quelle = {
                "zeitraum_von": str(vj_von),
                "zeitraum_bis": str(vj_bis),
                "anzahl_exporte": len(exports_vj),
            }
    else:
        werte_pro_monat = {}
        for von_m, bis_m, mk in monate:
            werte_pro_monat[mk] = _journal_summen_pro_monat(von_m, bis_m, db)

    zeilen   = _zeilensummen(werte_pro_monat, monate_keys)
    spalten_a = _spaltensummen(werte_pro_monat, monate_keys, A_CODES)
    spalten_b = _spaltensummen(werte_pro_monat, monate_keys, B_CODES_SUMME)
    spalten_c = _spaltensummen(werte_pro_monat, monate_keys, C_CODES)

    felder_meta = [
        {"tabelle": t, "code": code, "label": label, "auto": auto, "negativ": negativ}
        for t, code, label, auto, negativ in EKS_FELDER_META
    ]

    return {
        "monate": monate_keys,
        "werte": werte_pro_monat,
        "zeilensummen": zeilen,
        "spaltensummen_a": spalten_a,
        "spaltensummen_b": spalten_b,
        "spaltensummen_c": spalten_c,
        "felder": felder_meta,
        "art": art,
        "quelle": quelle,
        "bewilligungszeitraum_von": str(monate[0][0]),
        "bewilligungszeitraum_bis": str(monate[-1][1]),
    }


@router.get("/halbjahr/pdf")
def eks_halbjahr_pdf(
    start: date = Query(...),
    art: str = Query("abschliessend"),
    db: Session = Depends(get_db),
):
    """Generiert das EKS-PDF für den 6-Monats-Bewilligungszeitraum."""
    data = eks_halbjahr(start=start, art=art, db=db)

    unt = db.query(Unternehmen).first()
    unt_dict: dict = {}
    if unt:
        unt_dict = {
            "firmenname": unt.firmenname or "",
            "vorname": unt.vorname or "",
            "nachname": unt.nachname or "",
            "strasse": unt.strasse or "",
            "hausnummer": unt.hausnummer or "",
            "plz": unt.plz or "",
            "ort": unt.ort or "",
            "steuernummer": unt.steuernummer or "",
            "rechtsform": unt.rechtsform or "",
            "geburtsdatum": unt.geburtsdatum,
            "bg_nummer": unt.bg_nummer or "",
            "jobcenter_name": unt.jobcenter_name or "",
            "unterschrift_bild": unt.unterschrift_bild or "",
        }

    einst = db.query(EksEinstellungen).filter_by(id=1).first()
    einst_dict = _einst_to_dict(einst)

    pdf_bytes = generate_eks_pdf(
        bewilligungszeitraum_von=date.fromisoformat(data["bewilligungszeitraum_von"]),
        bewilligungszeitraum_bis=date.fromisoformat(data["bewilligungszeitraum_bis"]),
        art=art,
        monate=data["monate"],
        werte=data["werte"],
        zeilensummen=data["zeilensummen"],
        spaltensummen_a=data["spaltensummen_a"],
        spaltensummen_b=data["spaltensummen_b"],
        spaltensummen_c=data["spaltensummen_c"],
        felder=data["felder"],
        unternehmen=unt_dict,
        einstellungen=einst_dict,
    )

    eks_export = EksExport(
        zeitraum_von=date.fromisoformat(data["bewilligungszeitraum_von"]),
        zeitraum_bis=date.fromisoformat(data["bewilligungszeitraum_bis"]),
        art=art,
        daten_json=json.dumps({
            "zeilensummen": data["zeilensummen"],
            "werte": data["werte"],
        }),
    )
    db.add(eks_export)
    db.commit()

    dateiname = f"EKS_{data['bewilligungszeitraum_von']}_{data['bewilligungszeitraum_bis']}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{dateiname}"'},
    )


# ---------------------------------------------------------------------------
# Legacy-Endpunkte (berechnen / pdf) – bleiben für Kompatibilität
# ---------------------------------------------------------------------------

@router.get("/berechnen")
def eks_berechnen(
    von: date = Query(...),
    bis: date = Query(...),
    art: str = Query("abschliessend"),
    db: Session = Depends(get_db),
):
    felder_werte = _journal_summen_pro_monat(von, bis, db)
    meta = [
        {
            "tabelle": t, "code": code, "label": label,
            "auto": auto, "wert": felder_werte.get(code, "0.00"),
        }
        for t, code, label, auto in EKS_FELDER_META
    ]
    return {"zeitraum_von": str(von), "zeitraum_bis": str(bis), "art": art, "felder": meta, "quelle": None}


def _eks_pdf_generieren_legacy(zeitraum_von, zeitraum_bis, art, felder, db):
    unt = db.query(Unternehmen).first()
    unt_dict: dict = {}
    if unt:
        unt_dict = {
            "firmenname": unt.firmenname or "",
            "vorname": unt.vorname or "",
            "nachname": unt.nachname or "",
            "strasse": (unt.strasse or "") + " " + (unt.hausnummer or ""),
            "plz": unt.plz or "",
            "ort": unt.ort or "",
            "steuernummer": unt.steuernummer or "",
        }
    start = date(zeitraum_von.year, zeitraum_von.month, 1)
    monate = _monatsgrenzen(start)
    werte = {mk: felder for _, _, mk in monate}  # same values for all months
    zeilen = {code: felder.get(code, "0.00") for code in ALLE_CODES}
    spalten_a = _spaltensummen(werte, [mk for _, _, mk in monate], A_CODES)
    spalten_b = _spaltensummen(werte, [mk for _, _, mk in monate], B_CODES)
    spalten_c = _spaltensummen(werte, [mk for _, _, mk in monate], C_CODES)
    felder_meta = [{"tabelle": t, "code": code, "label": label, "auto": auto} for t, code, label, auto in EKS_FELDER_META]
    pdf_bytes = generate_eks_pdf(
        bewilligungszeitraum_von=zeitraum_von,
        bewilligungszeitraum_bis=zeitraum_bis,
        art=art,
        monate=[mk for _, _, mk in monate],
        werte=werte,
        zeilensummen=zeilen,
        spaltensummen_a=spalten_a,
        spaltensummen_b=spalten_b,
        spaltensummen_c=spalten_c,
        felder=felder_meta,
        unternehmen=unt_dict,
    )
    eks_export = EksExport(
        zeitraum_von=zeitraum_von,
        zeitraum_bis=zeitraum_bis,
        art=art,
        daten_json=json.dumps({"zeilensummen": zeilen}),
    )
    db.add(eks_export)
    db.commit()
    dateiname = f"EKS_{zeitraum_von}_{zeitraum_bis}.pdf"
    return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf",
                             headers={"Content-Disposition": f'inline; filename="{dateiname}"'})


@router.get("/pdf")
def eks_pdf_get(
    zeitraum_von: date = Query(...),
    zeitraum_bis: date = Query(...),
    art: str = Query("abschliessend"),
    felder: str = Query(...),
    db: Session = Depends(get_db),
):
    return _eks_pdf_generieren_legacy(zeitraum_von, zeitraum_bis, art, json.loads(felder), db)


@router.post("/pdf")
def eks_pdf(req: EksPdfRequest, db: Session = Depends(get_db)):
    return _eks_pdf_generieren_legacy(req.zeitraum_von, req.zeitraum_bis, req.art, req.felder, db)


# ---------------------------------------------------------------------------
# EKS-Einstellungen (GET / PUT)
# ---------------------------------------------------------------------------

_EINST_BOOL_FELDER = [
    "wohnung_gewerblich", "produkte_kostenfrei", "personal_beschaeftigt",
    "weiteres_personal", "umsatzsteuerpflichtig", "zuschuss_erhalten",
    "zuschuss_beantragt", "darlehen", "kind_ausserhalb", "unterhalt",
    "fahrten_betriebsstaette", "mehraufwand_verpflegung",
]

_EINST_STR_FELDER = [
    "taetigkeitsart_text", "taetigkeitsbeginn", "taetigkeitsende",
    "gewerbliche_raeume", "gewerbliche_flaeche", "anzahl_beschaeftigte",
    "anzahl_weiteres_personal", "personal_ab", "darlehen_hoehe",
    "darlehen_eingang", "darlehen_rueckzahlung_ab", "darlehen_tilgung",
    "darlehen_ausgaben_art", "darlehen_ausgaben_hoehe", "km_einfach",
    "arbeitstage_pro_woche", "arbeitstage_verpflegung",
]


def _einst_to_dict(einst: "EksEinstellungen | None") -> dict:
    if einst is None:
        return {f: False for f in _EINST_BOOL_FELDER} | {f: "" for f in _EINST_STR_FELDER}
    return {
        **{f: bool(getattr(einst, f, False)) for f in _EINST_BOOL_FELDER},
        **{f: getattr(einst, f) or "" for f in _EINST_STR_FELDER},
    }


@router.get("/einstellungen")
def eks_einstellungen_get(db: Session = Depends(get_db)):
    """Laedt die gespeicherten EKS-Formularfelder (Singleton id=1)."""
    e = db.query(EksEinstellungen).filter_by(id=1).first()
    if e is None:
        return _einst_to_dict(None)
    from api.schemas import EksEinstellungenResponse
    return EksEinstellungenResponse.model_validate(e)


@router.put("/einstellungen")
def eks_einstellungen_put(data: dict, db: Session = Depends(get_db)):
    """Speichert / aktualisiert die EKS-Formularfelder."""
    e = db.query(EksEinstellungen).filter_by(id=1).first()
    allowed = set(_EINST_BOOL_FELDER + _EINST_STR_FELDER)
    if e is None:
        kwargs = {k: v for k, v in data.items() if k in allowed}
        e = EksEinstellungen(id=1, **kwargs)
        db.add(e)
    else:
        for k, v in data.items():
            if k in allowed:
                setattr(e, k, v)
    db.commit()
    db.refresh(e)
    return _einst_to_dict(e)
