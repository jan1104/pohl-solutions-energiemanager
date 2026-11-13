# Nächste Entwicklungsschritte

## 0.1 — überprüfbare Grundlage

Rechenkern, Szenariodaten, Kostenmodell, historische Lastprofilhilfe, HA-Einrichtung und UI-Prototyp. Lokale Kern-/Eingabetests und Browserlogik werden ausgeführt. Vollständiger HA-Start und Verhalten in einer echten Testinstanz sind zusätzlich zu prüfen; unter dem lokalen Windows-System konnte HA wegen plattformabhängiger Abhängigkeiten nicht vollständig gestartet werden.

## 0.2 — Preisquellen und Konfiguration

Auswählbare Bezugs-/Einspeisequellen, JSON-URL, HA-Sensor, Festpreis, beobachteter SMARD-Adapter und klare Tarifumrechnung. Erweiterte Datenvalidierung und getrennte lokale Konfigurationsvorschau. Details und Quellenstatus siehe [PRICE_SOURCES.md](PRICE_SOURCES.md). Arbeitsfortschritt siehe [WORK_PLAN.md](WORK_PLAN.md).

## Danach — echte Datengrundlage

- Zuerst Anlage, dann Anschluss und Messgerät: [PROJECT_SCHEMA_V2_DRAFT.md](PROJECT_SCHEMA_V2_DRAFT.md). Entwicklungsmodell und explizite Migrationsvorschau geprüft; JS-Struktur-/Migrationsvertrag und gemeinsamer JSON-Grenzvertrag geprüft; expliziter Persistenzwechsel mit Originalerhalt und versionsbewusste HA-Speicherung implementiert. Die Format-2-Ansicht führt bereits durch Anlage und Netzanschluss. Bestehende Projekte können nach Vorschau und Bestätigung umgestellt werden. Die geführte Netzmessung unterstützt vorhandene und neue Gesamtwirkleistungskanäle. Messquellen lassen sich in der Ansicht konfigurieren. Gespeicherte Kanäle lassen sich ausdrücklich mit einem Testwert prüfen. Der Modbus-Lesepfad ist mit synthetischen Registerantworten geprüft. Die Quellenprüfung berücksichtigt die Registerbreite bereits beim Import. Als Nächstes folgt die ausdrücklich gestartete Prüfung dieses Lesepfads in der Oberfläche.
- Zentrale Datenspeicherung im Grundmodul: [CENTRAL_STORAGE.md](CENTRAL_STORAGE.md). HA-Projektablage seit 0.5.0 an SQLite angeschlossen; ausdrücklicher asynchroner Konfigurationszugang für Fachmodule implementiert; überschreibungsfreie konsistente Sicherung als Kern-API implementiert; automatische Aktivierung, Historien und Sicherungs-/Restore-Bedienung noch offen.
- Grundmodul und eigene Prognosemodule: [MODULE_KERNEL.md](MODULE_KERNEL.md). Basisfunktionen in HA angebunden; konkrete Prognose-/Fachverträge und Provider noch offen.
- Gemeinsame Grundfunktionen/Datenfluss: [SYSTEM_LOGIC.md](SYSTEM_LOGIC.md). Zentrale TCP-/Gatewayverwaltung, lesendes RTU-over-TCP und Profil-Lesevertrag implementiert; zentraler Besitzer an HA-Lebensdauer und internen ausdrücklichen Leseaufruf angebunden; Bedienoberfläche, physische Gatewayprüfung und weitere Transportarten offen.
- Vorhandene HA-Entitäten und Node-RED-Flows inventarisieren, ohne Zugangsdaten ins Repository zu übernehmen.
- Vorzeichen/Einheiten und Messstellenbilanz Eastron/Janitza abgleichen.
- Reine Laufzeitprüfung von Messwertalter, Originalmesszeit, Quellenherkunft und Ableitungen sowie explizite Einzelmessstellenbindung an übergebene Rohwerte umgesetzt. Automatische Quellenidentität, elektrische Abdeckung und lesende Adapteranbindung noch offen. Siehe [RUNTIME_METERING.md](RUNTIME_METERING.md).
- Verfügbarkeit der Preisquellen einschließlich Zeitumstellung und verzögerter Folgetagsveröffentlichung weiter überwachen und einen geeigneten produktiven Datenanbieter festlegen.
- Separate tatsächliche Bezugs- und Einspeiseverträge abbilden.
- PV-/Wetterprognose anbinden; historische Lastmessungen importieren.
- Prognosen mit rollierendem Rücktest messen, MAE/Bias dokumentieren, einfache Baseline schlagen.

## 0.3 bis 0.5 — Projektverwaltung und native HA-Oberfläche

- Ab 0.5.1 ruhige Projektübersicht: ein nächster Schritt für leere Projekte; seltene Aktionen und Formulare werden gezielt geöffnet.
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
