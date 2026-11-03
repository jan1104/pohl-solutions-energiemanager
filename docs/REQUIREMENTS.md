# Anforderungen und offene Entscheidungen

Stand: 2026-11-03. Bestätigte Wünsche sind von Vorschlägen und noch offenen Entscheidungen getrennt. Referenzanlage und Verträge werden nicht mit privaten Unterlagen im Repository hinterlegt.

## Bestätigt

- Marke: Pohl Solutions Energiemanager; verständliche deutsche Bedienung in Home Assistant, Zusammenarbeit mit Node-RED.
- Allgemeines Produkt für unterschiedliche Anlagen und Geräte; Vincent ist nur eine Beispielanwendung. Dessen Kapazität, Tarife, Messstellen und Geräte dürfen keine fest eingebauten Betriebsannahmen werden.
- Erste nutzbare Version: Home-Assistant-Integration mit eigener übersichtlicher Bedienoberfläche, zunächst Solis/Bluesun; weitere Geräte später.
- Bereits die erste Version plant mehrere Speicher-Wechselrichter gemeinsam. Jeder besitzt eigene SOC-/Kapazitäts-/Leistungsgrenzen und angeschlossene Batterien; Zahl der Türme ist nicht mit Zahl unabhängiger Wechselrichter gleichzusetzen.
- Eine HA-Installation muss mehrere getrennte Anlagen verwalten können, beispielsweise zwei Hallen mit jeweils eigenem Stromanschluss. Je Anlage zunächst ein gemeinsamer Netzanschluss; mehrere Speicher dahinter werden gemeinsam geplant. Netzbilanzen, Tarife, Reserven und Gerätezuordnungen bleiben je Anlage getrennt.
- Messgeräte und Shelly-Messwerte müssen je Anlage hinzufügbar sein. Messrollen und enthaltene Unterzähler sind ausdrücklich zuzuordnen, damit Verbräuche nicht doppelt gezählt werden.
- Flexible Verbraucher wie Heizstäbe für Heizungen sollen ergänzbar sein. Ob deren Steuerung bereits zum ersten nutzbaren Umfang gehört und welche Regelarten erforderlich sind, ist noch offen.
- Geführte Einrichtung mit wenigen Pflichtangaben und optionalen Experteneinstellungen.
- PV-Prognosen: vorhandene HA-Prognose bevorzugen; direkt eingebundenen Prognosedienst ebenfalls anbieten. Möglichst kostenlos starten, kostenpflichtige Dienste optional. Konkreter Anbieter und dessen Grenzen noch zu prüfen.
- Später führt der Energiemanager Gerätebefehle direkt aus; Node-RED darf Wünsche übergeben. Es erhält damit keine parallele unkoordinierte Schreibverantwortung.
- Einspeisung wird beim Referenzfall über einen Direktvermarkter nach Viertelstundenpreisen vergütet. Die genaue Preisformel einschließlich Abzügen ist noch offen.
- Netzladen ist erlaubt, sofern die Gesamtrechnung es rechtfertigt. Bei vorhandenem PV-Überschuss reduziert AC-Laden zunächst die Einspeisung; der Planer darf dieselbe Energie nicht zusätzlich als Netzbezug zählen.
- Bestehende PV-Wechselrichter speisen weiter ein. Überschuss oberhalb der möglichen Speicherladung darf ins Netz gehen; keine zugesagte Nulleinspeisung der gesamten Anlage.
- Wirtschaftliche Planung soll Bezug, Einspeisung, Verluste, marginalen Verschleiß, PV und Hausverbrauch gemeinsam berücksichtigen.
- Wahl zwischen wirtschaftlicher Planung und möglichst vermiedenem Netzbezug. Kostenminimum und geringster Energiebezug sind unterschiedliche Ziele und müssen in der Oberfläche getrennt erklärt werden.
- Prognosen und Plan passen sich an geänderten Verbrauch, PV und Preise an. Begrenzter Rechenbedarf ist eine ausdrückliche Anforderung.
- SOC-Fenster/Entladetiefe werden im Energiemanager vorgegeben; Lebensdauerannahmen müssen dazu passen.
- Mindestreserve und optionale Notstromreserve sind je Anlage einfach einstellbar. Kein fester Reservewert wurde beschlossen. Eine Reserve allein garantiert keine Notstromversorgung; diese erfordert passende Anlagenfähigkeiten.
- Gezielter Batterieverkauf soll einschließlich netzgeladener Energie unterstützt werden, sofern der jeweilige Vertrag dies erlaubt. Je Anlage sind Netzladen und Batterieexport getrennte Freigaben; diese Produktanforderung aktiviert keinen Export in bestehenden Konfigurationen.
- Aktuell liegen nur Börsenpreise vor. Bezugsaufschläge und Einspeiseabzüge müssen noch geklärt werden. Berechnungen ohne vollständige Tarifangaben sind als Szenario mit unvollständigen Vertragsdaten zu kennzeichnen, nicht als tatsächlicher Gewinn.
- Konfigurierbare Preisquellen und Kostenannahmen, professionelle übersichtliche Oberfläche, Git-Versionierung und Entwicklung alle sechs Stunden.
- Gegenwärtige Software bleibt Planung/Simulation. Diese Anforderungen erteilen keine Freigabe für Live-Schreibzugriffe.

