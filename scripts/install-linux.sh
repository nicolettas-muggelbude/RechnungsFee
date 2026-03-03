#!/bin/bash
# RechnungsFee – Desktop-Integration für Linux
# Erstellt einen Starter in GNOME, KDE, XFCE und anderen Desktop-Umgebungen.
#
# Verwendung:
#   chmod +x install-linux.sh
#   ./install-linux.sh /pfad/zu/RechnungsFee_amd64.AppImage
#
# Ohne Argument wird ~/Downloads/RechnungsFee*.AppImage gesucht.

set -e

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

# ── Icons aus AppImage extrahieren ─────────────────────────────────────────────
ICON_BASE="$HOME/.local/share/icons/hicolor"
TMP_DIR="$(mktemp -d)"
echo "Extrahiere Icons..."

cd "$TMP_DIR"
"$APPIMAGE" --appimage-extract "usr/share/icons" > /dev/null 2>&1 || true

if [ -d "$TMP_DIR/squashfs-root/usr/share/icons/hicolor" ]; then
  for size in 16 32 48 64 128 256 512; do
    SRC="$TMP_DIR/squashfs-root/usr/share/icons/hicolor/${size}x${size}/apps"
    if [ -d "$SRC" ]; then
      mkdir -p "$ICON_BASE/${size}x${size}/apps"
      cp "$SRC"/*.png "$ICON_BASE/${size}x${size}/apps/" 2>/dev/null || true
    fi
  done
  rm -rf "$TMP_DIR"
  echo "  Icons installiert nach ~/.local/share/icons/hicolor/"
else
  rm -rf "$TMP_DIR"
  echo "  Hinweis: Icons konnten nicht extrahiert werden – App-Icon fehlt ggf. im Starter."
fi

# ── .desktop-Datei anlegen ─────────────────────────────────────────────────────
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/de.rechnungsfee.app.desktop"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Name=RechnungsFee
Comment=Buchhaltung für Freiberufler & Kleinunternehmer (§19 UStG)
Exec=$APPIMAGE %u
Icon=de.rechnungsfee.app
Type=Application
Categories=Office;Finance;Accounting;
StartupWMClass=rechnungsfee
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
