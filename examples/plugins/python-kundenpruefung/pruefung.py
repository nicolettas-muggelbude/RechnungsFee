"""Fachlogik, die auch ohne Wasm-Toolchain mit normalem Python testbar ist."""
import json


def pruefe_kunde(payload_json: str) -> str:
    daten = json.loads(payload_json)
    if not isinstance(daten, dict) or daten.get('_schema') != 'customer@1':
        raise ValueError('Das Plugin erwartet einen Kunden im Format customer@1.')
    if not any(str(daten.get(feld) or '').strip() for feld in ('firmenname', 'vorname', 'nachname')):
        raise ValueError('Bitte gib einen Firmennamen oder einen Vor-/Nachnamen ein.')
    email = daten.get('email')
    if isinstance(email, str):
        # Nur das im Customer-DTO explizit änderbare E-Mail-Feld normalisieren.
        daten['email'] = email.strip()
    return json.dumps(daten, ensure_ascii=False)
