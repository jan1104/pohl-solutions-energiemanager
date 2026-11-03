# Elektrische Bilanz und organisatorische Bereiche

Stand: 03.11.2026. Allgemeiner Modellierungsentwurf; tatsächliche Standortzuordnungen bleiben lokal unter private/. Keine implementierte Messgeräteanbindung.

## Begriffe

- Projekt: übergeordnete Konfiguration, enthält alle Anlagen/Bereiche und Netzanschlüsse.
- Netzanschluss: elektrische Bilanz-/Tarifgrenze und gemeinsame Optimierungsgruppe.
- Anlage/Bereich: vom Nutzer benannte organisatorische Gruppe, kein Beweis eines eigenen Netzanschlusses.
- Elektrischer Zweig: tatsächlicher Abgang, kann Erzeuger, Speicher und Verbraucher zugleich enthalten.
- Kommunikationsweg: wie ein Gerät erreichbar ist; unabhängig von dessen Messort.

Mehrere Bereiche hinter demselben Anschluss werden gemeinsam geplant. Getrennte Anschlüsse erhalten getrennte Bilanzen; eine gemeinsame Übersicht verrechnet deren Energie nicht physikalisch.

## Allgemeiner Testfall mit gemeinsamem Anschluss

```text
Netzanschluss → Hauptmessung G
├── Verbrauchszweig → Messung H
│   ├── Allgemeinverbrauch
│   └── Flexible Verbraucher mit eigenen Unterzählern
└── Gemischter PV-/Speicherzweig → Messung B
    ├── PV-Wechselrichter
    ├── Speicher-Wechselrichter
    └── Wärmebereich → gemeinsame Dreiphasenmessung T
        └── Mehrere dreiphasige Heizverbraucher
```

Alle Zweigleistungen hier positiv bei Leistungsaufnahme aus dem übergeordneten Knoten, negativ bei Rücklieferung; G positiv bei Netzbezug. Bezeichnungen und genaue Gerätewerte sind ein abstraktes Modell, keine Live-Daten.

### Unabhängige Prüfgleichungen

Bei vollständiger Erfassung und zeitlich passenden AC-Messungen gilt näherungsweise `G = H + B`. Differenz `G - H - B` als Bilanzrest ausweisen; Messungenauigkeit, Verluste, nicht zeitgleiche Erfassung und ungemessene Abgänge berücksichtigen.

Für den gemischten Zweig gilt `B = T + L_sonstige - PV + Batterie_AC`, Batterie_AC positiv beim Laden. B ist deshalb keine reine PV-Erzeugung. Falls B und H gemessen werden, kann G damit geprüft werden, aber nicht eine aus H/B berechnete Größe zugleich als unabhängiger Kontrollbeweis dienen.

Gesamter Endverbrauch ist in diesem Beispiel `H + T + L_sonstige`; eigene Unterzähler im Verbrauchszweig werden nicht nochmals dazu addiert. Wenn H bereits Ladestationen umfasst, ist Allgemeinverbrauch optional `H - Summe_Ladestationen`, mit passender Datenabdeckung und Plausibilitätsprüfung. Negative/unsichere Differenz nicht heimlich auf null begrenzen.

### Aggregierte und einzelne Messungen

Eine gemeinsame Dreiphasenmessung mehrerer dreiphasiger Geräte liefert Gesamt- und Phasenlast, keine unabhängige Istleistung jedes Geräts. Drei Phasenkanäle nicht als drei verschiedene Heizstäbe darstellen. Mehrere Geräte können trotzdem einzeln schaltbar sein. Einzelverbrauch nur mit eigenem Messwert als gemessen ausweisen; modellierte Aufteilungen klar als Schätzung kennzeichnen.

Die Regeln müssen Messgruppe und einzelne Aktoren gemeinsam modellieren. Den gemeinsamen Istverbrauch nicht jedem Aktor vollständig zuweisen. Identifizierte Reaktion auf einzelne Schaltvorgänge kann später ein Schätzmodell liefern, ersetzt aber keine direkte Messung.

## Import-/Validierungsregeln

- Bereich und Netzanschluss explizit referenzieren; räumlicher Name darf die Optimierungsgrenze nicht implizieren.
- Zweige müssen einen eindeutigen elektrischen Elternknoten besitzen; keine Kreise.
- Messrolle, Vorzeichen und enthaltene Unterzweige führen. Derselbe Wert kann Referenz in mehreren Ansichten sein, bleibt aber eine Quelle.
- Hauptnetzbilanz nicht mit einem Haus-Unterzähler verwechseln.
- Nur vollständige zeitlich gültige Quellen vergleichen. Abgeleitete Werte einschließlich Formel und Abhängigkeiten anzeigen, Zirkelschlüsse ablehnen.
- Gateway-Untergeräte über eigene Adressen identifizieren, auch wenn Messorte an verschiedenen Zweigen liegen. Kommunikationsbaum ersetzt keinen elektrischen Zweigbaum.

## Abnahmefälle

Netzbezug, Rückspeisung, Speicherladen/-entladen, Lastsprung im Wärmebereich, einzelne untergemessene Ladestation und Teil-Ausfall simulieren. Besonders prüfen: Wärme erhöht B und G entsprechend, ohne als negative PV-Prognose missverstanden zu werden; Unterverbrauch wird nicht doppelt gezählt; Änderungen eines Bereichs planen den ganzen gemeinsamen Anschluss neu.
