use std::sync::Mutex;
use tauri::{Emitter, Manager};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

/// Globaler State: der vom Sidecar belegte Port
struct BackendPort(Mutex<u16>);

/// Globaler State: Handle des laufenden Sidecar-Prozesses
struct BackendChild(Mutex<Option<CommandChild>>);

/// Globaler State: Sitzungstoken für die lokale API (Security-Audit F4 Teil 2).
///
/// Pro App-Start 32 Zufallsbytes aus dem Zufallsgenerator des Betriebssystems, hex-kodiert.
/// Der Sidecar bekommt es über stdin (nicht über argv – die Kommandozeile ist per `ps` für
/// alle Benutzer sichtbar), das Hauptfenster per IPC (`get_backend_token`). Jeder API-Request
/// schickt es als `Authorization: Bearer <token>` mit. Bewusst kein JWT: ein Aussteller,
/// ein Prüfer, keine Claims – ein Zufallstoken ist einfacher und hat weniger Fallstricke.
struct BackendToken(String);

fn neues_sitzungstoken() -> String {
    let mut bytes = [0u8; 32];
    getrandom::getrandom(&mut bytes).expect("Zufallsgenerator des Betriebssystems nicht verfügbar");
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

/// POST /api/shutdown mit Sitzungstoken – direkt über TCP statt per curl, damit das Token
/// nicht in der Kommandozeile eines Hilfsprozesses auftaucht (dort für alle Benutzer sichtbar).
/// Liefert true bei HTTP 200.
fn sende_shutdown(port: u16, token: &str, timeout: std::time::Duration) -> bool {
    use std::io::{Read, Write};
    let addr = std::net::SocketAddr::from(([127, 0, 0, 1], port));
    let mut stream = match std::net::TcpStream::connect_timeout(&addr, timeout) {
        Ok(s) => s,
        Err(_) => return false,
    };
    let _ = stream.set_read_timeout(Some(timeout));
    let _ = stream.set_write_timeout(Some(timeout));
    let anfrage = format!(
        "POST /api/shutdown HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nAuthorization: Bearer {}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
        port, token
    );
    if stream.write_all(anfrage.as_bytes()).is_err() {
        return false;
    }
    let mut puffer = [0u8; 32];
    match stream.read(&mut puffer) {
        Ok(n) if n > 0 => {
            let antwort = String::from_utf8_lossy(&puffer[..n]);
            antwort.starts_with("HTTP/1.1 200") || antwort.starts_with("HTTP/1.0 200")
        }
        _ => false,
    }
}

/// IPC-Command: Frontend fragt den Backend-Port ab
#[tauri::command]
fn get_backend_port(state: tauri::State<BackendPort>) -> u16 {
    *state.0.lock().unwrap()
}

/// IPC-Command: Frontend holt das Sitzungstoken (nur Fenster „main“ hat IPC-Rechte,
/// siehe capabilities/default.json – PDF-Fenster bekommen es nicht).
#[tauri::command]
fn get_backend_token(state: tauri::State<BackendToken>) -> String {
    state.0.clone()
}

/// Backend-Prozessbaum beenden.
///
/// Wichtig: Das Sidecar wird mit PyInstaller `--onefile` gebaut. Auf Linux/macOS
/// forkt der Onefile-Bootloader beim Start einen Kindprozess (das eigentliche
/// uvicorn) und wartet darauf – die von Tauri gehaltene PID ist die des
/// Bootloaders, NICHT die des Kindes. Ein simples `child.kill()` beendet daher
/// nur den Bootloader; das geforkte uvicorn bleibt als verwaister Prozess im
/// Task-Manager zurück (Issue: Zombie-Backend nach Beenden unter Linux).
///
/// Strategie (alle Plattformen):
///   1. POST /api/shutdown  → uvicorn beendet sich selbst sauber (Handles frei);
///      auf Linux/macOS beendet sich dadurch auch der wartende Bootloader.
///   2. 1,5 s warten – uvicorn + Bootloader beenden sich in der Regel in < 300 ms
///   3. Fallback falls noch alive:
///      - Windows: taskkill /F /T /PID (Tree-Kill)
///      - Linux/macOS: pkill -9 -P <bootloader-pid> (geforktes Kind) + kill -9 <pid> (Bootloader)
///
/// wait=true  → blockiert komplett (IPC vor exit(0), NSIS wartet)
/// wait=false → non-blocking (CloseRequested / RunEvent::Exit)
fn kill_backend_inner(child: CommandChild, port: u16, token: String, wait: bool) {
    #[cfg(target_os = "windows")]
    {
        let pid = child.pid();
        drop(child);

        let shutdown_url = format!("http://127.0.0.1:{}/api/shutdown", port);
        log::info!("Sende Shutdown-Request an {} (PID {})", shutdown_url, pid);

        if wait {
            // 1. Graceful: HTTP POST an /api/shutdown – blockiert bis Antwort (max. 3 s)
            if sende_shutdown(port, &token, std::time::Duration::from_secs(3)) {
                log::info!("Graceful shutdown OK");
            } else {
                log::warn!("Graceful shutdown fehlgeschlagen – fahre mit taskkill fort");
            }

            // 2. Kurz warten: Prozess beendet sich nach /shutdown selbst
            std::thread::sleep(std::time::Duration::from_millis(1500));

            // 3. Fallback: taskkill falls noch alive
            let _ = std::process::Command::new("taskkill")
                .args(["/F", "/T", "/PID", &pid.to_string()])
                .creation_flags(CREATE_NO_WINDOW)
                .output();

            log::info!("Backend (PID {}) beendet (wait=true)", pid);
        } else {
            // Non-blocking: Shutdown-Request feuern und nicht warten
            std::thread::spawn(move || {
                sende_shutdown(port, &token, std::time::Duration::from_secs(2));
            });
            let _ = std::process::Command::new("taskkill")
                .args(["/F", "/T", "/PID", &pid.to_string()])
                .creation_flags(CREATE_NO_WINDOW)
                .spawn();
            log::info!("Backend (PID {}) beendet (wait=false)", pid);
        }
    }
    #[cfg(not(target_os = "windows"))]
    {
        let pid = child.pid();
        drop(child);

        let shutdown_url = format!("http://127.0.0.1:{}/api/shutdown", port);
        log::info!("Sende Shutdown-Request an {} (PID {})", shutdown_url, pid);

        if wait {
            // 1. Graceful: HTTP POST an /api/shutdown (max. 3 s)
            if sende_shutdown(port, &token, std::time::Duration::from_secs(3)) {
                log::info!("Graceful shutdown OK");
            } else {
                log::warn!("Graceful shutdown fehlgeschlagen – fahre mit Kill fort");
            }

            // 2. Kurz warten: Bootloader beendet sich nach /shutdown selbst (wartet auf sein Kind)
            std::thread::sleep(std::time::Duration::from_millis(1500));

            // 3. Fallback: geforktes uvicorn-Kind + Bootloader selbst hart beenden falls noch alive
            let _ = std::process::Command::new("pkill")
                .args(["-9", "-P", &pid.to_string()])
                .output();
            let _ = std::process::Command::new("kill")
                .args(["-9", &pid.to_string()])
                .output();

            log::info!("Backend (PID {}) beendet (wait=true)", pid);
        } else {
            // Non-blocking: Shutdown-Request feuern und nicht warten
            std::thread::spawn(move || {
                sende_shutdown(port, &token, std::time::Duration::from_secs(2));
            });
            let _ = std::process::Command::new("pkill")
                .args(["-9", "-P", &pid.to_string()])
                .spawn();
            let _ = std::process::Command::new("kill")
                .args(["-9", &pid.to_string()])
                .spawn();
            log::info!("Backend (PID {}) beendet (wait=false)", pid);
        }
    }
}

/// IPC-Command: URL mit System-Standard-App öffnen (z.B. mailto:, https:)
#[tauri::command]
fn open_url(url: String, app: tauri::AppHandle) -> Result<(), String> {
    app.shell().open(&url, None).map_err(|e| e.to_string())
}

/// IPC-Command: vom Frontend vor exit(0) aufgerufen – wartet bis Backend wirklich beendet ist
#[tauri::command]
fn kill_backend(
    child_state: tauri::State<BackendChild>,
    port_state: tauri::State<BackendPort>,
    token_state: tauri::State<BackendToken>,
) {
    let port = *port_state.0.lock().unwrap();
    if let Some(child) = child_state.0.lock().unwrap().take() {
        kill_backend_inner(child, port, token_state.0.clone(), true);  // wait=true: blockiert bis Backend weg ist
    }
}

/// Globaler State: Pfade des letzten Drag & Drop ins Fenster (Security-Audit F5).
///
/// Das Backend nimmt keine Dateipfade mehr an. Gezogene Dateien liest Tauri selbst
/// (`lese_gedroppte_datei`) und das Frontend lädt sie hoch wie eine ausgewählte Datei.
/// Gelesen wird nur, was der Benutzer gerade wirklich ins Fenster gezogen hat – ein
/// eingeschleustes Skript kann damit keine beliebigen Dateien von der Platte holen.
struct GedropptePfade(Mutex<Vec<std::path::PathBuf>>);

/// Dateiendungen, die ein Drop-Import verarbeitet (Rechnungsimport: pdf/xml, Bank-Import: csv/txt/xml/zip).
const DROP_ENDUNGEN: [&str; 5] = ["pdf", "xml", "csv", "txt", "zip"];
/// Wie MAX_UPLOAD im Backend (utils/sicherheit_middleware.py).
const DROP_MAX_BYTES: u64 = 500 * 1024 * 1024;

/// IPC-Command: Datei aus dem letzten Drag & Drop lesen (Inhalt als ArrayBuffer ans Frontend).
#[tauri::command]
fn lese_gedroppte_datei(
    pfad: String,
    state: tauri::State<GedropptePfade>,
) -> Result<tauri::ipc::Response, String> {
    let pfad = std::path::PathBuf::from(pfad);
    if !state.0.lock().unwrap().iter().any(|p| p == &pfad) {
        return Err("Diese Datei wurde nicht in die App gezogen.".into());
    }
    let endung = pfad
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.to_ascii_lowercase())
        .unwrap_or_default();
    if !DROP_ENDUNGEN.contains(&endung.as_str()) {
        return Err("Dieser Dateityp wird hier nicht unterstützt.".into());
    }
    let meta = std::fs::metadata(&pfad).map_err(|e| format!("Datei nicht gefunden: {e}"))?;
    if !meta.is_file() {
        return Err("Das ist keine Datei.".into());
    }
    if meta.len() > DROP_MAX_BYTES {
        return Err("Die Datei ist zu groß.".into());
    }
    let daten = std::fs::read(&pfad).map_err(|e| format!("Datei konnte nicht gelesen werden: {e}"))?;
    Ok(tauri::ipc::Response::new(daten))
}

