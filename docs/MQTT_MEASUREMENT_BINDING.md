# Zugestellte MQTT-Leistungsnachrichten zuordnen

Entwicklungsstand 18.11.2026, noch nicht im veröffentlichten HACS-Release 0.6.0. `adapters/mqtt_measurement.py` verarbeitet ausdrücklich übergebene Nachrichten. Es verbindet sich nicht mit einem Broker, abonniert keine Topics und startet keine Geräteabfrage oder Hintergrundaufgabe. Die direkte Brokeranbindung bleibt ein eigener Schritt.

## Gespeicherte Quelle und Eingabe

`bind_mqtt_power_message(...)` wählt eine gespeicherte MQTT-Leistungsmessstelle aus dem validierten Projektformat 1 oder 2. Das zugestellte Topic muss exakt der gespeicherten Quelle entsprechen. Es gibt keine automatische Bereinigung und kein Wildcard-Matching. Quelle und Feldpfad bleiben in der Messwertherkunft erhalten; die kanonische Quellenkennung muss vom späteren Adapter ausdrücklich geliefert werden, statt aus einer beliebigen Broker-Verbindung geraten zu werden.

Der Payload ist UTF-8-JSON als Text oder Bytes, höchstens 64 KiB und Tiefe 24. Doppelte Objektschlüssel, ungültiges UTF-8, nicht endliche Zahlen und mehrdeutige beziehungsweise ungültige JSON-Daten werden abgewiesen. Fehler geben keinen Payload-Inhalt aus.

Die UTF-8-Prüfung gilt auch nach der JSON-Dekodierung für sämtliche Schlüssel und Zeichenketten, einschließlich ungenutzter Metadaten. Einzelne Unicode-Surrogate aus JSON-Escapes werden abgewiesen; gültige Escape-Paare für Zeichen außerhalb der Basisebene bleiben zulässig.

Ohne `json_path` beziehungsweise bei `null` muss die JSON-Wurzel selbst eine endliche Zahl sein. Mit Pfad werden durch Punkte getrennte, wörtliche Objektschlüssel gelesen, beispielsweise `meter.power` aus `{"meter":{"power":2500}}`. Leerzeichen in Schlüsseln werden beibehalten. Leere Segmente, Array-Zugriffe, Ausdrücke und Schlüssel mit eingebettetem Punkt werden nicht als zusätzliche Pfadsprache interpretiert. Ein fehlender oder nicht numerischer Zielwert ist ein Fehler. Zeichenketten wie `"2500"`, Boolean und `null` werden nicht als Leistung umgedeutet.

## Einheit, Zeit und Qualität

Der dekodierte Rohwert wird dem bestehenden Messstellen-Binder übergeben. Einheit W/kW, Ausrichtung, Messort, Phase und Quellenbezug stammen aus demselben Vertrag wie bei anderen Leistungsadaptern. Die bestehende MQTT-Quellenkonfiguration hat keinen zusätzlichen Skalierungsfaktor; der Binder verwendet Faktor 1. Es wird kein neuer MQTT-Skalierungsparameter eingeführt.

Empfangszeit, aktuelle Auswertungszeit, Altersgrenze und die Information `retained` sind ausdrückliche Eingaben. Eine unabhängig nachgewiesene Geräte-Messzeit kann übergeben werden. Fehlt diese, bleibt der Leistungswert ungültig (`missing_time`), unabhängig davon, ob die Nachricht gerade empfangen oder als retained zugestellt wurde. Zeitangaben in beliebigen Payload-Feldern werden nicht automatisch als Gerätezeit übernommen. Vorhandene veraltete oder widersprüchliche Zeitangaben werden durch die gemeinsamen Qualitätsprüfungen markiert.

Das Ergebnis enthält dekodierten Rohwert, retained-Metadatum und die gebundene Leistung mit Gültigkeit/Herkunft. Es speichert nichts in der Datenbank und gelangt nicht automatisch in einen Plan. Der spätere Verbraucher muss den Gültigkeitsstatus beachten; ein lesbarer Rohwert allein ist keine aktuelle Netzbilanz.

## Prüfung und offene Anbindung

Synthetische Tests prüfen beide Projektformate, numerische Wurzel-/Objektwerte, W/kW-Umrechnung, Quellenherkunft, unveränderte Eingaben, Topic-/Schlüssel-Leerzeichen, Grenzen, Fehlertexte und Messzeit-/retained-Fälle. Es wird kein Broker angesprochen. Noch offen: eigener Brokerbesitzer samt Start/Stop, Zugangsdatenreferenzen, Abonnements, Nachrichtenverteilung und HA-Einrichtung. Diese reine Zuordnung behauptet keine fertige MQTT-Verbindung und keine reale Gerätekompatibilität.
