use std::sync::Mutex;
use tauri::Manager;
use tauri_plugin_shell::ShellExt;

/// Globaler State: der vom Sidecar belegte Port
struct BackendPort(Mutex<u16>);

/// IPC-Command: Frontend fragt den Backend-Port ab
#[tauri::command]
fn get_backend_port(state: tauri::State<BackendPort>) -> u16 {
    *state.0.lock().unwrap()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(
            tauri_plugin_log::Builder::default()
                .level(log::LevelFilter::Info)
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

            let (_rx, _child) = sidecar_cmd
                .spawn()
                .expect("Backend-Sidecar konnte nicht gestartet werden");

            log::info!("Backend-Sidecar gestartet auf Port {}", port);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .run(tauri::generate_context!())
        .expect("Fehler beim Starten der Tauri-Anwendung");
}
