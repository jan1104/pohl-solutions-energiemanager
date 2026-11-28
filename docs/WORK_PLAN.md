# Arbeitsplan

Stand: 2026-11-28. Dieser Plan steuert die weitere Entwicklung in diesem Chat und die wiederkehrenden Läufe alle sechs Stunden.

## Auftrag und Grenzen

- Repository: `D:\depot\pohl-solutions-energiemanager`, GitHub-Repository `jan1104/pohl-solutions-energiemanager`. Nutzer hat es für HACS öffentlich gestellt (am 03.11.2026 geprüft). Persönliche Projektdateien bleiben außerhalb von Git.
- Änderungen in kleinen zusammenhängenden Schritten implementieren, passend testen, dokumentieren, committen und in dieses Repository pushen. Nach erfolgreicher Prüfung angeforderte Testupdates als HACS-Release bereitstellen.
- Fremde oder uncommittete Änderungen erhalten. Vor Beginn Status, letzte Commits und AGENTS.md lesen.
- Keine Live-Gerätesteuerung, Veröffentlichung, Bereitstellung an einer Anlage oder Lizenzänderung. Geräteadapter zunächst lesend beziehungsweise simuliert.
- Bei wesentlichen abgeschlossenen Verbesserungen, Fehlern oder erforderlichen Entscheidungen berichten. Unveränderte oder nicht handlungsrelevante Stände nicht wiederholt melden.

## Erledigter Ausgangspunkt 0.1

- [x] Privates Repository und Git-Versionsverwaltung.
- [x] Kostenmodell mit expliziten Lebensdauer- und SOC-Annahmen.
- [x] Getrennte marginale Verschleißkosten und umgelegte Investitionskosten.
- [x] Diskrete Viertelstundenplanung mit physikalischen Grenzen.
- [x] HA-Einrichtung und reine Plansensoren.
- [x] Historische Lastprofilhilfe mit DST- und Fehlerauswertungstests.
- [x] Bedienbarer deutscher Oberflächenprototyp und validierter Planimport.
- [x] Python-, JavaScript- und echte HA-Laufzeitprüfungen auf GitHub erfolgreich.

## Aktueller Schritt 0.2: Preisquellen

- [x] Bezug und Einspeisung getrennt auswählen: vorhandene Prognosepreise, HA-Sensor, JSON-URL, Festpreis oder SMARD.
- [x] Einheiten und Tariftransformationen ausdrücklich konfigurieren; keine Vermischung von EUR/MWh, ct/kWh und EUR/kWh.
- [x] Negative Preise, fehlende Folgetagspreise und Zeitumstellung korrekt behandeln.
- [x] Netzwerkabrufe begrenzen, Fehler sichtbar machen und keine Preise erfinden.
- [x] Bedienoberfläche mit URL-/Sensorauswahl und klarer Unterscheidung zwischen Vorschau und aktiver HA-Konfiguration.
- [x] Reale HA-Tests für Quellenwechsel und gültige/ungültige Daten ergänzen.
- [x] Dokumentation, Änderungsprotokoll und Versionsnummer aktualisieren; geprüften Stand committen/pushen.

V0.2 ist implementiert und lokal mit 83 Python-Tests sowie JavaScript- und Oberflächenprüfungen getestet. Die erweiterte echte HA-Laufzeitprüfung ist im GitHub-Lauf 41618373561 auf Commit e02b711 erfolgreich. Die lokale Vorschau ruft keine Preise ab; die aktive Integration kann konfigurierte Quellen lesen. Der SMARD-Nutzungsstatus ist in PRICE_SOURCES.md dokumentiert.

## Überarbeitete Arbeitsliste nach Logikprüfung

Numerische Planerkosten am 28.11.2026: Endliche Eingaben konnten unendliche Einzel-/Horizontkosten oder trotz endlicher Gesamtkosten/Baseline eine unendliche Ersparnis liefern. Neue Regressionen reproduzierten diese Fehler vor der Änderung. Netz- und Intervallkosten, laufende Pfadkosten samt Durchsatz sowie abschließende Kosten und Differenz werden nun auf Endlichkeit geprüft. Nicht darstellbare Berechnungen weisen die gesamte Anfrage als ValueError ab, auch bei einem nicht gewählten Kandidaten; keine Kandidaten werden still übersprungen oder auf Grenzwerte gesetzt. Übergroße Ganzzahlen liefern denselben Eingabefehler statt OverflowError. Innerhalb vollständig darstellbarer Berechnungen bleiben Arithmetik und Optimierstrategie gleich; ein synthetischer großer endlicher Kostenfall prüft dies zusätzlich. Keine UI-Änderung, Geräteabfrage oder Raspberry-Pi-Leistungsaussage.

Prüfung: lokal 678 Python-Tests und 42 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. Ruff und Diff-Prüfung erfolgreich. GitHub prüft die echte HA-Laufzeit nach dem Push.

Planer-Zeitvertrag am 28.11.2026: Direkte Planeranfragen akzeptierten positive Dauern, deren datetime-Intervall auf Null rundet, sowie Lücken/Überlappungen bis zu einer Millisekunde. Ungültige Zeitstempeltypen oder UTC-/Endzeitüberläufe konnten außerdem ungeordnete Laufzeitfehler auslösen. Vor der Optimierung werden nun ausdrückliche datetime-Zeitstempel, positive darstellbare UTC-Intervalle und exakt anschließende UTC-Grenzen verlangt. Synthetische Regressionen wurden zunächst gegen den bisherigen Stand reproduziert. Ein Mikrosekundenintervall bleibt gültig; Tests führen tatsächlich gekürzte HA-Intervalle einschließlich Mikrosekunden durch den Planer. Bestehender Herbst-Zeitumstellungstest bleibt erhalten. Keine Änderung des Zustandsrasters, von Kosten, Leistungsgrenzen oder UI und kein Gerätezugriff.

Prüfung: lokal 672 Python-Tests und 39 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. Ruff und Diff-Prüfung erfolgreich. Keine UI-Änderung; echte HA-Abnahme läuft nach dem Push im vorhandenen GitHub-Check.

Historische Lastdaten am 27.11.2026: Reiner Adapter `normalize_load_history` übernimmt ausdrücklich gelieferte vollständige Viertelstunden-Mittelwerte in W/kW mit Quellenkennung. Ergebnis enthält unveränderliche LoadObservation-Tupel in UTC/kW für vorhandene Prognose-/Rücktestfunktionen. Strikte chronologische Reihenfolge, eindeutige Instanzen und Viertelstundenraster; Zeitumstellungs-Offsets bleiben verschiedene Messintervalle. Lücken werden nicht interpoliert oder auf Null gesetzt. `aggregation='mean'` ist eine ausdrückliche Aussage des Aufrufers, kein Nachweis der Messqualität. Kein Lesen von Dateien, Geräten oder Providern und keine Datenbank-/UI-Anbindung; diese Schritte bleiben offen.

Eingabevertrag: 1–60000 Datensätze mit ausschließlich `start`, `duration_minutes` (15) und `value`; Einheit, Mittelwertdeklaration und Quellenkennung separat. Lokal 666 Python-Tests und 31 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. 20 neue synthetische Adapter-/Kompositionstests und Ruff erfolgreich; keine UI-Änderung.

Legacy-Importvertrag am 27.11.2026: Format 2 prüfte Unicode-Faltungen gesperrter Feldnamen bereits wie Python; der gemeinsame ältere Browserpfad verwendete dagegen nur Kleinschreibung. Dadurch konnten etwa `paßword` oder `ſecret` im Format-1-Entwurf/Export passieren, während das Backend sie ablehnte. Beide Browserpfade verwenden nun denselben bestehenden Faltungsvergleich. Tests prüfen verschachtelte synthetische Feldnamen, direkte Prüfung, Import/Export und Python-/JS-Vertrag. Keine Untersuchung tatsächlicher Projektdateien oder Zugangsdaten; keine Aussage über einen erfolgten Datenabfluss. Reine Modellvalidierung ohne Änderung von Layout, Formularen oder Desktop-/Mobilbedienung; Frontend synchronisiert.

Prüfung: lokal 646 Python-Tests und 31 Untertests sowie 84 JavaScript-Tests erfolgreich; ein Windows-Symlink-Test übersprungen. Ruff und Synchronisations-/Pakettests erfolgreich. Die bestehende strengere Python-Prüfung bleibt unverändert.

Überholte Prognoseeinstellungen am 27.11.2026: Änderungen im Fachmodulspeicher ändern nicht die Projektrevision. Eine bereits laufende Lastprognose konnte deshalb noch Ergebnisse alter Einstellungen liefern. Lastprognose 0.1.1 prüft nach Berechnung die gespeicherte Einstellungsrevision erneut, einschließlich bisher fehlender Einstellungen. Abweichungen liefern ModuleUnavailable ohne Ergebnis. Grundmodul 0.1.6 reicht ausdrückliche Nichtverfügbarkeit mit sanitierter Meldung weiter, ohne einen dauerhaften Ausführungsfehler zu erfinden; bereits deaktivierte Zustände bleiben erhalten. Keine automatische Wiederholung. Die Zusicherung gilt zum abschließenden Lesen, nicht für zukünftige Änderungen nach Rückgabe. Synthetische Kern-/SQLite- und HA-Laufzeittests prüfen Revisionwechsel und ausdrücklich erfolgreichen Neuaufruf.

Codeprüfungs-Hinweise umgesetzt: Fachmodul deklariert Grundmodul 0.1.6 als Mindestversion; Kompatibilität mit 0.1.5/0.1.6 wird getestet. Gesteuerte Rechentests geben ihr Gate auch im Fehlerfall frei und warten auf ausstehende Tasks. Lokal 27 gezielte Fachmodul-/Kerneltests und Ruff erfolgreich; echte HA-Abnahme folgt im GitHub-Lauf.

