# Pohl Solutions Energiemanager

Lokale, nachvollziehbare Energieplanung für Home Assistant und Node-RED.

**Version 0.1.0 ist eine Entwicklungsversion für Planung und Simulation. Sie schreibt keine Befehle an Wechselrichter, Speicher oder andere Geräte.** Der Browserprototyp ist eine getrennte Vorschau, noch kein eingebautes Home-Assistant-Dashboard.

## Was bereits funktioniert

- Viertelstundenplanung aus expliziten PV-/Lastprognosen und getrennten Bezugs-/Einspeisepreisen.
- Batteriemodell mit Kapazität, SOC-Grenzen, AC-Lade-/Entladeleistung und Wirkungsgraden.
- Optionale Netzladung und Batterieeinspeisung, beide standardmäßig aus.
- Wirtschaftliche Planung mit separat angesetztem marginalem Verschleiß; keine doppelte Investitionsverrechnung.
- Lebenszyklusrechnung: Kaufpreis, nutzbarer SOC-Bereich, Zyklen-, Alters- und Nutzungsannahmen, durchschnittliche Kapazität, Restwert und Betriebskosten.
- Historische Lastprofilprognosen mit zeitlicher Gewichtung, Werktags-/Wochenendmustern, Streuungsbändern und Fehlerauswertung als getestete Hilfsfunktionen. Noch keine automatische HA-Historienanbindung.
- Home-Assistant-Einrichtung, Eingabevalidierung und lesbare Plan-/Diagnosesensoren.
- Lokaler Oberflächenprototyp mit Kostenrechner, Planimport, Diagrammen und Geräteübersicht.
- Automatische Prüfungen über GitHub Actions.

## Schnell ansehen

`preview/index.html` im Browser öffnen. Die Vorschau benötigt keine Installation und keine Verbindung ins Internet. Sichtbare Demo-Zeitreihen sind synthetisch und keine echten SMARD-/Anlagendaten. Der Beispielrechner speichert keine Gerätebefehle.

Einen tatsächlichen Szenarioplan erzeugen und anschließend in der Vorschau importieren:

```powershell
python tools/plan.py examples/demo-forecast.json --output outputs/demo-plan.json
```

Auch diese Beispieldatei enthält ausschließlich synthetische Daten. Das Programm ist ein lokaler Rechner und verbindet sich mit keinem Gerät.

## Projektstruktur

```text
custom_components/pohl_solutions_energiemanager/
  core/                 Reiner Planungs- und Kostenkern ohne HA-Abhängigkeit
  forecasting.py        Historische Lastprognose und Fehlerauswertung
  config_flow.py        Einrichtung und Einstellungen in Home Assistant
  coordinator.py        Validierte Prognosedaten → Plan
  sensor.py             Lesbare Planwerte und Diagnose
preview/                Lokaler Oberflächenprototyp
examples/               Synthetische Beispiele
tools/                  Lokaler Planungsaufruf
tests/                  Automatische Prüfungen
docs/                   Architektur, Datenvertrag, Annahmen und nächste Schritte
```

## Home Assistant

Der Integrationseintrag benötigt einen SOC-Sensor sowie einen Sensor mit einer vollständigen Prognosereihe im Attribut `slots`. Die Daten können zunächst von Node-RED bereitgestellt werden. Siehe [Datenvertrag](docs/DATA_CONTRACT.md).

Zur Entwicklung den Ordner `custom_components/pohl_solutions_energiemanager` in das entsprechende `custom_components`-Verzeichnis einer **Testinstanz** kopieren, HA neu starten und unter Geräte & Dienste hinzufügen. Alternativ das private GitHub-Repository in HACS als benutzerdefiniertes Integrationsrepository hinzufügen, wenn der eigene HACS-Zugriff private Repositories unterstützt. Keine Aufnahme in einen öffentlichen Katalog behauptet.

Zielbasis: Home Assistant 2026.1 oder neuer. Der reine Rechenkern läuft mit Python 3.12+. Home Assistant selbst hat eigene Python-/Betriebssystemanforderungen.

**Noch nicht im Umfang:** automatischer SMARD-Abruf, Tarifanbieter, automatische Wetter-/PV-Prognose, automatische Historienabfrage, vollständiges HA-Dashboard, direktes Lesen/Schreiben von Solis/Sungrow/Janitza und produktiver Regelbetrieb. Ein vorhandener Sensor-/Treibername ist kein Nachweis einer Schreibfreigabe.

## Annahmen und Grenzen

Der Planer sucht ein Optimum auf einem diskreten Energieraster. Das ist eine deterministische Näherung, kein garantiertes kontinuierliches Optimum und keine belastbare Aussage über zukünftige Einsparungen. Die Auflösung ist konfigurierbar. Kleine Energiemengen unterhalb des Rasters können entfallen.

Standardmäßig endet der Horizont mit mindestens dem Anfangsladezustand. Dadurch wird der Vergleich nicht durch kostenloses Leeren des Speichers geschönt. Im Plan werden Annahmen und der Vergleich mit einer ungenutzten Batterie ausgewiesen. Bei abweichendem Endziel ist der Vergleich nicht energiegleich.

Alle Prognosen bleiben Szenarien. Historische Quantilbänder sind noch keine kalibrierten Wahrscheinlichkeitsintervalle. Der Nutzer muss Kosten- und Lebensdauerannahmen prüfen; LiFePO4 ist keine pauschale Garantie für eine bestimmte Zyklenzahl.

## Entwicklung und Versionsverwaltung

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install pytest ruff tzdata
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe -m ruff check .
node --test preview/test-preview.cjs
```

Auf Linux/macOS `.venv/bin/python` verwenden. Änderungen in kleinen Commits halten, Verhalten in `CHANGELOG.md` dokumentieren. `main` enthält den geprüften Entwicklungsstand; es gibt noch keine als produktionsreif bezeichnete Veröffentlichung.

Originale Standortunterlagen, Verträge, Seriennummern und HA-Zugangsdaten gehören in `private/` oder außerhalb dieses Repositories. Sie werden nicht mit versioniert.

Copyright © 2026 Pohl Solutions. Eine Freigabe als Open Source ist mit diesem privaten Repository nicht verbunden; eine Lizenzentscheidung ist offen.
