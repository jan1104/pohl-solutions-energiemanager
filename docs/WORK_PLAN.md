# Arbeitsplan

Stand: 2026-11-03. Dieser Plan steuert die weitere Entwicklung in diesem Chat und die wiederkehrenden Läufe alle sechs Stunden.

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

0.3.1: Einstieg auf frei benannten Energiemanager ohne HA-Sensorpflicht umgestellt; bestehende Simulation separat in Optionen. Neue Projekte leer anlegen, bestehende Importe erhalten. Standort/Netzanschluss/Bereich/Gerätegruppe künftig sauber trennen, siehe PROJECT_HIERARCHY.md. Eigene Standortverwaltung und direkter Geräteassistent noch offen.

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
- [ ] Kleine Lasten/Ladeleistungen korrekt berücksichtigen; nachgewiesenen 1-kW-Fall als Regression aufnehmen.
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

Nächster unabhängiger Entwicklungsschritt: Regression und Ressourcenvergleich für kleine Leistungen sowie Entwurf für gemeinsame Mehrspeicherplanung. Bestätigt: mehrere getrennte Anlagen in einer HA-Installation, je Anlage ein Netzanschluss und mehrere Speicher; Solis/Bluesun zuerst, geführte Einrichtung, später direkte Gerätesteuerung, Messgeräte/Shelly und flexible Verbraucher im ersten nutzbaren Umfang. Prioritäten und Energiequellen sind je Gerät einstellbar. Vorhandene Heizstäbe bieten HA-Ein/Aus und Shelly-Messung, keine nachgewiesene externe Leistungsregelung. Offen: Vorlagen, konkrete Geräte, Rückfall-/Wunschprioritäten, HA-Hardware, Prognosedienst, Reservepolitik und Vertragsformeln. Aktuelle Version bleibt Planung/Simulation.

## Pro wiederkehrendem Lauf

1. Status/Plan/letzte Tests lesen, einen nützlichen offenen Punkt auswählen.
2. Annahmen und Datenverträge vor Änderungen klären; bei Bedarf Subagenten für unabhängige Aufgaben nutzen.
3. Implementieren und relevante Regressionstests ausführen.
4. Bei Oberflächenänderung Desktop und Mobilansicht prüfen.
5. Dokumentieren, Commit erstellen, privates Remote aktualisieren und relevante CI-Ergebnisse prüfen.
6. Diesen Plan um den tatsächlichen Stand und den nächsten konkreten Schritt ergänzen.

Nicht belegte Prognosegüte, fehlende Gerätezugänge oder externe Entscheidungen werden als offen dokumentiert. Sie rechtfertigen keine erfundenen Ergebnisse und keine wiederholten kosmetischen Änderungen.