Gesamtprüfung: lokal 646 Python-Tests und 31 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. Keine UI-Änderung oder Datenbankmigration.

Belegter Importvertragsfehler am 26.11.2026: JavaScript konnte eine Messgröße als Array wie `["active_power"]` durch implizite Eigenschaftsschlüssel-Konvertierung akzeptieren, wenn der Kanal noch keiner Bilanzmessung zugewiesen war. Python wies dasselbe Projekt ab. Der gemeinsame Browservalidator verlangt nun ausdrücklich einen String vor dem Nachschlagen der Messgröße. Modell- und Python/JS-Vertragstests prüfen direkte Validierung und Import verschiedener falscher Typen. Frontend-Kopie synchronisiert. Reine Datenvalidierung, keine Änderung von Layout, Formularen oder Desktop-/Mobilbedienung und keine Projektmigration.

Prüfung: lokal 641 Python-Tests und 31 Untertests sowie 84 JavaScript-Tests erfolgreich. Ein Windows-Symlink-Test übersprungen. Ruff, Synchronisations-/Pakettests und unabhängige Vertragsprüfung erfolgreich.

Gespeicherte JSON-Eindeutigkeit am 26.11.2026: Der bisherige Lesepfad prüfte gespeicherte Daten erst nach Standard-JSON-Dekodierung; doppelte Schlüssel wurden dabei bereits still zusammengeführt. Ein eigener begrenzter Dekoder weist nun doppelte Schlüssel einschließlich verschachtelter Objekte und beschädigte JSON-/Unicode-Daten vor der Übernahme ab. Fehler enthalten keine Dokumentinhalte. Die vorhandene Prüfung neuer Schreibdaten bleibt zusätzlich erhalten. Temporäre SQLite-Korruptionstests prüfen vollständiges Scheitern einer betroffenen Sammellesung, weiterhin lesbare andere Dokumente sowie unveränderte Körper/Revisionen ohne Reparatur. Die reine Kennungsauflistung lädt weiterhin keine Körper. Keine Migration oder Oberfläche.

Prüfung: lokal 641 Python-Tests und 31 Untertests erfolgreich; ein Windows-Symlink-Test übersprungen. 48 gezielte Speichertests und Ruff erfolgreich. Keine UI-Änderung oder Zugriff auf tatsächliche Projektdaten.

Belegter Herkunftsfehler am 25.11.2026: Formeleingaben konnten Listen enthalten, obwohl das Ergebnis als unveränderliches PowerValue ausgegeben wird. Bisher referenzierte dessen Formelfeld dieselbe Eingabeliste; spätere Änderungen konnten Nachweis und bereits berechnete Leistung widersprüchlich machen. Die Berechnung friert jetzt die verwendeten Quellen-/Koeffizientenpaare ein und verwendet genau diese Kopie für Rechnung und Ausgabe. Neue Auswertungen dürfen weiterhin geänderte Konfigurationen nutzen. Regressionen prüfen äußere/innere Listenänderung sowie ungültige Messwerte; keine Änderung von Einheiten, Bilanzformeln oder Gerätezugriff.

Prüfung: lokal 632 Python-Tests und 31 Untertests erfolgreich; ein Windows-Symlink-Test übersprungen. 25 gezielte Messwerttests und Ruff erfolgreich. Keine UI-Änderung.

Laufzeitabnahme des Lastprognose-Fachmoduls am 25.11.2026: Die echte HA-Smoke-Prüfung registriert erstmals die konkrete Implementierung über BaseRuntime mit temporärer SQLite-Projektablage und HA-Executor. Synthetische Historie prüft keine Ausführung bei Registrierung/Status, gemeinsame Einstellungen ohne Ergebnis-Schreibvorgang, Berechnung außerhalb der Eventloop, isolierten Fehler mit ausdrücklicher Quittierung, Projektänderung während ausstehender Berechnung und Sperre nach Stop. Keine Produktaktivierung, UI, Geräteverbindung oder reale Prognosegüte. Diese Integrationsprüfung wird unter Linux/HA auf GitHub ausgeführt; lokale Prüfung ersetzt keine echte HA-Ausführung.

Lokale Prüfung: 22 gezielte Fachmodul-/Kerneltests erfolgreich; Ruff, Kompilierung der HA-Prüfung und Diff-Prüfung erfolgreich. HA-Laufzeitprüfung bleibt der nachfolgende GitHub-Check dieses Commits.

Lastprognose-Fachmodul am 24.11.2026: `load_forecast_module` stellt Manifest 0.1.0/API 1 mit Grund-/Speicherabhängigkeiten und Konfigurationsschema 1 bereit. Ausdrücklich registrierter Handler liest optionale `settings` ausschließlich aus dem übergebenen Modulkontext; keine Standardwerte werden gespeichert. Begrenzte unveränderliche Anfrage enthält übergebene Historie, Zielzeiten, Wissensstand und Zeitzone. Bestehender Prognosekern berechnet über einen ausdrücklich injizierten Executor außerhalb der Eventloop. Abbruch wartet auf übergebene reine Rechenarbeit; keine harte CPU-Isolation. Kein Provider, Abruf, Ergebnisspeicherung, Oberfläche oder automatische Aktivierung. Projekt-/Revisionsschutz bleibt bei der vorhandenen BaseRuntime-Registrierung.

Prüfung: lokal 630 Python-Tests und 31 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. Neue Tests verwenden temporäre echte SQLite-Modulkontexte und prüfen Einstellungen ohne Schreibnebenwirkung, fehlende Historie, gelöste Aufruferlisten, Umfangsgrenzen, fremden Kontext sowie Abbruch-Drain. Ruff erfolgreich. Codeprüfungs-Hinweis zur ausdrücklichen Speicher-Modulkennung umgesetzt; keine UI-Änderung.

Prognose-Eingabevertrag am 24.11.2026: Boolean-Lastwerte und -Prognosebänder wurden durch `isfinite` als Zahlen akzeptiert; eine fehlende lokale Zeitzone verwendete still die Betriebssystemzeitzone. Prognose und Auswertung verlangen nun endliche numerische Werte ohne Boolean; ungültige Typen/übergroße Ganzzahlen ergeben ValueError. Explizite tzinfo-Instanz erforderlich, Tagesanzahlen positive echte Ganzzahlen und Halbwertszeit eine positive endliche Zahl. Nicht darstellbare Historiengrenzen und falsche Zeitstempeltypen werden als Eingabefehler abgewiesen. Keine Wetterdaten, geänderte Prognosemethode oder automatische Planung.

Prüfung: lokal 627 Python-Tests und 31 Untertests erfolgreich; ein Windows-Symlink-Test übersprungen. Ruff erfolgreich; bestehende Zeitumstellungs-, Rücktest- und Zeitzonen-Zähltests bleiben grün. Keine UI-Änderung.

Begrenztes Dokumentverzeichnis am 24.11.2026: Fachmodule können dynamisch benannte gespeicherte Konfigurationen über `list_keys`/`async_list_keys` im eigenen Projekt-/Modulbereich wiederfinden. Nur Kennungen, keine Körper, bis 128 pro Seite, Standard 50; explizite binäre Sortierung und exklusiver Cursor. Datenbank-/Schemaprüfung bleibt in der Seitentransaktion. Asynchrone Parameterprüfung erfolgt vor Executor-Arbeit. Seiten sind getrennte Lesestände, kein eingefrorenes Gesamtverzeichnis. Keine neue Tabelle, automatische Aktivierung oder Oberfläche.

Prüfung: lokal 604 Python-Tests und 31 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. Ruff und unabhängige Codeprüfung ohne Befund. Sortierung, Cursor, Bereichsgrenzen, fehlende Körperdekodierung, Schemawechsel und Prüfung vor Executor-Arbeit getestet. Keine UI-Änderung oder Datenbankmigration.

Konsistente Konfigurationslesung am 23.11.2026: `ModuleStorage.get_many(keys)` liest bis zu 128 ausdrücklich benannte Dokumente eines Projekt-/Modulbereichs in einer gemeinsamen SQLite-Lesetransaktion. Fehlende Schlüssel bleiben None; Revisionen und Schema werden geprüft. Einzelget nutzt denselben Pfad. `AsyncModuleStorage.async_get_many` friert geprüfte Schlüssel vor dem Executor ein und nutzt den vorhandenen Abbruch-/Drain-Vertrag. Temporäre SQLite-Tests mit explizitem WAL prüfen einen Schreibcommit während des Lesens: beide Dokumente bleiben im ursprünglichen Lesestand. Bereichsgrenzen, Schemakonflikt, getrennte Rückgabedaten, Grenzwerte und veränderte Aufruferliste geprüft. Keine neue Tabelle, Historie, automatische Abfrage oder Oberfläche.

Prüfung: lokal 594 Python-Tests und 31 Untertests erfolgreich; ein Windows-Symlink-Test übersprungen. Ruff und unabhängige Codeprüfung ohne Befund. Keine UI-Änderung oder Datenbankmigration.

Preiszuordnungsgrenzen am 22.11.2026: Sehr kleine positive Prognosedauern konnten in der datetime-Auflösung auf Null gerundet werden. Externe Preiszuordnung dividierte dann durch Null; Fest-/Prognosepreise konnten ein leeres Intervall übernehmen. Alle Preisarten verlangen nun ein tatsächlich positives darstellbares Intervall, bevor Preise zugeordnet werden. Ein Mikrosekundenintervall bleibt zulässig. Übergroße Ganzzahlen werden auch bei direkten HA-/Python-Preiswerten als ValueError abgewiesen, statt OverflowError an die Laufzeit durchzureichen. Kein neuer Abruf, Datenersatz oder Oberfläche.

Prüfung: lokal 584 Python-Tests und 31 Untertests erfolgreich; ein Windows-Symlink-Test übersprungen. Ruff erfolgreich. Regressionen decken Prognose-, Fest- und externe Preise sowie die positive Auflösungsgrenze ab; keine UI-Änderung.

