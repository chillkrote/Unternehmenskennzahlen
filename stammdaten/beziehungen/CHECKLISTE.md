# Checkliste: Unternehmensnetz aus Jahresbericht und weiteren Quellen erheben

Abgeleitet aus der Auswertung Volkswagen (Berichtsjahr 2025, `daten/U000712_volkswagen.json`). Gilt für jeden Konzern;
Aufbau der Datei siehe `README.md`. Nur frei zugängliche Quellen, nichts schätzen.

## 1. Quellen in dieser Reihenfolge

| Stufe | Quelle | Was sie liefert | Kennzeichnung |
|---|---|---|---|
| A | Geschäftsbericht des Konzerns (Lagebericht und Anhang) | Struktur, Segmente, Produktion, Beteiligungen, Aktionäre | sicher |
| A | Geschäftsberichte börsennotierter Töchter (bei VW: Porsche AG, TRATON) | Werke, Stückzahlen je Modell und Werk, Absatz je Marke | sicher |
| B | Unternehmensseiten: Werks-Faktenblätter, Newsroom, „Zahlen & Fakten“ je Standort | Tätigkeit am Standort, Produktion, Beschäftigte, Gründungsjahr | sicher (Stand-Datum notieren) |
| B | Pressemitteilungen der Töchter zum Jahresergebnis (Produktion, Absatz) | Stückzahlen je Marke oder Werk | sicher |
| C | Fachpresse und Zeitungen | Werte, die das Unternehmen nicht selbst veröffentlicht (Kapazitäten, Lieferumfänge, Kunden) | `"unsicher": true` |

Bei VW verwendet: 6 Kapitel aus dem Geschäftsbericht, 20 Newsroom-Faktenblätter, Werksseiten von Audi, Pressemitteilungen
von Škoda, SEAT und TRATON, die Geschäftsberichte von Porsche und TRATON sowie 15 Presseartikel.

## 2. Im Geschäftsbericht des Konzerns durchsuchen

- [ ] **Struktur und Geschäftstätigkeit**: Konzernbereiche, Segmente, Marken, Liste der Produktionsstandorte (Anzahl, Länder), Sitz der Markengesellschaften
  Suchbegriffe: „Struktur“, „Geschäftstätigkeit“, „Produktionsstandorte“, „Marken“, „Segmente“
- [ ] **Produktion**: Fahrzeugproduktion je Region oder Land, je Marke, Komponentenwerke (Motoren, Getriebe, Batterien), Werksverbund, Werke, die für andere Marken fertigen
  Suchbegriffe: „Produktion“, „Fertigung“, „Werk“, „Standort“, „Auftragsfertigung“, „Komponenten“
- [ ] **Aktionärsstruktur**: Eigentümer mit Stimmrechtsanteil
  Suchbegriffe: „Aktionärsstruktur“, „Stimmrechte“, „Stammaktien“
- [ ] **Anhang, Konsolidierungskreis**: Tochterunternehmen, Gemeinschaftsunternehmen, assoziierte Unternehmen mit Anteil, Umsatz (100 %), Dividende an den Konzern
  Suchbegriffe: „Konsolidierungskreis“, „Gemeinschaftsunternehmen“, „assoziierte Unternehmen“, „at Equity“, „Anteilsbesitz“
- [ ] **Anhang, wesentliche Ereignisse**: Zukäufe, Anteilsänderungen, neue Beteiligungen und Partnerschaften im Berichtsjahr
  Suchbegriffe: „Erwerb“, „Beteiligung“, „Kapitalerhöhung“, „Partnerschaft“, „Joint Venture“
- [ ] **Segmentbericht**: Umsatz und Absatz je Segment oder Marke als Kennzahlen der Markenzentralen
- [ ] **Kunden und Lieferanten**: wichtige Kunden (Konzerne liefern Plattformen und Komponenten auch an Externe), Lieferantenbeziehungen, Abhängigkeiten
  Suchbegriffe: „Kunde“, „Lieferung an“, „Plattform“, „Lizenz“, „Lieferant“, „Rohstoffe“

