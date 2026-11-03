# Anforderungen und offene Entscheidungen

Stand: 2026-11-03. Bestätigte Wünsche sind von Vorschlägen und noch offenen Entscheidungen getrennt. Referenzanlage und Verträge werden nicht mit privaten Unterlagen im Repository hinterlegt.

## Bestätigt

- Marke: Pohl Solutions Energiemanager; verständliche deutsche Bedienung in Home Assistant, Zusammenarbeit mit Node-RED.
- Einspeisung wird beim Referenzfall über einen Direktvermarkter nach Viertelstundenpreisen vergütet. Die genaue Preisformel einschließlich Abzügen ist noch offen.
- Netzladen ist erlaubt, sofern die Gesamtrechnung es rechtfertigt. Bei vorhandenem PV-Überschuss reduziert AC-Laden zunächst die Einspeisung; der Planer darf dieselbe Energie nicht zusätzlich als Netzbezug zählen.
- Bestehende PV-Wechselrichter speisen weiter ein. Überschuss oberhalb der möglichen Speicherladung darf ins Netz gehen; keine zugesagte Nulleinspeisung der gesamten Anlage.
- Wirtschaftliche Planung soll Bezug, Einspeisung, Verluste, marginalen Verschleiß, PV und Hausverbrauch gemeinsam berücksichtigen.
- Wahl zwischen wirtschaftlicher Planung und möglichst vermiedenem Netzbezug. Kostenminimum und geringster Energiebezug sind unterschiedliche Ziele und müssen in der Oberfläche getrennt erklärt werden.
- Prognosen und Plan passen sich an geänderten Verbrauch, PV und Preise an. Begrenzter Rechenbedarf ist eine ausdrückliche Anforderung.
- SOC-Fenster/Entladetiefe werden im Energiemanager vorgegeben; Lebensdauerannahmen müssen dazu passen.
- Konfigurierbare Preisquellen und Kostenannahmen, professionelle übersichtliche Oberfläche, Git-Versionierung und Entwicklung alle sechs Stunden.
- Gegenwärtige Software bleibt Planung/Simulation. Diese Anforderungen erteilen keine Freigabe für Live-Schreibzugriffe.

## Vorgeschlagener Aufbau, noch zu konkretisieren

1. Messdaten mit eindeutiger Herkunft, Zeitpunkt, Einheit und Vorzeichen erfassen.
2. PV- und Lastprognosen sowie tatsächliche Vertragswerte für einen rollierenden Horizont zusammenführen.
3. Einen wirtschaftlichen Viertelstundenplan mit Mindestreserve, Leistungsgrenzen und nachvollziehbarem Restenergiewert berechnen.
4. Bei neuen Preisen/Prognosen oder wesentlicher anhaltender Abweichung neu planen; kurze Änderungen zusammenfassen und Berechnungen begrenzen.
5. Später ein separater schneller Regler: aktuellen Sollwert anhand der frischen Netzbilanz und BMS-Grenzen begrenzen. Der Viertelstundenplan ersetzt keine laufende Leistungsmessung.
6. Gründe, Datenalter, Unsicherheit, tatsächliche Ergebnisse und manuellen Vorrang anzeigen.

## Fragerunde 2 – Antwort ausstehend

- Darf Batterieenergie gezielt verkauft werden? Nur Eigenverbrauch, zusätzlich gespeicherte PV oder auch netzgeladene Energie? Vertragliche Zulässigkeit nicht voraussetzen.
- Welche Mindest-/Notstromreserve ist gewünscht und darf darüber eine dynamische Reserve geplant werden?
- Sind vollständige Vertragsformeln oder HA-Sensoren für Bezug und Einspeisung verfügbar?

## Weitere Fragen, in kleinen Runden zu klären

- Gewünschte Priorität: Euro minimieren, Netzbezug minimieren oder definierte Mehrkosten für Autarkie akzeptieren? Welche manuellen Betriebsarten?
- Standort/Ausrichtung/Leistung der PV, bestehender Prognosedienst und HA-Entitäten; Leistungsbegrenzungen und Verschattung.
- Verfügbare Last-, PV-, Netz- und SOC-Historie, Messintervalle, Datenlücken; besondere Verbraucher und wiederkehrende Arbeitszeiten.
- Tatsächliche Solis/BSE-Modellkennung, Firmware, BMS-Grenzen, nutzbare Kapazität und Messung beider Türme. Pauschal 50 kW sind keine garantierte Ladeleistung bei jedem SOC.
- Rolle von Plexlog und Node-RED, bestehende Schreibzugriffe, Kommunikationswege und gewünschter alleiniger Sollwertgeber.
- Anschlusslimits, weitere Verbraucher am PV-Abgang, eindeutige Messstellenbilanz. Ein Zweigzähler ist nicht automatisch ein reiner Erzeugungszähler.
- Zulässiges Verhalten bei fehlenden Preisen, Prognosen, Internet, Messwerten und HA-Neustart; manuelle Rücknahme und Erreichbarkeit.
- Hardware für HA, akzeptable Berechnungsdauer und Zeitraum der Historie; daraus messbares Ressourcenbudget ableiten.
- Kaufpreis, Förderungen/Restwert, laufende Kosten, Wirkungsgrade, belegte Lebensdauerbedingungen und gewünschte Wirtschaftlichkeitsanzeige.
- Erster Einsatz nur Vincent oder mehrere Anlagen? Lokale Datenhaltung, Aufbewahrung und Sicherung; zunächst HA-Oberfläche oder eigenständige Anwendung?

Offene Antworten werden nicht aus technischen Standardwerten als Kundenentscheidung abgeleitet. Weiterentwicklung kann unabhängige Prüfungen und Infrastruktur umsetzen, muss abhängige Betriebsentscheidungen offenlassen.
