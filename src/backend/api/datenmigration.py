"""
Datenübernahme / CSV-Import für Kunden, Lieferanten und Artikel.

Unterstützt beliebige CSV-Formate (mit/ohne Header, Semikolon/Komma/Tab)
mit manueller Feldzuordnung und optionalen gespeicherten Mappings.
"""

import csv
import io
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Kunde, Lieferant, Artikel, ArtikelGruppe
from api.schemas import (
    ImportSpaltenResponse,
    ImportVorschauZeile,
    ImportRequest,
    ImportErgebnis,
    ImportMappingVorlageCreate,
    ImportMappingVorlageResponse,
)
from utils.bank_csv_parser import detect_encoding, detect_delimiter

router = APIRouter(prefix="/api/datenmigration", tags=["datenmigration"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _parse_csv_raw(raw: bytes, hat_header: bool) -> tuple[list[str], list[list[str]], str, str]:
    """CSV parsen, Spaltennamen und Vorschau-Zeilen zurückgeben."""
    encoding = detect_encoding(raw)
    text_content = raw.decode(encoding, errors="replace")
    delimiter = detect_delimiter(text_content)

    reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
    zeilen = [row for row in reader if any(cell.strip() for cell in row)]

    if not zeilen:
        return [], [], delimiter, encoding

    if hat_header:
        spaltennamen = [h.strip() for h in zeilen[0]]
        datenzeilen = zeilen[1:]
    else:
        if zeilen:
            anzahl = len(zeilen[0])
        else:
            anzahl = 0
        spaltennamen = [f"Spalte {i + 1}" for i in range(anzahl)]
        datenzeilen = zeilen

    vorschau = [row for row in datenzeilen[:5]]
    return spaltennamen, vorschau, delimiter, encoding


def _zeile_zu_dict(row: list[str], spaltennamen: list[str], mapping: dict[str, str]) -> dict:
    """CSV-Zeile anhand des Mappings in ein Felder-Dict umwandeln."""
    ergebnis = {}
    for i, wert in enumerate(row):
        col_key = spaltennamen[i] if i < len(spaltennamen) else f"Spalte {i + 1}"
        zielfeld = mapping.get(col_key, "").strip()
        if zielfeld and zielfeld != "__ignorieren__":
            ergebnis[zielfeld] = wert.strip()
    return ergebnis


def _typ_aus_nummer(nummer: str) -> Optional[str]:
    """10xxx → kunden, 70xxx → lieferanten, sonst None."""
    nr = nummer.strip()
    try:
        n = int(nr)
        if 10000 <= n <= 19999:
            return "kunden"
        if 70000 <= n <= 79999:
            return "lieferanten"
    except ValueError:
        pass
    return None


def _duplikat_kunden(db: Session, daten: dict) -> Optional[int]:
    kundennummer = daten.get("kundennummer", "").strip()
    if kundennummer:
        row = db.execute(
            text("SELECT id FROM kunden WHERE kundennummer = :nr AND aktiv = 1"),
            {"nr": kundennummer},
        ).fetchone()
        if row:
            return row[0]
    firmenname = daten.get("firmenname", "").strip().lower()
    nachname = daten.get("nachname", "").strip().lower()
    if firmenname:
        row = db.execute(
            text("SELECT id FROM kunden WHERE LOWER(firmenname) = :fn AND aktiv = 1"),
            {"fn": firmenname},
        ).fetchone()
        if row:
            return row[0]
    if nachname:
        row = db.execute(
            text("SELECT id FROM kunden WHERE LOWER(nachname) = :nn AND aktiv = 1"),
            {"nn": nachname},
        ).fetchone()
        if row:
            return row[0]
    return None


def _duplikat_lieferanten(db: Session, daten: dict) -> Optional[int]:
    lieferantennummer = daten.get("lieferantennummer", "").strip()
    if lieferantennummer:
        row = db.execute(
            text("SELECT id FROM lieferanten WHERE lieferantennummer = :nr AND aktiv = 1"),
            {"nr": lieferantennummer},
        ).fetchone()
        if row:
            return row[0]
    firmenname = daten.get("firmenname", "").strip().lower()
    if firmenname:
        row = db.execute(
            text("SELECT id FROM lieferanten WHERE LOWER(firmenname) = :fn AND aktiv = 1"),
            {"fn": firmenname},
        ).fetchone()
        if row:
            return row[0]
    return None


def _duplikat_artikel(db: Session, daten: dict) -> Optional[int]:
    artikelnummer = daten.get("artikelnummer", "").strip()
    if artikelnummer:
        row = db.execute(
            text("SELECT id FROM artikel WHERE artikelnummer = :nr AND aktiv = 1"),
            {"nr": artikelnummer},
        ).fetchone()
        if row:
            return row[0]
    bezeichnung = daten.get("bezeichnung", "").strip().lower()
    if bezeichnung:
        row = db.execute(
            text("SELECT id FROM artikel WHERE LOWER(bezeichnung) = :bz AND aktiv = 1"),
            {"bz": bezeichnung},
        ).fetchone()
        if row:
            return row[0]
    return None


def _naechste_nummer(db: Session, typ: str) -> str:
    row = db.execute(
        text("SELECT format, naechste_nr FROM nummernkreise WHERE typ = :t AND aktiv = 1"),
        {"t": typ},
    ).fetchone()
    if not row:
        return ""
    fmt, nr = row
    nummer = fmt.replace("####", str(nr).zfill(4))
    db.execute(
        text("UPDATE nummernkreise SET naechste_nr = naechste_nr + 1 WHERE typ = :t"),
        {"t": typ},
    )
    return nummer


def _kunde_anlegen(db: Session, daten: dict, ueberschreiben_id: Optional[int] = None):
    felder = {
        "firmenname": daten.get("firmenname") or None,
        "vorname": daten.get("vorname") or None,
        "nachname": daten.get("nachname") or None,
        "strasse": daten.get("strasse") or None,
        "hausnummer": daten.get("hausnummer") or None,
        "plz": daten.get("plz") or None,
        "ort": daten.get("ort") or None,
        "land": daten.get("land") or "DE",
        "email": daten.get("email") or None,
        "telefon": daten.get("telefon") or None,
        "ust_idnr": daten.get("ust_idnr") or None,
        "z_hd": daten.get("z_hd") or None,
        "notizen": daten.get("notizen") or None,
    }
    try:
        felder["skonto_prozent"] = Decimal(daten["skonto_prozent"]) if daten.get("skonto_prozent") else None
        felder["skonto_tage"] = int(daten["skonto_tage"]) if daten.get("skonto_tage") else None
    except (InvalidOperation, ValueError):
        felder["skonto_prozent"] = None
        felder["skonto_tage"] = None

    if ueberschreiben_id:
        db.execute(
            text("""UPDATE kunden SET firmenname=:firmenname, vorname=:vorname, nachname=:nachname,
                    strasse=:strasse, hausnummer=:hausnummer, plz=:plz, ort=:ort, land=:land,
                    email=:email, telefon=:telefon, ust_idnr=:ust_idnr, z_hd=:z_hd,
                    notizen=:notizen, skonto_prozent=:skonto_prozent, skonto_tage=:skonto_tage,
                    aktualisiert_am=CURRENT_TIMESTAMP WHERE id=:id"""),
            {**felder, "id": ueberschreiben_id},
        )
        return "aktualisiert"

    kundennummer = daten.get("kundennummer") or _naechste_nummer(db, "kunde")
    db.execute(
        text("""INSERT INTO kunden (firmenname, vorname, nachname, strasse, hausnummer, plz, ort, land,
                email, telefon, ust_idnr, kundennummer, z_hd, notizen, skonto_prozent, skonto_tage,
                aktiv, erstellt_am, aktualisiert_am)
                VALUES (:firmenname, :vorname, :nachname, :strasse, :hausnummer, :plz, :ort, :land,
                :email, :telefon, :ust_idnr, :kundennummer, :z_hd, :notizen, :skonto_prozent, :skonto_tage,
                1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""),
        {**felder, "kundennummer": kundennummer},
    )
    return "importiert"


def _lieferant_anlegen(db: Session, daten: dict, ueberschreiben_id: Optional[int] = None):
    felder = {
        "firmenname": daten.get("firmenname") or daten.get("nachname") or "Unbekannt",
        "vorname": daten.get("vorname") or None,
        "nachname": daten.get("nachname") or None,
        "strasse": daten.get("strasse") or None,
        "hausnummer": daten.get("hausnummer") or None,
        "plz": daten.get("plz") or None,
        "ort": daten.get("ort") or None,
        "land": daten.get("land") or "DE",
        "email": daten.get("email") or None,
        "telefon": daten.get("telefon") or None,
        "ust_idnr": daten.get("ust_idnr") or None,
        "z_hd": daten.get("z_hd") or None,
        "notizen": daten.get("notizen") or None,
    }

    if ueberschreiben_id:
        db.execute(
            text("""UPDATE lieferanten SET firmenname=:firmenname, vorname=:vorname, nachname=:nachname,
                    strasse=:strasse, hausnummer=:hausnummer, plz=:plz, ort=:ort, land=:land,
                    email=:email, telefon=:telefon, ust_idnr=:ust_idnr, z_hd=:z_hd,
                    notizen=:notizen WHERE id=:id"""),
            {**felder, "id": ueberschreiben_id},
        )
        return "aktualisiert"

    lieferantennummer = daten.get("lieferantennummer") or _naechste_nummer(db, "lieferant")
    db.execute(
        text("""INSERT INTO lieferanten (firmenname, vorname, nachname, strasse, hausnummer, plz, ort, land,
                email, telefon, ust_idnr, lieferantennummer, z_hd, notizen, aktiv, erstellt_am)
                VALUES (:firmenname, :vorname, :nachname, :strasse, :hausnummer, :plz, :ort, :land,
                :email, :telefon, :ust_idnr, :lieferantennummer, :z_hd, :notizen,
                1, CURRENT_TIMESTAMP)"""),
        {**felder, "lieferantennummer": lieferantennummer},
    )
    return "importiert"


def _artikel_anlegen(db: Session, daten: dict, ueberschreiben_id: Optional[int] = None):
    typ = daten.get("typ", "artikel").strip().lower()
    if typ not in ("artikel", "dienstleistung", "fremdleistung"):
        typ = "artikel"
    try:
        vk_brutto = Decimal(daten.get("vk_brutto", "0").replace(",", "."))
    except InvalidOperation:
        vk_brutto = Decimal("0")
    try:
        ek_netto = Decimal(daten.get("ek_netto", "0").replace(",", ".")) if daten.get("ek_netto") else None
    except InvalidOperation:
        ek_netto = None
    try:
        steuersatz = Decimal(daten.get("steuersatz_prozent", "19").replace(",", "."))
    except InvalidOperation:
        steuersatz = Decimal("19")
    vk_netto = (vk_brutto / (1 + steuersatz / 100)).quantize(Decimal("0.01"))

    felder = {
        "typ": typ,
        "bezeichnung": daten.get("bezeichnung") or "Unbekannt",
        "einheit": daten.get("einheit") or "Stück",
        "steuersatz": steuersatz,
        "vk_brutto": vk_brutto,
        "vk_netto": vk_netto,
        "ek_netto": ek_netto,
        "artikelcode": daten.get("artikelcode") or None,
        "hersteller": daten.get("hersteller") or None,
        "beschreibung": daten.get("beschreibung") or None,
    }

    if ueberschreiben_id:
        db.execute(
            text("""UPDATE artikel SET typ=:typ, bezeichnung=:bezeichnung, einheit=:einheit,
                    steuersatz=:steuersatz, vk_brutto=:vk_brutto, vk_netto=:vk_netto,
                    ek_netto=:ek_netto, artikelcode=:artikelcode, hersteller=:hersteller,
                    beschreibung=:beschreibung, aktualisiert_am=CURRENT_TIMESTAMP
                    WHERE id=:id"""),
            {**felder, "id": ueberschreiben_id},
        )
        return "aktualisiert"

    artikelnummer = daten.get("artikelnummer") or _naechste_nummer(db, "artikel")
    db.execute(
        text("""INSERT INTO artikel (artikelnummer, typ, bezeichnung, einheit, steuersatz,
                vk_brutto, vk_netto, ek_netto, artikelcode, hersteller, beschreibung,
                aktiv, erstellt_am, aktualisiert_am)
                VALUES (:artikelnummer, :typ, :bezeichnung, :einheit, :steuersatz,
                :vk_brutto, :vk_netto, :ek_netto, :artikelcode, :hersteller, :beschreibung,
                1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"""),
        {**felder, "artikelnummer": artikelnummer},
    )
    return "importiert"


# ---------------------------------------------------------------------------
# Muster-CSV
# ---------------------------------------------------------------------------

_MUSTER_CSVS = {
    "kunden": (
        "# firmenname: Firmenname (leer bei Privatperson)\n"
        "# vorname: Vorname\n"
        "# nachname: Nachname\n"
        "# strasse: Straße (ohne Hausnummer)\n"
        "# hausnummer: Hausnummer\n"
        "# plz: Postleitzahl\n"
        "# ort: Ort\n"
        "# land: Länderkürzel (z.B. DE, AT, CH)\n"
        "# email: E-Mail-Adresse\n"
        "# telefon: Telefonnummer\n"
        "# ust_idnr: Umsatzsteuer-ID (z.B. DE123456789)\n"
        "# kundennummer: Eigene Kundennummer (leer = automatisch)\n"
        "# z_hd: Zu Händen\n"
        "# notizen: Interne Notizen\n"
        "# skonto_prozent: Skonto in Prozent (z.B. 2.00)\n"
        "# skonto_tage: Skonto-Zahlungsziel in Tagen\n"
        "firmenname;vorname;nachname;strasse;hausnummer;plz;ort;land;email;telefon;ust_idnr;kundennummer;z_hd;notizen;skonto_prozent;skonto_tage\n"
        "Musterfirma GmbH;;Müller;Hauptstraße;1;12345;Berlin;DE;info@musterfirma.de;030123456;DE123456789;;;; ; \n"
        ";Anna;Schmidt;Gartenweg;5;80331;München;DE;a.schmidt@example.com;;;;KD-0002;; ; \n"
    ),
    "lieferanten": (
        "# firmenname: Firmenname (PFLICHT)\n"
        "# vorname: Vorname Ansprechpartner\n"
        "# nachname: Nachname Ansprechpartner\n"
        "# strasse: Straße\n"
        "# hausnummer: Hausnummer\n"
        "# plz: Postleitzahl\n"
        "# ort: Ort\n"
        "# land: Länderkürzel\n"
        "# email: E-Mail-Adresse\n"
        "# telefon: Telefonnummer\n"
        "# ust_idnr: Umsatzsteuer-ID\n"
        "# lieferantennummer: Eigene Lieferantennummer (leer = automatisch)\n"
        "# z_hd: Zu Händen\n"
        "# notizen: Interne Notizen\n"
        "firmenname;vorname;nachname;strasse;hausnummer;plz;ort;land;email;telefon;ust_idnr;lieferantennummer;z_hd;notizen\n"
        "Lieferant AG;;;Industrieweg;10;10115;Berlin;DE;bestellung@lieferant.de;030987654;;LI-0001;; \n"
        "Großhandel Nord GmbH;;;Hafenstraße;22;20457;Hamburg;DE;info@grosshandel-nord.de;;;; ; \n"
    ),
    "artikel": (
        "# typ: artikel | dienstleistung | fremdleistung (PFLICHT)\n"
        "# bezeichnung: Artikelbezeichnung (PFLICHT)\n"
        "# einheit: Stück, Stunden, kg, m², etc.\n"
        "# steuersatz_prozent: 0, 7 oder 19\n"
        "# vk_brutto: Verkaufspreis brutto (PFLICHT)\n"
        "# ek_netto: Einkaufspreis netto (optional)\n"
        "# artikelcode: Eigene Artikelnummer/EAN (leer = automatisch)\n"
        "# hersteller: Herstellername\n"
        "# beschreibung: Langbeschreibung\n"
        "typ;bezeichnung;einheit;steuersatz_prozent;vk_brutto;ek_netto;artikelcode;hersteller;beschreibung\n"
        "artikel;Schrauben M6x20;Stück;19;0.25;0.10;SCH-M6-20;Würth;Sechskantschrauben galvanisch verzinkt\n"
        "dienstleistung;Beratungsstunde;Stunden;19;120.00;;;;Beratung und Konzeption\n"
    ),
}


@router.get("/muster-csv/{typ}")
def muster_csv_download(typ: str):
    if typ not in _MUSTER_CSVS:
        raise HTTPException(404, f"Unbekannter Typ: {typ}")
    inhalt = _MUSTER_CSVS[typ]
    return StreamingResponse(
        io.BytesIO(inhalt.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="muster_{typ}.csv"'},
    )


# ---------------------------------------------------------------------------
# Spalten / Vorschau (für Mapping-UI)
# ---------------------------------------------------------------------------

@router.post("/spalten", response_model=ImportSpaltenResponse)
async def spalten_lesen(
    datei: UploadFile = File(...),
    hat_header: bool = Form(True),
):
    raw = await datei.read()
    spaltennamen, vorschau, delimiter, encoding = _parse_csv_raw(raw, hat_header)
    if not spaltennamen:
        raise HTTPException(400, "CSV ist leer oder konnte nicht gelesen werden.")
    return ImportSpaltenResponse(
        spaltennamen=spaltennamen,
        vorschau=vorschau,
        delimiter=delimiter,
        encoding=encoding,
    )


# ---------------------------------------------------------------------------
# Mapping-Vorlagen
# ---------------------------------------------------------------------------

@router.get("/mapping-vorlagen", response_model=list[ImportMappingVorlageResponse])
def mapping_vorlagen_liste(db: Session = Depends(get_db)):
    rows = db.execute(text(
        "SELECT id, name, typ, hat_header, mapping_json, typ_erkennung_aktiv, erstellt_am "
        "FROM import_mapping_vorlagen ORDER BY erstellt_am DESC"
    )).fetchall()
    return [
        ImportMappingVorlageResponse(
            id=r[0], name=r[1], typ=r[2], hat_header=bool(r[3]),
            mapping_json=r[4], typ_erkennung_aktiv=bool(r[5]), erstellt_am=r[6],
        )
        for r in rows
    ]


@router.post("/mapping-vorlagen", response_model=ImportMappingVorlageResponse)
def mapping_vorlage_speichern(data: ImportMappingVorlageCreate, db: Session = Depends(get_db)):
    jetzt = datetime.now()
    result = db.execute(
        text("""INSERT INTO import_mapping_vorlagen (name, typ, hat_header, mapping_json, typ_erkennung_aktiv, erstellt_am)
                VALUES (:name, :typ, :hat_header, :mapping_json, :typ_erkennung_aktiv, :erstellt_am)"""),
        {**data.model_dump(), "erstellt_am": jetzt},
    )
    db.commit()
    return ImportMappingVorlageResponse(id=result.lastrowid, erstellt_am=jetzt, **data.model_dump())


@router.delete("/mapping-vorlagen/{vorlage_id}", status_code=204)
def mapping_vorlage_loeschen(vorlage_id: int, db: Session = Depends(get_db)):
    db.execute(text("DELETE FROM import_mapping_vorlagen WHERE id = :id"), {"id": vorlage_id})
    db.commit()


# ---------------------------------------------------------------------------
# Vorschau mit Duplikat-Prüfung
# ---------------------------------------------------------------------------

@router.post("/vorschau/{typ}", response_model=list[ImportVorschauZeile])
async def import_vorschau(
    typ: str,
    datei: UploadFile = File(...),
    hat_header: bool = Form(True),
    mapping_json: str = Form(...),
    typ_erkennung_aktiv: bool = Form(False),
    db: Session = Depends(get_db),
):
    if typ not in ("kunden", "lieferanten", "artikel", "gemischt"):
        raise HTTPException(400, f"Unbekannter Typ: {typ}")

    raw = await datei.read()
    spaltennamen, _, _, _ = _parse_csv_raw(raw, hat_header)

    # Alle Zeilen nochmal parsen (vorschau enthält nur 5)
    encoding = _detect_enc(raw)
    text_content = raw.decode(encoding, errors="replace")
    delimiter = detect_delimiter(text_content)
    import csv as _csv
    reader = _csv.reader(io.StringIO(text_content), delimiter=delimiter)
    alle_zeilen = [row for row in reader if any(c.strip() for c in row)]
    datenzeilen = alle_zeilen[1:] if hat_header else alle_zeilen

    try:
        mapping: dict[str, str] = json.loads(mapping_json)
    except Exception:
        raise HTTPException(400, "mapping_json ist kein gültiges JSON.")

    ergebnis = []
    for idx, row in enumerate(datenzeilen, start=2 if hat_header else 1):
        daten = _zeile_zu_dict(row, spaltennamen, mapping)

        ziel_typ = typ
        if typ == "gemischt" and typ_erkennung_aktiv:
            nr = daten.get("kundennummer", "") or daten.get("lieferantennummer", "")
            erkannt = _typ_aus_nummer(nr)
            if erkannt:
                ziel_typ = erkannt
                # Kundennummer/Lieferantennummer korrekt setzen
                if erkannt == "kunden":
                    daten["kundennummer"] = nr
                    daten.pop("lieferantennummer", None)
                else:
                    daten["lieferantennummer"] = nr
                    daten.pop("kundennummer", None)
            else:
                ergebnis.append(ImportVorschauZeile(
                    zeile=idx, daten=daten, status="fehler",
                    fehler="Typ nicht erkennbar (Nummer passt weder zu 10xxx noch 70xxx)",
                ))
                continue

        fehler = _validiere(ziel_typ, daten)
        if fehler:
            ergebnis.append(ImportVorschauZeile(zeile=idx, daten=daten, status="fehler", fehler=fehler))
            continue

        duplikat_id = _pruefe_duplikat(ziel_typ, db, daten)
        daten["__typ__"] = ziel_typ
        ergebnis.append(ImportVorschauZeile(
            zeile=idx, daten=daten,
            status="duplikat" if duplikat_id else "neu",
            duplikat_id=duplikat_id,
        ))

    return ergebnis


def _detect_enc(raw: bytes) -> str:
    from utils.bank_csv_parser import detect_encoding
    return detect_encoding(raw)


def _validiere(typ: str, daten: dict) -> Optional[str]:
    if typ == "kunden":
        if not daten.get("firmenname") and not daten.get("nachname"):
            return "firmenname oder nachname erforderlich"
    elif typ == "lieferanten":
        if not daten.get("firmenname"):
            return "firmenname erforderlich"
    elif typ == "artikel":
        if not daten.get("bezeichnung"):
            return "bezeichnung erforderlich"
        if not daten.get("vk_brutto"):
            return "vk_brutto erforderlich"
    return None


def _pruefe_duplikat(typ: str, db: Session, daten: dict) -> Optional[int]:
    if typ == "kunden":
        return _duplikat_kunden(db, daten)
    if typ == "lieferanten":
        return _duplikat_lieferanten(db, daten)
    if typ == "artikel":
        return _duplikat_artikel(db, daten)
    return None


# ---------------------------------------------------------------------------
# Import durchführen
# ---------------------------------------------------------------------------

@router.post("/importieren/{typ}", response_model=ImportErgebnis)
def import_durchfuehren(typ: str, request: ImportRequest, db: Session = Depends(get_db)):
    if typ not in ("kunden", "lieferanten", "artikel", "gemischt"):
        raise HTTPException(400, f"Unbekannter Typ: {typ}")

    importiert = 0
    aktualisiert = 0
    ignoriert = 0
    fehler_liste = []

    for zeile_obj in request.zeilen:
        if zeile_obj.aktion == "ignorieren":
            ignoriert += 1
            continue

        daten = zeile_obj.daten
        ziel_typ = daten.pop("__typ__", typ)
        ueberschreiben_id = zeile_obj.duplikat_id if zeile_obj.aktion == "überschreiben" else None

        try:
            if ziel_typ == "kunden":
                result = _kunde_anlegen(db, daten, ueberschreiben_id)
            elif ziel_typ == "lieferanten":
                result = _lieferant_anlegen(db, daten, ueberschreiben_id)
            elif ziel_typ == "artikel":
                result = _artikel_anlegen(db, daten, ueberschreiben_id)
            else:
                fehler_liste.append({"zeile": zeile_obj.zeile, "fehler": f"Unbekannter Typ: {ziel_typ}"})
                continue

            if result == "importiert":
                importiert += 1
            else:
                aktualisiert += 1

        except Exception as exc:
            fehler_liste.append({"zeile": zeile_obj.zeile, "fehler": str(exc)})

    db.commit()
    return ImportErgebnis(
        importiert=importiert,
        aktualisiert=aktualisiert,
        ignoriert=ignoriert,
        fehler=fehler_liste,
    )