Grafiken im Bericht sind oft Vektorpfade ohne Text. Dann die Seite als Bild rendern und ablesen und das in `hinweis` vermerken.

## 3. Je Standort erfassen

- [ ] Name, Gesellschaft, Marke, Ort, Land (ISO-2)
- [ ] Art: `hauptsitz`, `hauptsitz_tochter`, `fahrzeugwerk`, `komponentenwerk`, `werk` (Produktion außerhalb der Autoindustrie), `filiale` (Bank), `batterie`, `finanzen`, `vertrieb`, `entwicklung`, `joint_venture`, `beteiligung`, `partner`, `kunde`, `eigentuemer`, `lieferant`
- [ ] Tätigkeit in einem Satz: was dort gebaut oder geleistet wird (Modelle, Komponenten, Funktionen)
- [ ] Kennzahlen mit Wert, Einheit, Jahr und Quelle: Produktion (Stück), Beschäftigte, Anteil des Konzerns (%), Umsatz, Kapazität (nur als `geplante Kapazität`), Auslieferungen
- [ ] Unternehmens-ID, falls der Standort eine eigene Gesellschaft mit ID ist (verknüpft die Suche auf der Weltkugel)
- [ ] Stand-Datum der Quelle, wenn es vom Berichtsjahr abweicht (Faktenblätter werden laufend aktualisiert)

## 4. Je Beziehung erfassen

| Art | Bedeutung | typische Menge |
|---|---|---|
| `tochter` | Konzern hält Mehrheit | Anteil in % |
| `produktion` | Werk gehört zur Marke oder Tochter | Produktion in Stück |
| `lieferung` | Werk liefert Teile oder Fahrzeuge an ein anderes Werk | Stück (Motoren, Getriebe, Fahrzeuge) |
| `logistik` | Umschlag, Verschiffung, Verteilung | Stück |
| `joint_venture` | Gemeinschaftsunternehmen | Anteil, Umsatz (100 %), Dividende |
| `beteiligung` | Minderheitsbeteiligung | Anteil in %, Kaufpreis |
| `eigentuemer` | Großaktionär des Konzerns | Stimmrechte in % |
| `kunde` | externer Abnehmer (Plattform, Komponenten, Dienste) | Umfang, wenn veröffentlicht |
| `lieferant` / `partner` | wichtige Zulieferer, Technologiepartner | – |
| `filiale` | Filiale oder Niederlassung (Banken) | – |

- [ ] Richtung: `von` = Lieferant oder Mutter, `nach` = Empfänger oder Tochter
- [ ] Gut (was fließt) und kurzer Text
- [ ] Menge nur, wenn veröffentlicht. Handelsvolumina in Euro zwischen Werken nennen Konzerne fast nie; dann Stückzahlen angeben
- [ ] `ziel_sammel: true`, wenn ein Empfängerwerk stellvertretend für mehrere steht (z. B. „Antriebe an Konzernwerke“)

## 5. Zuverlässigkeit

- **sicher**: Geschäftsbericht, Werksseite oder Pressemitteilung des Unternehmens mit klarem Bezugsjahr
- **unsicher** (`"unsicher": true`, auf der Karte gestrichelt): nur Presse, Wert ohne klares Bezugsjahr, Plan- oder Kapazitätswerte, Angaben aus Vorjahren
- Widersprechen sich Quellen, gilt der Geschäftsbericht. Die Abweichung kommt in `hinweis`

## 6. Abschluss

- [ ] `python3 beziehungen.py koordinaten` und die Treffer prüfen (Nominatim liefert bei Bundesstaaten oft die Mitte des Staates, so bei Puebla)
- [ ] `python3 beziehungen.py pruefen` meldet 0 Fehler
- [ ] Jeder Standort hat mindestens eine Beziehung, sonst schwebt er ohne Bogen auf der Karte
- [ ] Im `hinweis` steht, was fehlt (z. B. nur die wichtigsten von über 100 Werken, keine Euro-Volumina)
- [ ] Bau und `node app/tests/netz-smoke.js app/dist/weltkugel.html`
