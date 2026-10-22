"""
Issue #453: fpdf2 setzt multi_cell() standardmäßig im Blocksatz (Align.J). Ohne ausdrückliche
Ausrichtung entstanden in Mahnungen, Rechnungs-Hinweisen und Auswertungen große Wortlücken.
Festgelegt: Fließtext in allen PDFs linksbündig im Flattersatz. Dieser Test verhindert, dass ein
neuer multi_cell()-Aufruf ohne align wieder unbemerkt im Blocksatz landet.
"""
import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def _aufrufe_ohne_ausrichtung() -> list[str]:
    fundstellen = []
    for datei in sorted(BACKEND.glob("utils/*.py")) + sorted(BACKEND.glob("api/*.py")):
        baum = ast.parse(datei.read_text(encoding="utf-8"))
        for knoten in ast.walk(baum):
            if (isinstance(knoten, ast.Call)
                    and getattr(knoten.func, "attr", None) == "multi_cell"
                    and not any(kw.arg == "align" for kw in knoten.keywords)
                    and len(knoten.args) < 6):   # 6. Positionsargument wäre align
                fundstellen.append(f"{datei.relative_to(BACKEND)}:{knoten.lineno}")
    return fundstellen


def test_jeder_multi_cell_aufruf_hat_ausdrueckliche_ausrichtung():
    fundstellen = _aufrufe_ohne_ausrichtung()
    assert not fundstellen, (
        "multi_cell() ohne align= gefunden (fpdf2-Standard ist Blocksatz) – bitte align=\"L\" "
        "ergänzen: " + ", ".join(fundstellen)
    )
