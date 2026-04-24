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
  local pkg_manager="" webkit_pkg="" egl_pkg="" fuse_pkg="" extra_pkgs=""

  # Paketmanager und Paketnamen erkennen
  if command -v apt &>/dev/null; then
    pkg_manager="apt"
    webkit_pkg="libwebkit2gtk-4.1-0"
    egl_pkg="libegl1"
    extra_pkgs="libgl1-mesa-dri"
    # FUSE 2: Paketname je nach Ubuntu/Debian-Version
    if apt-cache show libfuse2t64 &>/dev/null 2>&1; then
      fuse_pkg="libfuse2t64"
    elif apt-cache show libfuse2to64 &>/dev/null 2>&1; then
      fuse_pkg="libfuse2to64"
    else
      fuse_pkg="libfuse2"
    fi
  elif command -v dnf &>/dev/null; then
    pkg_manager="dnf"
    webkit_pkg="webkit2gtk4.1"
    egl_pkg="mesa-libEGL"
    extra_pkgs="mesa-dri-drivers"
    fuse_pkg="fuse-libs"
  elif command -v zypper &>/dev/null; then
    pkg_manager="zypper"
    webkit_pkg="libwebkit2gtk-4.1-0"
    egl_pkg="libEGL1"
    extra_pkgs=""
    fuse_pkg="libfuse2"
  elif command -v pacman &>/dev/null; then
    pkg_manager="pacman"
    webkit_pkg="webkit2gtk-4.1"
    egl_pkg=""
    extra_pkgs=""
    fuse_pkg="fuse2"
  fi

  local webkit_ok=true egl_ok=true fuse_ok=true

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

  # FUSE 2 prüfen (AppImage-Voraussetzung)
  ldconfig -p 2>/dev/null | grep -q "libfuse\.so\.2" || fuse_ok=false

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

  if $fuse_ok; then
    echo "  ✓ libfuse2 vorhanden"
  else
    echo "  ✗ libfuse2 fehlt  ← AppImage startet nicht ohne FUSE 2"
  fi

  echo "────────────────────────────────────────────────────────────────────────"

  if $webkit_ok && $egl_ok && $fuse_ok; then
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
  if ! $fuse_ok; then
    echo "     libfuse2 fehlt → AppImage startet nicht."
  fi
  if ! $webkit_ok || ! $egl_ok; then
    echo "     RechnungsFee wird wahrscheinlich ein weißes Fenster zeigen."
  fi
  echo ""

  if [ -z "$pkg_manager" ]; then
    echo "  Kein bekannter Paketmanager gefunden."
    echo "  Bitte webkit2gtk 4.1 und libfuse2 für deine Distribution manuell installieren."
    echo ""
    return 0
  fi

  _install_deps "$pkg_manager" "$webkit_pkg" "$egl_pkg" "$fuse_pkg" "$extra_pkgs"
}

# ── Reparatur-Modus: Pakete neu installieren (auch wenn vorhanden) ─────────────
repair_deps() {
  local pkg_manager="" webkit_pkg="" egl_pkg="" fuse_pkg="" extra_pkgs=""

  if command -v apt &>/dev/null; then
    pkg_manager="apt"; webkit_pkg="libwebkit2gtk-4.1-0"
    egl_pkg="libegl1"; extra_pkgs="libgl1-mesa-dri"
    if apt-cache show libfuse2t64 &>/dev/null 2>&1; then
      fuse_pkg="libfuse2t64"
    elif apt-cache show libfuse2to64 &>/dev/null 2>&1; then
      fuse_pkg="libfuse2to64"
    else
      fuse_pkg="libfuse2"
    fi
  elif command -v dnf &>/dev/null; then
    pkg_manager="dnf"; webkit_pkg="webkit2gtk4.1"
    egl_pkg="mesa-libEGL"; extra_pkgs="mesa-dri-drivers"; fuse_pkg="fuse-libs"
  elif command -v zypper &>/dev/null; then
    pkg_manager="zypper"; webkit_pkg="libwebkit2gtk-4.1-0"
    egl_pkg="libEGL1"; extra_pkgs=""; fuse_pkg="libfuse2"
  elif command -v pacman &>/dev/null; then
    pkg_manager="pacman"; webkit_pkg="webkit2gtk-4.1"
    egl_pkg=""; extra_pkgs=""; fuse_pkg="fuse2"
  else
    echo "Kein bekannter Paketmanager gefunden."
    exit 1
  fi

  echo ""
  echo "── Reparatur-Modus ────────────────────────────────────────────────────"
  echo "  Installiert Systembibliotheken neu (behebt weiße Fenster)."
  echo "────────────────────────────────────────────────────────────────────────"
  echo ""

  _install_deps "$pkg_manager" "$webkit_pkg" "$egl_pkg" "$fuse_pkg" "$extra_pkgs" "reinstall"
}