Preisantworten am 22.11.2026: Reiner JSON-Dekoder vor dem HTTP-Cache weist doppelte Schlüssel (auch in Metadaten), nicht endliche Zahlen, ungültiges UTF-8/Unicode und Tiefe über 32 ab. Grenze 2 MiB; BOM und gültige negative Preise bleiben unterstützt. Bisher übernahm der Standardparser bei doppelten Feldern still den letzten Wert. Sanitierte Fehler ohne Antwort-/URL-Inhalt; ungültige Daten gelangen nicht in den Cache. Synthetische Parserregressionen sowie HA-Loopback-Prüfung für Ablehnung, erfolgreichen Wiederholungsabruf und anschließende Cache-Nutzung. Kein neuer externer Abruf oder Gerätezugriff.

Prüfung: lokal 576 Python-Tests und 31 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. 43 Preiskerntests und Ruff erfolgreich. Codeprüfung ohne verbleibenden Befund; übergroße Ganzzahlen werden ebenfalls vor der Preisnormalisierung als ValueError abgewiesen. Echte HA-Loopback-Prüfung erfolgt im GitHub-Linux-Lauf; keine UI-Änderung.

Vergleichsprognose am 22.11.2026: `compare_load_forecast` ergänzt den ausdrücklichen Offline-Rücktest um Persistenz der Messung genau 168 verstrichene Stunden zuvor (UTC, keine lokale Kalenderwoche). Beide Ergebnisse enthalten dieselben Zielzeitpunkte und dieselbe Istabdeckung; fehlende Vergleichsmessungen führen zum Fehler statt zum Weglassen. `mae_improvement_kw` ist Vergleichs-MAE minus Modell-MAE: positiv besser, negativ schlechter, Null gleich. Die Baseline wiederholt einen Punktwert in allen Bandfeldern; dies sind keine geschätzten Unsicherheitsintervalle. Synthetische Tests prüfen Verbesserung, Verschlechterung, Gleichstand, fehlende Messung und Herbst-Zeitumstellung. Keine tatsächliche Prognosegüte, automatische Modellauswahl, Datenabfrage oder Planung behauptet.

Prüfung: lokal 560 Python-Tests und 31 Untertests erfolgreich; ein Windows-Symlink-Test übersprungen. Ruff erfolgreich; keine UI-Änderung. Ein Codeprüfungs-Hinweis auf überlaufende Fehlerstatistiken wurde mit expliziter Bereichsprüfung und Regression umgesetzt: statt Infinity/NaN schlägt die Auswertung bei nicht darstellbarer Summierung fehl.

Numerische Kostengrenzen am 21.11.2026: Endliche Eingaben konnten unendliche Lebensdauer-/Energiekosten ergeben; kleine positive Wirkungsgrade konnten durch Produktunterlauf eine Division durch Null auslösen. Gemeinsame Prüfung endlicher Zahlen einschließlich sehr großer Ganzzahlen, normalisierte Rechenwerte und ausdrückliche Prüfung abgeleiteter Kosten/Energien. Nicht darstellbare Ergebnisse werden als ValueError abgewiesen. Null Jahreszyklen bleiben ein zulässiges Szenario ohne kWh-Kostenwert; negative Energiepreise bleiben erlaubt. SOC-Faktor vor Multiplikation bilden, um unnötigen Zwischenüberlauf bei darstellbarer Kapazität zu vermeiden. Keine geänderten Wirtschaftlichkeitsannahmen oder neuen UI-Felder.

Prüfung: lokal 555 Python-Tests und 31 Untertests erfolgreich; ein Windows-Symlink-Test übersprungen. Ruff erfolgreich. Synthetische Grenzfälle und bestehende Kostenbeispiele geprüft; keine UI-Änderung. Der Codeprüfungs-Hinweis auf unterlaufende positive Stück-/Betriebskosten wurde ebenfalls mit Fehlerprüfung und Regressionen umgesetzt.

Ressourcenaufwand der Lastprognose am 20.11.2026: Geeignete Historie wird einmal nach lokaler Uhrzeit indiziert; Wochentag und lokales Datum werden dabei mitgeführt. Bisher wurden historische Zeitstempel für jedes Ziel mehrfach in Ortszeit umgerechnet. Kandidatengruppen, getrennte UTC-Intervalle bei Zeitumstellung, gezählte Kalendertage und Gewichtung bleiben erhalten. Ein deterministischer Zeitzonen-Zähltest prüft 42 historische und 28 Zielintervalle mit genau 70 Umrechnungen und identischen Prognoseergebnissen. Kein erfundener Raspberry-Pi-Laufzeitwert, kein neuer Provider oder Hintergrundauftrag.

Prüfung: lokal 552 Python-Tests und 18 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. 31 Prognosetests einschließlich Rücktest und Zeitumstellung erfolgreich; Ruff ohne Befund. Keine UI-Änderung.

Rollierender Lastprognose-Rücktest am 20.11.2026: `backtest_load_forecast` erzeugt für jedes ausdrücklich gewählte Zielintervall eine Prognose mit dessen Beginn als Wissensstand. Nur bereits abgeschlossene Intervalle trainieren; ein früheres Ziel kann später legitime Historie werden. UTC-Reihenfolge und vollständige Istmessungen erforderlich; fehlende Historie/Messungen führen zum Fehler statt zu selektiver Fehlerstatistik. Unveränderliches Ergebnis mit Einzelprognosen, Intervallzahl, MAE und vorzeichenbehaftetem Bias in kW. Synthetische Regressionen einschließlich Herbst-Zeitumstellung; kein Abruf, Speichern oder automatische Aktivierung. Keine Aussage zur tatsächlichen Prognosegüte. Provider-/Modulanbindung bleibt offen.

Prüfung: lokal 551 Python-Tests und 18 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. Ruff erfolgreich. Der Rücktest berechnet jeden Zielzeitpunkt separat und läuft ausschließlich auf ausdrücklichen Offline-Aufruf; kein Hintergrundauftrag auf dem Raspberry Pi.

Belegter Prognosefehler am 20.11.2026: Bei sehr kleiner zulässiger Halbwertszeit konnten sämtliche absoluten Altersgewichte auf Null unterlaufen. Die Quantilauswahl lieferte dann fälschlich die kleinste historische Last für alle Bänder. Gewichtung relativ zur neuesten Messung der ausgewählten Vergleichsgruppe erhält mathematisch die Gewichtsverhältnisse und mindestens ein Gewicht 1. Regressionen prüfen kurze/minimal darstellbare Halbwertszeit sowie gewöhnliche gewichtete Quantile. Keine zusätzlichen Daten, Provider, Oberfläche oder automatische Planung; keine Prognosegüte behauptet.

Prüfung: lokal 544 Python-Tests und 18 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. 23 Prognosetests einschließlich Zeitumstellung erfolgreich; Ruff und unabhängige Codeprüfung ohne Befund. Keine UI-Änderung.

HA-Zustandsadapter am 18.11.2026 (unveröffentlicht): Ausdrücklich übergebene Zustandszeichenketten lassen sich über gespeicherte HA-Leistungsmessstellen binden. Entitätskennung und Einheit müssen exakt passen. Begrenzte ASCII-Dezimal-/Exponentzahlen, keine implizite Umdeutung von unbekannt/nicht verfügbar, Einheiten, Kommazahlen oder Boolean. Gemeinsame Leistungs-/Zeit-/Herkunftsprüfung; Empfang ersetzt keine Messzeit. Kein HA-Import, Zustandsabruf, Abonnement, Speicherung oder neue Oberfläche. Details RUNTIME_METERING.md. Automatische HA-Entitätsanbindung bleibt offen.

Prüfung: 38 gezielte Adaptertests; lokal insgesamt 541 Python-Tests und 18 Untertests erfolgreich, ein Windows-Symlink-Test übersprungen. Ruff und unabhängige Codeprüfung ohne Befund. Keine UI-Änderung.

Kommunikationsherkunft am 18.11.2026 (unveröffentlicht): Ein neuer reiner MQTT-Einstieg prüft die zugestellte Verbindungskennung gegen den gesamten gespeicherten Geräte-/Loggerweg vor der Payload-Verarbeitung. Gleiche Topics verschiedener Verbindungen bleiben getrennt. MQTT und Modbus verwenden denselben Wegprüfer; nur Modbus verlangt eine eigene Unit-ID. Elektrische Eltern werden nie als Kommunikationsweg verwendet. Tests prüfen beide Projektformate, direkte und mehrstufige Wege, wiederholte/fehlende/widersprüchliche Referenzen, falsche Verbindungen/Transportarten, unveränderte Daten und Zeitqualität. Kein Brokerzugriff, keine neue Oberfläche und kein Release. Details MQTT_MEASUREMENT_BINDING.md.

Prüfung der Kommunikationsherkunft: lokal 503 Python-Tests und 18 Untertests erfolgreich, ein Windows-Symlink-Test mangels Berechtigung übersprungen; Ruff erfolgreich. Unabhängige Codeprüfung ohne blockierenden Befund. Keine Änderung der Oberfläche oder des Speicherformats.

Stabilitätskorrektur am 18.11.2026 (unveröffentlicht): Die MQTT-UTF-8-Prüfung erfasst nun auch dekodierte Schlüssel und Zeichenketten. Einzelne Surrogate konnten zuvor über JSON-Escapes in ansonsten gültigen UTF-8-Nachrichten passieren. Synthetische Text-/Byte-Tests prüfen verschachtelte Metadaten, Schlüssel, ungültige Paare, gültige Unicode-Paare und unveränderte Leistungs-/Zeitzuordnung. Keine zusätzliche Pfadsprache: Bestehende punktgetrennte Schlüssel bleiben unverändert; eine spätere Erweiterung muss ausdrücklich konfiguriert werden. Kein Brokerzugriff oder neues Release.

