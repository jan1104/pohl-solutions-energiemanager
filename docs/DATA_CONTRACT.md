# Datenvertrag Version 0.1

## Lokaler Rechner

`tools/plan.py` liest ein JSON-Objekt mit `battery` und `slots`. `examples/demo-forecast.json` zeigt einen vollständigen synthetischen Zweitagesfall. Der Rechner kennt keinen Live-Modus und speichert nur auf ausdrückliche Ausgabeangabe.

## Home-Assistant-Eingang

Der ausgewählte Prognosesensor besitzt im Attribut `slots` eine Liste:

```json
{
  "slots": [
    {
      "start": "2026-11-04T12:00:00+01:00",
      "duration_hours": 0.25,
      "pv_kw": 80.0,
      "load_kw": 25.0,
      "import_price_eur_kwh": 0.29,
      "export_price_eur_kwh": 0.07
    }
  ]
}
```

Diese Werte sind nur eine Schemaillustration. Für einen gültigen aktuellen HA-Plan muss die Reihe die **laufende** Viertelstunde enthalten und danach lückenlos fortgesetzt werden. Alle ursprünglichen Intervalle sind 15 Minuten lang. Der laufende Schritt wird auf seine Restdauer gekürzt; dafür wird die mittlere PV-/Lastprognose dieses Intervalls auch für die verbleibende Zeit angenommen. Der aktuelle SOC wird als Anfangszustand verwendet.

Der Prognosesensor muss erreichbar und innerhalb von 24 Stunden berichtet worden sein; der SOC innerhalb von 30 Minuten. Identisch wiederholte Zustände werden über `last_reported` berücksichtigt. Diese Fristen sind lediglich Eingabegrenzen des Planungsprototyps, keine zulässigen Reaktionszeiten für eine spätere Live-Regelung.

Fehlende, nichtendliche, überlappende, lückenhafte, zeitlich unpassende oder veraltete Daten ergeben einen Diagnosezustand statt eines erfundenen Plans. Der Pure-Python-Kern akzeptiert andere positive Schrittweiten; der HA-Eingang ist absichtlich auf Viertelstunden festgelegt.

SOC-Grenzen und aktuelle Kapazität müssen konsistent sein. Statische Leistungsgrenzen sind keine aktuelle BMS-Ladefreigabe. Optional zugeordnete Netz-/PV-/Lastsensoren werden in 0.1 als Quellen dokumentiert; sie schließen noch keinen aktiven Regelkreis.

## Ausgabe

Planobjekt mit `planning_only: true`, `slots`, `total_cost_eur`, `baseline_cost_eur`, `savings_eur` und `assumptions`. Jeder Schritt enthält zusätzlich:

- `battery_power_kw`: AC-Leistung, positiv Laden.
- `grid_power_kw`: Netzleistung, positiv Bezug.
- `soc_pct`: Zustand **am Ende** des Intervalls.
- `cost_eur`: Bezug minus Einspeiseerlös plus angesetzter Verschleiß.
- `reason`: nachvollziehbare Beschreibung.

Die Vorschau kann das vom CLI gespeicherte Planobjekt importieren. Ein solcher Import ist keine Verbindung zur Anlage.

In Home Assistant entstehen Status-, Fahrplan-, aktuelle/nächste Planleistungs- und Szenariovorteil-Sensoren. Der Fahrplan liegt im Attribut `slots` des Fahrplansensors. Bei häufigen Neuberechnungen sollte dessen vollständige Historisierung im Recorder bewusst geplant werden.

Service `pohl_solutions_energiemanager.replan` mit `entry_id` berechnet genau diesen Eintrag neu. Event `pohl_solutions_energiemanager_plan_updated` signalisiert einen neuen Plan mit `entry_id`, `generated_at` und `planning_only: true`. Es ist kein Ausführungsauftrag. Node-RED soll in dieser Version daraus ausschließlich Anzeigen und Prüfungen erstellen.
