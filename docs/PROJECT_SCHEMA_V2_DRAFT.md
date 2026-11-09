# Entwicklungsformat 2: Anlage vor Anschluss und Messgerät

Stand 09.11.2026. Der Entwicklungsstand kann vorhandene SQLite-Projekte in Format 1 und 2 lesen und im jeweiligen Format speichern. Neue Projekte starten in Format 1. Beim Setup behält ein vorhandenes Projekt seine Version. Version 0.5.1 verwendet Format 1. Die Projektoberfläche im Entwicklungsstand unterstützt beide Formate. Die lokale Vorschau startet mit einem leeren Projekt in Format 2.

## Bestätigter Bedienablauf

1. Projekt beim Hinzufügen der Integration benennen.
2. Anlage anlegen, auch ohne Anschlüsse, Geräte oder Messwerte. Ort ist eine optionale Angabe, keine zusätzliche Pflichtstufe.
3. Anschlüsse/Abgänge benennen, etwa HAK. Ort und Beschreibung ergänzen; optionale Absicherung in A und Phasen strukturiert führen, nicht aus Freitext ableiten.
4. Messgerät hinzufügen oder vorhandenes auswählen. Dessen Kanal ausdrücklich dem Anschluss zuordnen. Fehlende Messung als unvollständigen Entwurf erhalten, ohne Platzhalter-Hardware oder Istwerte zu erfinden.
5. Weitere Geräte und gemeinsame Verbindungen referenzieren statt duplizieren.

Für Format 2 zeigt die Projektansicht zunächst „Anlage hinzufügen“. Sobald eine Anlage besteht, folgt „Netzanschluss hinzufügen“. Ort, Beschreibung, Absicherung in Ampere und Phasen stehen bei Bedarf unter „Optionale Angaben“. Ein Anschluss ohne Messung erscheint im Aufbau mit „Netzmessung offen“. Die Anlage und der Anschluss lassen sich speichern, bevor ein Messgerät zugeordnet ist.

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

Die Kopie wird gegen Format 2 geprüft. Wenn zusätzliche Metadaten die 2-MiB-Grenze überschreiten oder ungültig sind, bricht die Vorschau ab, ohne das Original zu ändern. Keine automatische Speicherung oder Downgrade-Konvertierung. `validate_project` prüft Format 1 einschließlich seiner Netzmesspflicht. Der Browser erkennt beide Formate. Im HA-Panel muss das Importformat zum geladenen Projekt passen, und der Speicher prüft zusätzlich gegen die SQLite-Schemaversion.

## Nachweis und nächster Schritt

23 neue synthetische Tests prüfen die getrennten Schritte Projekt → leere Anlage → ungemessener Anschluss, Metadaten, gemeinsame/getrennte Anschlüsse, Gatewayzuordnungen über Anlagenbereiche, Migration beider öffentlichen Beispiele, unveränderte Identitäten, Fehlzuordnungen und unveränderte Originale. Bestehende Format-1- und Python/JS-Paritätsprüfungen bleiben erfolgreich.

Die JavaScript-Entwicklungsfunktionen `validateProjectV2`, `migrateProjectV1ToV2` und `configurationIssuesV2` teilen die bestehenden elektrischen Prüfungen. Die Oberfläche verwendet die Prüfung beim Bearbeiten und nutzt einen gemeinsamen strikten Parser für beide Formate. Laufzeitübergreifende Vertragstests vergleichen Migration beider öffentlicher Beispiele und des leeren Projekts, 26 gültige/ungültige Entwürfe sowie Hinweiscodes. Zusätzliche Browserlogiktests prüfen unabhängige Kopien, ungültige JSON-Werte und die strikte Prüfung des jeweiligen Projektformats.

## Gemeinsamer JSON-Grenzvertrag (06.11.2026)

