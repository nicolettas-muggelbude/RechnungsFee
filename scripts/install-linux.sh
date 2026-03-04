#!/bin/bash
# RechnungsFee – Desktop-Integration für Linux
# Erstellt einen Starter in GNOME, KDE, XFCE und anderen Desktop-Umgebungen.
# Benötigt KEIN sudo – alles wird im Benutzerverzeichnis installiert.
#
# Verwendung:
#   chmod +x install-linux.sh
#   ./install-linux.sh /pfad/zu/RechnungsFee_amd64.AppImage
#
# Ohne Argument wird ~/Downloads/RechnungsFee*.AppImage gesucht.

set -e

ICON_URL="https://raw.githubusercontent.com/nicolettas-muggelbude/RechnungsFee/main/src-tauri/icons/256x256.png"

# ── AppImage finden ────────────────────────────────────────────────────────────
APPIMAGE="${1:-}"
if [ -z "$APPIMAGE" ]; then
  APPIMAGE="$(ls -t "$HOME/Downloads/RechnungsFee"*.AppImage 2>/dev/null | head -1)"
fi
if [ -z "$APPIMAGE" ] || [ ! -f "$APPIMAGE" ]; then
  echo "Fehler: AppImage nicht gefunden."
  echo "Verwendung: $0 /pfad/zu/RechnungsFee_amd64.AppImage"
  exit 1
fi
APPIMAGE="$(realpath "$APPIMAGE")"
echo "AppImage: $APPIMAGE"

# ── Ausführbar machen ──────────────────────────────────────────────────────────
chmod +x "$APPIMAGE"

# ── Systemabhängigkeit prüfen (Debian/Ubuntu/MX-Linux) ────────────────────────
if command -v dpkg &>/dev/null; then
  if ! dpkg -s libwebkit2gtk-4.1-0 &>/dev/null; then
    echo ""
    echo "⚠  Fehlende Systemabhängigkeit: libwebkit2gtk-4.1-0"
    echo "   Bitte installieren mit:"
    echo "   sudo apt install libwebkit2gtk-4.1-0"
    echo ""
  fi
fi

# ── Icon herunterladen ─────────────────────────────────────────────────────────
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
ICON_FILE="$ICON_DIR/de.rechnungsfee.app.png"
mkdir -p "$ICON_DIR"

echo "Lade Icon herunter..."
if command -v wget &>/dev/null; then
  wget -qO "$ICON_FILE" "$ICON_URL" && echo "  Icon installiert." || echo "  Hinweis: Icon konnte nicht geladen werden – App-Icon fehlt ggf. im Starter."
elif command -v curl &>/dev/null; then
  curl -sSL "$ICON_URL" -o "$ICON_FILE" && echo "  Icon installiert." || echo "  Hinweis: Icon konnte nicht geladen werden – App-Icon fehlt ggf. im Starter."
else
  echo "  Hinweis: wget und curl nicht gefunden – Icon übersprungen."
fi

# ── .desktop-Datei anlegen ─────────────────────────────────────────────────────
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/de.rechnungsfee.app.desktop"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Name=RechnungsFee
Comment=Buchhaltung für Freiberufler & Kleinunternehmer (§19 UStG)
Exec=env LIBGL_ALWAYS_SOFTWARE=1 WEBKIT_DISABLE_DMABUF_RENDERER=1 $APPIMAGE %u
Icon=de.rechnungsfee.app
Type=Application
Categories=Office;Finance;Accounting;
StartupWMClass=de.rechnungsfee.app
Keywords=Rechnung;Buchhaltung;Kassenbuch;Freiberufler;GoBD;Steuer;
Terminal=false
DESKTOP

echo "Desktop-Eintrag erstellt: $DESKTOP_FILE"

# ── Desktop-Datenbanken aktualisieren ──────────────────────────────────────────
gtk-update-icon-cache -f -t "$ICON_BASE" 2>/dev/null || true
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo ""
echo "✓ RechnungsFee wurde erfolgreich als Starter integriert!"
echo ""
echo "  Das App-Icon erscheint in:"
echo "  • GNOME Activities / Ubuntu-Anwendungsmenü"
echo "  • KDE Application Launcher"
echo "  • XFCE / MATE Anwendungsmenü"
echo ""
echo "  Falls der Eintrag noch nicht erscheint: Abmelden und neu anmelden."
