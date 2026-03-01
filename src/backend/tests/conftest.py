import sys
from pathlib import Path

# Backend-Verzeichnis zum Suchpfad hinzufügen, damit alle Module importierbar sind
sys.path.insert(0, str(Path(__file__).parent.parent))
