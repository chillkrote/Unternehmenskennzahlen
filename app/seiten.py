"""Liest die Texte der Fußleiste (Impressum, Kontakt, About) aus app/seiten/*.md für den Einbau in die Oberfläche."""
import json
from pathlib import Path

HIER = Path(__file__).resolve().parent

# Reihenfolge = Reihenfolge der Schaltflächen (links nach rechts)
SEITEN = [("impressum", "Impressum"), ("kontakt", "Kontakt"), ("about", "About Sphaerae")]


def lade():
    out = []
    for id_, titel in SEITEN:
        f = HIER / "seiten" / f"{id_}.md"
        out.append({"id": id_, "titel": titel, "text": f.read_text(encoding="utf-8") if f.exists() else f"# {titel}\n\nNoch kein Text. Datei `app/seiten/{id_}.md` anlegen."})
    return out


def json_text():
    return json.dumps(lade(), ensure_ascii=False, separators=(",", ":"))