Lokale Prüfung dieses Stands: 480 Python-Tests und 18 Untertests erfolgreich; ein symbolischer-Link-Test unter Windows mangels Berechtigung übersprungen. Ruff erfolgreich. Keine UI-Änderung; unabhängige Codeprüfung ohne blockierenden Befund. GitHub prüft zusätzlich die echte HA-Laufzeit unter Linux.

MQTT-Vorbereitung am 17.11.2026 (unveröffentlicht): Ein reiner Adapter bindet ausdrücklich gelieferte UTF-8-JSON-Leistungsnachrichten an gespeicherte MQTT-Messstellen. Exaktes Topic, klar begrenzter Objektpfad, Payload-/Tiefengrenzen und keine mehrdeutigen oder nicht numerischen Werte. Gemeinsame Einheiten-/Herkunfts-/Zeitprüfung; retained oder Empfang allein ersetzen keine Geräte-Messzeit. Kein Broker, Abonnement, Dateischreiben oder neue Oberfläche. v0.6.0 bleibt das veröffentlichte HACS-Release; diese Entwicklungsänderung wird nur auf main gepusht. Details MQTT_MEASUREMENT_BINDING.md.

HACS-Freigabe am 17.11.2026 vom Nutzer ausdrücklich angefordert: Grundversion 0.6.0 als normales GitHub-Release mit Integrations-ZIP bereitstellen. Lokal 418 Python-Tests, 18 Untertests und 83 JavaScript-Tests erfolgreich. Desktop-/Mobilprüfung der Register- und Rohwertsimulation im wieder verfügbaren In-App-Browser bei 1440/390 Pixeln abgeschlossen. Keine Änderungen an echten Geräten; automatische Steuerung und Mehrspeicheroptimierung bleiben außerhalb dieses Releases. Veröffentlichung erst nach grünen GitHub-Prüfungen und Paketprüfung.

Projektverwaltung 0.1.3 / Registersimulation am 17.11.2026: Im vorhandenen Messkanaltest kann bei Modbus optional eine Registerantwort mit ausdrücklicher Byte-/Wort-Reihenfolge eingegeben werden. Route, Dekodierung und einzelne Kanalumrechnung nutzen denselben Adapter über einen synthetischen Reader. Rohwertprüfung bleibt Standard; kein Gerätezugriff oder Speichern. Tests prüfen Eingabevarianten, Berechtigungen, Route, Grenzen, Konflikte und unveränderte Datenbank. Visuelle Desktop-/Mobilabnahme noch offen: In-App-Browser nicht verfügbar, native Browsersteuerung durch URL-Richtlinienprüfung des Werkzeugs beendet; kein Umgehen dieser Einschränkung und kein Release.

Belegter Unload-Fehler / Grundmodul 0.1.5 am 16.11.2026: Fehler oder Abbruch beim Stop der letzten Runtime beziehungsweise Coordinator-Abmeldung konnten gemeinsame Panel-/Dienst-/Speicherreferenzen zurücklassen. Die gemeinsame Bereinigung läuft nun in `finally`; weitere aktive Einträge behalten ihre Ressourcen. HA-Prüfungen injizieren Signale nach echtem Abbau und prüfen Dienste, Panel, Datenreferenzen, WebSocket-Status sowie den zweiten aktiven Eintrag. Keine Geräteabfrage, Dateilöschung oder neue Oberfläche.

Grundmodul 0.1.4 am 16.11.2026: Ausdrücklich registrierter Fachmodulcode erhält seinen projekt-/modulgebundenen asynchronen Datenbankkontext vom Grundmodul. Reine Vorprüfung vor Datenbankarbeit, kompatible Speicherabhängigkeit und erneute Registrierungskontrolle. Kein Handler-Aufruf bei Registrierung/Status. Überholte Ergebnisse und fremde Projektbindung deaktivieren das Modul; keine stille Umleitung. Stop wartet auch auf vorbereitete Registrierungen. Synthetische Handler mit echter HA-/SQLite-Laufzeit prüfen diesen Ablauf. Keine automatische Entdeckung, neue Oberfläche oder Gerätesteuerung.

Projektverwaltung 0.1.2 am 16.11.2026: Unveränderte Export-/Statuszugriffe validieren und serialisieren den vollständigen privaten Projektbaum nicht mehr erneut. Exporttext und Zusammenfassung werden zusammen mit der Inhaltskennung bei Übernahme erzeugt; alle Ausgabeformate bleiben gleich. Zurückgegebene verschachtelte Zusammenfassungen werden vollständig kopiert. Die HA-Prüfung sperrt alle fünf Berechnungsfunktionen bei reinen Lesezugriffen und vergleicht gegen bisherige Ausgaben. Keine neue Oberfläche, Datenbankmigration oder Geräteabfrage.

Projektverwaltung 0.1.1 am 15.11.2026: Die Inhaltskennung wird pro übernommenem Projektstand einmal berechnet und für reine Revisionsabfragen wiederverwendet. Bisher wurde dabei jedes Mal der vollständige Projektbaum serialisiert und gehasht, auch mehrfach je Leseaufruf. Ein gemeinsamer Übernahmepfad aktualisiert den Wert bei Laden, Import, Migration, Konfliktnachladen und Simulation vor möglichen Abbruch-/Konfliktfehlern. SHA-Vertrag und numerische SQLite-CAS unverändert. HA-Tests prüfen kanonische Gleichheit und ausbleibende Hashaufrufe; keine erfundenen Pi-Leistungswerte. Keine neue Oberfläche oder Geräteabfrage.

Grundmodul 0.1.3 am 13.11.2026: Gespeicherte Modbus-Leistungsmessstellen lassen sich intern ausdrücklich über den zentralen HA-Verbindungsbesitzer lesen, dekodieren und mit Herkunft/Einheit/Ausrichtung binden. Die lokale Projektrevision wird durchgereicht; veraltete Ergebnisse werden verworfen. Unbekannte Geräte-Messzeit bleibt ungültig. Eine ungültige Empfangsuhr wird vor dem Gerätezugriff abgewiesen. Synthetische HA-Prüfungen decken Route, einzelne Skalierung, Quellenbezug und Projektwechsel ab. Keine Oberfläche, Live-Sensoren, Historie oder automatische Erfassung.

Grundmodul 0.1.2 am 13.11.2026: Die HA-Laufzeit besitzt jetzt den gemeinsam genutzten lesenden Verbindungsmanager. Ein interner ausdrücklicher Leseaufruf verlangt die lokale Projektrevision, erzeugt den Manager bei Bedarf und verwirft überholte Ergebnisse. Projektwechsel schließen den alten Besitzer vor Ersatz. Stop sperrt neue Aufrufe und wartet auch bei Abbruch auf die Bereinigung samt Besitzersperre. HA-Start, Status und Import lesen keine Geräte. Echte HA-/Projektablage mit synthetischen Transportbesitzern geprüft; kein neuer Service, keine Oberfläche, keine Historie oder automatische Erfassung.

Kommunikationsgrundlage 13.11.2026: Der bisher nur konfigurierbare transparente RTU-over-TCP-Tunnel hat einen lesenden FC03/04-Transport erhalten. Er nutzt die vorhandene Warteschlange und Verbindungslebensdauer, verlangt Port und serielle Unit-ID ausdrücklich und prüft CRC sowie Antwortgrenzen. Gemeinsame Endpunkte dürfen keine widersprüchlichen MBAP-/RTU-Konfigurationen erhalten. Tests laufen ausschließlich gegen synthetische Loopback-Server; keine USB-/Buszeit-/Gateway-Kompatibilitätsbehauptung. HA-Anbindung und übrige Protokolle bleiben offen. Details RTU_OVER_TCP.md.

Belegter Diagnosefehler 12.11.2026: Die Statusschleife rief sämtliche registrierten Modulhandler auf und quittierte deren Fehler. Sie ist nun auf die drei eingebauten Diagnosehandler begrenzt. Zusätzliche Fachmodule werden ausschließlich mit ihrem vorhandenen Zustand angezeigt. Grundmodulversion 0.1.1; HA-Smoke prüft Aufrufzähler und unveränderte Zustände bei verfügbaren, deaktivierten, fehlgeschlagenen und inkompatiblen Testmodulen. Keine neue Oberfläche oder Gerätekommunikation.

Grundspeicher 12.11.2026: Eine ausdrücklich gestartete SQLite-Sicherung kopiert alle Projekt-/Modulbereiche samt Revisionen konsistent, prüft die Kopie und veröffentlicht sie ohne Überschreiben eines bestehenden Ziels. Temporäre Testdaten prüfen auch bestätigte WAL-Inhalte, parallele unbestätigte Änderungen, Fehler und Zeitlimit. Keine neue Oberfläche, automatische Sicherung, Wiederherstellung oder Geräteverbindung. Die HA-Bedienung und der Restore-Ablauf bleiben offen.

Grundmodul-Priorität 12.11.2026: Ein ausdrücklicher asynchroner Modulkontext stellt die vorhandene gemeinsame SQLite-Datenbank für Fachmodulkonfiguration bereit. Der HA-ProjectStore liefert den Zugang mit fester Projekt-/Modul-/Schema-Zuordnung. Reservierte Kernbereiche bleiben geschützt; ein Projektwechsel leitet bestehende Kontexte nicht um. Schreibdaten werden vor der Worker-Warteschlange geprüft/kopiert und bereits übergebene Arbeit bei Abbruch vollständig abgewartet. Keine neue Oberfläche, Historie, Modulaktivierung oder Geräteverbindung. Nächste Schritte bleiben konkrete Fachschemas, Aktivierungs-/Lebensdauerverwaltung und zentrale Messhistorien.

