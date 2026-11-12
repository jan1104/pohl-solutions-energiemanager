# Änderungen

## 0.6.0 — vorbereitet, 2026-11-13

- Transparentes RTU über TCP als lesenden FC03/04-Transport ergänzt: ausdrücklicher Port, serielle Geräteadresse und CRC-Prüfung. Geteilte Verbindung pro Endpunkt; widersprüchliche MBAP-/RTU-Einträge werden vor dem Senden abgewiesen. Synthetisch getestet, noch kein automatischer HA-Geräteabruf.

- Grundmodul 0.1.1: Statusabrufe führen keine zusätzlich registrierten Fachmodulhandler mehr aus und quittieren deren Fehler nicht. Die drei eingebauten Diagnoseprüfungen und die Anzeige aller Modulzustände bleiben erhalten.

- Gemeinsame SQLite-Datenbank ausdrücklich als konsistente, geprüfte Kopie sichern. Bestehende Ziele werden nie überschrieben; alle Projekt-/Modulbereiche und Revisionen bleiben erhalten. Noch keine automatische Sicherung, HA-Bedienung oder Wiederherstellung.

- Fachmodule erhalten ausdrücklich einen asynchronen, fest an Projekt und Modul gebundenen Zugang zur gemeinsamen SQLite-Konfigurationsdatenbank. Schreibdaten werden vor Worker-Übergabe kopiert, Revisionen geprüft und laufende Arbeit bei Abbruch abgewartet. Noch keine automatische Modulaktivierung oder Messhistorie.

- Beim Hinzufügen eines Modbus-Geräts die eigene Unit-ID (1–247) direkt eingeben. Das optionale Feld erscheint nur für Modbus-Verbindungen; keine Adresse wird angenommen oder vom vorherigen Gerät übernommen.
- Neue HA-Projekte beginnen direkt mit der ersten Anlage. Projekt und Speicherformat werden atomar angelegt.
- Speichern und Wechseln der Ansicht schützen offene Formulare und ungeprüfte JSON-Änderungen vor versehentlichem Verwerfen.
- Überlaufende Modbus-Registerbereiche bereits beim Import und Bearbeiten der Quelle ablehnen. 32-Bit-Werte dürfen höchstens an Adresse 65534 beginnen.
- Modbus-Messkanäle über einen eingesetzten Reader dekodieren und in kW umrechnen. Synthetische Tests prüfen Gateway-Route, Skalierung und Messzeit.
- Gespeicherte Messkanäle im HA-Panel mit einem Testwert prüfen. Das simulierte Ergebnis zeigt die Umrechnung in kW und die gewählte Ausrichtung.
- Messquellen in Format-2-Projekten direkt bearbeiten. Das Formular unterstützt Modbus mit FC03/FC04, MQTT, Home Assistant und offene Quellen. Ein Wechsel ersetzt nur die Quellenfelder.
- Netzmessung am Format-2-Anschluss zuordnen. Die Auswahl zeigt freie Gesamtwirkleistungskanäle desselben Anschlusses. Neue Kanäle benötigen Name und Einheit. Offene Datenquellen bleiben sichtbar.
- Home-Assistant-Projekte können im Projektmenü die Anlagenstruktur prüfen und ausdrücklich übernehmen. Die Umstellung prüft beide Quellrevisionen und sichert das Original in SQLite.
- Format-2-Projekte führen zuerst durch die Anlage und danach zum Netzanschluss. Optionale Anschlussdaten lassen sich aufklappen. Offene Netzmessungen sind im Aufbau erkennbar. Die lokale Vorschau startet mit diesem Ablauf.
- Home Assistant öffnet vorhandene Projekte in Format 1 oder 2 und prüft Speicherimporte gegen das vorhandene Format. Format-2-Exporte bleiben im Importlimit. Veraltete Schreibzugriffe nach einem Schemawechsel melden einen Konflikt und laden den aktuellen Stand.
- Explizite atomare Schema-Migration im Grundspeicher und vorbereiteter Projekt-Formatwechsel: Vorschau mit SHA/Revision, geschützter Originalstand, vollständiger Rollback und Erhalt der Herkunftsmetadaten. Die Migration erfolgt über eine separate Entwicklungs-API.
- Gemeinsames JSON-Budget für Entwicklungsformat 2: Zahlenbereich und Unicode prüfen, gleiche Größenentscheidung in Python/JavaScript; keine stille Rundung oder verlorenen JS-Felder. Grenztests und unveränderte Originale bei abgelehnter Migration. Aktives Format 1 unverändert.
- Format-2-Entwicklungsmodell auch in JavaScript validierbar: explizite Vorschau-Migration und strukturierte Konfigurationshinweise mit Python-Vertragstests. Aktive Oberfläche, Import/Export und gespeicherte Projekte bleiben Format 1; JSON-Grenzvertrag im Folgeschritt vereinheitlicht.
- Entwicklungsmodell für Projekt → Anlage → Anschluss/Messgerät ergänzt: leere Anlagen, ungemessene Anschlussentwürfe und optionale Anschlussmetadaten. Organisatorische Zuordnung und elektrische Grenzen bleiben getrennt.
- Explizite Vorschau-Migration erhält vorhandene IDs/Verbindungen und markiert Anlagenzuordnung als unbestätigt. 23 neue synthetische Tests. Noch keine Aktivierung in HA/Oberfläche, keine Umschreibung gespeicherter Projekte und kein Release; siehe `docs/PROJECT_SCHEMA_V2_DRAFT.md`.

