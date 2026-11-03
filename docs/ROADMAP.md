# Nächste Entwicklungsschritte

## 0.1 — überprüfbare Grundlage

Rechenkern, Szenariodaten, Kostenmodell, historische Lastprofilhilfe, HA-Einrichtung und UI-Prototyp. Lokale Kern-/Eingabetests und Browserlogik werden ausgeführt. Vollständiger HA-Start und Verhalten in einer echten Testinstanz sind zusätzlich zu prüfen; unter dem lokalen Windows-System konnte HA wegen plattformabhängiger Abhängigkeiten nicht vollständig gestartet werden.

## 0.2 — Preisquellen und Konfiguration

Auswählbare Bezugs-/Einspeisequellen, JSON-URL, HA-Sensor, Festpreis, beobachteter SMARD-Adapter und klare Tarifumrechnung. Erweiterte Datenvalidierung und getrennte lokale Konfigurationsvorschau. Details und Quellenstatus siehe [PRICE_SOURCES.md](PRICE_SOURCES.md). Arbeitsfortschritt siehe [WORK_PLAN.md](WORK_PLAN.md).

## Danach — echte Datengrundlage

- Vorhandene HA-Entitäten und Node-RED-Flows inventarisieren, ohne Zugangsdaten ins Repository zu übernehmen.
- Vorzeichen/Einheiten und Messstellenbilanz Eastron/Janitza abgleichen.
- Verfügbarkeit der Preisquellen einschließlich Zeitumstellung und verzögerter Folgetagsveröffentlichung weiter überwachen und einen geeigneten produktiven Datenanbieter festlegen.
- Separate tatsächliche Bezugs- und Einspeiseverträge abbilden.
- PV-/Wetterprognose anbinden; historische Lastmessungen importieren.
- Prognosen mit rollierendem Rücktest messen, MAE/Bias dokumentieren, einfache Baseline schlagen.

## 0.3 — vollständige HA-Bedienung

- UI-Prototyp als echte HA-Oberfläche umsetzen, Kostenmodell dort integrieren.
- Geräteprofile mit Quellen, Firmware und nachgewiesenen Fähigkeiten.
- Mehrere Speicher, getrennte Reserveziele und Anschlussleistungsgrenzen.
- Sensitivitätsvergleich verschiedener Kapazitäten, SOC-Fenster und Kostenannahmen.
- Automatisch geplante Restenergieziele und Szenarien bei Prognoseunsicherheit.

## 0.4 — begrenzter Regelbetrieb

- Ein getesteter Solis/BSE-Adapter oder dokumentierte Node-RED-Befehlsschnittstelle.
- Vor Freigabe: Lesen, kleine Leistungsbefehle, Vorzeichen, Grenzen und Ausfallverhalten an der Testanlage nachweisen.
- Frische Netzbilanz, BMS-Grenzen, Stellrampen, Mindesthaltezeiten und Abweichung zwischen Plan und Ist.
- Definierter Rückfall bei HA-Neustart, Kommunikationsausfall, falschen Preisen und Messausfall.
- Erst anschließend automatische Aktorfreigabe; keine zweite konkurrierende Steuerung.

## Später

Heizstäbe, Wallboxen und flexible Verbraucher; zusätzliche Geräteadapter; nichtlineare Wirkungsgrade; belegte Alterungskennlinien; robuste/stochastische Planung; Vergleich tatsächlicher Einsparung mit fairen Gegenfällen. Diese Punkte sind Entwurf, keine bereits vorhandenen Funktionen.
