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
    }

    app_lib::run();
}
