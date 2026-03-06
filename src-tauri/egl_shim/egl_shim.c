/*
 * egl_shim.so – EGL-Fallback für Fedora/Bazzite AMD + Mesa
 *
 * Problem: Auf Fedora-basierten Systemen schlägt amdgpu_device_initialize
 * mit EACCES (-13) fehl → eglGetDisplay(EGL_DEFAULT_DISPLAY) gibt
 * EGL_NO_DISPLAY zurück → webkit2gtk 2.44 ruft g_error() → Absturz.
 *
 * Fix: eglGetDisplay abfangen. Gibt die echte Implementierung EGL_NO_DISPLAY,
 * liefern wir einen synthetischen Nicht-NULL-Sentinel zurück. Das verhindert
 * den g_error(). Wenn WebKit danach eglInitialize() mit unserem Sentinel
 * aufruft, geben wir EGL_FALSE zurück → WebKit fällt graceful auf
 * Software-Compositing zurück.
 *
 * Wird via LD_PRELOAD in WebKitWebProcess geladen (gesetzt in main.rs).
 */

#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdint.h>

typedef void* EGLDisplay;
typedef void* EGLNativeDisplayType;
typedef int   EGLBoolean;
typedef int   EGLint;

#define EGL_NO_DISPLAY   ((EGLDisplay)0)
#define EGL_FALSE        0
/* Eindeutiger Sentinel-Wert – kein gültiger EGLDisplay-Pointer */
#define FAKE_EGL_DISPLAY ((EGLDisplay)(uintptr_t)0xEE1D1EA)

EGLDisplay eglGetDisplay(EGLNativeDisplayType nd) {
    EGLDisplay (*real)(EGLNativeDisplayType) = dlsym(RTLD_NEXT, "eglGetDisplay");
    EGLDisplay d = real ? real(nd) : EGL_NO_DISPLAY;
    if (d == EGL_NO_DISPLAY) {
        fprintf(stderr, "[egl-shim] eglGetDisplay fehlgeschlagen (AMD EACCES?) "
                        "– Fake-Display fuer graceful Fallback\n");
        return FAKE_EGL_DISPLAY;
    }
    return d;
}

EGLBoolean eglInitialize(EGLDisplay dpy, EGLint *major, EGLint *minor) {
    if (dpy == FAKE_EGL_DISPLAY) {
        if (major) *major = 0;
        if (minor) *minor = 0;
        return EGL_FALSE; /* graceful failure → WebKit nutzt Software-Rendering */
    }
    EGLBoolean (*real)(EGLDisplay, EGLint*, EGLint*) =
        dlsym(RTLD_NEXT, "eglInitialize");
    return real ? real(dpy, major, minor) : EGL_FALSE;
}
