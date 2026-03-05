// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    // Linux: GDK_BACKEND=x11 MUSS vor GTK-Initialisierung gesetzt werden.
    // Tauri initialisiert GTK in run() → danach ignoriert GDK die Env-Var.
    // Hintergrund: Mesa 26.0.1 + AMD GPU → eglGetDisplay(EGL_DEFAULT_DISPLAY)
    // schlägt auf Wayland fehl (EGL_BAD_PARAMETER). X11-Backend nutzt GLX statt
    // EGL → kein eglGetDisplay-Aufruf → kein Crash. KDE Plasma hat immer XWayland.
    #[cfg(target_os = "linux")]
    std::env::set_var("GDK_BACKEND", "x11");

    app_lib::run();
}