Bedienlücke am 12.11.2026 geschlossen: Die vom Modell bereits unterstützte geräteeigene Modbus-Unit-ID lässt sich beim Anlegen direkt eingeben. Das Feld erscheint für TCP, TCP/RTU-Gateway, USB/RS485 und RTU über TCP, bleibt optional für Entwürfe und übernimmt keinen Standardwert. MQTT, HA und Solarman erhalten daraus keine Modbus-Adresse. Tests prüfen beide Projektformate, ungültige Adressen, Erhalt fehlerhafter Eingaben und explizite Speicherung. Desktop (1440 × 900) und Mobil (390 × 844) mit synthetischem Messgerät visuell geprüft. Keine Geräteverbindung und kein Release.

Grundversion 0.6.0 wird für den Nutzertest vorbereitet. Neue HA-Projekte starten direkt in Format 2. Eine atomare Neuanlage erhält konkurrierende oder bestehende Daten. Die Oberfläche verlangt die Übernahme oder das Schließen offener Bearbeitungen vor Speichern oder Formularwechsel. Testablauf und Umfang stehen in TESTING_0_6.md. Der aktuelle Lauf erstellt und pusht den geprüften Kandidaten mit lokalem Installationspaket. Die Veröffentlichung als HACS-Release erfolgt getrennt.

Eine belegte Grenzprüfung wurde korrigiert. Projektimport und Quellenformular akzeptierten bisher 32-Bit-Registerwerte ab Adresse 65535, obwohl der Lesepfad zwei Register benötigt und den Bereich ablehnt. Beide Projektvalidatoren prüfen nun die vollständige Registerbreite. Tests vergleichen Format 1/2, FC03/FC04 und 16-/32-Bit-Grenzen zwischen Python und JavaScript. Vorhandene Konfigurationen mit dieser ungültigen Adresse melden den Fehler an der Quelle und benötigen eine anhand der Geräteunterlagen korrigierte Adresse.

Der Modbus-Lesepfad verbindet eine gespeicherte Kanalzuordnung über einen eingesetzten Reader mit Registerdekodierung und der bestehenden Leistungsumrechnung. Die Route unterstützt beide Projektformate. Tests mit Testreadern und einem synthetischen Loopback-Server prüfen Zieladresse, Registerbreite, Umrechnung und die Trennung von Empfangs- und Messzeit. Der nächste Schritt ist eine ausdrücklich aufgerufene Testoberfläche für diesen simulierten Lesepfad. Reale Geräte benötigen belegte Registerparameter, Reihenfolge und Messzeit.

Die Messsimulation prüft eine gespeicherte Zuordnung mit einem eingegebenen Rohwert und ausdrücklicher Ausrichtung. Sie verwendet die vorhandene Bindungslogik für Skalierung und W/kW und kennzeichnet das Ergebnis sichtbar. Die Desktop- und Mobilprüfung erfolgte mit synthetischen Daten. Der simulierte Modbus-Lesepfad folgte im nächsten Entwicklungsschritt. Reale Register- und Geräteparameter müssen dafür getrennt belegt werden.

Format-2-Messstellen erhalten ihre Datenquelle direkt in der Projektansicht. Das Formular unterstützt Modbus mit FC03/FC04, MQTT und HA-Entitäten und kann eine Quelle offen lassen. Ein Wechsel ersetzt die bisherigen Quellenfelder, während Messort, Kanal und Einheit erhalten bleiben. Die Desktop- und Mobilprüfung verwendete synthetische Daten. Die Testwertprüfung folgte im nächsten Entwicklungsschritt.

Die Netzmessung in Format 2 lässt sich einem bestehenden Gesamtwirkleistungskanal zuordnen. Fehlt der Kanal, kann ein Entwurf mit Name und Einheit W oder kW am gewählten Messgerät angelegt werden. Das Formular beschränkt die Auswahl auf freie Kanäle am selben Anschluss und zeigt offene Quellen. Die Browserprüfung erfolgte mit synthetischen Daten bei 1440 und 390 Pixeln Breite. Das Quellenformular folgte im nächsten Entwicklungsschritt.

Am 09.11.2026 hat das HA-Projektmenü eine ausdrückliche Umstellung auf die Anlagenstruktur erhalten. Die Vorschau liest den gespeicherten Stand. Die Bestätigung prüft dessen Inhaltskennung und SQLite-Revision und sichert das Original im selben Schreibvorgang. Desktop und Mobilansicht wurden mit synthetischen Daten geprüft. Die Messkanalzuordnung folgte im nächsten Entwicklungsschritt.

Die Format-2-Projektansicht führt vom Projektnamen über die Anlage zum Netzanschluss. Angaben zu Ort, Beschreibung, Absicherung und Phasen lassen sich aufklappen. Bereiche referenzieren eine Anlage und einen ihrer Anschlüsse. Offene Netzmessungen sind im Aufbau erkennbar. Lokale Vorschau und vorhandene Format-2-Projekte verwenden den Ablauf. Die Browserprüfung mit synthetischen Daten erfolgte bei 1440 und 390 Pixeln Breite. Die Migrationsbestätigung folgte am 09.11.2026.

Am 08.11.2026 hat der ProjectStore das Lesen, Speichern und Exportieren vorhandener Format-2-Projekte übernommen. Die Namespace-Version bestimmt den zulässigen Import. Konflikte nach einem externen Schemawechsel aktualisieren die lokale Ansicht. Format-2-Exporte bleiben im Rohtextlimit und Statusantworten zeigen offene Messungen. Neue Projekte beginnen in Format 1. Lokal bestanden 342 Python-Tests, 18 Untertests und 45 JavaScript-Tests. Die Anlagenoberfläche folgte im nächsten Entwicklungsschritt.

Persistenzvorbereitung 06.11.2026: explizite atomare Namespace-Migration und Projekt-Formatwechsel als Entwicklungs-API implementiert. Lesende Vorschau, Quell-SHA/Revision, erneute Ableitung beim Commit, geschützte Originaldaten und Legacy-Herkunft; kein stilles Überschreiben. 19 neue Konflikt-/ABA-/Neustart-/Rollbacktests mit temporären Datenbanken. Lokal insgesamt 337 Python-Tests plus 18 Untertests und 45 JavaScript-Tests erfolgreich. Die versionsbewusste HA-Speicherung folgte am 08.11.2026. Die geführte Anlage-/Messgerätebedienung bleibt der nächste Schritt.

JSON-Grenzvertrag 06.11.2026: identisches konservatives 2-MiB-Budget für Entwicklungsformat 2, begrenzter gemeinsamer Zahlenbereich und Unicode-Skalarwerte implementiert. Unterschiede durch Float-Schreibweise/Leerzeichen geschlossen; ungültige oder verlustbehaftete JS-Objekte abweisen. Bereichs-/Budgetgrenzen und migrationsbedingte Ablehnung erhalten Originaldaten; Format 1 unverändert. Expliziter Persistenzwechsel anschließend vorbereitet (siehe oben); aktive HA-Übernahme und minimale Anlage-/Messgerätebedienung bleiben offen. Lokal 318 Python-Tests plus 18 Untertests und 45 JavaScript-Tests erfolgreich. Keine Änderung der Oberfläche, keine Aktivierung, kein Release.

Entwicklungsschritt 06.11.2026: explizite JS-API für Format-2-Prüfung, Vorschau-Migration und Konfigurationshinweise ergänzt; aktive UI und Import/Export bleiben Format 1. Migrationsergebnisse und Struktur-/Hinweiscodes mit Python verglichen, getrennte elektrische Grenzen erhalten. Lokal 316 Python-Tests plus 18 Untertests und 43 JavaScript-Tests erfolgreich. JSON-Grenzvertrag anschließend ergänzt (siehe oben); Persistenz und geführte Anlage-/Messgerätebedienung bleiben offen. Keine automatische Datenübernahme, keine Gerätezugriffe, kein Release.

Priorität nach Nutzerklärung 05.11.2026: Projekt beim Integrationsstart, danach Anlage vor Anschlüssen/Geräten. Entwicklungsformat 2 mit Anlagenreferenzen, optionalen HAK-Metadaten und noch ungemessenen Anschlüssen implementiert; bestehende Format-1-Importe bleiben unverändert streng. Explizite Vorschau-Migration erhält elektrische IDs/Beziehungen, errät keine Standorte und ändert keine Dateien. 23 neue Tests; lokal insgesamt 315 Python-Tests plus 18 Untertests erfolgreich. Noch keine UI-/HA-Aktivierung und kein Release. Nächster Schritt: Persistenzmigration und schrittweise minimale Bedienung samt Messgerätemodul. Details PROJECT_SCHEMA_V2_DRAFT.md.

Bedienkorrektur 0.5.1 (Nutzerfeedback 04.11.2026): ruhige Projektübersicht und geführter nächster Schritt statt gleichzeitig sichtbarer Toolbars/Formulare/Nullzähler. Seltene Optionen und JSON gezielt öffnen; Speichern, Fehler und Importvorschau müssen klar erreichbar bleiben. Keine Änderung an Datenformat oder zentraler Speicherlogik. Desktop-/Mobilansicht, fokussiertes Anlegen/Speichern und sichtbare Importvorschau geprüft. Lokal 292 Python-Tests plus 18 Untertests und 41 JavaScript-Tests erfolgreich; Revisionsschutz erhalten.

Testbares Grundmodul 0.5.0 (04.11.2026): gemeinsame SQLite-Projektablage an HA angeschlossen, Legacy-Projekt nur einmal atomar übernehmen und dessen Datei bytegleich erhalten. Keine Doppel-Schreibquelle; SHA-Revisionsschutz bleibt bestehen. Echte Basis-Registry für Grundmodul/Speicher/Projekt mit unabhängigen Modulversionen. Projekt-/Grundmodulnavigation und tatsächliche Statusanzeige; Desktop-/Mobilprüfung mit simulierter HA-Anbindung durchgeführt. Gezielte HA-Laufzeittests für Migration, Abbruch, Konflikt und Zugriff erweitert. Nutzertestablauf TESTING_0_5.md. Nächster Schritt: konkrete Fach-/Konfigurationsverträge und lesendes Prognosemodul; vollständige Geräte-/Historien-/Mehrspeicherfunktionen weiter offen.

