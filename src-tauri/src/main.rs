// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // Linux: Mesa 26.0.1 + AMD GPU → eglGetDisplay(EGL_DEFAULT_DISPLAY) = EGL_BAD_PARAMETER
    // WebKitWebProcess initialisiert EGL bedingungslos beim Start – BEVOR irgendwelche
    // WebKit-Flags (WEBKIT_DISABLE_DMABUF_RENDERER etc.) geprüft werden.
    //
    // Mesa wählt den EGL-Pfad anhand von Env-Vars:
    //   WAYLAND_DISPLAY gesetzt → Wayland-EGL  ← buggy auf AMD + Mesa 26
    //   WAYLAND_DISPLAY fehlt  → X11-EGL via DISPLAY=:0 ← funktioniert
    //
    // Beide müssen VOR gtk_init() gesetzt sein (= vor app_lib::run()).
    // KDE Plasma hat immer XWayland → DISPLAY=:0 ist gesetzt.
    #[cfg(target_os = "linux")]
    {
        std::env::set_var("GDK_BACKEND", "x11");
        std::env::remove_var("WAYLAND_DISPLAY");

        // EGL-Shim via LD_PRELOAD für WebKitWebProcess setzen.
        //
        // Das AppRun-Skript des AppImages überschreibt LD_PRELOAD mit seinem
        // eigenen libunionpreload.so – deshalb hier im Rust-Prozess neu setzen,
        // NACHDEM AppRun gelaufen ist. WebKitWebProcess erbt LD_PRELOAD als
        // Kindprozess und lädt den Shim beim Start.
        //
        // Der Shim fängt eglGetDisplay() ab: gibt die echte Implementierung
        // EGL_NO_DISPLAY zurück (AMD EACCES auf Fedora/Bazzite), liefert der
        // Shim einen Sentinel zurück → verhindert g_error() → WebKit fällt auf
        // Software-Compositing zurück.
        if let Ok(appdir) = std::env::var("APPDIR") {
            let shim = format!("{}/usr/lib/egl_shim.so", appdir);
            if std::path::Path::new(&shim).exists() {
                let current = std::env::var("LD_PRELOAD").unwrap_or_default();
                let new_preload = if current.is_empty() {
                    shim.clone()
                } else {
                    format!("{}:{}", shim, current)
                };
                std::env::set_var("LD_PRELOAD", &new_preload);
                eprintln!("[egl-shim] LD_PRELOAD gesetzt: {}", shim);
            }
        }
    }

    app_lib::run();
}
