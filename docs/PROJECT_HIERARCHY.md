# Projekt, Standort und elektrische Zuordnung

Einrichtung zuerst nur mit einem frei gewählten Namen des Energiemanagers. Keine vorhandenen HA-Sensoren voraussetzen. Projektverwaltung und später direkte Geräteanbindung müssen unabhängig von der optionalen sensorbasierten Simulation zugänglich sein.

## Empfohlene Bedienhierarchie

```text
Energiemanager / Projekt
└── Standort
    ├── Zugeordneter Netzanschluss
    ├── Elektrische Abgänge / Bereiche
    └── Geräte und optionale Gerätegruppen
        ├── Bestehende PV
        ├── Nachgerüsteter Speicher-WR → Batterien
        └── Verbraucher / Messgeräte
```

„Bestehende PV“ und „neuer Speicher“ sind frei benennbare Gerätegruppen, keine zwingende zusätzliche Ebene „Anlage“. Der Begriff Standort beschreibt räumliche Organisation. Netzanschluss beschreibt die elektrische Bilanz und Tarifgrenze. Ein gemeinsamer Netzanschluss muss trotz mehrerer Gebäude/Bereiche gemeinsam geplant werden; getrennte Anschlüsse nicht miteinander verrechnen. Standortname oder Gerätegruppe dürfen diese Grenze nicht automatisch bestimmen.

Kommunikationswege als separate Beziehungen darstellen: Ein Logger kann mehrere WR anbinden; ein Gateway mehrere Zähler. Das ändert weder deren Messort noch die Batterie-WR-Zuordnung. Datenquelle je Größe unabhängig auswählen: direkte Schnittstelle oder vorhandene HA-Entität; Geräteprofil und tatsächliche Fähigkeiten prüfen.

## Umsetzungsstand 0.3.1

- Ersteinrichtung: nur Name, leeres Projekt wird bei fehlendem Projekt angelegt.
- Bestehende Importe bleiben unverändert; kein Überschreiben bei Reload/weiterem Eintrag.
- Optionale Einzelbatterie-Simulation über Einstellungen getrennt erreichbar, benötigt dort weiterhin die entsprechenden Prognose-/SOC-Sensoren.
- Projektformat 1 besitzt Bereiche, Netzanschlüsse, elektrische Knoten und Geräte. Eine eigene Standort-/Gerätegruppenverwaltung und deren grafischer Assistent sind noch nicht implementiert. Vor Einführung Schema und Migration bestehender Exporte festlegen; keine vorhandene Funktion behaupten.
- Direkte Modbus-/MQTT-/Solarman-Treiber bleiben weiterer Implementierungsschritt. Keine Verbindung oder Registerzuordnung beim Anlegen des Namens erfinden.
