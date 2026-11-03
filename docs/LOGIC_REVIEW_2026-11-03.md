# Logikprüfung vom 03.11.2026

Prüfgrundlage: Commit `e02b711`, Quellcode von Rechenkern, HA-Koordinator und Lastprognose sowie vorhandene Tests/Dokumentation. Keine Prüfung an Live-Geräten und kein Nachweis realer Einsparung. Die folgenden Gegenbeispiele wurden mit dem lokalen Rechenkern ausgeführt.

## Nachgewiesene Probleme und Einschränkungen

### P1: Festes Endziel kann die Nachtentladung verhindern

Der HA-Koordinator setzt `terminal_soc_pct` stets gleich dem gerade gemessenen SOC. Ohne spätere Lademöglichkeit muss der Speicher seinen Anfangsinhalt behalten. Beispiel: 200,704 kWh, Start 50 %, 4 Stunden ohne PV, 20 kW Hauslast, Bezug 0,40 EUR/kWh, Netzladen aus. Ergebnis: 0 kWh Entladung, 32 EUR Bezugskosten. Das erfüllt den gewünschten Nachtbetrieb nicht.

Aufgabe: Rollierenden Horizont, Mindestreserve und wirtschaftlichen Wert der Restenergie gemeinsam entwerfen. Einfaches Absenken des Endziels auf Minimum kann den gegenteiligen Fehler auslösen: Entladung kurz vor Horizontende trotz später wertvollerer Verwendung. Änderung braucht Vergleichsfälle über mehrere Planungstage und wiederholte Neuplanung.

### P1: Grobes SOC-Raster übersieht kleine Leistungen

Bei 2 kWh Zustandsabstand ist ein üblicher Viertelstundenverbrauch oft kleiner als der nächste mögliche Energieschritt. Beispiel: dieselbe Batterie, 50 % Start, 10 % Endziel, 1 kW Hauslast über 16 Viertelstunden, keine PV, 0,40 EUR/kWh. Ergebnis: 0 kWh Entladung, 1,60 EUR Bezug, obwohl ausreichend nutzbare Energie vorhanden ist. Das Raster verhindert hier die Handlung.

Aufgabe: Verfahren auswählen, das kleine Leistungen korrekt abbildet und auf HA-Hardware schnell bleibt. Nicht lediglich das Raster beliebig verfeinern: Aufwand und Zustandsgrenze beachten. Gegen kontinuierlicher Referenzrechnung und einfachen analytischen Fällen prüfen.

### P1 vor späterem Regelbetrieb: Kein geschlossener Regelkreis

HA liest eine bereitgestellte Prognose und den SOC. Ausgewählte Netz-/PV-/Lastsensoren werden bisher nur zugeordnet. Es gibt keine laufende Überschussnachführung und keine Gerätebefehle. Der Fünf-Minuten-Abruf ist kein schneller Regler. Die Software ist ausdrücklich noch kein funktionsfertiges Anlagen-EMS.

Aufgabe: Messstellenbilanz, Plan/Ist-Abweichungen, schnelle Begrenzung und einmaligen Schreibverantwortlichen definieren; zunächst simulieren. Dynamische BMS-/Spannungsgrenzen, Anschlusslimits und tatsächliche Reaktion nachweisen.

### P2: Prognosequalität und dynamische Anpassung noch unbelegt

Die Lastprognose ist eine separat testbare historische Vergleichshilfe. Sie erstellt bisher nicht automatisch die HA-Planungsdaten. Historische Streubänder sind keine kalibrierten Wahrscheinlichkeiten. Ein angebundener PV-Prognoseadapter und reale rollierende Rücktests fehlen.

Aufgabe: Private Messhistorie sauber importieren, ohne Zukunftsdaten zu trainieren; naive Vergleichsprognosen und Planungsergebnisse rücktesten. Wetterdienst auswählen statt Wetterdaten zu erfinden.

### P2: Fehlerfälle und Datenfrische benötigen einen Betriebsentwurf

Ungültige Daten ergeben sichtbar einen ungültigen Plan statt erfundener Ersatzwerte. Gut für Simulation, aber noch keine beschlossene Betriebsstrategie. HA-Meldezeit beweist nicht das Alter der zugrunde liegenden Messung. SOC außerhalb des konfigurierten Fensters wird abgelehnt; Wiederanlauf unter einer betrieblichen Reserve ist noch nicht modelliert.

Aufgabe: Messzeit und Meldezeit unterscheiden, Datenqualität je Quelle führen, eingeschränkte Planung und späteren Geräte-Rückfall ausdrücklich definieren. Physische Schutzgrenzen von betrieblichen Wunschreserven trennen.

### P2: Restenergie und Baseline müssen wirtschaftlich fair sein

Der aktuelle Vergleich ist eine ungenutzte Batterie auf Anfangs-SOC. Bei anderem End-SOC wird die Vergleichbarkeit bereits ausdrücklich eingeschränkt. Für Verkaufserlöse und Tagesberichte reichen solche Szenariodifferenzen nicht als Einsparnachweis.

Aufgabe: Gleichwertige Anfangs-/Endbestände oder transparent bewertete Restenergie, getrennte Prognose- und Ist-Berichte; Verluste, Energieeinkauf und Verschleiß jeweils nur einmal verrechnen.

## Plausible vorhandene Grundlagen

- AC-Bilanz: Netzleistung = Hauslast − PV + Batterieladeleistung; physische Grenzen und Wirkungsgrade werden im diskreten Modell berücksichtigt.
- Bezug und Einspeisung besitzen getrennte Preise; negative Werte und explizite Einheiten sind vorgesehen.
- Kein doppelter Bezug für PV-Überschussladung: Entscheidend ist die gemeinsame Netto-Netzbilanz.
- Investitionsumlage und marginaler Verschleiß sind getrennt. Herstellerzyklen sind abhängig vom verwendeten SOC-Fenster und keine allgemeine Chemiegarantie.
- Zeitstempel und zusammenhängende Horizonte werden in UTC geprüft; Zeitumstellung hat Tests.
- Keine heimlichen Live-Schreibzugriffe und keine synthetischen Ersatzpreise bei fehlenden Echtdaten.

Diese Prüfung ersetzt weder eine vollständige Verifikation noch Hersteller-/Vertragsprüfung. Die Arbeitsliste beschreibt überprüfbare nächste Schritte, keine bereits verfügbaren Fähigkeiten.