_install_deps() {
  local pkg_manager="$1" webkit_pkg="$2" egl_pkg="$3" fuse_pkg="$4" extra_pkgs="$5"
  local mode="${6:-install}"  # install oder reinstall

  local cmd_label="Installieren"
  [ "$mode" = "reinstall" ] && cmd_label="Neu installieren"

  local pkgs="$webkit_pkg"
  [ -n "$egl_pkg" ]   && pkgs="$pkgs $egl_pkg"
  [ -n "$fuse_pkg" ]  && pkgs="$pkgs $fuse_pkg"
  [ -n "$extra_pkgs" ] && pkgs="$pkgs $extra_pkgs"

  echo "  $cmd_label mit sudo (Passwort erforderlich):"
  if [ "$pkg_manager" = "apt" ]; then
    if [ "$mode" = "reinstall" ]; then
      echo "    sudo apt install --reinstall $pkgs"
    else
      echo "    sudo apt install $pkgs"
    fi
  elif [ "$pkg_manager" = "dnf" ]; then
    if [ "$mode" = "reinstall" ]; then
      echo "    sudo dnf reinstall $pkgs"
    else
      echo "    sudo dnf install $pkgs"
    fi
  elif [ "$pkg_manager" = "zypper" ]; then
    echo "    sudo zypper install $pkgs"
  elif [ "$pkg_manager" = "pacman" ]; then
    echo "    sudo pacman -S $pkgs"
  fi
  echo ""
  printf "  Jetzt automatisch ausführen? [J/n] "
  read -r answer
  answer="${answer:-j}"

  if [[ "$answer" =~ ^[jJyY]$ ]]; then
    if [ "$pkg_manager" = "apt" ]; then
      if [ "$mode" = "reinstall" ]; then
        sudo apt install --reinstall -y $pkgs
      else
        sudo apt install -y $pkgs
      fi
    elif [ "$pkg_manager" = "dnf" ]; then
      if [ "$mode" = "reinstall" ]; then
        sudo dnf reinstall -y $pkgs 2>/dev/null || sudo dnf install -y $pkgs
      else
        sudo dnf install -y $pkgs
      fi
    elif [ "$pkg_manager" = "zypper" ]; then
      sudo zypper install -y $pkgs
    elif [ "$pkg_manager" = "pacman" ]; then
      sudo pacman -S --noconfirm $pkgs
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

# Icon ist eingebettet – kein Download, kein curl/wget nötig
ICON_B64="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"
echo "$ICON_B64" | base64 -d > "$ICON_FILE" && echo "  Icon installiert." || echo "  Hinweis: Icon konnte nicht geschrieben werden." 

# ── .desktop-Datei anlegen ─────────────────────────────────────────────────────
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/de.rechnungsfee.app.desktop"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Name=RechnungsFee
Comment=Buchhaltung für Freiberufler & Kleinunternehmer (§19 UStG)
Exec=env GDK_BACKEND=x11 WEBKIT_DISABLE_DMABUF_RENDERER=1 WEBKIT_DISABLE_COMPOSITING_MODE=1 $APPIMAGE %u
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
