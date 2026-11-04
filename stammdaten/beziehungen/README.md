# Unternehmensnetze (Weltkugel)

Standorte und Beziehungen eines Konzerns: Hauptsitz, Werke mit Tätigkeit und Kennzahlen, Tochterfirmen,
Gemeinschaftsunternehmen, Beteiligungen, Eigentümer, wichtige Kunden, Lieferbeziehungen mit Mengen.
Die Weltkugel (`app/dist/weltkugel.html`) zeigt ein Netz, sobald das Unternehmen (oder eine im Netz verknüpfte
Tochter) ausgewählt wird: Bögen vom Hauptsitz zu den Standorten, Pfeile in Lieferrichtung, ein Panel mit Liste,
Filter, Standortdetail und Quellen.

Erstes Beispiel: `daten/U000712_volkswagen.json` (Volkswagen Konzern, Berichtsjahr 2025).
Was in Berichten und weiteren Quellen zu suchen ist: `CHECKLISTE.md`.
Weitere Netze (Stand 04.11.2026): BASF, Bayer, Commerzbank, Apple, Microsoft, NVIDIA. Was sich nicht beschaffen ließ, steht in
`OFFENE_PUNKTE.md`. Standortart `werk` (Produktionsstandort außerhalb der Autoindustrie) und `filiale` (Standort und Beziehungsart für Bankfilialen) kamen dabei hinzu.
Test für alle Netze: `node app/tests/netze-alle-smoke.js app/dist/weltkugel.html`.

## Neues Unternehmen anlegen

1. Unternehmen muss eine ID haben (`stammdaten/unternehmen_ids.csv`, neu nur über `stammdaten/ids.py`).
2. Datei `daten/<ID>_<kurzname>.json` nach dem Aufbau unten anlegen, Koordinaten leer lassen.
3. `python3 beziehungen.py koordinaten` setzt Ortsmitten über OpenStreetMap Nominatim (Cache: `koordinaten_cache.json`,
   höchstens eine Anfrage pro Sekunde). Liegt der Treffer daneben, Cache-Eintrag von Hand korrigieren und erneut laufen lassen.
4. `python3 beziehungen.py pruefen` muss `0 Fehler` melden; sonst lässt der Build die Datei weg.
5. `python3 app/build.py --nur-seite`, danach `node app/tests/netz-smoke.js app/dist/weltkugel.html`.

## Aufbau

```jsonc
{
  "schema": 1,
  "unternehmen_id": "U000712",          // muss zum Dateinamen passen
  "name": "Volkswagen Konzern",
  "stand": "2026-11-03", "berichtsjahr": 2025,
  "hinweis": "Freitext zu Grenzen der Daten",
  "quellen": {                           // jede Angabe verweist auf mindestens einen Schlüssel
    "gb_struktur": { "titel": "…", "url": "https://…", "herausgeber": "Volkswagen AG", "jahr": 2026, "art": "geschaeftsbericht" }
  },
  "standorte": [{
    "id": "wob", "name": "Wolfsburg (Stammwerk)", "gesellschaft": "Volkswagen AG", "marke": "Volkswagen Pkw",
    "unternehmen_id": "U000712",         // optional: verknüpft Tochterfirmen mit der Weltkugel-Suche
    "art": "hauptsitz",                  // hauptsitz | hauptsitz_tochter | fahrzeugwerk | komponentenwerk | werk | batterie | finanzen | filiale
                                         // vertrieb | entwicklung | joint_venture | beteiligung | partner | kunde | eigentuemer | lieferant
    "ort": "Wolfsburg", "land": "DE", "taetigkeit": "Was dort passiert",
    "kennzahlen": [{ "name": "Fahrzeugproduktion", "wert": 0, "einheit": "Fahrzeuge", "jahr": 2025, "quelle": "<schlüssel>", "unsicher": true }],   // Beispielwerte
    "quellen": ["gb_struktur"],
    "unsicher": true,                    // optional, Angabe nur aus Presse oder Schätzung
    "versatz": [0.15, 0],                // optional, Verschiebung lon/lat bei mehreren Standorten im selben Ort
    "lat": 52.4206, "lon": 10.7862, "koordinate": "ort"   // "ort" = Ortsmitte aus Nominatim; ohne "ort" bleibt eine Handkoordinate stehen
  }],
  "beziehungen": [{
    "von": "gyoer", "nach": "wob",
    "art": "lieferung",                  // tochter | produktion | lieferung | logistik | joint_venture | beteiligung
                                         // eigentuemer | kunde | lieferant | partner | filiale
    "text": "Audi Hungaria liefert Antriebe an Konzernwerke …", "gut": "Antriebe (Motoren und E-Antriebe)",
    "menge": { "wert": 1585290, "einheit": "Antriebe", "jahr": 2025 },   // optional, nur veröffentlichte Werte
    "anteil": 50,                        // optional, Kapitalanteil in Prozent
    "ziel_sammel": true,                 // Ziel steht stellvertretend für mehrere Werke
    "quellen": ["audi_hungaria"], "unsicher": false
  }]
}
```

## Regeln

* Nur frei zugängliche Quellen (Geschäftsberichte, Werksseiten, Pressemitteilungen, Zeitungen). Keine kostenpflichtigen Dienste.
* Jede Kennzahl hat Wert, Einheit, Jahr und Quelle. Nichts schätzen oder erfinden; Angaben nur aus Presse oder
  ohne klares Bezugsjahr bekommen `"unsicher": true` (auf der Karte gestrichelt, im Panel markiert).
* Handelsvolumina in Euro zwischen einzelnen Werken veröffentlichen die meisten Konzerne nicht. Dann nur Stückzahlen
  (Produktion, Lieferungen) angeben und das im `hinweis` sagen.
* Mengen auf einer Beziehung beschreiben genau diese Beziehung; Werksproduktion gehört in die Kennzahlen des Standorts.
