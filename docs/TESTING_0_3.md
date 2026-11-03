# Erste Testversion 0.3.0

Diese Version macht die Projektstruktur und Datenzuordnung prüfbar. Sie ist noch kein aktiver Anlagenregler. Keine Geräte werden gesucht, gelesen oder geschaltet. Die neue Mehrgeräte-Projektstruktur ist noch nicht mit einer gemeinsamen Mehrspeicheroptimierung verbunden; der bisherige Einzelbatterie-Rechner bleibt eine separate Simulation mit den in LOGIC_REVIEW_2026-11-03.md beschriebenen Grenzen.

## Ohne Installation ausprobieren

1. Testpaket vollständig entpacken.
2. `preview/project.html` im Browser öffnen. Alle benötigten Dateien liegen im Paket, keine Internetverbindung erforderlich.
3. „Referenzbeispiel ansehen“ wählen und in der Vorschau „ausdrücklich übernehmen“. Das Beispiel ist anonymisiert; Endpunkte, Register und Tarife bleiben unbekannt, statt sie zu erfinden.
4. Zwischen „Elektrischer Aufbau“, „Kommunikationswege“ und „Messquellen“ wechseln.
5. Projekt und einzelne Objekte benennen; über „Lokal speichern“ im aktuellen Browser speichern oder als JSON exportieren.
6. Exportierte Datei erneut importieren, Vorschau prüfen und übernehmen. Browserstand und importierte Vorschau sind bis zur Übernahme getrennt.

Im persönlichen Testpaket liegt zusätzlich `beispiele/feuerwehr-heizzentrale.json`. Diese lokale Struktur verwendet die besprochenen Bereichsnamen; sie enthält keine erfundenen Livewerte, IPs oder Register und keine Zugangsdaten. Sie ist kein geprüftes Inbetriebnahmeprojekt. Die öffentlich versionierten Beispiele verwenden neutrale Namen.

Dateien gleichen Formats können im aufklappbaren JSON-Editor bearbeitet werden. Geräte hinzufügen oder Messquellen ändern geht in diesem ersten Stand über den validierten Editor; ein grafischer Geräteassistent und Gerätesuche folgen. Noch nicht eingerichtete Quellen werden sichtbar angezeigt. Browser-Speicherung kann je nach Browser eingeschränkt sein; JSON-Export ist die übertragbare Konfiguration.

## Was wir gemeinsam prüfen können

- Netzanschluss und die beiden Bereiche gehören zusammen.
- Vier bestehende PV-WR bleiben getrennt vom zusätzlich nachgerüsteten Speicher-WR.
- Batterietürme gehören zum Speicher-WR.
- Die 103er sind über den 604 erreichbar, aber messen andere elektrische Zweige.
- Ladestationen sind im Hauszweig enthalten; gemeinsame Heizmessung ist keine Einzelmessung jedes Heizstabs.
- Referenzprojekt exportieren, Namen ändern, importieren; Beziehungen und Anzahl bleiben erhalten.
- Absichtlich ungültigen Verweis im Editor eintragen: verständlicher Fehler, bisheriges Projekt unverändert.

## Home Assistant auf einer Testinstanz

1. Ordner `custom_components/pohl_solutions_energiemanager` in den `custom_components`-Ordner der Testinstanz kopieren und HA neu starten.
2. Integration über Geräte & Dienste hinzufügen. „Nur Projektverwaltung – noch keine Prognose/SOC erforderlich“ einschalten. Für diesen Modus müssen keine Sensorsignale erfunden werden.
3. In Entwicklerwerkzeuge → Aktionen `pohl_solutions_energiemanager.import_project` auswählen und den vollständigen JSON-Dateiinhalt im Feld `project_json` übergeben. Import ersetzt das eine gespeicherte Projekt; bei Bedarf vorher exportieren. Ein Projekt kann mehrere Netzanschlüsse und Bereiche enthalten.
4. `pohl_solutions_energiemanager.project_status` liefert Status, Objektanzahl und offene Zuordnungen.
5. `pohl_solutions_energiemanager.export_project` liefert den gespeicherten Inhalt als `project_json`. Dieses JSON ist wieder in der Browser-Projektverwaltung importierbar.

Die beiden Abfrageaktionen liefern eine Antwort und werden mit Antwortanforderung aufgerufen; in Entwicklerwerkzeuge → Aktionen die Antwort anzeigen lassen. Import unterstützt ebenfalls eine Antwort. Beispiel für eine Aktion mit Antwortvariable in einem HA-Skript:

```yaml
action: pohl_solutions_energiemanager.export_project
response_variable: projekt_export
```

Ein ungültiger Import wird abgelehnt. Die Speicherung wird geprüft, bevor der aktive Projektstand ersetzt wird. Der Statussensor zeigt im Projektmodus „Projektverwaltung“. Bestehende Planungsinstanzen mit Prognose/SOC können weiter genutzt werden; sie planen nicht automatisch die importierte Mehrgeräte-Konfiguration.

Die Browseroberfläche ist in 0.3 noch eine separate lokale Seite. Sie synchronisiert nicht automatisch mit HA. Der Transfer erfolgt über dasselbe JSON-Format. Ein integriertes HA-Panel ist weitere Arbeit, kein bereits vorhandenes Feature.

## Entwicklung prüfen

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
node --test preview/test-preview.cjs preview/test-project.cjs
.venv/Scripts/python.exe tools/project.py validate examples/reference-project.json
.venv/Scripts/python.exe tools/project.py roundtrip examples/reference-project.json --output outputs/projekt-kopie.json
```

Beim CLI-Roundtrip muss der Ausgabeordner vorhanden sein. JSON-Importlimit 2 MiB; Formatversion 1. Unbekannte Versionen/Felder, defekte Beziehungen, Kreise, doppelte Hauptquellen, unpassende Einheiten, definierte Zugangsdatenfelder und Steuerfreigaben werden abgelehnt. Beliebiger Text wird nicht automatisch von persönlichen Informationen bereinigt; reale Konfiguration nur privat speichern.
