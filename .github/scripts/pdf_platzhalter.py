"""Legt für alle im Git geführten, aber nicht ausgecheckten Dateien (PDF, .gz) leere Dateien in Originalgröße an.

Die Größen kommen aus der Git-Tree-API (ein Aufruf). os.truncate erzeugt Sparse-Dateien: Dateigröße stimmt, Speicher wird nicht belegt.
app/unternehmen.py liest davon nur die ersten Bytes (Git-LFS-Kennung) und die Größe."""
import json
import os
import subprocess
import sys
from pathlib import Path

repo = os.environ.get("GITHUB_REPOSITORY", "chillkrote/Unternehmenskennzahlen")
sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
baum = json.loads(subprocess.run(["gh", "api", f"repos/{repo}/git/trees/{sha}?recursive=1"], capture_output=True, text=True, check=True).stdout)
if baum.get("truncated"):
    sys.exit("Tree-API hat gekürzt; Platzhalter unvollständig")
n = 0
for e in baum["tree"]:
    if e["type"] == "blob" and e["path"].lower().endswith((".pdf", ".gz")):
        p = Path(e["path"])
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "wb") as f:
                f.truncate(e["size"])
            n += 1
print(f"{n} Platzhalter angelegt")