/// IPC-Command: User hat Schließen bestätigt – Backend beenden und Fenster schließen
#[tauri::command]
fn write_bytes_to_path(path: String, data: Vec<u8>) -> Result<(), String> {
    std::fs::write(&path, &data).map_err(|e| e.to_string())
}

#[tauri::command]
fn confirm_close(
    child_state: tauri::State<BackendChild>,
    port_state: tauri::State<BackendPort>,
    token_state: tauri::State<BackendToken>,
) {
    let port = *port_state.0.lock().unwrap();
    if let Some(child) = child_state.0.lock().unwrap().take() {
        kill_backend_inner(child, port, token_state.0.clone(), false);
    }
    // Fenster wird von JS nach diesem Return geschlossen
}

/// Issue #543: Das AppImage bringt kein eigenes GTK mit (GTK, GIO, gdk-pixbuf kommen vom
/// System), der AppRun-Hook von linuxdeploy-plugin-gtk lenkt die Modulpfade aber trotzdem in
/// nicht vorhandene Ordner im AppImage um. Folge u. a.: GTK findet die Druckmodule
/// (printbackends) nicht, der Druckdialog zeigt keine Drucker. Entfernt werden nur Variablen,
/// deren Ziel fehlt – liefert ein späterer Build GTK doch mit, bleibt alles unverändert.
/// Muss vor dem Start von GTK laufen. Rückgabe: entfernte Variablen (fürs Protokoll).
#[cfg(target_os = "linux")]
fn bereinige_appimage_gtk_umgebung() -> Vec<String> {
    let mut entfernt = Vec::new();
    if std::env::var_os("APPIMAGE").is_none() {
        return entfernt;
    }
    // (Variable, Unterpfad, der vorhanden sein muss)
    let pruefungen = [
        ("GTK_PATH", ""),
        ("GTK_EXE_PREFIX", "lib/gtk-3.0"),
        ("GTK_IM_MODULE_FILE", ""),
        ("GDK_PIXBUF_MODULE_FILE", ""),
        ("GIO_MODULE_DIR", ""),
        ("GI_TYPELIB_PATH", ""),
    ];
    for (var, unterpfad) in pruefungen {
        let Some(wert) = std::env::var_os(var) else { continue };
        let vorhanden = std::env::split_paths(&wert)
            .any(|p| !p.as_os_str().is_empty() && p.join(unterpfad).exists());
        if !vorhanden {
            std::env::remove_var(var);
            entfernt.push(format!("{var}={}", wert.to_string_lossy()));
        }
    }
    entfernt
}

