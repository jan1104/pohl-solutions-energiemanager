# Zugestellte MQTT-Leistungsnachrichten zuordnen

Entwicklungsstand 18.11.2026, noch nicht im veröffentlichten HACS-Release 0.6.0. `adapters/mqtt_measurement.py` verarbeitet ausdrücklich übergebene Nachrichten. Es verbindet sich nicht mit einem Broker, abonniert keine Topics und startet keine Geräteabfrage oder Hintergrundaufgabe. Die direkte Brokeranbindung bleibt ein eigener Schritt.

## Gespeicherte Quelle und Eingabe

`bind_mqtt_power_message(...)` wählt eine gespeicherte MQTT-Leistungsmessstelle aus dem validierten Projektformat 1 oder 2. Das zugestellte Topic muss exakt der gespeicherten Quelle entsprechen. Es gibt keine automatische Bereinigung und kein Wildcard-Matching. Quelle und Feldpfad bleiben in der Messwertherkunft erhalten; die kanonische Quellenkennung muss vom späteren Adapter ausdrücklich geliefert werden, statt aus einer beliebigen Broker-Verbindung geraten zu werden.

Der Payload ist UTF-8-JSON als Text oder Bytes, höchstens 64 KiB und Tiefe 24. Doppelte Objektschlüssel, ungültiges UTF-8, nicht endliche Zahlen und mehrdeutige beziehungsweise ungültige JSON-Daten werden abgewiesen. Fehler geben keinen Payload-Inhalt aus.

Die UTF-8-Prüfung gilt auch nach der JSON-Dekodierung für sämtliche Schlüssel und Zeichenketten, einschließlich ungenutzter Metadaten. Einzelne Unicode-Surrogate aus JSON-Escapes werden abgewiesen; gültige Escape-Paare für Zeichen außerhalb der Basisebene bleiben zulässig.

Ohne `json_path` beziehungsweise bei `null` muss die JSON-Wurzel selbst eine endliche Zahl sein. Mit Pfad werden durch Punkte getrennte, wörtliche Objektschlüssel gelesen, beispielsweise `meter.power` aus `{"meter":{"power":2500}}`. Leerzeichen in Schlüsseln werden beibehalten. Leere Segmente, Array-Zugriffe, Ausdrücke und Schlüssel mit eingebettetem Punkt werden nicht als zusätzliche Pfadsprache interpretiert. Ein fehlender oder nicht numerischer Zielwert ist ein Fehler. Zeichenketten wie `"2500"`, Boolean und `null` werden nicht als Leistung umgedeutet.

## Kommunikationsweg vor dem Topic prüfen

Für Nachrichten eines Verbindungsbesitzers gibt es `bind_connected_mqtt_power_message(...)`. Zusätzlich zu den bisherigen Eingaben verlangt dieser Einstieg eine ausdrückliche `connection_id`. Er ermittelt die gespeicherte MQTT-Verbindung des Messgeräts und vergleicht sie exakt mit der zugestellten Verbindung, bevor er den Payload dekodiert. Dasselbe Topic auf einem anderen konfigurierten Broker darf dadurch keine Messstelle versorgen.

Die gemeinsame reine Routenprüfung folgt ausschließlich `via_device_id` vom Messgerät über Logger/Gateways. Im gesamten Weg muss genau eine eindeutige Verbindungskennung vorkommen; wiederholte Referenzen auf dieselbe Verbindung sind erlaubt. Fehlende oder widersprüchliche Referenzen und andere Transportarten werden abgewiesen. Elektrische `parent_id`, Messort und Bereich liefern keine Kommunikationsverbindung. Eine Modbus-Unit-ID ist für MQTT nicht erforderlich. Modbus verwendet denselben Wegprüfer und behält seine zusätzliche Pflicht zur eigenen Unit-ID.

Das unveränderliche Ergebnis enthält die aufgelöste Route und das bisherige Nachrichtenergebnis (`route`, `message`). Der bisherige `bind_mqtt_power_message(...)` bleibt die niedrigere reine Payload-/Messstellenprüfung und prüft für sich keine Brokerherkunft. Spätere Verbindungsbesitzer müssen den neuen verbindungsgebundenen Einstieg verwenden und die Verbindungskennung aus ihrer eigenen Zuordnung liefern, niemals aus einem Payload-Feld. Ein frei übergebener String beweist keine authentifizierte Brokerherkunft. Verschiedene gespeicherte Verbindungskennungen werden auch dann getrennt behandelt, wenn sie auf denselben Host zeigen; Endpunkte werden hier nicht zusammengeführt. Die kanonische physische Quellenkennung bleibt eine zusätzliche ausdrückliche Adaptereingabe.

Beide Einstiege bleiben ohne Brokerzugriff, Speicherung, Abonnement oder Hintergrundaufgabe. Eine noch unvollständige Projektverbindung lässt sich weiter konfigurieren; sie liefert über den verbindungsgebundenen Einstieg noch keinen Wert.

## Einheit, Zeit und Qualität

Der dekodierte Rohwert wird dem bestehenden Messstellen-Binder übergeben. Einheit W/kW, Ausrichtung, Messort, Phase und Quellenbezug stammen aus demselben Vertrag wie bei anderen Leistungsadaptern. Die bestehende MQTT-Quellenkonfiguration hat keinen zusätzlichen Skalierungsfaktor; der Binder verwendet Faktor 1. Es wird kein neuer MQTT-Skalierungsparameter eingeführt.

Empfangszeit, aktuelle Auswertungszeit, Altersgrenze und die Information `retained` sind ausdrückliche Eingaben. Eine unabhängig nachgewiesene Geräte-Messzeit kann übergeben werden. Fehlt diese, bleibt der Leistungswert ungültig (`missing_time`), unabhängig davon, ob die Nachricht gerade empfangen oder als retained zugestellt wurde. Zeitangaben in beliebigen Payload-Feldern werden nicht automatisch als Gerätezeit übernommen. Vorhandene veraltete oder widersprüchliche Zeitangaben werden durch die gemeinsamen Qualitätsprüfungen markiert.

Das Ergebnis enthält dekodierten Rohwert, retained-Metadatum und die gebundene Leistung mit Gültigkeit/Herkunft. Es speichert nichts in der Datenbank und gelangt nicht automatisch in einen Plan. Der spätere Verbraucher muss den Gültigkeitsstatus beachten; ein lesbarer Rohwert allein ist keine aktuelle Netzbilanz.

## Prüfung und offene Anbindung

Synthetische Tests prüfen beide Projektformate, numerische Wurzel-/Objektwerte, W/kW-Umrechnung, Quellenherkunft, unveränderte Eingaben, Topic-/Schlüssel-Leerzeichen, Grenzen, Fehlertexte und Messzeit-/retained-Fälle. Es wird kein Broker angesprochen. Noch offen: eigener Brokerbesitzer samt Start/Stop, Zugangsdatenreferenzen, Abonnements, Nachrichtenverteilung und HA-Einrichtung. Diese reine Zuordnung behauptet keine fertige MQTT-Verbindung und keine reale Gerätekompatibilität.
