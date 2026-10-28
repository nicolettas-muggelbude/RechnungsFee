"""Python-Beispiel als Wasm-Component und installierbares .rfplugin paketieren."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

BEISPIEL = Path(__file__).resolve().parent
REPO = BEISPIEL.parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--componentize', help='Pfad zur componentize-py-Binärdatei')
    args = parser.parse_args()
    lokal = Path(sys.executable).parent / ('componentize-py.exe' if sys.platform == 'win32' else 'componentize-py')
    tool = args.componentize or (str(lokal) if lokal.exists() else shutil.which('componentize-py'))
    if not tool:
        parser.error('componentize-py fehlt. Installiere requirements-build.txt in einer Build-venv.')
    tool = str(Path(tool).resolve())
    dist = BEISPIEL / 'dist'
    dist.mkdir(exist_ok=True)
    wasm = dist / 'plugin.wasm'
    # --stub-wasi ist zwingend: RechnungsFee erlaubt keinen WASI-Import.
    subprocess.run([
        tool, '-d', str(REPO / 'src/backend/plugins/wit/rechnungsfee.wit'),
        '-w', 'plugin-world', 'componentize', '--stub-wasi',
        '-p', str(BEISPIEL), 'app', '-o', str(wasm),
    ], cwd=BEISPIEL, check=True)
    if wasm.stat().st_size > 20 * 1024 * 1024:
        raise SystemExit('Component überschreitet RechnungsFees 20-MB-Limit.')
    paket = dist / 'python-kundenpruefung.rfplugin'
    with zipfile.ZipFile(paket, 'w', compression=zipfile.ZIP_DEFLATED) as archiv:
        archiv.write(wasm, 'plugin.wasm')
        archiv.write(BEISPIEL / 'plugin.toml', 'plugin.toml')
    print(f'Wasm: {wasm}\nInstallierbares Paket: {paket}')


if __name__ == '__main__':
    main()
