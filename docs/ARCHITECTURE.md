# Architektur und Produktentscheidungen

## Ziel

Ein Bedienort für Energiekosten, Gerätezuordnung und wirtschaftliche Viertelstundenplanung mehrerer eigenständiger Anlagen. Je Netzanschluss werden mehrere Speicher und flexible Verbraucher gemeinsam geplant. Batterieexport, Netzladen, Verbraucherprioritäten und Energiequellen sind je Anlage/Gerät ausdrücklich konfiguriert. Vincent ist ein Beispiel, keine fest eingebaute Topologie. Bestätigte Anforderungen stehen in REQUIREMENTS.md.

## Vier getrennte Verantwortlichkeiten

1. Datenadapter liefern zeitgestempelte Messwerte, Preise und Prognosen mit eindeutigen Einheiten und Qualitätsangaben.
2. Der Planer berechnet einen nachvollziehbaren Fahrplan über beispielsweise 24–48 Stunden.
3. Eine spätere laufende Regelung korrigiert die Leistung anhand frischer Netzbilanz und tatsächlicher BMS-Freigaben.
4. Ein separat freizugebender Geräteadapter übersetzt validierte Ziele in belegte Hardwarebefehle.

Version 0.2 implementiert eine einzelne Batterieplanung, Preis-/Datenvalidierung, HA-Plansensoren und eine separate UI-Vorschau. Mehranlagen-, Mehrspeicher- und direkte Gerätefunktionen sind Zielarchitektur, noch keine vorhandenen Fähigkeiten. Es gibt keinen aktiven Geräteadapter. Kein HA-Service und kein Browserknopf sendet einen Hardwarebefehl.

## Einbettung und direkte Geräteanbindung – Zielarchitektur

- HA stellt zunächst Einrichtung und Oberfläche bereit. Anlagenmodelle, Optimierung, Messwertnormalisierung, Gerätekatalog und Kommunikationsadapter dürfen keine zwingende HA-Laufzeit voraussetzen; eine spätere eigenständige Anwendung soll dieselben Bausteine nutzen können.
- Eine Anlage besitzt einen Netzanschluss, eigene Tarife, Messrollen und Geräte. Übergreifende Übersichten dürfen Energie verschiedener Netzanschlüsse nicht verrechnen.
- Transportadapter: Modbus TCP, Modbus RTU/RS485, Solarman v5 und MQTT bereits im ersten nutzbaren Umfang. Geräteprofile beschreiben getrennt Register/Topics, Skalierung, Einheit, Aktualität, Identität und belegte Fähigkeiten.
- Geräteidentität und Zuordnung bleiben stabil, auch wenn sich eine IP-Adresse ändert. Ein Netzwerkfund beweist weder Geräteprofil noch Schreibfreigabe.
- Gerätesuche zeigt belegte Informationen und manuelle Alternativen; MQTT benötigt einen eingerichteten Broker, serielle Verbindungen eine ausgewählte Schnittstelle und Verbindungsparameter. Keine blinde Registersuche oder Schreibprobe zur Erkennung.
- Bibliothekskandidat für Solarman: [pysolarmanv5](https://github.com/jmccrohan/pysolarmanv5). Laut README, geprüft am 03.11.2026, kapselt die Bibliothek Modbus-RTU-Anfragen über Solarman v5 und unterstützt nicht jeden Solis-Logger, ausdrücklich nicht S3-WIFI-ST. Loggerprotokoll und Wechselrichterregister sind separat zu validieren.
- Gemeinsamer Einrichtungsablauf: Anlage anlegen, Verbindung finden/eingeben, Profil und Messrollen zuordnen, Daten prüfen, Plan ansehen, Steuerfähigkeiten konfigurieren und später ausdrücklich freigeben. Zugangsdaten bleiben außerhalb exportierter Pläne und Git.

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

Der Energiemanager soll Geräte selbst über validierte Adapter steuern; Node-RED kann Wünsche übergeben und ist keine erforderliche Ausführungsschicht. Ein Adapter muss Empfang, Einheit, Vorzeichen, Frische, Kommunikationsausfall und BMS-Limits prüfen. Ein Wechselrichter darf nicht parallel von widersprüchlichen Zeitplänen oder zwei gleichrangigen Schreibern geregelt werden. Zwei abfragende Master auf demselben Modbus-RTU-Bus sind nicht vorgesehen. Priorität und Ablauf externer Wünsche sind noch offen; keine unbestätigte Betriebsregel voraussetzen.

Solis/Sungrow-Verwandtschaft oder RJ45-Bauform legen weder Registerbelegung noch Protokoll fest. Tatsächliche Modelle und Firmware müssen im Geräteprofil stehen. Plexlog-Funktionen werden nach belegtem Treiberumfang genutzt, nicht anhand einer allgemeinen Hybrid-Kompatibilitätsangabe angenommen.
