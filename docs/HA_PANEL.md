# Eingebaute HA-Oberfläche ab 0.4.0

Nach Installation/Update über HACS Home Assistant neu starten. Eine vorhandene Integration muss nicht gelöscht werden. Anschließend als Administrator links „Energiemanager“ öffnen; Browser gegebenenfalls neu laden. URL innerhalb HA: `/pohl-energiemanager`.

## Benutzbar

- Tatsächlich in HA gespeichertes Projekt mit dessen Namen laden; keine automatische Demoanlage.
- Netzanschluss anlegen, weitere Bereiche demselben oder anderen Netzanschlüssen zuordnen.
- Verbindungen (Modbus TCP, TCP-RTU-Gateway, RS485/USB, RTU-over-TCP, Solarman, MQTT, HA) konfigurativ anlegen.
- Geräte zu Bereich und elektrischem Anschluss hinzufügen; Batterien einem geeigneten WR zuordnen.
- Elektrischen Aufbau, Kommunikationswege und Messquellen getrennt ansehen, Namen bearbeiten.
- Projekt als JSON exportieren/importieren, Vorschau ausdrücklich übernehmen und zentral „In Home Assistant speichern“.
- Änderungen bleiben bis zum Speichern im Entwurf. „Aus Home Assistant laden“ zeigt zunächst eine Vorschau; Verwerfen verändert nicht die Basisversion des eigenen Entwurfs. Bei zwischenzeitlicher Änderung durch eine andere Ansicht verhindert die Revisionsprüfung versehentliches Überschreiben.

Beim ersten Netzanschluss wird eine ausdrücklich unkonfigurierte Netzmessung angelegt, damit die Zuordnung nicht vergessen wird. Ein Geräteformular bestätigt weder Modellkompatibilität noch reale Verdrahtung. Erweitertes Kanal-/Registermapping und elektrische Unterzweige können derzeit im validierten JSON-Editor bearbeitet bzw. importiert werden; die Formulare ersetzen noch keinen vollständigen Inbetriebnahmeassistenten.

## Was noch fehlt

Die Formulare stellen noch keine Geräteverbindung her. Es gibt keine automatische Suche, Messwertabfrage oder Gerätesteuerung aus dieser Ansicht. Die neue lesende Modbusbibliothek ist erst simuliert geprüft und noch nicht an die Oberfläche angeschlossen. Mehrspeicheroptimierung, Prognoseanbindung und detaillierte Tarif-/Regelseiten bleiben weitere Schritte. Eine getrennte Standort-/Gerätegruppenverwaltung ist noch nicht Teil des Projektformats.

## Einbettung und Zugriff

Das HACS-Paket enthält die Oberfläche. Native `panel_custom`-Registrierung erzeugt den Seitenleisteneintrag. Statische Dateien enthalten ausschließlich Programmcode und anonymisierte Vorlagen. Die Seite bekommt Projektdaten über zwei serverseitig auf Administratoren beschränkte WebSocket-Kommandos. Authentifizierung bleibt bei HA; keine Tokens im iframe und keine separate Anmeldung.

- `pohl_energy/project/get`: Projekt, Zusammenfassung und Inhaltsrevision.
- `pohl_energy/project/set`: JSON plus Revision des ausdrücklich übernommenen Ausgangsstands. Validierung und Revisionsvergleich vor Speicherung unter gemeinsamem Lock.

Unbekannte/ungültige Projekte, alte Revisionen und Speicherfehler verändern den aktiven Projektstand nicht. Projektservices prüfen ebenfalls Administratorrechte für angemeldete Aufrufer. Vertrauenswürdige HA-Systemaufrufe bleiben möglich. Beim Entladen verschwinden Panel und Services; verbleibende Handler geben keine Daten aus einer entladenen Integration zurück.

Im Projektmodus werden die reinen Plansensoren nicht angelegt. Bereits vorhandene Plansensoren werden durch die Integration deaktiviert; benutzerdefinierte Namen und vom Benutzer/Gerät gesetzte Sperren bleiben erhalten. Die optionale Simulation kann sie später wieder aktivieren.

## Entwicklung und Prüfung

Gemeinsame UI-Quellen liegen in `preview/`. Nach Änderungen `python tools/sync_frontend.py` ausführen. Ein Pakettest vergleicht installierte Frontenddateien byteweise mit den geprüften Quellen. HA-Wrapper: `custom_components/pohl_solutions_energiemanager/frontend/pohl-panel.js`.

Automatische Prüfungen umfassen Ursprungs-/Fensterzuordnung, begrenzte Operationen, Revisionskonflikt mit Reload/Verwerfen, unveränderten Entwurf bei Fehlern, Nutzeraktionen im Projektmodell, native HA-Panelregistrierung, Berechtigungen und Setup-/Unload-/Reload-Aufräumen. Browserprüfung erfolgt mit simulierter HA-Anbindung; echte HA-Serverkomponenten werden zusätzlich in GitHub Actions getestet. Keine Prüfung in der laufenden Nutzeranlage behauptet.
