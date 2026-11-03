# Preisquellen

Bezug und Einspeisung werden unabhängig konfiguriert. Derselbe Börsenpreis kann bei zwei unterschiedlichen Verträgen zu verschiedenen tatsächlichen Preisen führen.

## Quellen

| Quelle | Eingabe | Bedeutung |
|---|---|---|
| Prognose enthält Preise | vorhandener Prognosesensor | Bereits fertige `import_price_eur_kwh` / `export_price_eur_kwh` aus dem ursprünglichen Datenvertrag |
| Home-Assistant-Sensor | Entity-ID | Preisreihe im Attribut `prices` |
| JSON-URL | vollständige HTTP-/HTTPS-Datenadresse | API liefert Preisreihe als JSON, kein Link auf eine Diagramm-Webseite |
| Festpreis | Zahl und Einheit | Konstanter Preis für den Planungshorizont |
| SMARD Deutschland/Luxemburg | Auswahl im HA-Eintrag | Experimenteller Adapter für Viertelstunden-Großhandelspreise, keine Aussage über den eigenen Vertragsendpreis |

Ein Link zur SMARD-Diagrammseite ist keine JSON-API-Adresse. Der native SMARD-Adapter verwendet eigene Datenendpunkte. Externe Datenquellen benötigen Netzverfügbarkeit und vollständige Abdeckung des gewünschten Prognosehorizonts. Fehlende Preise werden nicht fortgeschrieben oder durch null ersetzt.

## Einheit und Tarifberechnung

- `eur_kwh`: EUR/kWh, Faktor 1.
- `ct_kwh`: ct/kWh, Faktor 0,01.
- `eur_mwh`: EUR/MWh, Faktor 0,001.

Für externe Quellen und Festpreise: `Vertragspreis = normalisierter Quellenpreis × Multiplikator + Aufschlag in EUR/kWh`.

Beispiel, keine Tarifempfehlung: 100 EUR/MWh entsprechen 0,10 EUR/kWh. Bei Multiplikator 1 und Aufschlag 0,12 ergibt sich 0,22 EUR/kWh. Ein Einspeisevertrag kann auf derselben Quelle einen anderen Aufschlag verwenden. Negative Aufschläge und negative Preise sind erlaubt; Multiplikatoren dürfen nicht negativ sein.

Der Modus „Prognose enthält Preise“ übernimmt die bereits fertigen EUR/kWh-Werte unverändert. Dort werden keine zusätzlichen Umrechnungen oder Aufschläge angewandt. So werden Tarifbestandteile nicht doppelt gezählt.

## JSON-Format für Sensor und URL

```json
{
  "prices": [
    {
      "start": "2026-11-04T12:00:00+01:00",
      "duration_hours": 0.25,
      "value": 100.0
    },
    {
      "start": "2026-11-04T12:15:00+01:00",
      "duration_hours": 0.25,
      "value": 95.0
    }
  ]
}
```

Die Zahlen sind synthetische Formatbeispiele. Alternativ ist die Liste direkt erlaubt. Statt `duration_hours` kann ein expliziter, zeitzonenbehafteter `end`-Zeitstempel stehen. Die Planung arbeitet mit Viertelstunden; eine eigene JSON-Quelle darf auch ausdrücklich längere Preisperioden liefern, etwa einen konstanten Stundenpreis. Überlappen mehrere Preisperioden einen Planungsschritt, wird zeitanteilig gewichtet. Es werden keine fehlenden Preiswerte erfunden. Alle Intervalle werden nach UTC validiert, auch an Zeitumstellungstagen. Alle für den Plan benötigten Zeitbereiche müssen abgedeckt sein.

## SMARD: technischer und quellenbezogener Status

Der Adapter nutzt die beobachteten JSON-Endpunkte auf `www.smard.de/app/chart_data/4169/DE/`. Indexdateien enthalten Wochenanfänge, Zeitreihen Paare aus Unix-Millisekunden und EUR/MWh. Nicht veröffentlichte Werte können `null` sein und werden nicht als Preis behandelt. Diese Endpunkte sind beobachtete Web-Datenendpunkte, kein hier zugesichertes stabiles API-Angebot.

Quellenangabe: **Bundesnetzagentur | SMARD.de**, Preisregion Deutschland/Luxemburg, Ursprung laut SMARD ENTSO-E.

Stand 2026-11-03 weist die [SMARD-Seite zur Datennutzung](https://www.smard.de/home/datennutzung) darauf hin, dass die Lizenzierung der Großhandelspreise überprüft wird und diese bis auf Weiteres nicht weiterverwendet werden sollten. Der technische Adapter ist deshalb keine Zusicherung einer geeigneten Nutzungsberechtigung für ein gewerbliches Produkt. Er wird nicht automatisch aktiviert; echte SMARD-Preisreihen werden nicht mit diesem Repository verteilt. Für einen produktiven Einsatz muss eine geeignete Datenquelle beziehungsweise deren Nutzungsstatus feststehen. HA-Sensor, eigene JSON-Daten und Festpreise bleiben unabhängige Alternativen.

## Lokale Vorschau

Die Vorschau kann Preisquellen als Konfiguration bearbeiten, lokal speichern und exportieren. Das ist keine Verbindung zu einer HA-Instanz. Ein bereits importierter Fahrplan wird dadurch nicht rückwirkend neu berechnet; er benötigt einen neuen Planungslauf mit den geänderten Quellen.