/// Issue #544: Dateiname für „Speichern“ im PDF-Fenster. Die URL trägt ihn seit #476 als
/// `…/_datei/<Name>`; WebKitGTK schlägt trotzdem „document.pdf“ vor.
#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
fn pdf_dateiname_aus_url(url: &tauri::Url) -> String {
    let segmente: Vec<&str> = url.path_segments().map(|s| s.collect()).unwrap_or_default();
    let roh = segmente
        .iter()
        .position(|s| *s == "_datei")
        .and_then(|i| segmente.get(i + 1))
        .copied()
        .unwrap_or("");
    // Prozent-Kodierung auflösen (Umlaute, Leerzeichen)
    let bytes = roh.as_bytes();
    let mut dekodiert = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' && i + 2 < bytes.len() {
            if let Ok(b) = u8::from_str_radix(std::str::from_utf8(&bytes[i + 1..i + 3]).unwrap_or(""), 16) {
                dekodiert.push(b);
                i += 3;
                continue;
            }
        }
        dekodiert.push(bytes[i]);
        i += 1;
    }
    let name: String = String::from_utf8_lossy(&dekodiert)
        .chars()
        .map(|c| if matches!(c, '/' | '\\') || c.is_control() { '_' } else { c })
        .collect();
    let name = name.trim().trim_start_matches('.').to_string();
    if name.is_empty() {
        return "Dokument.pdf".into();
    }
    if name.to_ascii_lowercase().ends_with(".pdf") { name } else { format!("{name}.pdf") }
}

