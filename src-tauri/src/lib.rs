use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandChild;

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
/// PyInstaller --onefile startet auf Windows zwei Prozesse (Bootloader + Python-Child).
/// child.kill() tötet nur den Parent → Child läuft weiter.
/// Lösung: zuerst taskkill /F /T /PID (killt ganzen Baum), dann Handle droppen.
fn kill_backend_inner(child: CommandChild) {
    #[cfg(target_os = "windows")]
    {
        let pid = child.pid();
        // Handle freigeben OHNE kill() – taskkill übernimmt den ganzen Baum atomisch
        drop(child);
        let _ = std::process::Command::new("taskkill")
            .args(["/F", "/T", "/PID", &pid.to_string()])
            .spawn();  // spawn statt output – nicht auf Abschluss warten
        log::info!("Backend-Prozessbaum (PID {}) per taskkill /T beendet", pid);
    }
    #[cfg(not(target_os = "windows"))]
    {
        let _ = child.kill();
        log::info!("Backend-Sidecar beendet");
    }
}

/// IPC-Command: URL mit System-Standard-App öffnen (z.B. mailto:, https:)
#[tauri::command]
fn open_url(url: String, app: tauri::AppHandle) -> Result<(), String> {
    app.shell().open(&url, None).map_err(|e| e.to_string())
}

/// IPC-Command: wird vom Frontend beim Schließen und vor dem Update-Exit aufgerufen
#[tauri::command]
fn kill_backend(state: tauri::State<BackendChild>) {
    if let Some(child) = state.0.lock().unwrap().take() {
        kill_backend_inner(child);
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
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
            let port = portpicker::pick_unused_port().expect("Kein freier Port gefunden");
            log::info!("Backend-Port: {}", port);
            app.manage(BackendPort(Mutex::new(port)));

            let sidecar_cmd = app
                .shell()
                .sidecar("backend")
                .expect("Backend-Sidecar nicht gefunden")
                .args(["--port", &port.to_string()]);

            let (_rx, child) = sidecar_cmd
                .spawn()
                .expect("Backend-Sidecar konnte nicht gestartet werden");

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
                log::info!("GDK_BACKEND=x11 + WEBKIT_DISABLE_DMABUF_RENDERER=1 gesetzt");
            }

            // Hauptfenster programmatisch erstellen.
            // Schlüssel: Fenster wird IN setup() erstellt, NICHT aus tauri.conf.json.
            let main_window = tauri::WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::App("index.html".into()),
            )
            .title("RechnungsFee")
            .inner_size(1280.0, 800.0)
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

            // Backend beim Schließen des Hauptfensters synchron beenden.
            // CloseRequested feuert zuverlässiger als RunEvent::Exit und
            // vermeidet Race-Conditions mit shell.open() (PDF-Links).
            let ah = app.handle().clone();
            main_window.on_window_event(move |event| {
                if let tauri::WindowEvent::CloseRequested { .. } = event {
                    if let Some(child) = ah.state::<BackendChild>().0.lock().unwrap().take() {
                        kill_backend_inner(child);
                    }
                }
            });

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_port, kill_backend, open_url])
        .build(tauri::generate_context!())
        .expect("Fehler beim Erstellen der Tauri-Anwendung")
        .run(|app_handle, event| {
            // Fallback: Falls CloseRequested nicht gefeuert hat (z.B. kein Hauptfenster)
            if let tauri::RunEvent::Exit = event {
                if let Some(child) = app_handle.state::<BackendChild>().0.lock().unwrap().take() {
                    kill_backend_inner(child);
                }
            }
        });
}