Zentrale Datenhaltung (Nutzerklärung 04.11.2026): SQLite-Konfigurationsdienst im Grundmodul mit Projekt-/Modulnamensbereichen, getrennten Schemaversionen, Revisionsprüfung und atomaren Mehrdokumentänderungen implementiert. 21 neue temporäre Datenbanktests, einschließlich konkurrierender Repositoryinstanzen und Fremddatenbankerhalt; insgesamt lokal 292 Python-Tests plus 18 Untertests erfolgreich. Noch keine automatische Modulkontext-/HA-Anbindung, Historien-/Backupfunktion oder Übernahme des bestehenden Projektspeichers. Keine Doppel-Schreibquelle; Details/Nächster Schritt CENTRAL_STORAGE.md.

Grundmodul zuerst, Prognose separat (Nutzerklärung 04.11.2026): HA-unabhängigen Kernel mit eigenen Modulversionen, API-/Abhängigkeitsprüfung, Teilgraph-Sperren, asynchronen Einzelaufrufen und Schutz gegen überholte Ergebnisse/Fehler implementiert. 18 neue Tests, lokal insgesamt 271 Python-Tests plus 18 Untertests erfolgreich. Prognose als eigenständiges Fachmodul festgelegt; noch kein konkreter Provider an Kernel angeschlossen. Kein Hot-Update, keine Prozessisolation, kein geändertes Projektformat und noch keine HA-Laufzeitumstellung. Details/Nächste Schritte: MODULE_KERNEL.md; als Nächstes Daten-/Konfigurationsverträge und konkreten lesenden Prognosebaustein anbinden.

Bedien-/Modulpräzisierung am 04.11.2026 nach Nutzerklärung: Gerätebausteine für Messung, PV, Speicher, Wärme, Ladestation und Anlagenregler von Profilen/Transporten trennen. Eingabeorte, automatisch auslesbare Werte, manuelle Bestätigungen, gemeinsame Messgruppen, Formular-/Fähigkeitsvertrag und Funktionsabhängigkeiten in DEVICE_MODULES_AND_SETUP.md beschrieben. Dies ist ein Entwurf, keine implementierte Modulverwaltung. Nächster Bedienungsschritt: gemeinsamer Modul-/Feldvertrag mit Projektmigration, danach Messgerätebaustein durchgängig statt weiterer isolierter Formulare.

Nutzeranforderung gemeinsame Grundfunktionen am 04.11.2026: zentrale lesende TCP-/TCP-RTU-Gatewayverwaltung mit Connection-ID-Referenzen, gemeinsamem Client/Lock und Profil-Lesefassade umgesetzt. Gerätepfad folgt Gatewaybeziehung, nicht elektrischem Elternteil; Unit-ID bleibt geräteeigen. RegisterReader-Vertrag für wiederverwendbare Profile. Gesamte Datenfluss-/Eigentumslogik: SYSTEM_LOGIC.md. RTU-USB, rohes RTU-over-TCP, MQTT, Solarman und HA-Lebenszyklusanbindung bleiben offen. Kein Setup-/Importzugriff auf Geräte. 17 neue Simulator-/Konfigurationsprüfungen für geteilte Verbindung, Zieladressen, Abbruch und Shutdown; lokal insgesamt 253 Python-Tests plus 18 Untertests erfolgreich.

Unveröffentlichter Rechenkernschritt am 04.11.2026: dokumentierter 1-kW-/Viertelstundenfehler durch zusätzliche Zustände einer physisch begrenzten Eigenverbrauchsalternative korrigiert. Basisraster vollständig erhalten, keine erzwungene Strategie, vollständige Aufnahme nur bis 1001 Zustände; Verzicht wird im Plan begründet. Kleine Überschussladung mitgeprüft. Sechs neue Regressionen, lokal 236 Python-Tests plus 18 Untertests erfolgreich. Reproduzierbarer Windows-Ressourcenvergleich in SMALL_POWER_PLANNING.md; kein Raspberry-Pi- oder kontinuierlicher Optimalitätsnachweis. Allgemeine kleine Arbitrageleistungen, Endzielpolitik und Mehrspeicherplanung bleiben offen. Kein Release, keine Gerätezugriffe.

Weiterer unveröffentlichter Schritt am 04.11.2026: explizite Offline-Bindung einer Projektmessstelle an gelieferten numerischen Rohwert. Kanal-/Geräte-/Messknoten-/Quellherkunft erhalten; W/kW, konfigurierte Skalierung und zwingend angegebene Ausrichtung genau einmal anwenden. Unbekannte Zeiten nicht erfinden, unkonfigurierte Quelle nicht als gültige Messung akzeptieren. 26 neue Tests; lokal insgesamt 230 Python-Tests plus 18 Untertests erfolgreich. Keine UI-/Polling-Anbindung, physische Quellenalias- und elektrische Abdeckungsprüfung weiter offen. Nächster Schritt bleibt ausdrücklich lesender Adapter mit Zeit-/Identitätsnachweis; kein Release.

Unveröffentlichter Entwicklungsschritt am 04.11.2026: Laufzeitbaustein für normalisierte AC-Messwerte und lineare Ableitungen mit Quellenherkunft, Originalmess-/Empfangszeiten, Datenalter, Zeitversatz und Fehlerfortpflanzung. Getrennte Anschlüsse, Zirkelschlüsse und mehrfach genutzte Ursprungsquellen ablehnen. 23 neue synthetische Tests; insgesamt lokal 204 Python-Tests plus 18 Untertests erfolgreich. Noch keine Projekt-/Oberflächen-/Polling-Anbindung und keine Erkennung elektrisch überlappender verschiedener Zähler. Siehe RUNTIME_METERING.md. Nächster Schritt: Kanalzuordnung mit Abdeckungsprüfung; keine Verbindung als Setup-Nebenwirkung. Kein Release.

0.4.0: Nutzeranforderung echte HA-Seitenleiste umgesetzt: natives Panel „Energiemanager“, direkte HA-Projektpersistenz mit Administrator-/Revisionsprüfung, grafische Basisformulare und bestehende Struktur-/Importansichten. Projektmodus zeigt nur Status; alte Plansensoren reversibel deaktiviert. UI im HACS-ZIP enthalten und byteweise auf Synchronität geprüft. Keine Geräteabfrage aus den Formularen. Bedienung/Grenzen: HA_PANEL.md. Standort-/Regel-/Prognoseseiten und vollständige Messzuordnung weiter offen.

0.3.1: Einstieg auf frei benannten Energiemanager ohne HA-Sensorpflicht umgestellt; bestehende Simulation separat in Optionen. Neue Projekte leer anlegen, bestehende Importe erhalten. Standort/Netzanschluss/Bereich/Gerätegruppe künftig sauber trennen, siehe PROJECT_HIERARCHY.md. Eigene Standortverwaltung und direkter Geräteassistent noch offen.

Unveröffentlichter Entwicklungsschritt am 03.11.2026: lesender nativer Modbus-TCP-Client und UMG-103-CBM-Wirkleistungsprofil implementiert, ohne HA-/Setup-Anbindung. 47 neue Loopback-/Dekodierprüfungen erfolgreich, einschließlich zweier Zieladressen über einen gemeinsam genutzten Client. Keine Anlage verbunden, kein Scan, kein Aktor und kein HACS-Release. Details/Quellen/Grenzen: protocols/READ_ONLY_MODBUS.md. Standortassistent und erste explizite lesende Anbindung bleiben offen.

### Implementierter Zwischenstand 0.3: erste testbare Projektverwaltung

- [x] HA-unabhängiges Projektmodell mit getrennter elektrischer Topologie, Kommunikation und Messzuordnung; inklusive Gateway-Untergeräten und Batterie-WR-Beziehungen.
- [x] Strikter JSON-Import/-Export, Primärquellen-/Netz-/Teilbaumprüfung, Geheimnisfeld-/Steuerfreigabeprüfung, atomarer CLI-Roundtrip.
- [x] Offline-Projektansicht mit Vorlagen, drei Strukturansichten, Namenbearbeitung, Vorschau/Übernahme, Export und expliziter Browser-Speicherung.
- [x] HA-Projektmodus ohne Prognose/SOC und persistente Import-/Export-/Statusaktionen. Browserseite weiterhin separat; kein integriertes HA-Panel.
- [x] Anonymisiertes Referenzbeispiel und einfache Vorlage; tatsächliche Beispielnamen nur privat/lokales persönliches Testpaket.
- [x] Lokal 132 Python-Tests plus 18 Untertests, JavaScript-Tests sowie Desktop-/Mobilprüfung erfolgreich. Echte HA-Laufzeitprüfung wird für diesen Stand über GitHub Actions ausgeführt.

Testablauf: TESTING_0_3.md. Mehrgeräte-Konfiguration ist noch nicht an Optimierung angeschlossen. Treiber, Gerätesuche, vollständiger grafischer Assistent und Live-Steuerung sind nicht implementiert. Checklisten unten beschreiben auch darüber hinausgehende Abnahmekriterien.

Grundlagen: [bestätigte Anforderungen und Fragen](REQUIREMENTS.md), [nachgewiesene Logikbefunde](LOGIC_REVIEW_2026-11-03.md). Zunächst Rechenfehler und Datenmodell bearbeiten. Offene Betriebsentscheidungen nicht stillschweigend durch Standardwerte ersetzen.

