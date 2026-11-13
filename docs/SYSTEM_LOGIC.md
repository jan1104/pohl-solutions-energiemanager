# Gemeinsame Grundfunktionen und Systemlogik

Stand: 04.11.2026. Zielarchitektur und vorhandene Funktionen ausdrücklich getrennt. Aktuell keine Live-Steuerung; Verbindungsmodule noch nicht automatisch in HA aktiv.

## Einmal konfigurieren, mehrfach referenzieren

Ein Projekt enthält zentrale Verbindungen mit stabiler `connection_id`. Geräte verweisen darauf und tragen ihre eigene Zieladresse. Geräteprofile beschreiben Register/Bedeutung; sie bauen keinen eigenen Netzwerkclient auf. Mehrere Zähler hinter einem TCP-RTU-Gateway teilen sich denselben Transport und dessen serialisierte Warteschlange.

```text
Projekt
├── Elektrik: Netzanschlüsse → Zweige → Geräte/Messstellen
└── Kommunikation: zentrale Verbindungen
    └── Gateway-Verbindung
        ├── Zähler A: eigene Unit-ID, Messort Netz
        └── Zähler B: eigene Unit-ID, Messort Hauszweig
```

Kommunikation und elektrische Lage sind unabhängig. Eine gemeinsame Verbindung vereint keine Energiebilanzen getrennter Anschlüsse. Batterie-Elternbeziehung zum WR und `via_device_id` als Kommunikationsweg sind unterschiedliche Referenzen.

## Umgesetzte Zuständigkeiten

| Aufgabe | Baustein | Umfang |
| --- | --- | --- |
| Konfiguration | `core/project.py` | IDs, Referenzen, Kreise, Messrollen, Import/Export |
| Gerätepfad | `core/connection_routes.py` | Geräteeigene Unit-ID und konsistente Connection-ID aus Gatewaykette; keine Abfrage |
| Verbindungseigentum | `adapters/connections.py` | Zentraler Manager, geteilte native TCP-/Gatewayclients, geordnetes Beenden |
| Gemeinsamer Lesevertrag | `adapters/transports/base.py` | `RegisterReader.read_registers` für Profile unabhängig vom Framing |
| Framing | `adapters/transports/modbus_tcp.py` | FC03/04, Antwortprüfung, Timeout/Abbruch, Neuverbindung beim nächsten expliziten Lesen |
| Gerätebedeutung | `adapters/profiles/janitza_103_cbm.py` | Dokumentiertes Profil verwendet den gemeinsamen Lesevertrag |
| Messstellenbindung | `core/measurement_binding.py` | Gelieferte Rohwerte zuordnen, Skalierung/Einheit/Ausrichtung erhalten |
| Qualität/Ableitung | `core/metering.py` | Alter, Originalmesszeit, Quellenherkunft, Gleichzeitigkeit und Zirkelschlüsse |
| Planung | `core/optimizer.py` | Bestehende Einzelbatterie-Näherung auf expliziten Szenariodaten; noch kein Projekt-Mehrgeräteoptimierer |

### Geteilte Verbindungen

Ein `ReadOnlyConnectionManager` besitzt die Verbindungen einer Projektlaufzeit. Konstruktion und `for_connection(id)` öffnen keine Verbindung. Erst ein expliziter Leseaufruf erzeugt Verkehr. Native Modbus-TCP- und TCP-RTU-Gatewayeinträge mit identischem normalisiertem Host/Port teilen denselben Client, auch bei mehreren Konfigurations-IDs. Hostnamen werden bezüglich Groß-/Kleinschreibung und abschließendem Punkt normalisiert, IPs numerisch vereinheitlicht. Es erfolgt keine DNS-Abfrage zur Aliaserkennung. Verschiedene DNS-Namen oder Hostname/IP-Kombinationen können weiter denselben tatsächlichen Endpunkt bezeichnen: dafür dieselbe Connection-ID verwenden. Fehlender Port bedeutet Standard 502.

