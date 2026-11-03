# Architektur und Produktentscheidungen

## Ziel

Ein Bedienort für Energiekosten, Gerätezuordnung und wirtschaftliche Viertelstundenplanung. Die vorhandenen Sungrow-PV-Geräte erzeugen weiter. Ein Solis/BSE-Speicher kann Überschuss AC-seitig aufnehmen und später Hausverbrauch decken, ohne absichtliche Batterieeinspeisung. Das Produkt bleibt anlagenunabhängig konfigurierbar.

## Vier getrennte Verantwortlichkeiten

1. Datenadapter liefern zeitgestempelte Messwerte, Preise und Prognosen mit eindeutigen Einheiten und Qualitätsangaben.
2. Der Planer berechnet einen nachvollziehbaren Fahrplan über beispielsweise 24–48 Stunden.
3. Eine spätere laufende Regelung korrigiert die Leistung anhand frischer Netzbilanz und tatsächlicher BMS-Freigaben.
4. Ein separat freizugebender Geräteadapter übersetzt validierte Ziele in belegte Hardwarebefehle.

Version 0.1 implementiert Planung, Datenvalidierung und eine UI-Vorschau. Es gibt keinen aktiven Geräteadapter. Kein HA-Service und kein Browserknopf sendet einen Hardwarebefehl.

## Eingänge und Vorzeichen

- Netzwirkleistung positiv = Bezug, negativ = Einspeisung.
- Batterie-AC-Leistung positiv = Laden, negativ = Entladen.
- PV und Hauslast sind positive AC-Leistungen in kW.
- SOC ist Prozent der konfigurierten aktuellen Kapazität; Wirkungsgrade sind Bruchteile von 0 bis 1.
- Preise intern in EUR/kWh, keine Vermischung mit EUR/MWh oder ct/kWh.
- Intervalle werden über UTC-Instanzen validiert; Anzeige und Lastprofile können Ortszeit verwenden.

In jedem Planungsschritt gilt `Netz = Hauslast - PV + Batterie_AC`. Die Energieänderung der Batterie berücksichtigt beim Laden den Ladewirkungsgrad und beim Entladen den Entladewirkungsgrad. Keine gleichzeitige Ladung und Entladung in einem Schritt.

## Wirtschaftlichkeit

Die Zielfunktion enthält Bezugskosten minus Einspeiseerlös plus optionalen Verschleiß pro abgegebener AC-kWh. Die Vollkostenrechnung verteilt Investition/Betriebskosten auf die erwartete Lebensdauerenergie und ist eine getrennte Auswertung. Beide Beträge dürfen nicht unbemerkt addiert werden.

Ein voller Durchlauf des gewählten SOC-Fensters ist nicht automatisch ein äquivalenter 0–100%-Vollzyklus. Die Lebensdauerrechnung benennt ihre Zyklenbasis ausdrücklich. Eine andere Entladetiefe verändert den nutzbaren Energieinhalt; eine andere Zyklenlebensdauer darf nur auf einer belegten Kennlinie oder einer ausdrücklich geänderten Annahme beruhen.

Bereits entstandene PV-Investitionen sind keine zusätzlichen kurzfristigen Kosten einer einzelnen Ladeentscheidung. Der entgangene tatsächliche Einspeiseerlös ist dagegen relevant. Tarifverträge und steuerliche/abrechnungstechnische Behandlung werden nicht erfunden.

## Prognosen

Der Planer erhält vollständige Szenarien. Eine Baseline-Lastprognose ist implementiert: gleiche Ortszeit, bevorzugt gleicher Wochentag, danach Werktag/Wochenende; neuere Messungen bekommen mehr Gewicht. Zukünftige Messungen dürfen nie in das Training gelangen. Tageslicht, Bewölkung und neue Lasten werden damit noch nicht modelliert.

Vor einer lernenden Weiterentwicklung werden historische, rollierende Rücktests benötigt: MAE, systematischer Fehler und Vergleich mit einfachen Baselines. Als nächste Schritte sind Wetter-/PV-Adapter, Anlagenkennwerte, Feiertage und belegte Prognosekorrektur geplant. Keine Aussage „extrem schlau“ ersetzt eine gemessene Verbesserung.

## Spätere Gerätesteuerung

Node-RED kann als vorhandene Ausführungsschicht dienen. Der Energiemanager soll künftig klar benannte Ziele ausgeben; ein Adapter muss Empfang, Einheit, Vorzeichen, Frische, Kommunikationsausfall und BMS-Limits prüfen. Ein Wechselrichter darf nicht parallel von widersprüchlichen Zeitplänen oder zwei gleichrangigen Schreibern geregelt werden. Zwei abfragende Master auf demselben Modbus-RTU-Bus sind nicht vorgesehen.

Solis/Sungrow-Verwandtschaft oder RJ45-Bauform legen weder Registerbelegung noch Protokoll fest. Tatsächliche Modelle und Firmware müssen im Geräteprofil stehen. Plexlog-Funktionen werden nach belegtem Treiberumfang genutzt, nicht anhand einer allgemeinen Hybrid-Kompatibilitätsangabe angenommen.