Überarbeiteter Gesamtentwurf: [Navigation, Gerätehierarchie und Funktionsprüfung](NAVIGATION_AND_PRODUCT_DESIGN.md). Enthält Messkanal-/Phasenzuordnung, Batterien unter dem jeweiligen WR und sieben Hauptbereiche mit eindeutigen Einstellungsorten. Zielentwurf, kein Implementierungsnachweis.

Ergebnis der angeforderten parallelen Protokollprüfung: [Geräte-/Transportberichte und nächste Adapterschritte](protocols/README.md). Janitza-Gatewayfunktion und Plexlog-Vorgaberückmeldungen dokumentiert; installierte Parameter/Firmware und Regelzuständigkeiten bleiben zu erfassen. Keine Gerätekonfiguration geändert.

### 1. Rechenkern und wirtschaftliche Ziele

- [ ] Mehrere Solis/Bluesun-Speicher-Wechselrichter bereits im ersten nutzbaren Umfang gemeinsam optimieren: eigene SOCs, Wirkungsgrade, Reserven und Grenzen; gemeinsame Bilanz ohne Doppelzählung.
- [ ] Verfahren für mehrere Speicher benchmarken; ein kartesisches Produkt aller SOC-Raster wächst schnell und darf nicht ungeprüft übernommen werden. Gegen kleine exakt lösbare Mehrspeicherfälle vergleichen.
- [ ] Unnötiges Laden eines Speichers aus einem gleichzeitig entladenden Speicher verhindern oder einen ausdrücklich begründeten Nutzen nachweisen; Energiequellen für getrennte Exportfreigaben modellieren.
- [ ] Kleine Lasten/Ladeleistungen allgemein korrekt berücksichtigen; 1-kW-Last und kleine PV-Ladung sind durch zusätzliche Kandidatenzustände korrigiert und regressionsgeprüft. Allgemeine kleine Arbitrageleistungen und Verzicht am Zustandslimit bleiben Einschränkungen; siehe SMALL_POWER_PLANNING.md.
- [ ] Laufzeit und Speicherbedarf des bisherigen Verfahrens messen; Kandidat gegen kontinuierliche Referenz und analytische Fälle vergleichen.
- [ ] Ressourcenvergleich für Zielhardware Raspberry Pi 5 planen; Desktop-Messungen nicht als Pi-Nachweis ausgeben. RAM und weitere HA-Auslastung noch erfassen.
- [ ] Rollierendes Endenergie-/Reservekonzept entwerfen; keine pauschale Gleichsetzung von aktuellem und End-SOC.
- [ ] Nachtentladung, billiges Netzladen vor teurem Bezug, bevorstehenden PV-Überschuss und negative Einspeisepreise prüfen.
- [ ] Wirtschaftlichkeitsziel und Autarkiewunsch als getrennte Betriebsarten definieren; optionaler Batterieverkauf einschließlich netzgeladener Energie nur mit ausdrücklicher anlagenspezifischer Freigabe.
- [ ] Allgemeine Anlagenkonfiguration statt fest eingebauter Vincent-Werte; Mindestreserve und optionale Notstromreserve einfach einstellbar, ohne unbegründeten festen Standardwert.
- [ ] Betrieb unter Wunschreserve und oberhalb Wunschziel sauber von physischen BMS-Grenzen unterscheiden.
- [ ] Restenergie in Vergleichen fair bewerten; keine garantierten Einsparungen aus einem Prognoseplan ableiten.

Abnahme: bekannte Gegenbeispiele funktionieren; keine Energiebilanzverletzung; wiederholte Neuplanung leert/blockiert den Speicher nicht künstlich; Ressourcenbedarf ist dokumentiert.

### 2. Anlage, Messungen und Verträge

- [ ] Netzanschluss als elektrische Optimierungsgrenze von benannten Bereichen trennen; mehrere Bereiche an einem Anschluss ebenso wie getrennte Anschlüsse unterstützen. METERING_TOPOLOGY.md als Bilanz-/Validierungsgrundlage verwenden.
- [ ] Verschachtelte Nettozweigmessungen und gemeinsame Dreiphasenmessung mehrerer Verbraucher abbilden. Keine Einzel-Istleistungen aus einer Gesamtmessung erfinden; Messgruppe von einzelnen Stellgrößen trennen.
- [ ] Projekt als oberste Einheit modellieren; alle Anlagen/Objekte über stabile IDs referenzieren. Vincents Struktur als anonymisierten durchgängigen Referenzfall und reales lokales Privatprojekt verwenden; zusätzlich abweichende Anlagen testen.
- [ ] Herkunft jeder Bilanzgröße sichtbar machen: gemessen/berechnet/prognostiziert, Quelle, Zeit, Einheit und Formel. Hauptquelle festlegen, doppelte Nutzung und zirkuläre Ableitungen ablehnen.
- [ ] Mehrere eigenständige Anlagen in einer HA-Installation mit stabiler Anlagen-ID, eigenem Netzanschluss, Tarifen, Geräten und Plan konfigurieren; gemeinsame Übersicht anbieten.
- [ ] Änderungen, Datenfehler und Neuplanung auf die betroffene Anlage begrenzen; Netzbezug einer Halle nicht rechnerisch mit Einspeisung einer anderen Halle verrechnen.
- [ ] HA-Messentitäten einschließlich Shelly als Haupt-, Zweig- oder Gerätemessung aufnehmen; enthaltene Unterzähler nicht zusätzlich zum Gesamtwert summieren.
- [ ] Geräte-/Firmwareinventar und vorhandene HA-Entitäten/Node-RED-Flows aufnehmen; private Daten nur lokal.
- [ ] Eastron als gemeinsame Netzbilanz und Janitza-Zweige zuordnen; Erzeugung, Verbraucher und Speicher nicht doppelt zählen.
- [ ] Import-/Export-Vorzeichen und Messgleichzeitigkeit mit aufgezeichneten Fällen prüfen.
- [ ] Vollständige Bezugskosten und Direktvermarktungserlöse einschließlich Abzügen modellieren; Viertelstunden, Einheiten und Steuerbasis ausdrücklich festlegen.
- [ ] Bei bislang allein verfügbaren Börsenpreisen die Rechnung als unvollständiges Tarifszenario kennzeichnen; fehlende Aufschläge nicht als verifiziert null behandeln.
- [ ] Produktiven Preisanbieter und verzögerte Veröffentlichung behandeln; Tarifwechsel und Quellenfehler testen.
- [ ] Beide Batterietürme, Kapazität, SOC, BMS-Leistungsgrenzen, Spannung und Anschlussgrenzen abbilden.

Abnahme: eine nachvollziehbare Bilanz je Messintervall; Preise stimmen mit Vertragsbeispielen überein; jede Grenze hat eine Quelle.

### 3. Prognosen mit überprüfter Qualität

- [ ] Historische Messdaten über dokumentiertes Format importieren; Lücken/Ausreißer/Nettozweigmessungen erkennen.
- [ ] Lastprognose an HA-Datenfluss anschließen; Tages-/Wochenprofile, aktuelle Abweichungen und bekannte Sonderlasten berücksichtigen.
- [ ] Vorhandene HA-Prognose bevorzugen und direkten PV-Prognosedienst anbieten; Auswahl, Kosten und Einführung noch klären. Anlagenorientierung und Leistungsgrenzen berücksichtigen.
- [ ] Rollierende Rücktests ohne Zukunftswissen; MAE, Bias und wirtschaftliches Ergebnis gegen einfache Baselines ausweisen.
- [ ] Prognoseunsicherheit zunächst über transparente Szenarien behandeln; keine unbelegten Wahrscheinlichkeiten.

Abnahme: Bericht mit Zeitraum, Datenabdeckung, Baselines und Fehlern; fehlende Daten sind sichtbar und werden nicht als Nullverbrauch ausgegeben.

### 4. Dynamische Planung mit geringem Aufwand

- [ ] Zwei Zeitebenen entwerfen: wirtschaftliche Planung und davon getrennte schnelle Sollwertbegrenzung.
- [ ] Neuplanung bei neuen Preisen/Prognosen, relevanten anhaltenden Last-/PV-/SOC-Abweichungen und Konfigurationsänderung.
- [ ] Schwellen/Hysterese, Mindestabstand, gebündelte Ereignisse und Cache auf Zielhardware messen statt willkürlich versprechen.
- [ ] Gleichzeitige Berechnungen vermeiden; überholte Ergebnisse verwerfen; laufende HA-Oberfläche nicht blockieren.
- [ ] Gemessene Laufzeit, Datenalter, Planversion und Anlass der Neuplanung anzeigen.

Abnahme: Lastsprung und Preisänderung werden in Replay erkannt; kurze Schwankungen lösen keine Rechenflut aus; konkrete Zeit-/RAM-Grenzen nach Hardwareklärung festlegen.

### 5. Bedienung und Kostenrechnung

- [ ] Anlagenübersicht und Anlagenwechsel vorsehen; im Einrichtungsassistenten Netzanschluss, Messstellen, Speicher und Verbraucher eindeutig einer Anlage zuordnen.
- [ ] Echte HA-Oberfläche als erste Betriebsplattform aus dem lokalen Prototyp entwickeln; Anlage/Quellen/mehrere Speicher/Strategie mit wenigen Pflichtangaben geführt einrichten, Details optional für Experten.
- [x] Erste HA-Projektoberfläche mit Seitenleiste, Speichern/Laden, Import/Export, Netz-/Bereich-/Verbindungs-/Geräteformularen und drei Strukturansichten. Vollständige Prognose-/Regelbedienung bleibt offen.
- [ ] Einfache Startvorlage mit einem Wechselrichter und einem Speicher anbieten; weitere Speicher, Messgeräte, Heizstäbe und E-Ladestationen einzeln ergänzen. Eine nutzbare Hauslastquelle in der Einrichtung prüfen; Ableitungsweg noch klären.
- [ ] Kaufpreis, nutzbare Kapazität, SOC-Fenster, belegte Zyklen-/Kalenderannahmen, Betriebskosten und Wirkungsgrade bearbeiten.
- [ ] Investitionsumlage, marginalen Verschleiß, Verluste und entgangene Einspeiseerlöse verständlich getrennt darstellen.
- [ ] Plan/Ist, SOC, Haus/PV/Netz und Preise mit Begründungen anzeigen; Datenlücken und Prognoseunsicherheit kenntlich machen.
- [ ] Manueller Vorrang, Änderungen der Reserve und Vergleich von Strategien; Desktop/Mobilansicht und verständliche Fehlermeldungen prüfen.
- [ ] Prognostizierte und tatsächlich ermittelte Einsparungen unterscheiden; Einstellungen exportieren/sichern, ohne Geheimnisse offenzulegen.

