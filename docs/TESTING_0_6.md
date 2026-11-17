# Grundversion 0.6.0 testen

Die Grundversion umfasst Projektverwaltung, Speicherung, Geräte- und Messquellenzuordnung sowie eine ausdrücklich gestartete Messsimulation. Die weiterführende Anlagenautomatik ist im Arbeitsplan beschrieben.

## Installation

1. In HACS Version **0.6.0** auswählen und Home Assistant neu starten.
2. Den bestehenden Integrationseintrag beim Update behalten. Die Browserseite anschließend neu laden.
3. Als Administrator links **Energiemanager** öffnen. Unter **Grundmodul** wird die Produktversion angezeigt.

## Neues Projekt

Beim Hinzufügen der Integration den Namen des Energiemanagers eingeben. Ein neues Projekt beginnt mit **Anlage hinzufügen**. Anschließend einen Netzanschluss wie HAK anlegen. Ort, Beschreibung, Absicherung und Phasen lassen sich bei Bedarf aufklappen. Die Daten jeweils mit **Speichern** übernehmen.

Über **Hinzufügen** einen Bereich und anschließend ein Messgerät anlegen. Bei einem Modbus-Gerät die zuvor angelegte Verbindung auswählen und die **Modbus-Geräteadresse (Unit-ID)** aus der Gerätekonfiguration eintragen. Ein leerer Wert bleibt als Entwurf offen; er wird nicht durch 1 ersetzt. Mehrere Geräte dürfen dieselbe Verbindung referenzieren, ihre Adresse wird je Gerät angegeben.

Im Aufbau am Anschluss **Netzmessung zuordnen** wählen. Ein vorhandener Gesamtwirkleistungskanal kann ausgewählt werden. Alternativ einen Kanal mit Name und Einheit W oder kW anlegen.

Unter **Messungen** die **Quelle einrichten**. Unterstützt sind die Projektangaben für Modbus, MQTT und eine HA-Entität. Diese Angaben beschreiben die Quelle. Die Grundversion ruft sie beim Speichern nicht ab.

Nach dem Speichern **Mit Testwert prüfen** wählen. Testwert vor Skalierung und Umrechnung sowie Ausrichtung angeben. Das Ergebnis ist als simuliert gekennzeichnet. Es bleibt außerhalb von Messhistorie und Planung.

## Vorhandenes Projekt

Ein bestehendes Format-1-Projekt behält zunächst seinen Stand. Unter **Projektoptionen → Anlagenstruktur → Umstellung prüfen** wird eine Vorschau erzeugt. **Verwerfen** schließt sie. **Umstellen und speichern** übernimmt Format 2 und erhält den ursprünglichen Projektinhalt unter `original_v1` in SQLite. Die importierte Anlagenzuordnung anschließend prüfen.

## Speicherung prüfen

- Speichern, HA neu starten und Namen sowie Zuordnungen vergleichen.
- Das Projekt exportieren. Den exportierten Stand über **JSON importieren** zuerst als Vorschau prüfen und bei Bedarf übernehmen.
- In zwei Browseransichten denselben Stand öffnen. In A ändern und speichern. B muss bei einem abweichenden Speicherversuch einen Konflikt melden. Den aktuellen Stand über **Gespeicherten Stand laden** vergleichen.
- Bei ungültigen Eingaben muss die Fehlermeldung sichtbar bleiben und der gespeicherte Stand erhalten sein.

Die aktive Projektablage liegt unter `.storage/pohl_solutions_energiemanager.sqlite3` im HA-Konfigurationsverzeichnis. Vorhandene ältere HA-Projektdateien bleiben bei der Übernahme erhalten. Ein vollständiges HA-Backup sichert zusätzlich die Konfigurationsumgebung. Eine Rückkehr zu Version 0.5.x kann Format-2-Projekte nicht bearbeiten.

## Umfang der Prüfung

Der Releasekandidat wird mit Python-, Browserlogik-, Archiv- und echten HA-Laufzeitprüfungen getestet. Die visuelle Prüfung verwendet synthetische Projektangaben auf Desktop und Mobil. Tests mit Modbus-Antworten verwenden einen lokalen Testserver. Tatsächliche Gerätekompatibilität und Messwertgüte benötigen eine gesonderte Prüfung mit belegten Parametern.

Der Einrichtungsablauf wurde bei Desktop- und Mobilbreite über die Browseroberfläche geprüft. Bei der ersten Prüfung des Kandidaten am 11.11.2026 schlug die Screenshotaufnahme fehl. Das ergänzte Geräteformular mit Unit-ID wurde am 12.11.2026 bei 1440 × 900 und 390 × 844 Pixeln anhand von Screenshots geprüft; das synthetische Messgerät ließ sich anschließend speichern.


## Modbus-Registerantwort ohne Gerät prüfen

Im gespeicherten Projekt muss die Messstelle eine Modbus-Quelle besitzen. Das zugehörige Gerät benötigt seine eigene Unit-ID und einen eindeutigen Kommunikationsweg; Host/Port werden für diese Simulation nicht angesprochen. Unter **Messungen → Mit Testwert prüfen** bleibt die Prüfung eines berechneten Rohwerts der Standard. Bei einer Modbus-Quelle lässt sich ausdrücklich **Registerantwort prüfen** wählen.

Die angezeigte Anzahl ganzer Registerwerte von 0 bis 65535 eingeben. Byte- und Wort-Reihenfolge anhand der Geräteunterlagen auswählen; es wird keine Reihenfolge angenommen. Die Ausrichtung ebenfalls auswählen. **Testwert berechnen** zeigt die simulierte kW-Leistung, den dekodierten Rohwert und den zugeordneten Leseweg mit Unit-ID. Die Registerwerte sind eine manuell gelieferte Testantwort, kein Telegramm und kein Nachweis für Erreichbarkeit, korrekte Verdrahtung oder aktuelle Messdaten. Es wird weder ein Gerät angesprochen noch ein Ergebnis gespeichert.

Synthetisches Beispiel: `15606, 65535` bei Datentyp `s32`, Byte-/Wort-Reihenfolge jeweils `little` ergibt −2500 als dekodierten Rohwert. Bei Einheit W, Kanalfaktor 0,5 und Ausrichtung −1 ist das Ergebnis +1,25 kW. Dieses Beispiel gehört ausschließlich zum Test und ist kein Herstellerprofil.

**Prüfstand 17.11.2026:** 418 Python-Tests und 18 Untertests sowie 83 JavaScript-Tests bestehen lokal; ein Windows-Symlinktest ist mangels Berechtigung ausgelassen und läuft auf Linux CI. Die echte HA-2026.1.0-WebSocket-/SQLite-Prüfung kontrolliert Berechtigungen, Varianten, Konflikte und unveränderte Datei. Die zuvor blockierte visuelle Prüfung konnte anschließend im wieder verfügbaren In-App-Browser abgeschlossen werden: Desktop 1440 × 900 und Mobil 390 × 844, synthetischer Registertest mit +1,25 kW, wiederholtes Berechnen und Wechsel zur einfachen Rohwertprüfung mit −1,25 kW. Es wurde eine lokale HA-Oberflächen-Testumgebung mit synthetischen Antworten verwendet, keine reale Anlage.