## 0.5.1 — 2026-11-04

- Projektoberfläche vereinfacht: fokussierter Einstieg für leere Projekte, kompakte Hauptaktionen und schrittweises Öffnen von Hinzufügen, Projektoptionen und Expertenfunktionen.
- Import-/Export-/Vorlagenaktionen, Umbenennung und JSON-Editor bleiben erreichbar, überlagern aber nicht mehr die normale Projektübersicht. Speicherung und Revisionsschutz unverändert.

## 0.5.0 — 2026-11-04

- Testbares Grundmodul im HA-Panel: Projekt-/Grundmodulnavigation, echte Produkt-/Modulversionen, Speicherstatus und gezielter Statusabruf ohne Veränderung des Projektentwurfs.
- Zentraler SQLite-Projektstand mit einmaliger, atomarer Übernahme der bestehenden HA-Projektdatei. Original bleibt bytegleich als Sicherung erhalten; danach keine parallelen Schreibquellen. Inhaltliche SHA-Revisionsprüfung bleibt erhalten.
- Tatsächliche Basisfunktionen Grundmodul, Konfigurationsspeicher und Projektverwaltung über Modulregistry verfügbar. Eigene Modulversionen unabhängig vom Produktpaket. Umfang und Testschritte: `docs/TESTING_0_5.md`.

- Erste zentrale SQLite-Konfigurationsablage für das Grundmodul: getrennte Projekt-/Modulbereiche, eigene Schemaversionen, Schutz vor veralteten Schreibständen und atomare Mehrdokumentänderungen. 21 neue Datenbanktests.
- Bestehender HA-Projektspeicher bleibt unverändert maßgeblich. Automatische Modulkontextanbindung, Migration, Historien und Sicherung folgen; siehe `docs/CENTRAL_STORAGE.md`. Keine Datenbankdateien in Git.
- Erste versionierte Modulgrundlage: getrennte Modul-/API-Versionen, explizite Abhängigkeiten, begrenzte Async-Aufrufe, gezielte Fehlerfortpflanzung und Schutz gegen überholte Ergebnisse/Fehler. 18 neue synthetische Tests.
- Prognose als eigener Fachbaustein vorgesehen. Kernel noch nicht in HA verdrahtet; konkrete Datenverträge, Provider, Migrationen und Moduloberfläche folgen. Getrennte Versionen bedeuten kein unterbrechungsfreies Update oder Prozessisolation; siehe `docs/MODULE_KERNEL.md`.
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