Format 2 verwendet ein identisches konservatives **2-MiB-Strukturbudget** in Python und JavaScript. Strings und Schlüssel zählen als UTF-8-JSON inklusive Anführungszeichen/Escapes; Komma und Doppelpunkt zählen je zwei Bytes, Klammern je ein Byte. Jeder Zahlenwert reserviert 32 Bytes unabhängig von `1`/`1.0` oder Exponentialschreibweise. Boolesche Werte und null zählen ihre tatsächliche JSON-Länge. Damit liegt die kompakte beziehungsweise mit Standard-Leerzeichen serialisierte Ausgabe unter dem Budget; dies ist ausdrücklich keine Größe für eingerückte Exporte. Der Dateiimport begrenzt zusätzlich den rohen Eingabetext, den auch Leerzeichen und Unicode-Escapes vergrößern können.

Alle Zahlen müssen endlich und betragsmäßig höchstens `9007199254740991` sein; beliebig große Python-Ganzzahlen werden nicht still in JavaScript gerundet. Einzelne Unicode-Surrogate in Schlüsseln/Werten werden abgelehnt; Unicode-Skalarwerte einschließlich Emoji bleiben erlaubt. JavaScript-spezifische Sparse-Arrays, Symbole und nicht aufzählbare Felder werden abgelehnt statt beim Kopieren verloren. Reine Leerraumnamen einschließlich BOM und Unicode-Aliase verbotener Geheimnisfelder werden konsistent abgelehnt.

Grenztests vergleichen exakt 2 MiB und ein Byte darüber, Zahlenbereich, Unterlauf-Minimalwert, negative Null, bool/null, Steuerzeichen/Escapes, Emoji-Schlüssel, einzelne Surrogate und unveränderte Originale. Format 1 behält sein bisheriges Verhalten. Eine Migration außerhalb des neuen Wertebereichs bricht mit Fehler ab; sie rundet oder entfernt keine Nutzerdaten. Der versionsbewusste Speichervertrag ist unten beschrieben.

## Expliziter Persistenzwechsel

`core/project_migration.py` bietet eine lesende Vorschau des aktiven SQLite-Projekts mit Dokumentrevision, Inhalts-SHA, unabhängigem Format-2-Entwurf und Konfigurationshinweisen. Der ausdrückliche Commit verlangt beide Quellkennungen und berechnet den Entwurf erneut aus dem dauerhaft gespeicherten Original; Änderungen am Vorschauobjekt werden nicht übernommen.

Der Wechsel speichert in einer Transaktion den neuen aktiven Stand, die ursprünglichen Format-1-Projektdaten unter `original_v1`, die bisherigen Legacy-Herkunftsmetadaten unverändert und einen separaten Formatwechselnachweis. Die Namespace-Schemaversion wechselt auf 2; alte Handles können danach weder lesen noch schreiben. Vorhandene Backup-/Nachweisdokumente werden nie überschrieben. Unbekannte zusätzliche Dokumente führen zu einem Konflikt, statt still verloren zu gehen. Fehler, konkurrierende Änderungen und zwischenzeitliches Ändern/Zurücksetzen (ABA) lassen das ursprüngliche Schema erhalten. Wiederöffnen unter Schema 2 ist getestet; dies ist keine vollständige Dateisicherung oder Downgradefunktion.

## Versionsbewusste Speicherung in Home Assistant

Der ProjectStore öffnet die vorhandene Namespace-Version 1 oder 2 und prüft den Dokumentinhalt gegen dieselbe Version. Ein frischer Namespace startet in Version 1. Der Formatwechsel ist eine eigene Aktion im Projektmenü. Ein leerer Namespace in Version 2 führt zu einem Fehler, auch bei vorhandener Legacy-Datei.

Für Projekte in Format 2 verwendet die HA-Speicherschicht kompaktes UTF-8-JSON. Die Exportdatei passt dadurch in das Rohtextlimit des Imports. Beide Formate teilen die Prüfung auf doppelte JSON-Schlüssel und nicht endliche Zahlen. Import und Speichern übernehmen ausschließlich Dokumente in der aktuellen Namespace-Version. Die Statusantwort zu Format 2 enthält die Anlagenanzahl und strukturierte Hinweise zu offenen Zuordnungen und Messungen. Ein veralteter Schreibzugriff nach einem Schemawechsel lädt den aktuellen Stand und meldet einen Konflikt.

