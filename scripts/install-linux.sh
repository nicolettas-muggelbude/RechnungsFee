#!/bin/bash
# RechnungsFee – Desktop-Integration für Linux
# Erstellt einen Starter in GNOME, KDE, XFCE und anderen Desktop-Umgebungen.
# Prüft und repariert automatisch fehlende Systemabhängigkeiten.
# Benötigt KEIN sudo für die Integration – nur optional für die Reparatur.
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

# ── Systemabhängigkeiten prüfen und ggf. reparieren ───────────────────────────
check_and_fix_deps() {
  local pkg_manager="" webkit_pkg="" egl_pkg="" extra_pkgs=""

  # Paketmanager und Paketnamen erkennen
  if command -v apt &>/dev/null; then
    pkg_manager="apt"
    webkit_pkg="libwebkit2gtk-4.1-0"
    egl_pkg="libegl1"
    extra_pkgs="libgl1-mesa-dri"
  elif command -v dnf &>/dev/null; then
    pkg_manager="dnf"
    webkit_pkg="webkit2gtk4.1"
    egl_pkg="mesa-libEGL"
    extra_pkgs="mesa-dri-drivers"
  elif command -v zypper &>/dev/null; then
    pkg_manager="zypper"
    webkit_pkg="libwebkit2gtk-4.1-0"
    egl_pkg="libEGL1"
    extra_pkgs=""
  elif command -v pacman &>/dev/null; then
    pkg_manager="pacman"
    webkit_pkg="webkit2gtk-4.1"
    egl_pkg=""
    extra_pkgs=""
  fi

  local webkit_ok=true egl_ok=true

  # webkit2gtk prüfen
  if [ "$pkg_manager" = "apt" ]; then
    dpkg -s "$webkit_pkg" &>/dev/null || webkit_ok=false
  elif [ "$pkg_manager" = "dnf" ] || [ "$pkg_manager" = "zypper" ]; then
    rpm -q "$webkit_pkg" &>/dev/null || webkit_ok=false
  elif [ "$pkg_manager" = "pacman" ]; then
    pacman -Q "$webkit_pkg" &>/dev/null || webkit_ok=false
  fi

  # libEGL prüfen
  ldconfig -p 2>/dev/null | grep -q "libEGL\.so\.1" || egl_ok=false

  echo ""
  echo "── Systemprüfung ──────────────────────────────────────────────────────"

  if $webkit_ok; then
    echo "  ✓ $webkit_pkg installiert"
  else
    echo "  ✗ $webkit_pkg fehlt  ← Ursache für weißes Fenster"
  fi

  if $egl_ok; then
    echo "  ✓ libEGL vorhanden"
  else
    echo "  ✗ libEGL fehlt  ← Ursache für weißes Fenster"
  fi

  echo "────────────────────────────────────────────────────────────────────────"

  if $webkit_ok && $egl_ok; then
    echo "  ✓ Alle Abhängigkeiten in Ordnung."
    echo ""
    echo "  Hinweis: Falls RechnungsFee trotzdem ein weißes Fenster zeigt,"
    echo "  kann ein Defekt in einer Systembibliothek die Ursache sein."
    echo "  Reparatur-Option: $0 --repair $APPIMAGE"
    return 0
  fi

  # Fehlende Pakete gefunden
  echo ""
  echo "  ⚠  Fehlende Abhängigkeiten erkannt."
  echo "     RechnungsFee wird wahrscheinlich ein weißes Fenster zeigen."
  echo ""

  if [ -z "$pkg_manager" ]; then
    echo "  Kein bekannter Paketmanager gefunden."
    echo "  Bitte webkit2gtk 4.1 für deine Distribution manuell installieren."
    echo ""
    return 0
  fi

  _install_deps "$pkg_manager" "$webkit_pkg" "$egl_pkg" "$extra_pkgs"
}

