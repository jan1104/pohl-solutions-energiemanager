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

- [ ] Bezug und Einspeisung getrennt auswählen: vorhandene Prognosepreise, HA-Sensor, JSON-URL, Festpreis oder SMARD.
- [ ] Einheiten und Tariftransformationen ausdrücklich konfigurieren; keine Vermischung von EUR/MWh, ct/kWh und EUR/kWh.
- [ ] Negative Preise, fehlende Folgetagspreise und Zeitumstellung korrekt behandeln.
- [ ] Netzwerkabrufe begrenzen, Fehler sichtbar machen und keine Preise erfinden.
- [ ] Bedienoberfläche mit URL-/Sensorauswahl und klarer Unterscheidung zwischen Vorschau und aktiver HA-Konfiguration.
- [ ] Reale HA-Tests für Quellenwechsel und gültige/ungültige Daten ergänzen.
- [ ] Dokumentation, Änderungsprotokoll und Versionsnummer aktualisieren; geprüften Stand committen/pushen.

## Danach, in dieser Reihenfolge

1. **Datenqualität und Rücktests:** Vorhandene historische Messdaten über ein ausdrücklich beschriebenes Importformat einlesen. Keine privaten CSVs im Repository. Lastprognose gegen einfache Baselines in rollierenden Zeitfenstern prüfen, MAE/Bias dokumentieren.
2. **PV-Prognoseadapter:** Vorhandene HA-Prognose auswählen, Quellenalter und Leistungsgrenzen ausweisen, mit tatsächlicher Erzeugung rücktesten. Keine erfundene Wetterprognose.
3. **Anlagenprofile und Messstellen:** Eastron als gemeinsame Netzbilanz, Janitza als getrennte Messstellen, vier Sungrows und ein Solis als konfigurierbares Referenzprofil. Doppelzählung und Vorzeichen mit Tests verhindern.
4. **HA-Bedienung:** Funktionen des lokalen Prototyps schrittweise in eine tatsächliche HA-Oberfläche übernehmen. Kostenmodell, Preisquellen und Annahmen sollen an einem nachvollziehbaren Ort bearbeitet werden können.
5. **Planungsverbesserung:** Unterschiedliche Reserven, Endenergieziele, BMS-Prognosegrenzen, Szenarien bei unsicherer PV/Last. Verbesserungen gegen bekannte Fälle und Baselines messen.
6. **Node-RED-Schnittstelle:** Dokumentierter simulierter Sollwertvertrag mit Frische, Einheiten, Rückmeldung und Rückfall. Kein Aktoraufruf ohne spätere ausdrückliche Freigabe.

## Pro wiederkehrendem Lauf

1. Status/Plan/letzte Tests lesen, einen nützlichen offenen Punkt auswählen.
2. Annahmen und Datenverträge vor Änderungen klären; bei Bedarf Subagenten für unabhängige Aufgaben nutzen.
3. Implementieren und relevante Regressionstests ausführen.
4. Bei Oberflächenänderung Desktop und Mobilansicht prüfen.
5. Dokumentieren, Commit erstellen, privates Remote aktualisieren und relevante CI-Ergebnisse prüfen.
6. Diesen Plan um den tatsächlichen Stand und den nächsten konkreten Schritt ergänzen.

Nicht belegte Prognosegüte, fehlende Gerätezugänge oder externe Entscheidungen werden als offen dokumentiert. Sie rechtfertigen keine erfundenen Ergebnisse und keine wiederholten kosmetischen Änderungen.