## Vorgeschlagener Aufbau, noch zu konkretisieren

1. Messdaten mit eindeutiger Herkunft, Zeitpunkt, Einheit und Vorzeichen erfassen.
2. PV- und Lastprognosen sowie tatsächliche Vertragswerte für einen rollierenden Horizont zusammenführen.
3. Einen wirtschaftlichen Viertelstundenplan mit Mindestreserve, Leistungsgrenzen und nachvollziehbarem Restenergiewert berechnen.
4. Bei neuen Preisen/Prognosen oder wesentlicher anhaltender Abweichung neu planen; kurze Änderungen zusammenfassen und Berechnungen begrenzen.
5. Später ein separater schneller Regler: aktuellen Sollwert anhand der frischen Netzbilanz und BMS-Grenzen begrenzen. Der Viertelstundenplan ersetzt keine laufende Leistungsmessung.
6. Gründe, Datenalter, Unsicherheit, tatsächliche Ergebnisse und manuellen Vorrang anzeigen.

## Fragerunde 2 – beantwortet

- Batterieverkauf: auch netzgeladener Strom, sofern vertraglich erlaubt.
- Reserve: konfigurierbar, optionaler Notstrom; einfache Bedienung und allgemeine Anlagenverwendbarkeit sind entscheidend. Dynamische Reservepolitik und konkrete Werte noch offen.
- Preise: nur Börsenpreise verfügbar; vollständige Aufschläge/Abzüge fehlen.

## Fragerunden 3 und 4 – beantwortet

- HA mit eigener Oberfläche; Solis/Bluesun zuerst; geführte Einrichtung plus Expertenoptionen.
- Mehrere Speicher-Wechselrichter bereits gemeinsam in der ersten Version.
- HA-Prognose bevorzugen, zusätzlich direkte Prognosedienste anbieten.
- Energiemanager als späterer direkter Gerätecontroller, Node-RED als Wunschgeber.

## Fragerunde 5 – beantwortet, Prioritäten weiterhin offen

- Ein gemeinsamer Netzanschluss je Anlage; mehrere eigenständige Anlagen in einer HA-Installation sind erforderlich.
- Zusätzlich Messgeräte/Shelly und flexible Verbraucher wie Heizstäbe aufnehmen.
- Prognosedienste möglichst kostenlos, kostenpflichtige Angebote optional.
- Vorrang und Ablauf manueller/Node-RED-Wünsche wurden noch nicht festgelegt.

## Fragerunde 6 – Antwort ausstehend

- Flexible Verbraucher bereits in Version 1 steuerbar, nur Ein/Aus oder auch stufenlos, oder zunächst nur Messung?
- Heizstabziele: Zieltemperatur/Fertigstellungszeit, ausschließlich PV-Überschuss oder beides auswählbar?
- Zeitlich begrenzter manueller Vorrang, dauerhafter Handbetrieb oder Entscheidung später?

Notstromreserve ist technisch eine Randbedingung, die auch bei wirtschaftlicher Planung oder bei Minimierung des Netzbezugs gelten kann. Die vorgeschlagene einfache Bedienung darf diese Kombination nicht verhindern.

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
- Lokale Datenhaltung, Aufbewahrung und Sicherung; gemeinsame Übersicht und Berechtigungen für mehrere Anlagen?

Offene Antworten werden nicht aus technischen Standardwerten als Kundenentscheidung abgeleitet. Weiterentwicklung kann unabhängige Prüfungen und Infrastruktur umsetzen, muss abhängige Betriebsentscheidungen offenlassen.