# ── Reparatur-Modus: Pakete neu installieren (auch wenn vorhanden) ─────────────
repair_deps() {
  local pkg_manager="" webkit_pkg="" egl_pkg="" extra_pkgs=""

  if command -v apt &>/dev/null; then
    pkg_manager="apt"; webkit_pkg="libwebkit2gtk-4.1-0"
    egl_pkg="libegl1"; extra_pkgs="libgl1-mesa-dri"
  elif command -v dnf &>/dev/null; then
    pkg_manager="dnf"; webkit_pkg="webkit2gtk4.1"
    egl_pkg="mesa-libEGL"; extra_pkgs="mesa-dri-drivers"
  elif command -v zypper &>/dev/null; then
    pkg_manager="zypper"; webkit_pkg="libwebkit2gtk-4.1-0"
    egl_pkg="libEGL1"; extra_pkgs=""
  elif command -v pacman &>/dev/null; then
    pkg_manager="pacman"; webkit_pkg="webkit2gtk-4.1"
    egl_pkg=""; extra_pkgs=""
  else
    echo "Kein bekannter Paketmanager gefunden."
    exit 1
  fi

  echo ""
  echo "── Reparatur-Modus ────────────────────────────────────────────────────"
  echo "  Installiert Systembibliotheken neu (behebt weiße Fenster)."
  echo "────────────────────────────────────────────────────────────────────────"
  echo ""

  _install_deps "$pkg_manager" "$webkit_pkg" "$egl_pkg" "$extra_pkgs" "reinstall"
}

_install_deps() {
  local pkg_manager="$1" webkit_pkg="$2" egl_pkg="$3" extra_pkgs="$4"
  local mode="${5:-install}"  # install oder reinstall

  local cmd_label="Installieren"
  [ "$mode" = "reinstall" ] && cmd_label="Neu installieren"

  echo "  $cmd_label mit sudo (Passwort erforderlich):"
  if [ "$pkg_manager" = "apt" ]; then
    if [ "$mode" = "reinstall" ]; then
      echo "    sudo apt install --reinstall $webkit_pkg $egl_pkg $extra_pkgs"
    else
      echo "    sudo apt install $webkit_pkg $egl_pkg $extra_pkgs"
    fi
  elif [ "$pkg_manager" = "dnf" ]; then
    if [ "$mode" = "reinstall" ]; then
      echo "    sudo dnf reinstall $webkit_pkg $egl_pkg $extra_pkgs"
    else
      echo "    sudo dnf install $webkit_pkg $egl_pkg $extra_pkgs"
    fi
  elif [ "$pkg_manager" = "zypper" ]; then
    echo "    sudo zypper install $webkit_pkg $egl_pkg"
  elif [ "$pkg_manager" = "pacman" ]; then
    echo "    sudo pacman -S $webkit_pkg"
  fi
  echo ""
  printf "  Jetzt automatisch ausführen? [J/n] "
  read -r answer
  answer="${answer:-j}"

  if [[ "$answer" =~ ^[jJyY]$ ]]; then
    if [ "$pkg_manager" = "apt" ]; then
      if [ "$mode" = "reinstall" ]; then
        sudo apt install --reinstall -y $webkit_pkg $egl_pkg $extra_pkgs
      else
        sudo apt install -y $webkit_pkg $egl_pkg $extra_pkgs
      fi
    elif [ "$pkg_manager" = "dnf" ]; then
      if [ "$mode" = "reinstall" ]; then
        sudo dnf reinstall -y $webkit_pkg $egl_pkg $extra_pkgs 2>/dev/null || \
        sudo dnf install -y $webkit_pkg $egl_pkg $extra_pkgs
      else
        sudo dnf install -y $webkit_pkg $egl_pkg $extra_pkgs
      fi
    elif [ "$pkg_manager" = "zypper" ]; then
      sudo zypper install -y $webkit_pkg $egl_pkg
    elif [ "$pkg_manager" = "pacman" ]; then
      sudo pacman -S --noconfirm $webkit_pkg
    fi
    echo ""
    echo "  ✓ Erledigt. RechnungsFee neu starten."
  else
    echo "  Übersprungen. Bei weißem Fenster den Befehl oben manuell ausführen."
  fi
  echo ""
}

# ── Reparatur-Modus direkt aufrufen: ./install-linux.sh --repair [AppImage] ──
if [ "${1:-}" = "--repair" ]; then
  shift
  APPIMAGE="${1:-}"
  if [ -z "$APPIMAGE" ]; then
    APPIMAGE="$(ls -t "$HOME/Downloads/RechnungsFee"*.AppImage 2>/dev/null | head -1)"
  fi
  repair_deps
  exit 0
fi

check_and_fix_deps

# ── Icon herunterladen ─────────────────────────────────────────────────────────
ICON_BASE="$HOME/.local/share/icons/hicolor"
ICON_DIR="$ICON_BASE/256x256/apps"
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
Exec=env WEBKIT_DISABLE_DMABUF_RENDERER=1 $APPIMAGE %u
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
echo ""
echo "  Weißes Fenster? Reparatur ausführen mit:"
echo "    ./install-linux.sh --repair"
echo ""
