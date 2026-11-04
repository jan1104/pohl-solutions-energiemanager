# Nächste Entwicklungsschritte

## 0.1 — überprüfbare Grundlage

Rechenkern, Szenariodaten, Kostenmodell, historische Lastprofilhilfe, HA-Einrichtung und UI-Prototyp. Lokale Kern-/Eingabetests und Browserlogik werden ausgeführt. Vollständiger HA-Start und Verhalten in einer echten Testinstanz sind zusätzlich zu prüfen; unter dem lokalen Windows-System konnte HA wegen plattformabhängiger Abhängigkeiten nicht vollständig gestartet werden.

## 0.2 — Preisquellen und Konfiguration

Auswählbare Bezugs-/Einspeisequellen, JSON-URL, HA-Sensor, Festpreis, beobachteter SMARD-Adapter und klare Tarifumrechnung. Erweiterte Datenvalidierung und getrennte lokale Konfigurationsvorschau. Details und Quellenstatus siehe [PRICE_SOURCES.md](PRICE_SOURCES.md). Arbeitsfortschritt siehe [WORK_PLAN.md](WORK_PLAN.md).

## Danach — echte Datengrundlage

- Grundmodul und eigene Prognosemodule: [MODULE_KERNEL.md](MODULE_KERNEL.md). Getesteter Versions-/Abhängigkeitskernel vorhanden; konkrete Fachverträge, Provider und HA-Anbindung noch offen.
- Gemeinsame Grundfunktionen/Datenfluss: [SYSTEM_LOGIC.md](SYSTEM_LOGIC.md). Zentrale TCP-/Gatewayverwaltung und Profil-Lesevertrag implementiert; HA-Anbindung und weitere Transportarten offen.
- Vorhandene HA-Entitäten und Node-RED-Flows inventarisieren, ohne Zugangsdaten ins Repository zu übernehmen.
- Vorzeichen/Einheiten und Messstellenbilanz Eastron/Janitza abgleichen.
- Reine Laufzeitprüfung von Messwertalter, Originalmesszeit, Quellenherkunft und Ableitungen sowie explizite Einzelmessstellenbindung an übergebene Rohwerte umgesetzt. Automatische Quellenidentität, elektrische Abdeckung und lesende Adapteranbindung noch offen. Siehe [RUNTIME_METERING.md](RUNTIME_METERING.md).
- Verfügbarkeit der Preisquellen einschließlich Zeitumstellung und verzögerter Folgetagsveröffentlichung weiter überwachen und einen geeigneten produktiven Datenanbieter festlegen.
- Separate tatsächliche Bezugs- und Einspeiseverträge abbilden.
- PV-/Wetterprognose anbinden; historische Lastmessungen importieren.
- Prognosen mit rollierendem Rücktest messen, MAE/Bias dokumentieren, einfache Baseline schlagen.

## 0.3 / 0.4 — Projektverwaltung und erste native HA-Oberfläche

- Umgesetzt: HA-Seitenleisteneintrag „Energiemanager“, dauerhaft gespeichertes Projekt, Basisformulare für Netzanschlüsse, Bereiche, Verbindungen und Geräte; Import/Export und getrennte Strukturansichten.
- Offen: durchgehend geführte Messquellen-Zuordnung, Kostenmodell und aktive Planung in dieser Oberfläche integrieren.
- Geräteprofile mit Quellen, Firmware und nachgewiesenen Fähigkeiten.
- Mehrere Speicher, getrennte Reserveziele und Anschlussleistungsgrenzen.
- 1-kW-Viertelstundenfehler im bisherigen endlichen Modell mit zusätzlichen Kandidatenzuständen korrigiert; allgemeine kontinuierliche Genauigkeit und Raspberry-Pi-Ressourcennachweis bleiben offen. Siehe [SMALL_POWER_PLANNING.md](SMALL_POWER_PLANNING.md).
- Sensitivitätsvergleich verschiedener Kapazitäten, SOC-Fenster und Kostenannahmen.
- Automatisch geplante Restenergieziele und Szenarien bei Prognoseunsicherheit.

## Später, erst nach gesonderter Freigabe — begrenzter Regelbetrieb

- Ein getesteter Solis/BSE-Adapter oder dokumentierte Node-RED-Befehlsschnittstelle.
- Vor Freigabe: Lesen, kleine Leistungsbefehle, Vorzeichen, Grenzen und Ausfallverhalten an der Testanlage nachweisen.
- Frische Netzbilanz, BMS-Grenzen, Stellrampen, Mindesthaltezeiten und Abweichung zwischen Plan und Ist.
- Definierter Rückfall bei HA-Neustart, Kommunikationsausfall, falschen Preisen und Messausfall.
- Erst anschließend automatische Aktorfreigabe; keine zweite konkurrierende Steuerung.

## Später

Heizstäbe, Wallboxen und flexible Verbraucher; zusätzliche Geräteadapter; nichtlineare Wirkungsgrade; belegte Alterungskennlinien; robuste/stochastische Planung; Vergleich tatsächlicher Einsparung mit fairen Gegenfällen. Diese Punkte sind Entwurf, keine bereits vorhandenen Funktionen.
