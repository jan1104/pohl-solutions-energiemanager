# Transport, Messgeräte und Rückmeldung

Stand: 03.11.2026. Dokumentenprüfung; keine Netzwerk-/Busabfrage, keine Inbetriebnahme und keine Gerätebefehle. Modellprofile müssen vor Einsatz zur tatsächlichen Hardware/Firmware passen.

## Modbus: Verbindung und Gerät getrennt behandeln

Der [offizielle TCP-Implementierungsleitfaden](https://www.modbus.org/docs/Modbus_Messaging_Implementation_Guide_V1_0b.pdf), Abschnitt Unit Identifier, beschreibt IP als Adresse eines Gateways und Unit-ID zur Weiterleitung an ein serielles Ziel. Deshalb ist ein Geräte-Endpunkt nicht allein eine IP, sondern beispielsweise Verbindung + Zieladresse + Registerprofil. Der konkrete Gatewaymodus entscheidet über Port und Adressierung; direkte TCP-Geräte können andere Unit-ID-Regeln verwenden.

Der [serielle Modbus-Leitfaden V1.02](https://www.modbus.org/file/secure/modbusoverserial.pdf), Abschnitte 2.1/2.2, beschreibt einen Master mit mehreren adressierten Slaves. Ein zusätzlicher USB-RS485-Adapter am selben aktiven Masterbus ist kein paralleler lesender Zugang. Gateway oder abgestimmte einzige Busverwaltung nutzen.

Für den Energiemanager folgt daraus:

- Gemeinsame Verbindung pro physischem Bus/Gateway, darunter mehrere separat identifizierte Geräte.
- Busabfragen koordinieren, Timeout und Warteschlange begrenzen; nicht jedes logische Gerät mit unabhängigem Poller gegen denselben Bus betreiben.
- Registerprofil gehört zum Zielgerät, nicht automatisch zum Gateway. Gateway-Eigenmessung und durchgereichte Messung unterscheiden.
- Adressbasis, Funktionscode, Datentyp, Wort-/Bytefolge, Einheit und Vorzeichen ausdrücklich speichern.
- Nur dokumentierte Lesezugriffe bei Erkennung. Keine Broad­cast-Schreibtests oder automatische Änderung serieller Parameter.
- TCP-Erreichbarkeit bedeutet weder bekannte Gerätemarke noch Schreibfreigabe. RTU-over-TCP und natives Modbus TCP benötigen getrennte Treiberoptionen, falls ein Gateway dies verlangt.

## Eastron SDM630-Modbus

Primärquelle: [Eastron SDM630 Modbus Protocol Implementation V1.8](https://www.eastroneurope.com/images/uploads/products/protocol/SDM630_MODBUS_Protocol.pdf), insbesondere Abschnitt 1.1–1.3. Herstellerdownloadverzeichnis: https://www.eastrongroup.com/download/.

Das geprüfte Protokoll dokumentiert RS485/Modbus RTU, Messwerte über FC04 und Float32-Werte in zwei Registern. Daten umfassen Spannung/Strom je Phase, Wirk-/Blind-/Scheinleistung, Leistungsfaktor, Frequenz und Energiezähler für Bezug/Einspeisung. Registerorder und Verdrahtungsart beachten. V1.8 nennt maximal 40 Messwerte/80 Register je Abfrage; nicht unbesehen auf andere SDM-Varianten übertragen.

Konfigurationsregister sind keine Energiefluss-Sollwerte. Ein Energiezähler schaltet durch ein schreibbares Register nicht automatisch Lasten. SDM630-Modbus V2, MCT, TCP und M-Bus sind unterschiedliche Varianten; Produktbezeichnung und passende Version vor Implementierung bestätigen.

Für einen bereits direkt von einem WR abgefragten Zähler zunächst die Messung über dokumentierte WR-/Gateway-Daten oder eine unabhängige Messstelle beziehen. Kein zweiter RTU-Master am Zählerbus. Quelle und Datenalter müssen sichtbar bleiben.

## Shelly: Fähigkeiten statt pauschaler Markentreiber

Primärquellen:

- [Gen2+ EM](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/EM/): EM.GetStatus und Komponentenstatus für Messung.
- [EMData](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/EMData/): Energiezähler und vorhandene historische Messdaten.
- [Switch](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/): Switch.Set und Status für Geräte mit Switch-Komponente.
- [MQTT](https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Mqtt/): RPC und Statusmeldungen über konfigurierten Broker.
- [Gen1 API](https://shelly-api-docs.shelly.cloud/gen1/): separat prüfen; keine Gen2-Payloads voraussetzen.

EM-Status liefert unter anderem phasenbezogene elektrische Werte und Summen; EMData führt Bezug-/Rückspeiseenergie pro Phase. Switch ist eine eigene Fähigkeit, nicht implizit in jeder Messeinheit enthalten. Für reale Hardware Komponentenbestand und Messmodus auslesen; generische drei Kanäle nicht ohne Verdrahtungsnachweis in drei unabhängige Verbraucher umdeuten.

Die MQTT-Komponente dokumentiert Statusmeldungen und RPC-/Control-Wege. Aktivierung, Topic-Präfix und tatsächliche Komponenten sind gerätespezifisch zu prüfen. Ein MQTT-Gerät wird über Broker/Topics erreicht, nicht durch eine generische Modbus-IP-Suche. Der Hersteller dokumentiert keine universelle Struktur für beliebige andere MQTT-Geräte.

Die gewünschte Gerätekonfiguration kann daher Messung, Freigabe und ggf. Leistungsvorgabe separat zuordnen. Für Wiederholungen explizite Ein-/Aus-Werte statt blindem Toggle bevorzugen. Befehlsannahme, bestätigten Gerätezustand und gemessenen Verbrauch getrennt anzeigen. Retained-/alte Nachrichten nicht ungeprüft als aktuelle Messung oder neue Freigabe verwenden.

## Abnahme eines Geräteprofils

1. Modell/Firmware/Schnittstellenversion dokumentieren; Herkunft der Register oder Topicstruktur hinterlegen.
2. Identität, Einheiten und Vorzeichen anhand aufgezeichneter Leseantworten prüfen; keine privaten Rohdaten in Git.
3. Rollen der Messkanäle zuordnen und Bilanz mit unabhängiger Messung vergleichen.
4. Timeout, Unterbrechung, Datenalter und Wiederverbindung simulieren.
5. Steuerfunktionen separat dokumentieren und erst nach späterer Freigabe an Hardware prüfen; bisherige Funktionen bleiben lesend/simuliert.

Ein validiertes Transportmodul ersetzt keine Modellprüfung. Fehlende Modellunterlagen bedeuten „Profil offen“, nicht erfundene Register.
