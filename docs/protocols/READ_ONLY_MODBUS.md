# Lesende Modbus-Basis – unveröffentlichter Entwicklungsstand

Stand: 03.11.2026. Transportbibliothek ohne HA-Abhängigkeit oder zusätzliche Pakete. Nicht in Setup, Projektimport oder Hintergrundabfragen eingebunden. Kein Netzwerk-/Busscan, keine Verbindung zur Referenzanlage und keine Schreibfunktionen.

## Implementiert

`adapters/transports/modbus_tcp.py`: explizit aufgerufener nativer Modbus-TCP-Client für FC03/FC04. Ein Client serialisiert seine Abfragen und wird für mehrere Geräteadressen eines Gateways wiederverwendet. IP/Port beschreiben den Endpunkt, Unit-ID das Ziel. Ein Verbindungsmanager über mehrere Clientinstanzen ist noch nicht implementiert; pro gemeinsamem Gateway-/Buspfad eine Instanz verwenden.

Transaktionsnummer, Protokollkennung, Zieladresse, Längen und Funktionscode werden geprüft. Geräteausnahmen sind Fehler statt Messwerte; vollständige Geräteausnahmen erlauben weitere Abfragen auf derselben Verbindung. Unvollständige/ungültige Antworten, Timeout und laufender Abbruch schließen den Stream; der nächste explizite Leseaufruf verbindet neu. Abbruch eines nur wartenden Aufrufs unterbricht keine bereits laufende Transaktion. Timeout umfasst auch Warteschlange und Verbindungsaufbau. Keine automatischen Wiederholungen oder Nullwert-Ersatzmessungen.

MBAP/Unit-ID-Grundlage: [offizieller Modbus-TCP-Implementierungsleitfaden](https://www.modbus.org/docs/Modbus_Messaging_Implementation_Guide_V1_0b.pdf). Dieser Transport ist weder rohes RTU-over-TCP noch Solarman v5. USB-RS485, MQTT, weitere Transportvarianten und ein zentraler Verbindungsmanager bleiben eigene Schritte.

## Erstes Geräteprofil

`adapters/profiles/janitza_103_cbm.py`: Phasen-/Gesamtwirkleistung für UMG 103-CBM Firmware ab 2.0. Dokumentierte Big-Endian-Floatwerte ab Adresse 19020, insgesamt acht 16-Bit-Register, Einheit W → intern kW. Herstellerquelle: [Modbus-Adressenliste 2.057.005.1.e, Seite 12](https://www.janitza.com/files/download/manuals/current/UMG103-CBM/janitza-mal-umg103cbm-en.pdf). Floatwerte enthalten laut Hersteller bereits die konfigurierten Wandlerfaktoren; keine zusätzliche pauschale CT-Multiplikation.

Richtung bleibt im Gerätevorzeichen erhalten bzw. kann ausdrücklich invertiert werden. Tatsächliche Messrolle, Firmware, CT-Richtung und Adressierung müssen vor Anwendung bestätigt werden. Abfragezeit wird als `acquired_at` geführt, nicht als vom Gerät bestätigte Messzeit. Ein erfolgreicher Gatewayabruf beweist nicht das Alter eines eventuell zwischengespeicherten Werts. Kein Profil für UMG 103 ohne CBM oder Eigenmessung des 604-PRO behauptet.

## Simuliert geprüft

47 neue Tests unter `tests/test_modbus_tcp.py`, ausschließlich Server auf 127.0.0.1 mit flüchtigen Ports und frei erfundenen Testwerten. Zwei Zieladressen auf derselben Verbindung, Fragmentierung, verschiedene Byte-/Wortreihenfolgen, negative Leistung, W/kW, Geräteausnahmen, ungültige Header/Datenlängen, Verbindungsende, Timeout und Abbruch. Keine Raspberry-Pi-Laufzeitmessung oder nachgewiesene Gerätekompatibilität ableiten.

Nächste Abnahme: Status-/Fehlerdarstellung und bewusste lesende Einrichtung, zentraler Client je Verbindung, belegtes 604-Eigenprofil, Frische-/Messrollenmodell und Hardwaretest mit bestätigten lokalen Parametern. Import/Setup dürfen weiterhin keine Hardwarekommunikation als Seiteneffekt auslösen.
