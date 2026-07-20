#!/bin/bash
# RechnungsFee – Desktop-Integration für Linux
# Erstellt einen Starter in GNOME, KDE, XFCE und anderen Desktop-Umgebungen.
# Prüft und repariert automatisch fehlende Systemabhängigkeiten.
# Benötigt KEIN sudo für die Integration – nur optional für die Reparatur.
#
# Verwendung (kein chmod +x nötig, weder für dieses Skript noch die AppImage):
#   bash install-linux.sh [/pfad/zu/RechnungsFee_amd64.AppImage]
#
# Ohne Argument wird zuerst im aktuellen Verzeichnis, dann im Verzeichnis
# dieses Skripts und zuletzt in ~/Downloads nach RechnungsFee*.AppImage gesucht.

set -e


# ── AppImage finden ────────────────────────────────────────────────────────────
# Suchreihenfolge: 1) explizites Argument  2) aktuelles Verzeichnis (häufigster Fall:
# beide Dateien liegen nebeneinander, Skript wird von dort aufgerufen)  3) Verzeichnis
# des Skripts selbst (falls per Pfad von woanders aufgerufen)  4) ~/Downloads (Fallback,
# z. B. Doppelklick im Dateimanager mit abweichendem Arbeitsverzeichnis).
APPIMAGE="${1:-}"
if [ -z "$APPIMAGE" ]; then
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  APPIMAGE="$(ls -t ./RechnungsFee*.AppImage 2>/dev/null | head -1)"
fi
if [ -z "$APPIMAGE" ]; then
  APPIMAGE="$(ls -t "$SCRIPT_DIR"/RechnungsFee*.AppImage 2>/dev/null | head -1)"
fi
if [ -z "$APPIMAGE" ]; then
  APPIMAGE="$(ls -t "$HOME/Downloads/RechnungsFee"*.AppImage 2>/dev/null | head -1)"
fi
if [ -z "$APPIMAGE" ] || [ ! -f "$APPIMAGE" ]; then
  echo "Fehler: AppImage nicht gefunden."
  echo "Gesucht in: aktuellem Verzeichnis, Skript-Verzeichnis und ~/Downloads"
  echo "Verwendung: $0 /pfad/zu/RechnungsFee_amd64.AppImage"
  exit 1
fi
APPIMAGE="$(realpath "$APPIMAGE")"
echo "AppImage: $APPIMAGE"

# ── Ausführbar machen ──────────────────────────────────────────────────────────
chmod +x "$APPIMAGE"

# ── Systemabhängigkeiten prüfen und ggf. reparieren ───────────────────────────
_check_and_install_tesseract() {
  local pkg_manager="${1:-}"

  echo "── Optionale Komponente: Tesseract OCR ─────────────────────────────────"
  echo "  Wird benötigt um gescannte Eingangsrechnungen automatisch zu erkennen."
  echo ""

  if command -v tesseract &>/dev/null; then
    echo "  ✓ tesseract-ocr bereits installiert ($(tesseract --version 2>&1 | head -1))"
    echo "────────────────────────────────────────────────────────────────────────"
    return 0
  fi

  echo "  ○ tesseract-ocr ist nicht installiert."
  echo ""

  local tess_pkg="" tess_lang_pkg=""
  case "$pkg_manager" in
    apt)    tess_pkg="tesseract-ocr";  tess_lang_pkg="tesseract-ocr-deu" ;;
    dnf)    tess_pkg="tesseract";      tess_lang_pkg="tesseract-langpack-deu" ;;
    zypper) tess_pkg="tesseract-ocr";  tess_lang_pkg="tesseract-ocr-traineddata-german" ;;
    pacman) tess_pkg="tesseract";      tess_lang_pkg="tesseract-data-deu" ;;
    *)
      echo "  Für OCR bitte manuell installieren: tesseract-ocr + Sprachpaket Deutsch"
      echo "────────────────────────────────────────────────────────────────────────"
      return 0
      ;;
  esac

  printf "  Jetzt installieren? [J/n] "
  read -r answer
  answer="${answer:-j}"

  if [[ "$answer" =~ ^[jJyY]$ ]]; then
    case "$pkg_manager" in
      apt)    sudo apt install -y "$tess_pkg" "$tess_lang_pkg" ;;
      dnf)    sudo dnf install -y "$tess_pkg" "$tess_lang_pkg" ;;
      zypper) sudo zypper install -y "$tess_pkg" "$tess_lang_pkg" ;;
      pacman) sudo pacman -S --noconfirm "$tess_pkg" "$tess_lang_pkg" ;;
    esac
    echo ""
    if command -v tesseract &>/dev/null; then
      echo "  ✓ Tesseract OCR installiert. OCR für gescannte Rechnungen ist aktiv."
    else
      echo "  ✗ Installation fehlgeschlagen. OCR wird übersprungen."
    fi
  else
    echo "  Übersprungen. OCR für gescannte Rechnungen ist nicht verfügbar."
    echo "  Manuell nachinstallieren: sudo $pkg_manager install $tess_pkg $tess_lang_pkg"
  fi
  echo "────────────────────────────────────────────────────────────────────────"
}