/// Freier Dateipfad im Ordner: „Name.pdf“, sonst „Name (2).pdf“, „Name (3).pdf“ …
#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
fn freier_pfad(ordner: &std::path::Path, dateiname: &str) -> std::path::PathBuf {
    let kandidat = ordner.join(dateiname);
    if !kandidat.exists() {
        return kandidat;
    }
    let pfad = std::path::Path::new(dateiname);
    let stamm = pfad.file_stem().and_then(|s| s.to_str()).unwrap_or("Dokument");
    let endung = pfad.extension().and_then(|s| s.to_str()).map(|e| format!(".{e}")).unwrap_or_default();
    (2..)
        .map(|n| ordner.join(format!("{stamm} ({n}){endung}")))
        .find(|p| !p.exists())
        .unwrap()
}

/// Issue #544: Download aus dem PDF-Fenster (Speichern-Symbol des Betrachters) unter Linux.
/// Ohne Handler speicherte WebKitGTK still als „document.pdf“ in den Download- oder sogar den
/// Startordner, ohne jede Rückmeldung. Jetzt: Download-Ordner, sprechender Name, Hinweis.
/// (Windows/WebView2 zeigt einen eigenen Speichern-Dialog – dort kein Handler.)
#[cfg(target_os = "linux")]
fn pdf_download(webview: tauri::Webview, event: tauri::webview::DownloadEvent<'_>) -> bool {
    use tauri::webview::DownloadEvent;
    use tauri_plugin_dialog::{DialogExt, MessageDialogKind};
    let app = webview.app_handle();
    let ordner = || {
        app.path()
            .download_dir()
            .ok()
            .filter(|p| p.is_dir())
            .or_else(|| app.path().home_dir().ok())
            .unwrap_or_else(std::env::temp_dir)
    };
    match event {
        // Greift nicht immer: beim Speichern-Symbol des PDF-Betrachters legt WebKitGTK das Ziel
        // selbst fest (Startordner, „document.pdf“) – dann korrigiert der Finished-Zweig.
        DownloadEvent::Requested { url, destination } => {
            *destination = freier_pfad(&ordner(), &pdf_dateiname_aus_url(&url));
            log::info!("PDF speichern: Ziel {}", destination.display());
            true
        }
        DownloadEvent::Finished { url, path, success } => {
            // Der Betrachter speichert oft aus seinem Speicher (Adresse ohne …/_datei/<Name>) –
            // dann trägt die Adresse des Fensters den Namen, über sie wurde das PDF geöffnet.
            let fenster_url = webview.url().ok();
            log::info!(
                "PDF speichern: Download {url}, Fenster {}",
                fenster_url.as_ref().map(|u| u.as_str()).unwrap_or("-")
            );
            let mut name = pdf_dateiname_aus_url(&url);
            if name == "Dokument.pdf" {
                if let Some(f) = &fenster_url {
                    name = pdf_dateiname_aus_url(f);
                }
            }
            let endpfad = match (success, path) {
                (true, Some(p)) => Some(verschiebe_download(&p, &ordner(), &name)),
                _ => None,
            };
            let (text, art) = match (success, &endpfad) {
                (true, Some(p)) => (format!("Gespeichert unter:\n{}", p.display()), MessageDialogKind::Info),
                (true, None) => ("Die Datei wurde gespeichert.".to_string(), MessageDialogKind::Info),
                _ => ("Die Datei konnte nicht gespeichert werden.".to_string(), MessageDialogKind::Error),
            };
            log::info!("PDF speichern: {text}");
            app.dialog().message(text).title("PDF speichern").kind(art).show(|_| {});
            true
        }
        _ => true,
    }
}

