# Baut das Python-Backend als PyInstaller-Sidecar für Tauri (Windows).
# Ausgabe: src-tauri/binaries/backend-{triple}.exe
param(
    [string]$Triple = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RepoRoot "src\backend"
$BinariesDir = Join-Path $RepoRoot "src-tauri\binaries"

# Target-Triple ermitteln
if ($Triple -eq "") {
    if (Get-Command rustc -ErrorAction SilentlyContinue) {
        $Triple = (rustc -vV | Select-String "host:").ToString().Replace("host: ", "").Trim()
    } else {
        $Triple = "x86_64-pc-windows-msvc"
    }
}

Write-Host "[Sidecar] Target-Triple: $Triple"
Write-Host "[Sidecar] Backend-Verzeichnis: $BackendDir"

# Virtuelle Umgebung aktivieren (falls vorhanden)
$Activate = Join-Path $BackendDir ".venv\Scripts\Activate.ps1"
if (Test-Path $Activate) {
    & $Activate
}

# PyInstaller sicherstellen
pip install --quiet pyinstaller

New-Item -ItemType Directory -Force -Path $BinariesDir | Out-Null

# Binary bauen
Push-Location $BackendDir
try {
    pyinstaller `
        --onefile `
        --name backend `
        "--distpath=$BinariesDir" `
        "--workpath=$RepoRoot\build\pyinstaller_work" `
        "--specpath=$RepoRoot\build\pyinstaller_spec" `
        --hidden-import uvicorn.logging `
        --hidden-import uvicorn.loops `
        --hidden-import uvicorn.loops.auto `
        --hidden-import uvicorn.protocols `
        --hidden-import uvicorn.protocols.http `
        --hidden-import uvicorn.protocols.http.auto `
        --hidden-import uvicorn.protocols.websockets `
        --hidden-import uvicorn.protocols.websockets.auto `
        --hidden-import uvicorn.lifespan `
        --hidden-import uvicorn.lifespan.on `
        --hidden-import api.unternehmen `
        --hidden-import api.konten `
        --hidden-import api.kategorien `
        --hidden-import api.setup `
        --hidden-import api.kassenbuch `
        --hidden-import api.kunden `
        --hidden-import api.lieferanten `
        --hidden-import api.tagesabschluss `
        --hidden-import api.nummernkreise `
        --hidden-import api.export `
        --hidden-import api.rechnungen `
        --hidden-import api.backup `
        --hidden-import api.pdf_vorlagen `
        --hidden-import database.models `
        --hidden-import database.connection `
        --hidden-import database.seed `
        --hidden-import utils.gobd_export `
        --hidden-import utils.pdf_gobd_bericht `
        --hidden-import utils.pdf_tagesabschluss `
        --hidden-import utils.pdf_rechnung `
        --hidden-import utils.pdf_rechnung_vorlage1 `
        --hidden-import utils.pdf_shared `
        --hidden-import utils.signatur `
        --collect-all segno `
        "--add-data=$BackendDir\fonts;fonts" `
        main.py
} finally {
    Pop-Location
}

# Binary umbenennen: backend.exe → backend-{triple}.exe
$BinarySrc = Join-Path $BinariesDir "backend.exe"
$BinaryDst = Join-Path $BinariesDir "backend-$Triple.exe"

if (Test-Path $BinarySrc) {
    Move-Item -Force $BinarySrc $BinaryDst
    Write-Host "[Sidecar] Fertig: $BinaryDst"
} else {
    Write-Error "[Sidecar] Fehler: Binary nicht gefunden in $BinariesDir"
    exit 1
}
