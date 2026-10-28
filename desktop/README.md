# Terminal als macOS-Anwendung

Eine Electron-Hülle um die vorhandene HTML/JS-Oberfläche (`app/dist/bankterminal.html`). Alle Daten (Banken, Unternehmen, Börsendaten, Volkswirtschaft) stecken in dieser einen Datei und die Schriften (IBM Plex) liegen lokal, die App läuft daher komplett offline.

**Warum Electron und nicht Tauri:** Electron braucht keine Rust-Toolchain, die Seite wird überall gleich dargestellt (Tauri nutzt das WKWebView des jeweiligen macOS) und die Daten-Aktualisierung ist in JavaScript einfach. Dafür ist die .dmg etwa 100 MB groß statt etwa 15 MB. Ein späterer Wechsel zu Tauri wäre möglich, weil die Oberfläche unverändert bleibt.

## Download und erster Start

1. Auf GitHub: **Actions → „macOS-App bauen“ → neuester grüner Lauf → Artifacts → `Terminal-macOS`** (ZIP herunterladen und entpacken). Alternativ unter **Releases**, sobald ein Tag `desktop-v…` gesetzt wurde.
2. `Kennzahlen-Terminal-<Version>-arm64.dmg` (Apple-Silicon: M1 bis M4) oder `Kennzahlen-Terminal-<Version>-x64.dmg` (Intel) öffnen und die App in **Programme** ziehen.
3. Die App ist nicht von Apple notarisiert (dafür wäre das kostenpflichtige Developer-Programm nötig). macOS meldet deshalb beim ersten Start „kann nicht geöffnet werden“. So umgehst du das einmalig:
   * **Rechtsklick auf die App → Öffnen → Öffnen**, oder
   * **Systemeinstellungen → Datenschutz & Sicherheit → ganz unten „Kennzahlen-Terminal wurde blockiert“ → Trotzdem öffnen**, oder
   * im Terminal: `xattr -dr com.apple.quarantine /Applications/Kennzahlen-Terminal.app`
   Ab dem zweiten Start öffnet sie sich normal.

## Daten aktualisieren

Menü **Daten → Daten aktualisieren** (⌘U) lädt die neueste `bankterminal.html` vom Branch `terminal-dist` des Repos (die GitHub-Action „Börsendaten Terminal“ baut sie werktags neu). Weil das Repo privat ist, fragt die App beim ersten Mal nach einem GitHub-Token:

1. GitHub → Settings → Developer settings → Fine-grained tokens → neuen Token anlegen, Repository `Unternehmenskennzahlen`, Berechtigung **Contents: Read-only**.
2. Token in das Fenster der App einfügen. Er wird verschlüsselt im macOS-Schlüsselbund abgelegt (Menü Daten → „GitHub-Token entfernen“ löscht ihn).

Die geladene Fassung liegt unter `~/Library/Application Support/Kennzahlen-Terminal/daten/`; „Auf mitgelieferte Daten zurücksetzen“ verwirft sie. Wird die App selbst neu gebaut, bringt sie die dann aktuelle Fassung mit.

## Berichte und Dokumente

Links zu Originalquellen und zu Dateien im Repo öffnen im Standardbrowser (die Dateien im privaten Repo verlangen dort deine GitHub-Anmeldung). Eine lokale Ablage der PDFs in der App wäre eine spätere Erweiterung (das Repo enthält mehrere hundert MB).

## Selbst bauen

```bash
cd desktop
npm ci
npm start        # Entwicklung: startet die App direkt
npm run dist     # nur auf macOS: .dmg und .zip nach desktop/dist/
```
Wird `app/build.py` neu ausgeführt, kopiert `npm run prepare-assets` (Teil von `start` und `dist`) die neue Seite in die App.
