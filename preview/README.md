# Lokale Oberfläche · v0.2.0

`index.html` direkt in einem aktuellen Browser öffnen. Keine Installation und kein Netzwerkzugang erforderlich.

Die Ansicht ist ein deutscher, responsiver **UI-Prototyp**, keine installierte Home-Assistant-Oberfläche. Sie steuert keine Geräte. Die Startansicht enthält klar gekennzeichnete synthetische Daten; ihre einfache Beispielregel ist kein Optimierer. Der Preisverlauf ist frei erfunden.

## Bedienung

- **Übersicht:** Energieverlauf, Beispielsnapshot beziehungsweise Werte eines importierten Plans, Systemstruktur.
- **Energieplan:** Intervalle und Begründungen; CSV-Export; Plan-JSON importieren.
- **Geräte & Messung:** vorgesehene Anlagenstruktur, ausdrücklich ohne Live-Anbindung.
- **Kostenmodell:** Kaufpreis, Kapazität, SOC-Fenster, Lebensdauer, Nutzung und Wirkungsgrade ändern. Die Rechnung aktualisiert sich sofort. Alle Lebensdauerwerte sind veränderbare Annahmen, keine Herstellerzusagen. Der Batterietyp löst bewusst keine automatische Lebensdauerschätzung aus.
- **Preisquellen:** Bezug und Einspeisung unabhängig auf Prognosedatensatz, HA-Entität, JSON-API-URL, festen Tarif oder SMARD setzen. Quellen-Einheit, Vertragsfaktor und Zuschlag separat konfigurieren. Die Vorschau speichert nur die Konfiguration und ruft keine Preisquellen ab. Exportierte JSON-Werte entsprechen den flachen HA-Optionsschlüsseln und müssen separat in die HA-Einstellungen übernommen werden.
- **Einstellungen:** Kostenannahmen zurücksetzen und Datenverwendung nachlesen.

Kostenannahmen und ausdrücklich gespeicherte Preisquellen werden lokal im Browser gespeichert, sofern dieser lokale Speicherung erlaubt. Importierte Pläne werden nicht gespeichert. Änderungen im Kostenmodell oder an Preisquellen verändern weder einen importierten Plan noch dessen Parameter. Die Überblickskarten zeigen die feste Referenzanlage; das Kostenmodell ist davon getrenntes Szenario.

## Preisquellen-Konfiguration

Bezug (`import`) und Einspeisung (`export`) besitzen jeweils folgende unabhängige Felder:

| Feld | Werte / Bedeutung |
| --- | --- |
| `import_price_mode` | `forecast`, `entity`, `url`, `fixed`, `smard` |
| `import_price_entity` | HA-Entitäts-ID mit passender Preiszeitreihe bei `entity` |
| `import_price_url` | HTTP-/HTTPS-JSON-API bei `url`, keine Webseite und keine eingebetteten Zugangsdaten |
| `import_price_unit` | `eur_kwh`, `ct_kwh`, `eur_mwh` |
| `import_fixed_price` | Fester Quellenwert bei `fixed`, in der Quellen-Einheit |
| `import_price_multiplier` | Nichtnegativer Faktor nach Umrechnung nach EUR/kWh |
| `import_price_adder_eur_kwh` | Positiver Zuschlag oder negativer Abschlag in EUR/kWh |

Alle Schlüssel gibt es entsprechend mit `export_`-Präfix. `forecast` verwendet intern EUR/kWh; SMARD verwendet EUR/MWh. Für diese beiden Quellen setzt die Ansicht die Einheit automatisch und zeigt sie ausdrücklich an.

Vertragspreis = Quellenwert in EUR/kWh × Faktor + Zuschlag in EUR/kWh. Beispiel: 100 EUR/MWh × 0,001 × 1,19 + 0,02 EUR/kWh = 0,139 EUR/kWh.

Ein einzelner aktueller HA-Preiswert ist keine vollständige Tagespreisprognose. Die HA-Integration prüft die unterstützte Zeitreihenstruktur und Intervallabdeckung. Die Browseransicht testet weder Datenformat noch Erreichbarkeit einer URL und führt keinen SMARD-Abruf aus. Ein Webseitenlink kann syntaktisch als URL gültig sein, liefert aber nicht zwingend die benötigte JSON-Zeitreihe.

`pohl-preisquellen-ha-einstellungen.json` ist ein Export der Einstellungswerte, kein vollständiger Home-Assistant-Konfigurationseintrag. Der Export verändert HA nicht automatisch und berechnet keinen neuen Energieplan.

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