Profile erhalten über `for_connection` eine Lesereferenz ohne Schließfunktion. Nur der Manager beendet gemeinsame Clients. Beenden sperrt neue Aufrufe sofort und wartet auf bereits angenommene Abfragen einschließlich Warteschlange. Wiederholtes Beenden wartet auf dieselbe Bereinigung. Abbruch eines wartenden Geräts unterbricht keine andere laufende Abfrage; Abbruch eines auf Beendigung wartenden Aufrufers unterbricht die Bereinigung nicht. Eine beendete Instanz öffnet sich nicht wieder.

Mehrere unabhängig erzeugte Manager erkennen einander nicht. Die Anwendung muss vor Betriebsanbindung genau einen zentralen Besitzer je Projektlaufzeit sicherstellen und ihn beim Entladen beenden. Die HA-Grundlaufzeit besitzt den Manager seit 13.11.2026 und erzeugt ihn erst für einen ausdrücklichen internen Leseaufruf. Details unten; eine Bedienfunktion oder automatische Erfassung ist noch nicht angeschlossen.

`resolve_modbus_route(project, device_id)` validiert das Projekt und folgt ausschließlich `via_device_id`. Alle expliziten Connection-IDs entlang der Kette müssen übereinstimmen. Unit-ID kommt vom Zielgerät, niemals vom Gateway oder als angenommene 1. Projektformat 1 unterstützt 1–247; der generische TCP-Transport zusätzlich direkte TCP-Adresse 255. Pfadauflösung bestätigt keine Verdrahtung/Erreichbarkeit.

### Weitere Protokolle

Rohes RTU-over-TCP ist als ausdrücklich lesender Transport implementiert und in die gemeinsame Verbindungsverwaltung eingebunden; es benötigt einen angegebenen Port und verwendet RTU-CRC statt MBAP. Details und Grenzen: [RTU_OVER_TCP.md](RTU_OVER_TCP.md). USB-RS485, Solarman und MQTT bleiben eigene Implementierungen. TCP/Gateway verwendet MBAP, kein RTU-CRC-Framing. Der Manager lehnt noch nicht implementierte Transportarten ausdrücklich ab. Eine konfigurierte serielle Modbusroute kann bereits offline aufgelöst werden; das behauptet keinen fertigen RTU-Treiber. Zukünftige Modbusmodule sollen denselben RegisterReader-Vertrag erfüllen. MQTT braucht eine abonnierende Messwertschnittstelle statt eines erfundenen Registertransports.

## Durchgehender fachlicher Datenfluss

1. **Projekt einrichten:** Name, Bereiche, tatsächliche Netzanschlüsse, Geräte und zentrale Verbindungen. Anschluss ist Optimierungs-/Tarifgrenze. Zusätzliche Standort-/Gerätegruppenverwaltung über das bisherige Bereichsmodell hinaus fehlt noch.
2. **Quelle zuordnen:** Kanal, Adresse, Einheit, Skalierung, Ausrichtung, Messort und enthaltene Verbraucher. Vollständige grafische Zuordnung, Gerätesuche, Quellenalias-/Abdeckungsprüfung bleiben offen.
3. **Bewusst lesen:** Profil nutzt die geteilte Verbindung und dekodiert Werte. Empfangszeit beweist nicht das Alter eines Gatewaywerts. Nur tatsächliche Gerätezeit als solche führen. Das Janitza-Profil liefert bereits kW und darf nicht nochmals über den Rohwertpfad skaliert werden.
4. **Qualität und Bilanz:** Werte nach Messort bilanzieren. Unterzähler nicht zu ihrer enthaltenen Hauptmessung addieren. Ein gemischter PV-/Speicher-/Wärmezweig bleibt Nettozweig. Ungültige Werte bleiben unbekannt. Laufzeitwerte sind noch nicht durchgehend an HA und Planung angeschlossen.
5. **Prognosen/Tarife:** PV-/Lastviertelstunden, Bezugskosten und Einspeiseerlöse getrennt führen, inklusive Quellen, Einheiten, Abzügen, Datenalter und Prognosefehlern. Börsenpreise allein sind kein vollständiger Vertrag.
6. **Pro Anschluss planen:** Mehrere Speicher/Verbraucher mit eigenen Grenzen, Prioritäten und Energiequellen gemeinsam optimieren. Dieser Mehrgeräteoptimierer fehlt noch; das Einzelbatteriemodell darf nicht als solcher ausgegeben werden.
7. **Plan erklären:** Erwartete Kosten, Restenergie, Gründe und Annahmen; prognostizierter Vorteil getrennt vom Ist-Nachweis. Fehlende Echtdaten nicht durch Demo ersetzen.
8. **Später freigegebene Steuerung:** Ein Verantwortlicher je Stellgröße, Plexlog-/Netzbetreibervorgaben und lokale Schutzgrenzen berücksichtigen. Ausfallstrategie je realem Gerät prüfen. Import aktiviert keine Steuerfreigabe.