Die CI-Prüfung nutzt eine temporäre SQLite-Datenbank mit Home Assistants Executor. Sie deckt expliziten Wechsel, Wiederöffnen, gleichformatigen Import, Schutz vor veralteten Schreibständen und Ablehnung unpassender Formate ab. Die Oberfläche für Anlage und Netzanschluss ist im Entwicklungsstand verfügbar. Die Netzmessung lässt sich im Aufbau oder unter Messungen zuordnen.

## Bestehendes Projekt umstellen

In Home Assistant unter **Projektoptionen → Anlagenstruktur** auf **Umstellung prüfen** klicken. Offene Bearbeitungen zuerst abschließen und speichern. Die Vorschau zeigt die geplante Struktur und offene Zuordnungen. **Verwerfen** schließt die Vorschau. **Umstellen und speichern** übernimmt den angezeigten Stand und hält das bisherige Projektdokument in der SQLite-Projektablage fest.

Beide Anfragen erfordern ein Administratorkonto. Die Bestätigung bezieht sich auf den gespeicherten Inhalt und die SQLite-Revision der Vorschau. Hat sich der Speicherstand geändert, muss er neu geladen und erneut geprüft werden. Der Formatwechsel läuft in einer Transaktion. Bei einem leeren Projekt führt der nächste Schritt direkt zur ersten Anlage. Bei einem bestehenden Projekt wird die Zuordnung zur importierten Anlage als prüfbedürftig angezeigt.

Die Browserprüfung deckte Verwerfen und Bestätigen in einer lokalen Testansicht bei 1440 und 390 Pixeln Breite ab. Die HA-Laufzeitprüfung verwendet eine separate temporäre Datenbank.


## Netzmessung zuordnen

Im Aufbau oder unter **Messungen** beim gewünschten Anschluss **Netzmessung zuordnen** wählen. Fehlt dort ein Messgerät, führt das Formular zur Anlage eines Bereichs oder Messgeräts am betreffenden Anschluss. Geräte dürfen in einem anderen Bereich desselben Netzanschlusses liegen.

Zur Auswahl stehen freie Kanäle mit der Messgröße Gesamtwirkleistung. Phasenkanäle und Kanäle mit unbekanntem Phasenbezug erscheinen nicht in der Auswahl. Alternativ lässt sich am gewählten Messgerät ein Gesamtkanal mit Name und Einheit W oder kW anlegen. Die Quelle eines neuen Kanals bleibt offen. Die Ansicht zeigt Messort, Kanal, Messgerät und gegebenenfalls den Verbindungsweg. Die Zuordnung bleibt bis zum Speichern ein Projektentwurf.

Der Assistent prüft die Projektstruktur. Die Quelle und ihre Vorzeichen- und Skalierungsregeln müssen für spätere Messwerte ausdrücklich konfiguriert und geprüft werden. Die Zuordnung öffnet keine Geräteverbindung. Desktop und Mobilansicht wurden anhand einer synthetischen Projektkonfiguration geprüft.


## Messquelle einrichten

Unter **Messungen** am gewünschten Eintrag **Quelle einrichten** oder **Quelle bearbeiten** wählen. Das Formular zeigt Kanal, Messgerät und Einheit. Für Modbus sind die dokumentierte 0-basierte Registeradresse, FC03 oder FC04 und das Datenformat erforderlich. Ein optionaler Faktor multipliziert den dekodierten Wert. Für MQTT sind das Topic und bei Bedarf der JSON-Pfad einzutragen. Für Home Assistant wird die Entitäts-ID eingetragen. Mit **Offen lassen** lässt sich die Zuordnung zurücksetzen.

**Quelle übernehmen** ändert den Projektentwurf. **Speichern** übernimmt ihn in die Projektablage. Beim Wechsel der Quellenart werden die Felder der bisherigen Quelle entfernt. Messort, Messgerät, Kanalkennung und Einheit bleiben erhalten. Das Formular konfiguriert die Herkunft. Die Verbindung, die Registerbelegung am konkreten Gerät, die Vorzeichenrichtung und die Messwertfrische müssen für spätere Lesezugriffe separat geprüft werden. Desktop und Mobilansicht wurden mit einer synthetischen Projektkonfiguration geprüft.
