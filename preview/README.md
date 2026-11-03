# Lokale Oberfläche

`index.html` direkt in einem aktuellen Browser öffnen. Keine Installation und kein Netzwerkzugang erforderlich.

Die Ansicht ist ein deutscher, responsiver **UI-Prototyp**, keine installierte Home-Assistant-Oberfläche. Sie steuert keine Geräte. Die Startansicht enthält klar gekennzeichnete synthetische Daten; ihre einfache Beispielregel ist kein Optimierer. Der Preisverlauf ist frei erfunden.

## Bedienung

- **Übersicht:** Energieverlauf, Beispielsnapshot beziehungsweise Werte eines importierten Plans, Systemstruktur.
- **Energieplan:** Intervalle und Begründungen; CSV-Export; Plan-JSON importieren.
- **Geräte & Messung:** vorgesehene Anlagenstruktur, ausdrücklich ohne Live-Anbindung.
- **Kostenmodell:** Kaufpreis, Kapazität, SOC-Fenster, Lebensdauer, Nutzung und Wirkungsgrade ändern. Die Rechnung aktualisiert sich sofort. Alle Lebensdauerwerte sind veränderbare Annahmen, keine Herstellerzusagen. Der Batterietyp löst bewusst keine automatische Lebensdauerschätzung aus.
- **Einstellungen:** Kostenannahmen zurücksetzen und Datenverwendung nachlesen.

Kostenannahmen werden lokal im Browser gespeichert, sofern dieser lokale Speicherung erlaubt. Importierte Pläne werden nicht gespeichert. Änderungen im Kostenmodell verändern weder einen importierten Plan noch dessen Parameter. Die Überblickskarten zeigen die feste Referenzanlage; das Kostenmodell ist davon getrenntes Szenario.

## Planformat

Ein JSON-Plan benötigt `slots`, `total_cost_eur`, `baseline_cost_eur`, `savings_eur` und optional `assumptions` (Liste von Texten). Ein Intervall benötigt:

```json
{
  "start": "2026-11-03T12:00:00+01:00",
  "duration_hours": 0.25,
  "pv_kw": 60,
  "load_kw": 20,
  "battery_power_kw": 30,
  "soc_pct": 55,
  "grid_power_kw": -10,
  "import_price_eur_kwh": 0.25,
  "export_price_eur_kwh": 0.08,
  "cost_eur": -0.20,
  "reason": "PV-Überschuss speichern; verbleibende Energie einspeisen"
}
```

Das Beispiel beschreibt ein einzelnes Intervall, keinen vollständigen Plan. `battery_power_kw` ist AC-seitig positiv beim Laden, negativ beim Entladen. `grid_power_kw` ist positiv bei Bezug und negativ bei Einspeisung. `soc_pct` ist der Zustand am Ende des Intervalls. Preise sind EUR/kWh. Zeitintervalle müssen zusammenhängend und mit Zeitzone versehen sein. Die Anzeige verwendet Europe/Berlin.

Der Import prüft Struktur, endliche Zahlen, chronologische Kontinuität, AC-Leistungsbilanz und aggregierte Kosten. Er kann die physikalische Zulässigkeit des importierten SOC-Verlaufs ohne die ursprüngliche Batteriekonfiguration nicht vollständig beweisen. Für diese Prüfung ist der Planer verantwortlich.

## Rechnung

Nutzbare DC-Energie = Nennkapazität × SOC-Fenster.

Erwartete Durchläufe = Minimum aus Zyklenannahme und Kalenderjahren × Durchläufen/Jahr. Hier bezeichnet ein Durchlauf das **gewählte SOC-Fenster**, nicht zwingend einen äquivalenten Vollzyklus bezogen auf die komplette Nennkapazität. Die Zyklenannahme muss dazu passen.

Lebenszeit-AC-Ausgabe = nutzbare DC-Energie × Durchläufe × mittlerer Kapazitätsfaktor × Entladewirkungsgrad.

Umgelegte Investition = (Kaufpreis − Restwert) / Lebenszeit-AC-Ausgabe.

Der Ladewirkungsgrad wird in der separat angezeigten AC-Gesamteffizienz berücksichtigt; er verringert nicht erneut die aus einer vollständigen nutzbaren DC-Füllung abgegebene Energie. Zusätzlicher marginaler Verschleiß bleibt ein getrennter Ansatz, um CAPEX nicht doppelt zu verrechnen. Wartung, Finanzierung, Abzinsung und Tarifkosten sind in diesem einfachen Rechner noch nicht enthalten.

## Prüfung

```text
node --check preview/app.js
node preview/test-preview.cjs
```