_check_and_install_ghostscript() {
  local pkg_manager="${1:-}"

  echo "── Optionale Komponente: Ghostscript ───────────────────────────────────"
  echo "  Wird benötigt um Belege als PDF/A-3 zu archivieren (GoBD-Langzeitarchiv)."
  echo ""

  if command -v gs &>/dev/null; then
    echo "  ✓ ghostscript bereits installiert ($(gs --version 2>&1 | head -1))"
    echo "────────────────────────────────────────────────────────────────────────"
    return 0
  fi

  echo "  ○ ghostscript ist nicht installiert."
  echo ""

  local gs_pkg="ghostscript"
  case "$pkg_manager" in
    apt|dnf|zypper) gs_pkg="ghostscript" ;;
    pacman)         gs_pkg="ghostscript" ;;
    *)
      echo "  Für PDF/A-Archivierung bitte manuell installieren: ghostscript"
      echo "────────────────────────────────────────────────────────────────────────"
      return 0
      ;;
  esac

  printf "  Jetzt installieren? [J/n] "
  read -r answer
  answer="${answer:-j}"

  if [[ "$answer" =~ ^[jJyY]$ ]]; then
    case "$pkg_manager" in
      apt)    sudo apt install -y "$gs_pkg" ;;
      dnf)    sudo dnf install -y "$gs_pkg" ;;
      zypper) sudo zypper install -y "$gs_pkg" ;;
      pacman) sudo pacman -S --noconfirm "$gs_pkg" ;;
    esac
    echo ""
    if command -v gs &>/dev/null; then
      echo "  ✓ Ghostscript installiert. PDF/A-Archivierung ist aktiv."
    else
      echo "  ✗ Installation fehlgeschlagen. PDF/A-Archivierung wird übersprungen."
    fi
  else
    echo "  Übersprungen. PDF/A-Archivierung ist nicht verfügbar."
    echo "  Manuell nachinstallieren: sudo $pkg_manager install $gs_pkg"
  fi
  echo "────────────────────────────────────────────────────────────────────────"
}

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
    echo ""
    _check_and_install_tesseract "$pkg_manager"
    _check_and_install_ghostscript "$pkg_manager"
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
  echo ""
  _check_and_install_tesseract "$pkg_manager"
  _check_and_install_ghostscript "$pkg_manager"
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
ICON_B64="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
/w9yIFHSNNVDYAAAAABJRU5ErkJggg=="
echo "$ICON_B64" | base64 -d > "$ICON_FILE" && echo "  Icon installiert." || echo "  Hinweis: Icon konnte nicht geschrieben werden." 

# ── .desktop-Datei anlegen ─────────────────────────────────────────────────────
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/de.rechnungsfee.app.desktop"
mkdir -p "$DESKTOP_DIR"

# Auf KDE: GTK_THEME setzen damit der Dateiauswahl-Dialog das System-Theme übernimmt.
# Das AppImage bündelt WebKit2GTK und ignoriert sonst das systemseitige GTK-Theme (Issue #151).
GTK_THEME_ENV=""
if [ "${XDG_CURRENT_DESKTOP:-}" = "KDE" ] || [ "${DESKTOP_SESSION:-}" = "plasma" ]; then
  KDE_GTK_THEME="$(kreadconfig5 --group "GTK" --key "theme" 2>/dev/null || true)"
  if [ -n "$KDE_GTK_THEME" ]; then
    GTK_THEME_ENV="GTK_THEME=$KDE_GTK_THEME "
    echo "KDE erkannt – GTK_THEME=$KDE_GTK_THEME wird im Desktop-Starter gesetzt"
  fi
fi

cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Name=RechnungsFee
Comment=Buchhaltung für Freiberufler & Kleinunternehmer (§19 UStG)
Exec=env ${GTK_THEME_ENV}GDK_BACKEND=x11 WEBKIT_DISABLE_DMABUF_RENDERER=1 WEBKIT_DISABLE_COMPOSITING_MODE=1 $APPIMAGE %u
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
