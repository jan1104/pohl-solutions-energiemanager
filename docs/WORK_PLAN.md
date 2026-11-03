# Arbeitsplan

Stand: 2026-11-03. Dieser Plan steuert die weitere Entwicklung in diesem Chat und die wiederkehrenden Läufe alle sechs Stunden.

## Auftrag und Grenzen

- Repository: `D:\depot\pohl-solutions-energiemanager`, privates GitHub-Repository `jan1104/pohl-solutions-energiemanager`.
- Änderungen in kleinen zusammenhängenden Schritten implementieren, passend testen, dokumentieren, committen und in dieses private Repository pushen.
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

Grundlagen: [bestätigte Anforderungen und Fragen](REQUIREMENTS.md), [nachgewiesene Logikbefunde](LOGIC_REVIEW_2026-11-03.md). Zunächst Rechenfehler und Datenmodell bearbeiten. Offene Betriebsentscheidungen nicht stillschweigend durch Standardwerte ersetzen.

### 1. Rechenkern und wirtschaftliche Ziele

- [ ] Kleine Lasten/Ladeleistungen korrekt berücksichtigen; nachgewiesenen 1-kW-Fall als Regression aufnehmen.
- [ ] Laufzeit und Speicherbedarf des bisherigen Verfahrens messen; Kandidat gegen kontinuierliche Referenz und analytische Fälle vergleichen.
- [ ] Rollierendes Endenergie-/Reservekonzept entwerfen; keine pauschale Gleichsetzung von aktuellem und End-SOC.
- [ ] Nachtentladung, billiges Netzladen vor teurem Bezug, bevorstehenden PV-Überschuss und negative Einspeisepreise prüfen.
- [ ] Wirtschaftlichkeitsziel und Autarkiewunsch als getrennte Betriebsarten definieren; Batterieverkauf erst nach Antwort konfigurieren.
- [ ] Betrieb unter Wunschreserve und oberhalb Wunschziel sauber von physischen BMS-Grenzen unterscheiden.
- [ ] Restenergie in Vergleichen fair bewerten; keine garantierten Einsparungen aus einem Prognoseplan ableiten.

Abnahme: bekannte Gegenbeispiele funktionieren; keine Energiebilanzverletzung; wiederholte Neuplanung leert/blockiert den Speicher nicht künstlich; Ressourcenbedarf ist dokumentiert.

### 2. Anlage, Messungen und Verträge

- [ ] Geräte-/Firmwareinventar und vorhandene HA-Entitäten/Node-RED-Flows aufnehmen; private Daten nur lokal.
- [ ] Eastron als gemeinsame Netzbilanz und Janitza-Zweige zuordnen; Erzeugung, Verbraucher und Speicher nicht doppelt zählen.
- [ ] Import-/Export-Vorzeichen und Messgleichzeitigkeit mit aufgezeichneten Fällen prüfen.
- [ ] Vollständige Bezugskosten und Direktvermarktungserlöse einschließlich Abzügen modellieren; Viertelstunden, Einheiten und Steuerbasis ausdrücklich festlegen.
- [ ] Produktiven Preisanbieter und verzögerte Veröffentlichung behandeln; Tarifwechsel und Quellenfehler testen.
- [ ] Beide Batterietürme, Kapazität, SOC, BMS-Leistungsgrenzen, Spannung und Anschlussgrenzen abbilden.

Abnahme: eine nachvollziehbare Bilanz je Messintervall; Preise stimmen mit Vertragsbeispielen überein; jede Grenze hat eine Quelle.

### 3. Prognosen mit überprüfter Qualität

- [ ] Historische Messdaten über dokumentiertes Format importieren; Lücken/Ausreißer/Nettozweigmessungen erkennen.
- [ ] Lastprognose an HA-Datenfluss anschließen; Tages-/Wochenprofile, aktuelle Abweichungen und bekannte Sonderlasten berücksichtigen.
- [ ] PV-Prognosedienst/HA-Quelle auswählen; Anlagenorientierung und Leistungsgrenzen berücksichtigen.
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