### 5a. Flexible Verbraucher – Teil des ersten nutzbaren Umfangs

- [ ] Heizstäbe und weitere flexible Lasten als eigene Geräte mit Messung und nachgewiesenen Fähigkeiten aufnehmen; stufenlose Leistungsregelung bereits in der ersten nutzbaren Version unterstützen.
- [ ] Prioritäten und erlaubte Energiequellen je Verbraucher konfigurieren; „nur aktueller PV-Überschuss“ als Betriebsart anbieten, Batterie-/Netznutzung nur entsprechend gewählter Freigaben.
- [ ] Bestehenden Fall HA-Ein/Aus plus interne Regelung und Shelly-Messung abbilden. Nur für nachgewiesene Leistungsregler stufenlose Sollwerte anbieten; Messentität ist keine Stellgröße.
- [ ] Bei Beschränkung auf gespeicherte PV Herkunftsbilanz über Netzladen, Entladen und Verluste definieren; unbekannte Herkunft nicht aus SOC ableiten.
- [ ] Bei Überschussregelung laufende Heizleistung berücksichtigen: nach dem Einschalten sinkende Einspeisung bedeutet nicht, dass der ursprüngliche Überschuss verschwunden ist. Zusammenspiel mit Speicherregler gegen Schwingen und gegenseitiges Nachregeln testen.
- [ ] Verbraucher bereits in der gemessenen Hauslast erkennen; geplanten Mehrverbrauch und Grundlast ohne Doppelzählung prognostizieren.
- [ ] Temperatur-/Energiebedarf, Mindestlaufzeiten, Leistungsgrenzen und lokale Geräteschutzfunktionen je unterstütztem Gerät definieren; keine Schaltfähigkeit allein aus einem vorhandenen Messwert ableiten.
- [ ] Zuerst simulierte Entscheidungen und Messwertintegration; Live-Steuerung bleibt gesondert freizugeben.

### 6. Geräteintegration zunächst lesend und simuliert

- [ ] Eigene HA-unabhängige Adapter-/Geräteverwaltung entwerfen; HA bleibt erste Oberfläche, spätere eigenständige Auslieferung ermöglichen.
- [ ] Modbus TCP, RTU/RS485, Solarman v5 über pysolarmanv5 und MQTT im ersten nutzbaren Umfang implementieren, zunächst mit Simulatoren und nachgewiesenen Profilen.
- [ ] RTU über USB-RS485 und über TCP-zu-RTU-Gateway ausdrücklich abdecken; Gatewaymodus (Modbus TCP oder RTU-over-TCP), serielle Parameter, stabile USB-Zuordnung, Zieladressen und Wiederverbindung separat testen.
- [ ] Gerätesuche im gewählten Netz, MQTT über eingetragenen Broker und manuelle Einrichtung anbieten; IP/Hostname soweit verfügbar, Erkennungsgrund und unklare Zuordnung anzeigen.
- [ ] Geführte Bestätigung von Profil, Anlage und Messrollen; keine Registeradressen aus Hostnamen ableiten. Erkennung nur lesend, begrenzt und abbrechbar, ohne Gerätebefehle.
- [ ] Transporttests für Timeout, Wiederverbindung, unvollständige Antworten und konkurrierende Zugriffe; MQTT-Topics/Payloads, Authentifizierung und Datenfrische explizit zuordnen.
- [ ] Zunächst Solis/Bluesun unterstützen; Energiemanager als späteren direkten Gerätecontroller auslegen, Node-RED übergibt Wünsche über dokumentierte Schnittstelle.
- [ ] Wünsche mit Quelle, Priorität, Gültigkeit und Konfliktbehandlung definieren; Geräte-/Reservegrenzen bleiben von der gewählten Bedienpriorität getrennt.
- [ ] Rolle Plexlog/Node-RED/Solis klären; ein Sollwertgeber je Aktor, ein Master je RTU-Bus.
- [ ] Plexlog-Adapter zunächst lesend: OpenGateway-Version, Firmware, Gerätezuordnung und dokumentierte Messwerte prüfen; Vorzeichen normalisieren und doppelte Gateway-/Direktmessungen vermeiden.
- [ ] Maschinenlesbarkeit aktiver Direktvermarkter-/Netzbetreibervorgaben separat belegen. UI-Diagnose und Messregister nicht mit einer Sollwertschnittstelle gleichsetzen; unbekannte Vorgabe nicht als unbegrenzt behandeln.
- [x] Dokumentennachweis: Janitza 604-PRO als Gateway zu 103-CBM; Plexlog ThirdPartyClient mit lesbaren Vorgaberückmeldungen. Details unter docs/protocols/. Keine technische Prüfung an Geräten erfolgt.
- [ ] Janitza-Gateway mit gemeinsamen Verbindungsressourcen und einzelnen Zieladressen modellieren. Nutzer bestätigt 103er am 604-PRO; aktive Parameter später lesend erfassen, nicht pauschal umstellen.
- [x] Lesende TCP-Transportbasis und dokumentiertes 103-CBM-Leistungsprofil mit gemeinsamem Client/Unit-ID im Simulator testen. UMG-604-Eigenprofil, echte Endpunkte, Geräteverwaltung und Polling noch nicht implementiert.
- [ ] Externe Wirk-/Blindleistungsvorgaben mit Bezugsgröße, Herkunft, Gültigkeit und Regelzuständigkeit in Planung/Anzeige integrieren; bestehende Anlagenregelung nicht überschreiben und Wirkleistungsreserven bei Blindleistung gerätespezifisch berücksichtigen.
- [ ] Modell-/Firmwareabhängige Solis/BSE-Schnittstelle belegen; Register nicht aus Umlabelung ableiten.
- [ ] Simulierten Node-RED-Vertrag mit Einheiten, Gültigkeit, Quittierung, Planversion und Wiederholungsverhalten festlegen.
- [ ] Frische Netzbilanz/BMS-Grenzen erzwingen, Rampen und Abweichung Soll/Ist prüfen.
- [ ] Fehlerfallmatrix für Messausfall, Preisfehler, Internetverlust, HA-Neustart und konkurrierende Steuerung testen.
- [ ] Erst nach gesonderter Freigabe kontrollierte Gerätetests und danach automatische Aktorfreigabe.

### 7. Auslieferungsqualität

- [ ] Vollständigen versionierten Projekt-Konfigurationsexport und -import gemäß PROJECT_FORMAT.md implementieren; Vorschau, Migration, Referenzprüfung und atomare Übernahme testen.
- [ ] Export-/Import-Rundlauf für Gatewaygeräte, mehrere Speicher und getrennte Anlagen; keine privaten Zugangsdaten im Standardexport, keine automatischen Aktorbefehle beim Import.
- [ ] Installation/Update/Neustart und Konfigurationsmigration in echter HA-Testumgebung prüfen.
- [ ] Durchgängige Replaytests vom Messwert bis zum simulierten Sollwert; 23-/25-Stunden-Tage und unvollständigen Folgetag einschließen.
- [ ] Versions-/Änderungsprotokoll und bekannte Grenzen pflegen; kompatible HA-Versionen dokumentieren.
- [ ] CI-Warnungen zu Actions-Versionen gesondert bereinigen; aktueller erfolgreicher Lauf bleibt Referenz.
- [ ] Nachweisbare Reifegradgrenzen für Simulation, beobachtenden Parallelbetrieb und späteren Regelbetrieb festlegen.

Nächste unabhängige Schritte: geführte Standort-/Gerätezuordnung nach PROJECT_HIERARCHY.md, explizite lesende Einbindung der geprüften Transportbasis (ohne Setup-Seiteneffekt) sowie Regression/Ressourcenvergleich für kleine Speicherleistungen. Ein Projekt kann getrennte Anschlüsse und mehrere Bereiche an einem gemeinsamen Anschluss enthalten. Zielhardware Raspberry Pi 5 ist bestätigt; RAM und Last sind offen. Konkrete Geräteparameter, Rückfall-/Wunschprioritäten, Prognosedienst, Reservepolitik und Vertragsformeln bleiben offen. Aktuelle Version bleibt Planung/Simulation.

## Pro wiederkehrendem Lauf

1. Status/Plan/letzte Tests lesen, einen nützlichen offenen Punkt auswählen.
2. Annahmen und Datenverträge vor Änderungen klären; bei Bedarf Subagenten für unabhängige Aufgaben nutzen.
3. Implementieren und relevante Regressionstests ausführen.
4. Bei Oberflächenänderung Desktop und Mobilansicht prüfen.
5. Dokumentieren, Commit erstellen, autorisiertes Remote aktualisieren und relevante CI-Ergebnisse prüfen. Automatische Läufe erstellen keine neuen Releases ohne entsprechende Freigabe.
6. Diesen Plan um den tatsächlichen Stand und den nächsten konkreten Schritt ergänzen.

Nicht belegte Prognosegüte, fehlende Gerätezugänge oder externe Entscheidungen werden als offen dokumentiert. Sie rechtfertigen keine erfundenen Ergebnisse und keine wiederholten kosmetischen Änderungen.
