# Laufzeitwerte: Herkunft und zeitliche Gültigkeit

Stand: 04.11.2026, unveröffentlichter Entwicklungsschritt nach 0.4.0. Reine Python-APIs `core/metering.py` und `core/measurement_binding.py`: Einzelne Projektmessungen können explizit an übergebene Werte gebunden werden. Noch keine HA-Oberflächen-, Polling- oder Planungsanbindung. Sie öffnen keine Verbindung und verändern keine Geräte.

## Datenvertrag

Ein `PowerSample` enthält Netzanschluss-ID, AC-Wirkleistung in kW, Messzeit des zugrunde liegenden Werts und Empfangszeit. Jeder Messwert wird über eine kanonische Quellen-ID referenziert. Adapter müssen Einheiten und Vorzeichen vorher ausdrücklich normalisieren. Zwei Aliase desselben physischen Kanals dürfen nicht als unabhängige Quellen eingetragen werden. Unbekannte Messzeit darf nicht durch Empfangszeit ersetzt werden.

Mess- und Empfangszeit dürfen ausdrücklich unbekannt (`None`) sein. Solche Werte bleiben ungültig, ohne eine Zeit zu erfinden; die fehlende Zeit wird als `missing_time` fortgeführt. Ein fehlender bekannter Messwert unterscheidet sich weiterhin von einer unbekannten Quellreferenz in einer Formel.

`PowerFormula` beschreibt eine gewichtete Summe benannter Quellen oder weiterer Formeln, jeweils innerhalb eines Netzanschlusses. Es wird kein Ausdruckscode ausgeführt. Leere Formeln, Null-/nichtendliche Koeffizienten, unbekannte Referenzen, gemessen/berechnet-ID-Kollisionen, Kreise und mehrfach verwendete Ursprungsquellen innerhalb einer Ableitung werden abgelehnt. Grenzen: 64 verschachtelte Formeln und 128 Terme je Formel. Dieselbe Quelle darf in verschiedenen Ansichten und unabhängigen Abfragen wiederverwendet werden.

`evaluate_power` verlangt einen expliziten Auswertungszeitpunkt sowie maximale Messwertalter- und Zeitversatzgrenzen. Diese Grenzen haben keine pauschalen Vorgaben für Geräte oder spätere Regelzyklen. Zeitpunkte müssen Zeitzonen tragen und werden in UTC verglichen. Zukunftszeiten und Empfang vor Messung sind ungültig; eine Toleranz für Geräteuhrabweichungen ist derzeit nicht implementiert.

Ergebnis `PowerValue`: Leistung oder ausdrücklich kein Wert, Herkunft `measured`/`calculated`, Quellen-IDs, direkte Formel, älteste/neuste Ursprungsmesszeit und konkrete Fehlerkennungen. Eine neue Empfangszeit macht eine alte Messung nicht frisch. Abgeleitete Werte übernehmen die ursprünglichen Messzeiten. Fehlende/nichtendliche Leistung, veraltete Quellen, ungültige Zeitreihenfolge, zu großer Zeitversatz und Rechenüberlauf ergeben keinen Leistungswert; Null wird nicht als Ersatz angenommen. Unbekannte Quellreferenzen und fehlerhafte Zeittypen sind Konfigurationsfehler und lösen `ValueError` aus.

## Bilanzbeispiele und Grenzen

- Hausverbrauch aus Netz, PV und Speicher: `Haus = Netz + PV - Batterie_AC`, bei Netz positiv Bezug und Batterie positiv Laden. Lade- und Entladefälle sowie PV-Rückspeisung sind synthetisch geprüft.
- Hauptmessung und zwei unabhängige Nettozweigmessungen: `Rest = G - H - B`. Negative Reste bleiben negativ und werden nicht auf null begrenzt. Ein gemischter PV-/Speicher-/Wärmezweig wird als Nettozweig behandelt, nicht als reine PV-Erzeugung.
- Falls `G = H + B` selbst berechnet wurde, wird `G - H - B` als vermeintlicher unabhängiger Kontrollbeweis abgelehnt: H/B kommen doppelt im Ursprungsnachweis vor.

Quellenidentität ist noch kein elektrischer Abdeckungsnachweis. Verschiedene Zähler können dieselben Verbraucher enthalten: Haus-Hauptzähler plus enthaltene Wallbox oder Dreiphasensumme plus ihre Phasen dürfen nicht zusätzlich summiert werden. Das muss die spätere Projekt-/Topologiezuordnung vor Aufruf prüfen. Dieser Baustein kann solche unterschiedlichen, aber räumlich überlappenden Quellen noch nicht erkennen. Er verteilt auch keine Gesamtmessung auf einzelne Heizstäbe und beurteilt weder Verdrahtung noch Messgenauigkeit.