## Nächste Abnahmen

- Den an die HA-Lebensdauer gebundenen Manager über eine ausdrücklich ausgelöste Leseprüfung nutzbar machen; weiterhin kein Geräteabruf im Setup/Import.
- USB-RS485 ergänzen; für den implementierten RTU-over-TCP-Tunnel reale Gateway-/Busparameter belegen und prüfen. Ein Master je RTU-Bus.
- Quellenalias-/Registerüberlappung und elektrische Messabdeckung vor Summenbildung prüfen.
- Durchgehenden Simulator-/Replayfall vom bewusst gelesenen Wert bis zur Projektmessstelle/Bilanz prüfen; unbekannte Gerätezeit sichtbar erhalten.
- Danach Mehrgeräteplanung und geführte Bedienung verbinden. Reale Modelle, Parameter, Verträge und Ausfallstrategien bleiben zu belegen.


## HA-Besitz und ausdrückliche Leseaufrufe — 13.11.2026

`BaseRuntime` besitzt höchstens einen zentralen `ReadOnlyConnectionManager`. Der neue interne Aufruf `async_read_registers(...)` verlangt die erwartete Revision des lokalen ProjectStore. Erst dieser ausdrückliche Leseaufruf erzeugt bei Bedarf den Manager und liest über die angegebene Connection-ID. Konstruktion, HA-Start, Status und Projektimport erzeugen weder Manager noch Geräteverkehr. Kein neuer Service, WebSocket-Befehl, Zeitgeber oder automatischer Abruf ist freigegeben.

Mehrere Aufrufe desselben Projektstands verwenden denselben Besitzer und dessen Endpunkt-Warteschlangen. Bei einer anderen Projektrevision wird der alte Manager geschlossen und abgearbeitet, bevor ein neuer entsteht. Nach dem Warten werden Laufzeitzustand und Revision erneut geprüft. Ein Ergebnis wird verworfen, wenn zwischenzeitlich Projektstand oder Besitzer wechselten oder die Laufzeit beendet wurde. Die Revision bezieht sich auf den lokalen ProjectStore: sie ist kein Nachweis für externe Datenbankänderungen oder die Frische einer Geräteantwort. Keine Werte werden dadurch als Historie oder aktueller Plan gespeichert.

HA-Unload beendet die Laufzeit dauerhaft, sperrt neue Aufrufe und wartet auf die zentrale Bereinigung einschließlich der Besitzersperre. Wiederholte Stop-Aufrufe warten auf dieselbe Aufgabe. Ein Abbruch des aufrufenden Tasks wird erst nach Abschluss dieser Arbeit weitergegeben. Nach Stop ist eine neue BaseRuntime erforderlich; ein stilles Wiederöffnen der beendeten Instanz ist nicht erlaubt.

Die HA-Laufzeitprüfung verwendet eine echte Projektablage und eingesetzte synthetische Transportbesitzer. Sie prüft unveränderten Setup-/Status-/Importpfad, Wiederverwendung, überholte Ergebnisse, Besitzerwechsel und Abbruch während Stop beziehungsweise Rotation. Die getrennten Transporttests verwenden weiterhin ausschließlich Loopback-Server. Reale Geräte, Messzeiten und eine HA-Leseoberfläche bleiben gesondert zu prüfen.


Grundmodul 0.1.3 bindet zusätzlich die gespeicherte Modbus-Leistungsmessstelle über `async_read_power_measurement(...)` an denselben Besitzer. Registerroute und Kanalumrechnung stammen aus dem Projekt; geprüfte Reihenfolge, Quellenidentität, Ausrichtung und Zeitnachweise sind weiterhin ausdrücklich erforderlich. Details: RUNTIME_METERING.md. Kein automatischer Abruf und keine Ergebnisablage.
