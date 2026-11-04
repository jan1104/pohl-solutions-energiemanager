# Kleine Leistungen im endlichen Planungsmodell

Stand: 04.11.2026, unveröffentlicht. Keine Live-Steuerung oder neue Geräteanbindung.

## Nachgewiesener Fehlerfall und Änderung

Beim bisherigen gleichmäßigen Energieraster von 2 kWh konnte eine Viertelstunde mit 1 kW Last keinen nächsten Speicherzustand erreichen. Im dokumentierten synthetischen Fall (200,704 kWh, Anfang 50 %, Endminimum 10 %, Entladewirkungsgrad 95 %, 16 Viertelstunden ohne PV, Bezug 0,40 EUR/kWh) blieb die Batterie deshalb ungenutzt: 4 kWh Netzbezug und 1,60 EUR Szenariokosten.

Der Planer ergänzt nun die Energiezustände einer vollständig durchgerechneten Eigenverbrauchsalternative: ausgehend vom Anfangsbestand PV-Überschuss aufnehmen oder Nettoverbrauch decken, jeweils innerhalb Leistungs-, Wirkungsgrad- und Energiegrenzen. Die Endpunkte dieser Alternative erlauben die betreffenden kleinen Leistungsübergänge. Das ursprüngliche Raster einschließlich Anfang, Grenzwerten und Endziel bleibt vollständig erhalten. Die wirtschaftliche Suche darf diese Alternative nutzen, muss es aber nicht. Preise, Verschleiß, Export-/Netzladefreigaben und das Endminimum werden weiterhin vom bestehenden Planer geprüft.

Im genannten 1-kW-Fall werden jetzt alle 4 kWh Last gedeckt (numerisch bis zur Rundungstoleranz), die Szenariokosten sind null. Die zusätzliche Entnahme aus dem Speicher beträgt wegen 95 % Wirkungsgrad `4 / 0,95 kWh`. Ein weiterer analytischer Fall prüft 1-kW-PV-Überschussladung und spätere 1-kW-Last bei Wirkungsgrad 100 %. Diese Beispiele haben unterschiedliche Endbestände zur ungenutzten Batterie und sind kein energiegleicher Einsparnachweis.

## Begrenzung und verbleibende Probleme

Maximal 1001 Energiezustände insgesamt. Passt die vollständige Alternative nicht zusätzlich hinein, bleibt das ursprüngliche Modell unverändert; die Planannahmen nennen den Verzicht ausdrücklich. Es wird keine Teilstrecke als vollständige Korrektur ausgegeben und kein ursprünglicher Zustand entfernt. Bei Aufnahme ist der Suchgraph eine Erweiterung des alten Modells; dessen erreichbare Wege bleiben erhalten, abgesehen von bestehenden numerischen Toleranzen.

Das ist weiterhin eine endliche Näherung, kein kontinuierlicher Optimierer. Eine einzelne Eigenverbrauchsalternative enthält nicht alle wirtschaftlich sinnvollen Teilentladungen oder zeitlich verschobenen kleinen Ladeleistungen. Ein früher PV-Zyklus kann andere Zustände erzeugen als bewusstes Warten auf spätere günstigere Energie. Allgemeine Mehrspeicheroptimierung und Vergleich gegen eine kontinuierliche Referenz bleiben offen. Das pauschale HA-Endziel gleich Anfangs-SOC wurde ebenfalls nicht geändert: ohne spätere Lademöglichkeit kann es weiterhin die gewünschte Nachtentladung verhindern.

Nachgerechnetes verbleibendes Gegenbeispiel: 200,704 kWh, Anfang/Endminimum 50 %, beide Wirkungsgrade 95 %, Lade-/Entladegrenze 1 kW und 2-kWh-Raster. Drei Viertelstunden: erst 0,5 kW PV-Überschuss mit 0,50 EUR/kWh Einspeiseerlös, dann 1 kW Überschuss mit 0,01 EUR/kWh, zuletzt 1 kW Last mit 0,40 EUR/kWh Bezug. Das erweiterte Modell wählt `[0; +0,5; −0,45125] kW` mit −0,008875 EUR Kosten. Der physisch mögliche Plan `[0; +1; −0,9025] kW` endet ebenfalls bei 50 %, kostet aber nur −0,05275 EUR. Diese konkrete Lücke bleibt offen und verhindert die Behauptung, alle kleinen Leistungen seien optimal abgedeckt.

## Tatsächlich ausgeführter Ressourcenvergleich

Werkzeug: `python tools/benchmark_optimizer.py --repeats 3`. Feste synthetische Eingaben, Windows 11, Python 3.12.14, drei uninstrumentierte Zeitmessungen je Modell (Median). Speicher ist eine zusätzliche separate `tracemalloc`-Messung des Python-Allokationsmaximums im Rechenkern, nicht Prozess-RSS oder HA-Gesamtspeicher. Vergleichsmodell: unverändertes Basisraster mit abgeschalteter Zusatzzustandsfunktion, keine kontinuierliche Referenz.

| Synthetischer Fall | Modell | Zustände | Median | Python-Allokationsmaximum | Szenariokosten |
| --- | --- | ---: | ---: | ---: | ---: |
| 1 kW, 4 Stunden | Basis | 83 | 0,000291 s | 14,9 KiB | 1,60 EUR |
| 1 kW, 4 Stunden | Ergänzt | 99 | 0,000566 s | 14,4 KiB | 0,00 EUR |
| Gemischter 24-h-Tag | Basis | 83 | 0,012600 s | 182,2 KiB | 2,02332737 EUR |
| Gemischter 24-h-Tag | Ergänzt | 161 | 0,049791 s | 379,7 KiB | −7,10965956 EUR |

Der 24-h-Fall verwendet dieselben Anfangs-/Endminimumvorgaben (50 %) für beide Modelle, freie synthetische PV-/Lastwerte sowie vereinfachte Beispielpreise. Die Zahlen belegen nur diese Eingaben und diesen Rechner. Die Erweiterung erhöht hier den Aufwand; weder Laufzeit auf Raspberry Pi 5 noch Worst-Case-Laufzeit noch reale Wirtschaftlichkeit sind damit nachgewiesen. Dichtes Raster, lange Horizonte und viele zulässige Übergänge brauchen weiterhin Ressourcenbegrenzung und Zielhardwaretests.

Sechs zusätzliche Regressionen prüfen den dokumentierten Fehler, kleine PV-Ladung, wirtschaftliches Verwerfen der Alternative bei negativen Bezugs-/hohen Einspeisepreisen, physische Grenzen, transparenten Verzicht am Zustandslimit und Erhalt mindestens gleich guter Basismodellkosten in sechs weiteren synthetischen Szenarien. Alle bisherigen Endziel- und Bilanztests bleiben erhalten.
