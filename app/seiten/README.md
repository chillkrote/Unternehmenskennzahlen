# Seiten der Fußleiste

Die drei Schaltflächen unten mittig (Impressum, Kontakt, About Sphaerae) laden ihren Text aus diesen Markdown-Dateien:

| Datei | Schaltfläche |
|---|---|
| `impressum.md` | Impressum |
| `kontakt.md` | Kontakt |
| `about.md` | About Sphaerae |

Datei bearbeiten, committen, fertig. `build.py` bettet die Texte beim Bau in die Seite ein (`seiten.py`); an der Oberfläche ist nichts zu ändern.

* Platzhalter stehen in doppelten eckigen Klammern, z. B. `[[Vorname Nachname]]`, und werden im Terminal gelb markiert, damit nichts Unausgefülltes unbemerkt bleibt.
* Unterstützt: `#`/`##` Überschriften, Absätze, `-` Listen, `**fett**`, `*kursiv*`, `[Text](https://…)` und `mailto:`-Links. HTML-Kommentare (`<!-- … -->`) erscheinen nicht.
* Weitere Seite ergänzen: Datei hier anlegen und in `seiten.py` unter `SEITEN` eintragen.