- [ ] Echte HA-Oberfläche aus dem lokalen Prototyp entwickeln; Anlage/Quellen/Batterie/Strategie geführt einrichten.
- [ ] Kaufpreis, nutzbare Kapazität, SOC-Fenster, belegte Zyklen-/Kalenderannahmen, Betriebskosten und Wirkungsgrade bearbeiten.
- [ ] Investitionsumlage, marginalen Verschleiß, Verluste und entgangene Einspeiseerlöse verständlich getrennt darstellen.
- [ ] Plan/Ist, SOC, Haus/PV/Netz und Preise mit Begründungen anzeigen; Datenlücken und Prognoseunsicherheit kenntlich machen.
- [ ] Manueller Vorrang, Änderungen der Reserve und Vergleich von Strategien; Desktop/Mobilansicht und verständliche Fehlermeldungen prüfen.
- [ ] Prognostizierte und tatsächlich ermittelte Einsparungen unterscheiden; Einstellungen exportieren/sichern, ohne Geheimnisse offenzulegen.

### 6. Geräteintegration zunächst lesend und simuliert

- [ ] Rolle Plexlog/Node-RED/Solis klären; ein Sollwertgeber je Aktor, ein Master je RTU-Bus.
- [ ] Modell-/Firmwareabhängige Solis/BSE-Schnittstelle belegen; Register nicht aus Umlabelung ableiten.
- [ ] Simulierten Node-RED-Vertrag mit Einheiten, Gültigkeit, Quittierung, Planversion und Wiederholungsverhalten festlegen.
- [ ] Frische Netzbilanz/BMS-Grenzen erzwingen, Rampen und Abweichung Soll/Ist prüfen.
- [ ] Fehlerfallmatrix für Messausfall, Preisfehler, Internetverlust, HA-Neustart und konkurrierende Steuerung testen.
- [ ] Erst nach gesonderter Freigabe kontrollierte Gerätetests und danach automatische Aktorfreigabe.

### 7. Auslieferungsqualität

- [ ] Installation/Update/Neustart und Konfigurationsmigration in echter HA-Testumgebung prüfen.
- [ ] Durchgängige Replaytests vom Messwert bis zum simulierten Sollwert; 23-/25-Stunden-Tage und unvollständigen Folgetag einschließen.
- [ ] Versions-/Änderungsprotokoll und bekannte Grenzen pflegen; kompatible HA-Versionen dokumentieren.
- [ ] CI-Warnungen zu Actions-Versionen gesondert bereinigen; aktueller erfolgreicher Lauf bleibt Referenz.
- [ ] Nachweisbare Reifegradgrenzen für Simulation, beobachtenden Parallelbetrieb und späteren Regelbetrieb festlegen.

Nächster unabhängiger Entwicklungsschritt: Regression und Ressourcenvergleich für kleine Leistungen; gleichzeitig Antworten zu Batterieverkauf, Reserve und Tarifformeln einarbeiten. Endenergie-/Reservepolitik erst nach den erforderlichen Antworten implementieren.

## Pro wiederkehrendem Lauf

1. Status/Plan/letzte Tests lesen, einen nützlichen offenen Punkt auswählen.
2. Annahmen und Datenverträge vor Änderungen klären; bei Bedarf Subagenten für unabhängige Aufgaben nutzen.
3. Implementieren und relevante Regressionstests ausführen.
4. Bei Oberflächenänderung Desktop und Mobilansicht prüfen.
5. Dokumentieren, Commit erstellen, privates Remote aktualisieren und relevante CI-Ergebnisse prüfen.
6. Diesen Plan um den tatsächlichen Stand und den nächsten konkreten Schritt ergänzen.

Nicht belegte Prognosegüte, fehlende Gerätezugänge oder externe Entscheidungen werden als offen dokumentiert. Sie rechtfertigen keine erfundenen Ergebnisse und keine wiederholten kosmetischen Änderungen.
