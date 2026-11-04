# Laufzeitwerte: Herkunft und zeitliche Gültigkeit

Stand: 04.11.2026, unveröffentlichter Entwicklungsschritt nach 0.4.0. Die reine Python-API `core/metering.py` ist noch nicht an Projektformat, HA-Oberfläche, Polling oder Planung angeschlossen. Sie öffnet keine Verbindung und verändert keine Geräte.

## Datenvertrag

Ein `PowerSample` enthält Netzanschluss-ID, AC-Wirkleistung in kW, Messzeit des zugrunde liegenden Werts und Empfangszeit. Jeder Messwert wird über eine kanonische Quellen-ID referenziert. Adapter müssen Einheiten und Vorzeichen vorher ausdrücklich normalisieren. Zwei Aliase desselben physischen Kanals dürfen nicht als unabhängige Quellen eingetragen werden. Unbekannte Messzeit darf nicht durch Empfangszeit ersetzt werden.

`PowerFormula` beschreibt eine gewichtete Summe benannter Quellen oder weiterer Formeln, jeweils innerhalb eines Netzanschlusses. Es wird kein Ausdruckscode ausgeführt. Leere Formeln, Null-/nichtendliche Koeffizienten, unbekannte Referenzen, gemessen/berechnet-ID-Kollisionen, Kreise und mehrfach verwendete Ursprungsquellen innerhalb einer Ableitung werden abgelehnt. Grenzen: 64 verschachtelte Formeln und 128 Terme je Formel. Dieselbe Quelle darf in verschiedenen Ansichten und unabhängigen Abfragen wiederverwendet werden.

`evaluate_power` verlangt einen expliziten Auswertungszeitpunkt sowie maximale Messwertalter- und Zeitversatzgrenzen. Diese Grenzen haben keine pauschalen Vorgaben für Geräte oder spätere Regelzyklen. Zeitpunkte müssen Zeitzonen tragen und werden in UTC verglichen. Zukunftszeiten und Empfang vor Messung sind ungültig; eine Toleranz für Geräteuhrabweichungen ist derzeit nicht implementiert.

Ergebnis `PowerValue`: Leistung oder ausdrücklich kein Wert, Herkunft `measured`/`calculated`, Quellen-IDs, direkte Formel, älteste/neuste Ursprungsmesszeit und konkrete Fehlerkennungen. Eine neue Empfangszeit macht eine alte Messung nicht frisch. Abgeleitete Werte übernehmen die ursprünglichen Messzeiten. Fehlende/nichtendliche Leistung, veraltete Quellen, ungültige Zeitreihenfolge, zu großer Zeitversatz und Rechenüberlauf ergeben keinen Leistungswert; Null wird nicht als Ersatz angenommen. Unbekannte Quellreferenzen und fehlerhafte Zeittypen sind Konfigurationsfehler und lösen `ValueError` aus.

## Bilanzbeispiele und Grenzen

- Hausverbrauch aus Netz, PV und Speicher: `Haus = Netz + PV - Batterie_AC`, bei Netz positiv Bezug und Batterie positiv Laden. Lade- und Entladefälle sowie PV-Rückspeisung sind synthetisch geprüft.
- Hauptmessung und zwei unabhängige Nettozweigmessungen: `Rest = G - H - B`. Negative Reste bleiben negativ und werden nicht auf null begrenzt. Ein gemischter PV-/Speicher-/Wärmezweig wird als Nettozweig behandelt, nicht als reine PV-Erzeugung.
- Falls `G = H + B` selbst berechnet wurde, wird `G - H - B` als vermeintlicher unabhängiger Kontrollbeweis abgelehnt: H/B kommen doppelt im Ursprungsnachweis vor.

Quellenidentität ist noch kein elektrischer Abdeckungsnachweis. Verschiedene Zähler können dieselben Verbraucher enthalten: Haus-Hauptzähler plus enthaltene Wallbox oder Dreiphasensumme plus ihre Phasen dürfen nicht zusätzlich summiert werden. Das muss die spätere Projekt-/Topologiezuordnung vor Aufruf prüfen. Dieser Baustein kann solche unterschiedlichen, aber räumlich überlappenden Quellen noch nicht erkennen. Er verteilt auch keine Gesamtmessung auf einzelne Heizstäbe und beurteilt weder Verdrahtung noch Messgenauigkeit.

23 neue synthetische Tests prüfen Bilanz, Vorzeichen, Zeitgrenzen, Fehlerfortpflanzung, Quellenwiederverwendung, Tautologien, Netztrennung, nichtendliche Werte und Rekursion. Keine Messdaten oder Prognosegüte an einer realen Anlage geprüft.

Nächster Schritt: explizite Projektkanal-Zuordnung mit Abdeckungsprüfung und tatsächlicher Messzeit aus einem lesenden Adapter. Erst dann können Werte für Plan/Ist und späteren Regelbetrieb verwendet werden.