23 neue synthetische Tests prüfen Bilanz, Vorzeichen, Zeitgrenzen, Fehlerfortpflanzung, Quellenwiederverwendung, Tautologien, Netztrennung, nichtendliche Werte und Rekursion. Keine Messdaten oder Prognosegüte an einer realen Anlage geprüft.

## Einzelmessung an das Projekt binden

`bind_power_measurement(project, measurement_id, reading, polarity=..., now=..., max_age=..., max_skew=...)` validiert eine vollständige Projektkopie und wählt genau die referenzierte Messstelle, deren Kanal, tatsächlichen elektrischen Messknoten und Netzanschluss. Es werden keine Geräte gesucht oder abgefragt. Kanalquelle bleibt unabhängig vom elektrischen Messort.

Ein `RawPowerReading` enthält den bereits numerisch dekodierten Register-/MQTT-/HA-Wert **vor** Anwendung von `source.scale` und W→kW-Umrechnung, die ursprünglichen Zeiten und eine vom Adapter gelieferte kanonische Quellen-ID. Die Bindung führt die konfigurierte Skalierung genau einmal aus, wandelt W in kW und wendet die zwingend explizite Ausrichtung `polarity=+1/-1` an. Für HA/MQTT gibt es gemäß Format 1 keine zusätzliche `scale`-Angabe. Ein Adapter, der bereits skalierte kW liefert, darf diesen Rohwertpfad nicht ein zweites Mal verwenden. Negative Skalierung und Ausrichtung sind getrennte Faktoren; Konfiguration und tatsächliche Richtung müssen später bei Inbetriebnahme geprüft werden.

Das Ergebnis `BoundPowerMeasurement` hält Messstellen-, Kanal-, Geräte- und Messknoten-ID, Rolle, Phase, Quellbeschreibung, Ausgangseinheit, Skalierung, Ausrichtung und Empfangszeit sowie den qualitätsgeprüften `PowerValue` fest. Rollen/Phasen werden erhalten, aber weder aus Namen erschlossen noch in Einzelverbraucher aufgeteilt. Eine unkonfigurierte Quelle wird auch bei plausibel übergebenem Wert ungültig. Fehlender Wert, unbekannte Messzeit, veraltete Daten und Überlauf bleiben ausdrücklich ungültig. Projekt und Eingabe werden nicht verändert.

Kanonische Quellen-IDs werden noch nicht aus Netzwerkendpunkten, Registerbereichen oder Topicpfaden erzeugt oder auf physische Aliase geprüft. Das ist Aufgabe der folgenden Adapter-/Zuordnungsstufe: derselbe HA-Kanal über mehrere Geräteeinträge, überlappende Modbus-Register oder DNS-/IP-Aliase dürfen nicht als unabhängig bestätigt werden. Der Baustein löst keine Gatewayroute auf und erfindet keine fehlende Unit-ID. Die Quellenkonfiguration wird nur als Herkunft erhalten; Erreichbarkeit und korrekte Zuordnung des tatsächlich gelieferten Payloads sind damit noch nicht bestätigt.

26 zusätzliche synthetische Tests prüfen Projektzuordnung, W/kW, Skalierung, Ausrichtung, MQTT-Quellbeschreibung, Zeit-/Fehlerfortpflanzung und unveränderte Eingaben. Insgesamt 49 Tests für diese beiden Bausteine. Kein Live-Gerätenachweis.

Nächster Schritt: Quellenalias-/Abdeckungsprüfung und tatsächliche Messzeit aus einem ausdrücklich lesenden Adapter anbinden. Erst danach können diese Werte für Plan/Ist und späteren Regelbetrieb verwendet werden.


## Simulation mit gespeichertem Messkanal

Das HA-Panel kann auf ausdrückliche Anforderung einen numerischen Testwert über denselben Bindungsbaustein wie eine gelieferte Messung umrechnen. Die Bindung akzeptiert Projekte in Format 1 oder 2. Der Administratoraufruf prüft die gespeicherte Revision, verwendet rein synthetische Zeitangaben und liefert nur das gekennzeichnete Ergebnis. Werte, Ausrichtung und Resultat bleiben außerhalb der Projektablage und Planung.


## Modbus-Lesepfad mit eingesetztem Reader

