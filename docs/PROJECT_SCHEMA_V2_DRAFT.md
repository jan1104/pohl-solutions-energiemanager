# Entwicklungsformat 2: Anlage vor Anschluss und Messgerät

Stand: 05.11.2026. Reiner Modell-/Migrationsbaustein in `core/project_v2.py`, noch nicht in HA, SQLite-Projektübernahme oder Oberfläche aktiviert. Version 0.5.1 verwendet weiterhin Format 1. Kein Release, keine Geräteabfrage und keine automatische Umschreibung bestehender Daten.

## Bestätigter Bedienablauf

1. Projekt beim Hinzufügen der Integration benennen.
2. Anlage anlegen, auch ohne Anschlüsse, Geräte oder Messwerte. Ort ist eine optionale Angabe, keine zusätzliche Pflichtstufe.
3. Anschlüsse/Abgänge benennen, etwa HAK. Ort und Beschreibung ergänzen; optionale Absicherung in A und Phasen strukturiert führen, nicht aus Freitext ableiten.
4. Messgerät hinzufügen oder vorhandenes auswählen. Dessen Kanal ausdrücklich dem Anschluss zuordnen. Fehlende Messung als unvollständigen Entwurf erhalten, ohne Platzhalter-Hardware oder Istwerte zu erfinden.
5. Weitere Geräte und gemeinsame Verbindungen referenzieren statt duplizieren.

Dieser Modellschritt ersetzt den aktuellen UI-Startknopf noch nicht. Als Nächstes muss die durchgehende Bedienung „Anlage hinzufügen“ umgesetzt werden.

## Modell

Root entspricht Format 1 mit `schema_version: 2` und zusätzlicher Sammlung `plants`. Anlage ist organisatorisch; Netzanschluss bleibt elektrische Bilanz-/Tarifgrenze.

- `plants`: erforderliche `id`, `name`, `grid_ids` (eindeutige vorhandene Netzanschluss-IDs, darf leer sein). Optional `description` (2048 Zeichen), `location` (512) und `assignment_confirmed` (bool).
- Ein Netzanschluss kann mehrere Anlagen versorgen. Eine organisatorische Anlage kann getrennte Anschlüsse referenzieren; deren Bilanzen bleiben getrennt. Jeder bestehende Anschluss braucht mindestens eine Anlagenzuordnung.
- `areas`: zusätzlich erforderliches `plant_id`. Der Netzanschluss des Bereichs muss auch von seiner Anlage referenziert werden. Verbindungen bleiben unabhängig davon projektweit verfügbar.
- `nodes`: optional `description`, `location`, `fuse_a` (endlich, positiv, A) und `phases` (1 oder 3). Diese Konfiguration ist weder Verdrahtungsnachweis noch schon vom Planer durchgesetzte Anschlussbegrenzung.
- Ohne primäre Netzmessung bleibt ein Anschluss ein gültiger Entwurf. Baum-, Kanal-, Geräte-, Gateway- und Messrollenprüfung sowie der Schutz vor doppelter Primärzuordnung bleiben erhalten.
- Weiterhin 2 MiB, begrenzte JSON-Tiefe und keine Geheimnis-/Steuerfreigabefelder. Maximal 500 Anlagen zusätzlich zu höchstens 2000 bisherigen Fachobjekten, also maximal 2500 insgesamt.

`configuration_issues_v2` meldet unbestätigte Anlagenzuordnung, fehlende primäre Netzmessung und Messstellen mit unkonfigurierter Quelle. Keine Aussage über Datenfrische, Prognose, Planbarkeit oder Steuerfreigabe. Auch ein leeres Projekt ohne solche Hinweise ist keine betriebsbereite Anlage.

## Explizite Vorschau-Migration

`migrate_project_v1_to_v2` validiert das Original vollständig und erstellt eine unabhängige Kopie. Ein leeres Projekt bleibt ohne erfundene Anlage leer. Vorhandene Struktur erhält einen einzigen Container „Importierte Anlage“, ausdrücklich `assignment_confirmed: false`. Standorte werden nicht aus Netz-/Bereichsnamen geraten.

Alle bisherigen elektrischen IDs, Grenzen, Messungen, Gateway-/Verbindungspfade, Batterie-WR-Beziehungen und Einstellungen bleiben erhalten. Bereiche erhalten nur die Anlagenreferenz. Mehrere ursprüngliche Netzanschlüsse werden nicht zu einem Anschluss zusammengeführt.

Die Kopie wird gegen Format 2 geprüft. Wenn zusätzliche Metadaten die 2-MiB-Grenze überschreiten oder ungültig sind, bricht die Vorschau ab, ohne das Original zu ändern. Keine automatische Speicherung oder Downgrade-Konvertierung. Der bisherige `validate_project` und alle HA-/Browserimporte bleiben strikt Format 1 einschließlich seiner bisherigen Netzmesspflicht.

## Nachweis und nächster Schritt

23 neue synthetische Tests prüfen die getrennten Schritte Projekt → leere Anlage → ungemessener Anschluss, Metadaten, gemeinsame/getrennte Anschlüsse, Gatewayzuordnungen über Anlagenbereiche, Migration beider öffentlichen Beispiele, unveränderte Identitäten, Fehlzuordnungen und unveränderte Originale. Bestehende Format-1- und Python/JS-Paritätsprüfungen bleiben erfolgreich.

Nächster zusammenhängender Schritt: JavaScript-Prüfung/Vorschau ergänzen, versionierten Persistenzwechsel mit Konflikt-/Neustarttests entwickeln und danach die minimale UI samt Messgerätezuordnung anbinden. Erst nach durchgehender Prüfung ein testbares Paket anbieten. Kein Vorziehen der Modellaktivierung.
