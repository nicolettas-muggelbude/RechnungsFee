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

/// IPC-Command: Frontend fragt den Backend-Port ab
#[tauri::command]
fn get_backend_port(state: tauri::State<BackendPort>) -> u16 {
    *state.0.lock().unwrap()
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
fn kill_backend_inner(child: CommandChild, port: u16, wait: bool) {
    #[cfg(target_os = "windows")]
    {
        let pid = child.pid();
        drop(child);

        let shutdown_url = format!("http://127.0.0.1:{}/api/shutdown", port);
        log::info!("Sende Shutdown-Request an {} (PID {})", shutdown_url, pid);

        if wait {
            // 1. Graceful: HTTP POST an /api/shutdown – curl.exe blockiert bis Antwort
            let status = std::process::Command::new("curl.exe")
                .args(["-s", "-m", "3", "-X", "POST", &shutdown_url])
                .creation_flags(CREATE_NO_WINDOW)
                .output();
            match &status {
                Ok(o) if o.status.success() => log::info!("Graceful shutdown OK"),
                _ => log::warn!("Graceful shutdown fehlgeschlagen – fahre mit taskkill fort"),
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
            let _ = std::process::Command::new("curl.exe")
                .args(["-s", "-m", "2", "-X", "POST", &shutdown_url])
                .creation_flags(CREATE_NO_WINDOW)
                .spawn();
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
            // 1. Graceful: HTTP POST an /api/shutdown
            let status = std::process::Command::new("curl")
                .args(["-s", "-m", "3", "-X", "POST", &shutdown_url])
                .output();
            match &status {
                Ok(o) if o.status.success() => log::info!("Graceful shutdown OK"),
                _ => log::warn!("Graceful shutdown fehlgeschlagen – fahre mit Kill fort"),
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
            let _ = std::process::Command::new("curl")
                .args(["-s", "-m", "2", "-X", "POST", &shutdown_url])
                .spawn();
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
fn kill_backend(child_state: tauri::State<BackendChild>, port_state: tauri::State<BackendPort>) {
    let port = *port_state.0.lock().unwrap();
    if let Some(child) = child_state.0.lock().unwrap().take() {
        kill_backend_inner(child, port, true);  // wait=true: blockiert bis Backend weg ist
    }
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
) {
    let port = *port_state.0.lock().unwrap();
    if let Some(child) = child_state.0.lock().unwrap().take() {
        kill_backend_inner(child, port, false);
    }
    // Fenster wird von JS nach diesem Return geschlossen
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
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
        .setup(|app| {
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

            let sidecar_cmd = app
                .shell()
                .sidecar("backend")
                .expect("Backend-Sidecar nicht gefunden")
                .args(["--port", &port.to_string()]);

            let (rx, child) = sidecar_cmd
                .spawn()
                .expect("Backend-Sidecar konnte nicht gestartet werden");

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
        .invoke_handler(tauri::generate_handler![get_backend_port, kill_backend, open_url, confirm_close, write_bytes_to_path])
        .build(tauri::generate_context!())
        .expect("Fehler beim Erstellen der Tauri-Anwendung")
        .run(|app_handle, event| {
            // Fallback: Falls CloseRequested nicht gefeuert hat (z.B. kein Hauptfenster)
            if let tauri::RunEvent::Exit = event {
                let port = *app_handle.state::<BackendPort>().0.lock().unwrap();
                if let Some(child) = app_handle.state::<BackendChild>().0.lock().unwrap().take() {
                    kill_backend_inner(child, port, false);  // non-blocking Fallback
                }
            }
        });
}