/// Fertigen Download in den Zielordner unter dem gewünschten Namen bringen, falls WebKitGTK ihn
/// woanders bzw. als „document.pdf“ abgelegt hat. Liegt er schon richtig oder schlägt das
/// Verschieben fehl, bleibt er, wo er ist (Rückgabe: tatsächlicher Ort).
#[cfg_attr(not(target_os = "linux"), allow(dead_code))]
fn verschiebe_download(ist: &std::path::Path, ordner: &std::path::Path, dateiname: &str) -> std::path::PathBuf {
    if ist.parent() == Some(ordner) && ist.file_name().and_then(|n| n.to_str()) == Some(dateiname) {
        return ist.to_path_buf();
    }
    let ziel = freier_pfad(ordner, dateiname);
    let ok = std::fs::rename(ist, &ziel).is_ok()
        // anderes Dateisystem: kopieren und Original entfernen
        || (std::fs::copy(ist, &ziel).is_ok() && std::fs::remove_file(ist).is_ok());
    if ok { ziel } else { ist.to_path_buf() }
}

/// IPC-Command: PDF/Dokument des lokalen Backends in eigenem Fenster öffnen (Issue #544).
/// Bisher per `new WebviewWindow()` im Frontend – dort lässt sich kein Download-Handler setzen.
/// Nur Adressen des eigenen Backends (127.0.0.1/localhost). `async`: Fenster aus einem
/// synchronen Command zu erzeugen, kann unter Windows hängen bleiben.
#[tauri::command]
async fn oeffne_pdf_fenster(app: tauri::AppHandle, url: String, titel: String) -> Result<(), String> {
    let ziel: tauri::Url = url.parse().map_err(|_| format!("Ungültige Adresse: {url}"))?;
    if ziel.scheme() != "http" || !matches!(ziel.host_str(), Some("127.0.0.1") | Some("localhost")) {
        return Err("Nur Dokumente des lokalen Backends können so geöffnet werden.".into());
    }
    let label = format!(
        "pdf-{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or_default()
    );
    let fenster = tauri::WebviewWindowBuilder::new(&app, label, tauri::WebviewUrl::External(ziel))
        .title(titel)
        .inner_size(960.0, 800.0)
        .center()
        .resizable(true);
    #[cfg(target_os = "linux")]
    let fenster = fenster.on_download(pdf_download);
    fenster.build().map_err(|e| e.to_string())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{freier_pfad, pdf_dateiname_aus_url, verschiebe_download};

    #[test]
    fn download_wird_umbenannt_und_verschoben() {
        let basis = std::env::temp_dir().join(format!("rf-dl-{}", std::process::id()));
        let start = basis.join("start");
        let ziel = basis.join("ziel");
        std::fs::create_dir_all(&start).unwrap();
        std::fs::create_dir_all(&ziel).unwrap();
        let doc = start.join("document.pdf");
        std::fs::write(&doc, b"%PDF").unwrap();
        let ende = verschiebe_download(&doc, &ziel, "Rechnung_RE-1.pdf");
        assert_eq!(ende, ziel.join("Rechnung_RE-1.pdf"));
        assert!(!doc.exists() && ende.exists());
        // schon richtig: bleibt
        assert_eq!(verschiebe_download(&ende, &ziel, "Rechnung_RE-1.pdf"), ende);
        // zweite Datei gleichen Namens wird nummeriert
        std::fs::write(&doc, b"%PDF").unwrap();
        assert_eq!(verschiebe_download(&doc, &ziel, "Rechnung_RE-1.pdf"), ziel.join("Rechnung_RE-1 (2).pdf"));
        std::fs::remove_dir_all(&basis).unwrap();
    }

    fn name(url: &str) -> String {
        pdf_dateiname_aus_url(&url.parse().unwrap())
    }

    #[test]
    fn dateiname_aus_der_adresse() {
        assert_eq!(name("http://127.0.0.1:8002/api/rechnungen/201/pdf/_datei/Rechnung_RE-260139.pdf"), "Rechnung_RE-260139.pdf");
        assert_eq!(name("http://127.0.0.1:8002/api/mahnwesen/6/pdf/_datei/MHN-260038.pdf?nur_ansehen=true"), "MHN-260038.pdf");
        assert_eq!(name("http://127.0.0.1:8002/api/euer/pdf/_datei/E%C3%9CR_2026?jahr=2026"), "EÜR_2026.pdf");
        assert_eq!(name("http://127.0.0.1:8002/api/x/_datei/..%2F..%2Fgeheim.pdf"), "_.._geheim.pdf");
        assert_eq!(name("http://127.0.0.1:8002/api/rechnungen/201/pdf"), "Dokument.pdf");
        assert_eq!(name("http://127.0.0.1:8002/api/rechnungen/201/pdf/_datei/"), "Dokument.pdf");
    }

    #[test]
    fn freier_pfad_nummeriert() {
        let ordner = std::env::temp_dir().join(format!("rf-test-{}", std::process::id()));
        std::fs::create_dir_all(&ordner).unwrap();
        assert_eq!(freier_pfad(&ordner, "A.pdf"), ordner.join("A.pdf"));
        std::fs::write(ordner.join("A.pdf"), b"x").unwrap();
        assert_eq!(freier_pfad(&ordner, "A.pdf"), ordner.join("A (2).pdf"));
        std::fs::write(ordner.join("A (2).pdf"), b"x").unwrap();
        assert_eq!(freier_pfad(&ordner, "A.pdf"), ordner.join("A (3).pdf"));
        std::fs::remove_dir_all(&ordner).unwrap();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    #[cfg(target_os = "linux")]
    let gtk_entfernt = bereinige_appimage_gtk_umgebung();
    #[cfg(not(target_os = "linux"))]
    let gtk_entfernt: Vec<String> = Vec::new();

    tauri::Builder::default()
        .manage(GedropptePfade(Mutex::new(Vec::new())))
        // F5: gezogene Pfade merken, bevor das Frontend sie per lese_gedroppte_datei anfragt
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::DragDrop(tauri::DragDropEvent::Drop { paths, .. }) = event {
                *window.state::<GedropptePfade>().0.lock().unwrap() = paths.clone();
            }
        })
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
                .target(tauri_plugin_log::Target::new(
                    tauri_plugin_log::TargetKind::LogDir { file_name: Some("rechnungsfee".into()) },
                ))
                .target(tauri_plugin_log::Target::new(
                    tauri_plugin_log::TargetKind::Stdout,
                ))
                .build(),
        )
        .setup(move |app| {
            for eintrag in &gtk_entfernt {
                log::info!("AppImage: GTK-Umgebungsvariable ohne Ziel entfernt (Issue #543): {eintrag}");
            }

            // Zombie-Backend vom letzten Absturz ODER von einem Update-Relaunch-Race
            // killen, bevor ein neues gestartet wird. Schützt vor DB-Schreibsperren
            // (Issue #268: manchmal läuft nach Update+Neustart noch ein altes Backend,
            // beide konkurrieren kurz um dieselbe SQLite-Datei → Start hängt).
            //
            // Wichtig: Ein einfaches "kill und weiter" reicht nicht – taskkill/pkill
            // kehren zurück sobald das Signal geschickt wurde, nicht erst wenn der
            // Prozess wirklich beendet ist. Daher kurz nachprüfen (max. 2 s).
            #[cfg(target_os = "windows")]
            {
                let _ = std::process::Command::new("taskkill")
                    .args(["/F", "/IM", "backend.exe"])
                    .creation_flags(CREATE_NO_WINDOW)
                    .output();
                for _ in 0..20 {
                    let laeuft_noch = std::process::Command::new("tasklist")
                        .args(["/FI", "IMAGENAME eq backend.exe", "/NH"])
                        .creation_flags(CREATE_NO_WINDOW)
                        .output()
                        .map(|o| String::from_utf8_lossy(&o.stdout).to_lowercase().contains("backend.exe"))
                        .unwrap_or(false);
                    if !laeuft_noch { break; }
                    std::thread::sleep(std::time::Duration::from_millis(100));
                }
            }
            #[cfg(target_os = "linux")]
            {
                // Zombie-Backends killen – Muster passt für:
                //   AppImage:  /tmp/.mount_*/usr/bin/backend-x86_64-unknown-linux-gnu
                //   Dev-Modus: .../src-tauri/binaries/backend-x86_64-unknown-linux-gnu
                // -9 (SIGKILL) statt Default-SIGTERM, damit nicht auf ein evtl.
                // ignoriertes/verzögertes Signal-Handling gewartet werden muss.
                let muster = "backend-x86_64-unknown-linux-gnu";
                let _ = std::process::Command::new("pkill").args(["-9", "-f", muster]).output();
                for _ in 0..20 {
                    let laeuft_noch = std::process::Command::new("pgrep").args(["-f", muster])
                        .output().map(|o| o.status.success()).unwrap_or(false);
                    if !laeuft_noch { break; }
                    std::thread::sleep(std::time::Duration::from_millis(100));
                }
            }
            #[cfg(target_os = "macos")]
            {
                // Bisher fehlte diese Bereinigung auf macOS komplett (Issue #268).
                // Muster passt für backend-aarch64-apple-darwin / backend-x86_64-apple-darwin.
                let muster = "backend-.*-apple-darwin";
                let _ = std::process::Command::new("pkill").args(["-9", "-f", muster]).output();
                for _ in 0..20 {
                    let laeuft_noch = std::process::Command::new("pgrep").args(["-f", muster])
                        .output().map(|o| o.status.success()).unwrap_or(false);
                    if !laeuft_noch { break; }
                    std::thread::sleep(std::time::Duration::from_millis(100));
                }
            }

            let port = portpicker::pick_unused_port().expect("Kein freier Port gefunden");
            log::info!("Backend-Port: {}", port);
            app.manage(BackendPort(Mutex::new(port)));

            let token = neues_sitzungstoken();
            app.manage(BackendToken(token.clone()));

            let sidecar_cmd = app
                .shell()
                .sidecar("backend")
                .expect("Backend-Sidecar nicht gefunden")
                .args(["--port", &port.to_string(), "--token-stdin"]);

            let (rx, mut child) = sidecar_cmd
                .spawn()
                .expect("Backend-Sidecar konnte nicht gestartet werden");

            // Token als erste Zeile über stdin – der Sidecar liest es vor dem Start von uvicorn.
            child
                .write(format!("{}\n", token).as_bytes())
                .expect("Sitzungstoken konnte nicht an den Sidecar übergeben werden");

            // Backend-Output in separatem Task loggen – so sehen wir Crashes und Fehler
            tauri::async_runtime::spawn(async move {
                let mut rx = rx;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(bytes) => {
                            log::info!("[Backend] {}", String::from_utf8_lossy(&bytes).trim_end());
                        }
                        CommandEvent::Stderr(bytes) => {
                            log::warn!("[Backend] {}", String::from_utf8_lossy(&bytes).trim_end());
                        }
                        CommandEvent::Error(e) => {
                            log::error!("[Backend] Fehler: {}", e);
                        }
                        CommandEvent::Terminated(payload) => {
                            log::warn!(
                                "[Backend] Prozess beendet – Exit-Code: {:?}, Signal: {:?}",
                                payload.code,
                                payload.signal
                            );
                        }
                        _ => {}
                    }
                }
            });

            app.manage(BackendChild(Mutex::new(Some(child))));

            log::info!("Backend-Sidecar gestartet auf Port {}", port);

            // Linux: Sandbox + EGL deaktivieren BEVOR das Fenster erstellt wird.
            //
            // Problem: WebKit initialisiert EGL im Content-Prozess beim Start für
            // Platform-Detection und DMA-Buffer-Support – UNABHÄNGIG von
            // HardwareAccelerationPolicy::Never. Auf AMD + Mesa 26.0.1 schlägt
            // eglGetDisplay(EGL_DEFAULT_DISPLAY) mit EGL_BAD_PARAMETER fehl.
            //
            // Zwei Ursachen möglich:
            // (A) WebKit-Sandbox blockiert DRM-Device-Zugriff → EGL_BAD_PARAMETER statt
            //     graceful fallback → set_sandbox_enabled(false) behebt das.
            // (B) WebKit initialisiert DMA-Buffer-Renderer → WEBKIT_DISABLE_DMABUF_RENDERER=1
            //     verhindert den EGL-Aufruf im Content-Prozess.
            #[cfg(target_os = "linux")]
            {
                use webkit2gtk::{WebContext, WebContextExt};
                // (A) Sandbox deaktivieren
                if let Some(ctx) = WebContext::default() {
                    ctx.set_sandbox_enabled(false);
                }
                log::info!("WebKit-Sandbox deaktiviert (EGL-Fix)");
                // (B) GDK_BACKEND=x11 – GDK im Content-Prozess nutzt X11/GLX statt
                //     Wayland/EGL. Der Crash passiert in GDK's EGL-Init (nicht in
                //     WebKit's DMABuf-Code), daher greifen WEBKIT_DISABLE_*-Vars nicht.
                //     GDK im Parent ist bereits initialisiert → Env-Var hat dort keine
                //     Wirkung, wird aber vom Content-Prozess beim Start geerbt.
                //     KDE Plasma hat immer XWayland → DISPLAY ist gesetzt.
                std::env::set_var("GDK_BACKEND", "x11");
                // DMA-Buffer-Renderer zusätzlich deaktivieren (belt-and-suspenders)
                std::env::set_var("WEBKIT_DISABLE_DMABUF_RENDERER", "1");
                // webkit2gtk 2.46+ (Ubuntu 26.04) führt separaten Compositing-Prozess ein
                // der auf manchen Systemen crasht → WEBKIT_DISABLE_COMPOSITING_MODE=1 behebt das
                std::env::set_var("WEBKIT_DISABLE_COMPOSITING_MODE", "1");
                log::info!("GDK_BACKEND=x11 + WEBKIT_DISABLE_DMABUF_RENDERER=1 + WEBKIT_DISABLE_COMPOSITING_MODE=1 gesetzt");
            }

            // Hauptfenster programmatisch erstellen.
            // Schlüssel: Fenster wird IN setup() erstellt, NICHT aus tauri.conf.json.
            let main_window = tauri::WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::App("index.html".into()),
            )
            .title("RechnungsFee")
            .inner_size(1548.0, 904.0)
            .min_inner_size(900.0, 600.0)
            .resizable(true)
            .build()
            .expect("Hauptfenster konnte nicht erstellt werden");

            // Linux: HardwareAccelerationPolicy::Never sofort nach Fenstererstellung setzen.
            // glib::MainContext::invoke() läuft synchron wenn wir bereits auf dem Main-Thread
            // sind (was in setup() der Fall ist) → Closure vor URL-Load garantiert.
            #[cfg(target_os = "linux")]
            {
                use webkit2gtk::{SettingsExt, WebViewExt};
                let _ = main_window.with_webview(|wv| {
                    if let Some(settings) = wv.inner().settings() {
                        settings.set_hardware_acceleration_policy(
                            webkit2gtk::HardwareAccelerationPolicy::Never,
                        );
                        log::info!("WebKit HardwareAccelerationPolicy::Never gesetzt");
                    }
                });
            }

            // Gespeicherte Fenstergröße/-position wiederherstellen.
            use tauri_plugin_window_state::{WindowExt, StateFlags};
            let _ = main_window.restore_state(StateFlags::all());

            // Schließen wird vollständig vom JS-seitigen onCloseRequested behandelt.

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_port, get_backend_token, kill_backend, open_url, confirm_close, write_bytes_to_path, oeffne_pdf_fenster, lese_gedroppte_datei])
        .build(tauri::generate_context!())
        .expect("Fehler beim Erstellen der Tauri-Anwendung")
        .run(|app_handle, event| {
            // Fallback: Falls CloseRequested nicht gefeuert hat (z.B. kein Hauptfenster)
            if let tauri::RunEvent::Exit = event {
                let port = *app_handle.state::<BackendPort>().0.lock().unwrap();
                let token = app_handle.state::<BackendToken>().0.clone();
                if let Some(child) = app_handle.state::<BackendChild>().0.lock().unwrap().take() {
                    kill_backend_inner(child, port, token, false);  // non-blocking Fallback
                }
            }
        });
}
