"""
Regressionstests Security-Audit F5 – das Backend nimmt keine Dateipfade über HTTP an.

Vorher: POST /api/rechnungen/analysieren-pfad und POST /api/bank-import/vorschau-pfad lasen jeden
Pfad aus dem Request – ein eingeschleustes Skript konnte so beliebige PDF-/XML-/CSV-Dateien des
Benutzers lesen, die Antwort verriet außerdem, ob eine Datei existiert, und enthielt den absoluten
Pfad der Temp-Kopie (temp_path). Jetzt liest Tauri gezogene Dateien selbst (nur Pfade aus dem
letzten echten Drop, lese_gedroppte_datei in src-tauri/src/lib.rs) und das Frontend lädt sie hoch.
"""
import main
from api.schemas_rechnungen import AnalyseResponse

_PFAD_FELDER = {"pfad", "path", "dateipfad", "datei_pfad", "file_path", "filepath"}


def _schema(openapi: dict, schema: dict) -> dict:
    ref = schema.get("$ref")
    if ref:
        return openapi["components"]["schemas"][ref.rsplit("/", 1)[-1]]
    return schema


def test_pfad_endpunkte_entfernt():
    pfade = main.app.openapi()["paths"]
    assert "/api/rechnungen/analysieren-pfad" not in pfade
    assert "/api/bank-import/vorschau-pfad" not in pfade


def test_kein_endpunkt_nimmt_dateipfad_an():
    """Kein Request-Body- oder Query-Feld darf einen Dateipfad entgegennehmen. Konfigurierte
    Backup-Ziele (backup_extern_pfad_1/2) sind bewusst ausgenommen: eigenes Feld der Stammdaten,
    kein Lesezugriff auf eine beliebige Datei im Request."""
    openapi = main.app.openapi()
    funde = []
    for pfad, methoden in openapi["paths"].items():
        for methode, op in methoden.items():
            for param in op.get("parameters", []):
                if param.get("name", "").lower() in _PFAD_FELDER:
                    funde.append(f"{methode.upper()} {pfad} ?{param['name']}")
            inhalt = op.get("requestBody", {}).get("content", {})
            for medientyp in inhalt.values():
                schema = _schema(openapi, medientyp.get("schema", {}))
                for feld in schema.get("properties", {}):
                    if feld.lower() in _PFAD_FELDER:
                        funde.append(f"{methode.upper()} {pfad} body.{feld}")
    assert funde == []


def test_analyse_antwort_ohne_absoluten_pfad():
    assert "temp_path" not in AnalyseResponse.model_fields
