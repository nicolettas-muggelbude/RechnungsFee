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

/// IPC-Command: Frontend beendet den Backend-Sidecar explizit (beim Schließen und vor Update-Exit).
/// PyInstaller --onefile startet auf Windows zwei Prozesse (Bootloader + Python-Child).
/// child.kill() beendet nur den Bootloader – /T killt den gesamten Prozessbaum.
#[tauri::command]
fn kill_backend(state: tauri::State<BackendChild>) {
    if let Some(child) = state.0.lock().unwrap().take() {
        #[cfg(target_os = "windows")]
        let pid = child.pid();

        let _ = child.kill();

        #[cfg(target_os = "windows")]
        {
            let _ = std::process::Command::new("taskkill")
                .args(["/F", "/T", "/PID", &pid.to_string()])
                .output();
            log::info!("Backend-Sidecar Prozessbaum (PID {}) per taskkill /T beendet", pid);
        }
        #[cfg(not(target_os = "windows"))]
        log::info!("Backend-Sidecar beendet");
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
            // Freien Port wählen
            let port = portpicker::pick_unused_port().expect("Kein freier Port gefunden");

            log::info!("Backend-Port: {}", port);

            // State registrieren, damit get_backend_port es lesen kann
            app.manage(BackendPort(Mutex::new(port)));

            // Sidecar starten
            let sidecar_cmd = app
                .shell()
                .sidecar("backend")
                .expect("Backend-Sidecar nicht gefunden")
                .args(["--port", &port.to_string()]);

            let (_rx, child) = sidecar_cmd
                .spawn()
                .expect("Backend-Sidecar konnte nicht gestartet werden");

            // Child-Handle speichern, damit er beim App-Exit sauber beendet wird
            app.manage(BackendChild(Mutex::new(Some(child))));

            log::info!("Backend-Sidecar gestartet auf Port {}", port);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_port, kill_backend])
        .build(tauri::generate_context!())
        .expect("Fehler beim Erstellen der Tauri-Anwendung")
        .run(|app_handle, event| {
            if let tauri::RunEvent::Exit = event {
                if let Some(child) = app_handle.state::<BackendChild>().0.lock().unwrap().take() {
                    #[cfg(target_os = "windows")]
                    let pid = child.pid();

                    let _ = child.kill();

                    #[cfg(target_os = "windows")]
                    {
                        let _ = std::process::Command::new("taskkill")
                            .args(["/F", "/T", "/PID", &pid.to_string()])
                            .output();
                        log::info!("Backend-Sidecar Prozessbaum (PID {}) per taskkill /T beendet", pid);
                    }
                    #[cfg(not(target_os = "windows"))]
                    log::info!("Backend-Sidecar beendet");
                }
            }
        });
}