`read_modbus_power_measurement` verbindet die Projektmessstelle mit der Kommunikationsroute. Der Reader wird vom Aufrufer anhand der Verbindungs-ID bereitgestellt. Die Zieladresse ist die ausdrücklich konfigurierte Unit-ID des Messgeräts, auch wenn der Anschluss über ein Gateway läuft. Registeradresse, Lesefunktion und Datenformat stammen aus der Kanalquelle. Die Registeranzahl stammt aus demselben Format wie die Dekodierung.

Byte- und Wortreihenfolge, Quellenidentität, Ausrichtung und Altersgrenze kommen vom Aufrufer. Die Dekodierung liefert den Rohwert. Erst die Messwertbindung rechnet einmal in kW um und wendet Faktor und Ausrichtung an. Die Empfangszeit entsteht nach der Antwort. Eine unbekannte Gerätezeit bleibt unbekannt und führt zu einem ungültigen Leistungswert. Ein gemeldeter Lesefehler oder eine fehlerhafte Registerantwort bricht die Prüfung ab.

Die Tests verwenden eingesetzte Testreader und einen synthetischen Modbus-Server auf Loopback. Damit sind Weiterleitung, Wort-/Byte-Reihenfolge, Skalierung, Zeitprüfung und Herkunft gemeinsam geprüft. Die Integration ruft den Adapter derzeit nicht auf. Für einen späteren Lesezugriff müssen die Registerbelegung und Reihenfolge des tatsächlichen Geräts sowie die Herkunft seiner Messzeit nachgewiesen sein.


Die Registergrenze wird bereits bei der Projektprüfung berücksichtigt. Bei 32-Bit-Datenformaten ist 65534 die höchste Startadresse, bei 16-Bit-Formaten 65535. Dies gilt für FC03 und FC04. Bestehende Konfigurationen mit einem überlaufenden Registerbereich müssen anhand der Geräteunterlagen korrigiert werden. Der Import meldet die betroffene Quellenadresse.


## Messstellenlesen über die HA-Grundlaufzeit — 13.11.2026

`BaseRuntime.async_read_power_measurement(...)` verbindet eine gespeicherte Modbus-Leistungsmessstelle mit dem zentralen Verbindungsbesitzer und dem vorhandenen Dekodierungs-/Bindungsadapter. Der Aufruf ist ausschließlich eine interne, ausdrückliche API. Es gibt weiterhin keinen zusätzlichen Service, WebSocket-Befehl, Zeitgeber, Live-Sensor oder automatischen Geräteabruf.

Die erwartete lokale Projektrevision muss passen. Messstellen-/Geräte-/Connection-Zuordnung, Registeradresse, FC03/04, Datentyp und Kanal-Skalierung kommen aus dem gespeicherten Projekt. Die geprüfte Byte-/Wortreihenfolge, Ausrichtung, kanonische Quellenkennung und Altersgrenze bleiben ausdrücklich anzugeben; sie werden nicht aus Gerätemarke, Connection-ID oder plausiblen Zahlen geraten. Eine nicht aufrufbare Empfangsuhr wird bereits vor dem Zugriff abgelehnt.

Der Reader-Proxy verwendet dieselbe projektrevisionsgebundene Grundlaufzeit wie ausdrückliche Registerlesungen. Ergebnisse eines geänderten Projektstands oder einer beendeten Laufzeit werden verworfen. Die Registerdekodierung liefert den Rohwert vor Kanalskalierung; der Binder wendet Skalierung, W/kW-Umrechnung und Ausrichtung jeweils einmal an. Herkunft und Messstellenbezug bleiben im Ergebnis erhalten.

Ein Registerwert beweist keine Geräte-Messzeit. Ohne eine unabhängig gelieferte Messzeit bleibt das normalisierte Ergebnis ungültig und trägt den Hinweis `missing_time`; die Empfangszeit ersetzt diesen Nachweis nicht. Es werden keine Resultate als Historie oder Plan gespeichert. Auch die lokale Projektrevision ersetzt keine erneute Prüfung möglicher externer Datenbankänderungen.

Die echte HA-Laufzeitprüfung verwendet eine reale Projektablage und synthetische Readerantworten. Sie prüft FC/Registerbreite/Zieladresse, Quellenherkunft, einzelne Skalierung und Vorzeichen, unbekannte Messzeit sowie den Projektwechsel während einer Abfrage. Tatsächliche Geräte-/Zeitparameter, eine Leseoberfläche und zentrale Messhistorien bleiben offen.
