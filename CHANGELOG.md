# Änderungen

## Unveröffentlicht — 2026-11-04

- Bedien-/Modulentwurf konkretisiert: zentrale Eingabeorte, Herkunft automatisch/manuell bezogener Werte, wiederverwendbare Gerätebausteine und gemeinsame Messgruppen. Keine neue Laufzeitfunktion; siehe `docs/DEVICE_MODULES_AND_SETUP.md`.
- Zentrale lesende Verbindungsverwaltung: Geräte-/Profilreferenzen teilen einen nativen TCP-/Gatewayclient und dessen Warteschlange. Geräteeigene Unit-ID und Gatewayroute werden unabhängig vom elektrischen Messort aufgelöst.
- Gemeinsamer Register-Lesevertrag, geordnetes Beenden und explizite Ablehnung noch nicht implementierter Transportarten. Keine automatische HA-Anbindung oder USB-/RTU-over-TCP-Implementierung. Gesamtdatenfluss: `docs/SYSTEM_LOGIC.md`.
- Dokumentierten 1-kW-Viertelstundenfall im Planer korrigiert: begrenzte zusätzliche Energiezustände machen kleine Eigenverbrauchs-/Überschussübergänge wählbar, ohne das ursprüngliche Raster oder Endziel zu ändern. Vollständige Ergänzung nur innerhalb der Grenze von 1001 Zuständen, sonst sichtbarer Hinweis.
- Sechs neue Optimiererregressionen und ausführbarer synthetischer Ressourcenvergleich. Bleibt eine endliche Näherung; allgemeine kleine Arbitrageleistungen, Endenergiepolitik und Raspberry-Pi-Nachweis weiter offen. Details: `docs/SMALL_POWER_PLANNING.md`.
- Einzelne Projektmessstellen offline an ausdrücklich übergebene Rohwerte binden: Messort, Quelle, Rolle und Phase erhalten; Skalierung, W→kW und explizite Vorzeichenausrichtung nachvollziehbar ausführen. Keine Geräteverbindung oder Auswertung als Importnebenwirkung.
- Fehlende Mess-/Empfangszeiten bleiben unbekannt und ungültig. 26 weitere synthetische Tests; Quellenalias-/Abdeckungsprüfung, Adapter-/UI-Anbindung weiterhin offen.
- HA-unabhängige Prüfung von AC-Messwerten und gewichteten Ableitungen: Quellenherkunft, Mess-/Empfangszeit, Datenalter und Gleichzeitigkeit ausdrücklich führen; unbekannte oder ungültige Werte nicht durch null ersetzen.
- Kreisabhängigkeiten, Netzanschlussvermischung und mehrfach verwendete Ursprungsquellen ablehnen. Aus seinen Eingängen berechneter Netzbezug kann nicht als unabhängiger Bilanznachweis derselben Eingänge dienen.
- 23 synthetische Regressionen für Haus-/Nettozweigbilanz, Lade-/Entladevorzeichen, Fehlerfälle und Zeitgrenzen. Noch keine Projekt-/UI-/Polling-Anbindung oder elektrische Abdeckungsprüfung; Details: `docs/RUNTIME_METERING.md`. Keine neue Veröffentlichung.

## 0.4.0 — 2026-11-03

- Eigener HA-Seitenleisteneintrag „Energiemanager“ mit eingebauter Projektoberfläche und HA-Farben, ohne separate Browserinstallation.
- Projekt direkt aus HA laden/speichern, grafisch Netzanschlüsse, Bereiche, Verbindungen und Geräte hinzufügen; Batterien einem WR zuordnen, Import/Export und drei Strukturansichten.
- Adminpflicht für Projektzugriffe und Konfliktprüfung beim Speichern; Entwurf bleibt bei veraltetem Stand erhalten. Keine HA-Zugangsdaten werden an die eingebettete Seite weitergegeben.
- Im Projektmodus nur Statussensor; alte Plansensoren reversibel deaktivieren und bei Simulation wieder aktivieren, Benutzer-/Gerätesperren erhalten.
- HACS-ZIP enthält geprüfte Frontendassets, mobile HA-Navigation und erweiterte HA-/Browserprüfungen.

- HA-unabhängige, ausschließlich lesende Modbus-TCP-Basis mit expliziten Zieladressen für TCP-zu-RTU-Gateways. Gemeinsamer Zugriff pro Client wird serialisiert; Rahmenprüfung, begrenzte Wartezeit und Wiederverbindung nach Fehler/Abbruch.
- Erstes UMG-103-CBM-Leseprofil für Wirk-/Phasenleistungen mit dokumentierter Float-Dekodierung und W→kW-Umrechnung.
- Loopback-Simulatorprüfungen für mehrere Gatewayziele, ungültige Antworten, Gerätefehler, Timeout und Abbruch. Lesender Transport noch nicht an Geräteformulare/automatische Abfrage angeschlossen; keine Live-Geräte getestet.

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
