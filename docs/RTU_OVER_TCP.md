# Lesendes RTU über TCP

Stand: 13.11.2026. `adapters/transports/rtu_over_tcp.py` implementiert einen transparenten TCP-Tunnel für rohe Modbus-RTU-Frames. Die gemeinsame Verbindungsverwaltung verwendet ihn für die vorhandene Projekt-Verbindungsart `rtu_over_tcp`. Kein automatischer Abruf in HA und keine Live-Geräteprüfung.

## Abgrenzung bei der Einrichtung

- **Modbus TCP / TCP→RTU-Gateway:** Der Energiemanager sendet MBAP-Frames. Das Gateway übernimmt die Umsetzung zum seriellen Bus.
- **RTU über TCP:** Der Energiemanager sendet Geräteadresse, Funktionsdaten und RTU-CRC direkt durch einen transparenten Tunnel. Host und TCP-Port müssen ausdrücklich angegeben sein. Es wird kein Port geraten und kein anderes Protokoll ausprobiert.
- **RS485 über USB:** Noch kein implementierter Transport. Ein TCP-Tunnel ist kein Nachweis für direkten seriellen Betrieb.

Die Verbindung wird einmal angelegt. Geräte referenzieren dieselbe Verbindung und besitzen ihre eigene Unit-ID von 1 bis 247. Konfigurationsaliase mit identischem normalisiertem Host und Port teilen eine Verbindung und Warteschlange. Widersprüchliche MBAP-/RTU-Einträge für denselben erkennbaren Endpunkt werden vor der ersten Abfrage abgewiesen. Unterschiedliche DNS-Namen beziehungsweise Hostname/IP-Aliase werden weiterhin nicht durch Netzwerkabfragen aufgelöst.

## Lesevertrag und Fehler

Nur FC03 und FC04, höchstens 125 Register und keine überlaufenden Adressbereiche. Keine Broadcast-Adresse, direkte TCP-Adresse 255, Schreibfunktion, Suche oder Hintergrundwiederholung. Antworten werden auch bei TCP-Fragmentierung vollständig gelesen. Geräteadresse, Funktion, Datenlänge und CRC müssen passen. Nur eine vollständige CRC-geprüfte Modbus-Ausnahmeantwort darf dieselbe Verbindung weiterverwenden. Unvollständige/ungültige Antworten, Timeout und Abbruch während einer Abfrage verwerfen den Stream. Erst ein neuer ausdrücklicher Aufruf verbindet erneut. Ein einzelnes Zeitbudget umfasst Warteschlange, Verbindungsaufbau und Antwort.

RTU besitzt hier keine MBAP-Transaktionskennung. Deshalb bleibt höchstens eine Abfrage pro gemeinsamem Stream aktiv. Eine passende CRC bestätigt kein Messwertalter: zwischengespeicherte Tunnelantworten werden dadurch nicht als frisch erkannt. Empfangszeit darf weiterhin keine unbekannte Geräte-Messzeit ersetzen. Der externe Tunnel muss seinen seriellen Bus samt Baudrate, Parität, Buszugriff und RTU-Zeiten korrekt behandeln. Diese Implementierung weist keine physische RS485-Konformität oder Kompatibilität mit einem bestimmten Gateway nach. Ein RTU-Bus darf weiterhin nur einen Master haben.

Framing und CRC orientieren sich an der **Modbus Serial Line Specification and Implementation Guide V1.02**, insbesondere Abschnitt 2.5.1.2: CRC über die Nachricht, Übertragung des niederwertigen CRC-Bytes zuerst. Offizielle Quelle: [Modbus-Spezifikationen](https://www.modbus.org/modbus-specifications). Die transparente TCP-Übertragung ist eine ausdrücklich gewählte Tunnelanwendung; sie wird nicht als offizielles Modbus-TCP-Framing ausgegeben.

## Prüfung und nächste Schritte

Synthetische Loopback-Tests prüfen CRC-Testvektoren, FC03/04, die höchste Registeradresse, fragmentierte Antworten, gemeinsam genutzte Alias-Verbindungen, Fehlerantworten, ungültige Frames, Timeout/Abbruch und ausdrückliche Wiederverbindung. Tests der Eingabegrenzen und Protokollkonflikte bestätigen, dass keine Netzwerkverbindung geöffnet wird. Eine echte Anlage wurde nicht angesprochen.

Offen: HA-Lebensdauer und bewusst ausgelöste Leseprüfung in der Oberfläche, belegte Gatewayparameter, physische Tests sowie die übrigen Transportarten. Import, Einrichtung und Speichern starten keine Verbindung.
