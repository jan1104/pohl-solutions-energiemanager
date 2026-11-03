# Änderungen

## Noch nicht veröffentlicht

- HA-unabhängige, ausschließlich lesende Modbus-TCP-Basis mit expliziten Zieladressen für TCP-zu-RTU-Gateways. Gemeinsamer Zugriff pro Client wird serialisiert; Rahmenprüfung, begrenzte Wartezeit und Wiederverbindung nach Fehler/Abbruch.
- Erstes UMG-103-CBM-Leseprofil für Wirk-/Phasenleistungen mit dokumentierter Float-Dekodierung und W→kW-Umrechnung.
- Loopback-Simulatorprüfungen für mehrere Gatewayziele, ungültige Antworten, Gerätefehler, Timeout und Abbruch. Noch nicht an HA-Einrichtung oder automatische Geräteabfrage angeschlossen; kein neuer HACS-Release und keine Live-Geräte getestet.

## 0.3.1 — 2026-11-03

- Ersteinrichtung fragt nur den Namen des Energiemanagers ab; keine Prognose-/SOC-/Leistungssensoren und kein Projektmodus-Schalter mehr im Einstieg.
- Bei Projektverwaltung ein leeres benanntes Projekt einmalig anlegen; gespeicherte Projekte bei Reload oder erneutem Setup erhalten.
- Bisherige sensorbasierte Simulation in ein separates Optionsmenü verschoben; bestehende Simulationseinträge bleiben nutzbar.
- HA-Laufzeitprüfung für Namensvalidierung, einfache Einrichtung, getrennte Simulation und Erhalt importierter Daten erweitert.
- Standort-/Gerätegruppenmodell präzisiert, noch kein grafischer Geräteassistent oder direkter Gerätetreiber.

## 0.3.0 — 2026-11-03

- HACS-Releasepaket mit passendem Assetnamen, wiederholbarem Build und Prüfung von ZIP-Struktur/Versionen. HACS erfordert ein öffentliches Repository; Sichtbarkeit bleibt bis ausdrücklicher Freigabe privat.
- Ausführbares Projektformat mit getrennten Netzanschlüssen, Bereichen, elektrischen Zweigen, Verbindungen, Geräten, Batterien und Messzuordnungen.
- Validierter JSON-Import/-Export, stabile Beziehungen, Kreis-/Doppelzählungs-/Quellnetzprüfung und anonyme Referenz-/Startvorlagen.
- Lokale Projektoberfläche mit drei Strukturansichten, Namenbearbeitung, Bereichsfilter, Importvorschau, Editor und expliziter Browser-Speicherung.
- HA-Projektmodus ohne Prognose-/SOC-Zwang, persistentes Projekt sowie Import-/Export-/Statusaktionen; keine Geräteverbindungen oder Aktorbefehle.
- Python-/Browser-Vertragsprüfungen, atomarer CLI-Roundtrip und erweiterter echter HA-Test für Speicherung und Fehlerfälle.
- Projektkonfiguration noch nicht an Mehrspeicheroptimierung oder einen vollständigen grafischen Geräteassistenten angeschlossen. Testablauf: docs/TESTING_0_3.md.

## 0.2.0 — 2026-11-03

- Unabhängige Preisquellen für Bezug und Einspeisung: Prognose, HA-Sensor, JSON-URL, Festpreis und experimenteller SMARD-Adapter.
- Explizite Einheiten, Faktor und Aufschlag; vollständige Zeitabdeckung, negative Preise und fehlende Folgetagspreise validieren.
- Bedingte Preisquellen-Einrichtung in HA sowie lokale Konfigurationsvorschau mit Export.
- Begrenzte asynchrone JSON-Abrufe, Quellenangabe und dokumentierter aktueller SMARD-Nutzungsstatus.
- Tests für Preisnormalisierung, Tariftrennung, Zeitumstellung und Datenlücken.
- Priorisierter Arbeitsplan für die eingerichtete Weiterentwicklung alle sechs Stunden.

## 0.1.0 — 2026-11-03

Erste Entwicklungsversion. Lokale Planung und Simulation; keine Gerätesteuerung.

- Projektgrundlage, Konventionen und automatische Prüfungen.
- Wirtschaftlichkeitsrechnung und Viertelstundenplanung.
- Home-Assistant-Integration für validierte Prognosen und lesbare Planwerte.
- Lokaler deutschsprachiger Oberflächenprototyp.
- Prognosegrundlage mit historischen Lastprofilen und überprüfbaren Annahmen.
