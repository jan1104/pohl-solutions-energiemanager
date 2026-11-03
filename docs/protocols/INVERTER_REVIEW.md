# Wechselrichter, Logger und Protokolle – Quellenprüfung

Stand: 03.11.2026. Dokumentenprüfung ohne Netzscan, Geräteabfrage oder Schreibzugriff. Herstellerunterlagen beschreiben Fähigkeiten einer Baureihe; die konkrete installierte Kombination aus Modell, Hardware, Firmware und Logger ist noch nicht verifiziert. Kein Nachweis automatischer Kompatibilität aus Branding/Umlabelung.

## Ergebnisübersicht

| Gerät / Verbindung | Belegt | Noch zu prüfen |
|---|---|---|
| Solis S6-EH3P50K-H | Eigene RS485-Kommunikation für externe Geräte; Hybrid-Modbus-Protokoll vorhanden | Genaue Revision, Portfunktion, Modell-/Protokollkennung, freigegebene Befehle |
| Bluesun BSE50KH3 | Ähnliche veröffentlichte elektrische Eckdaten allein sind kein Protokollnachweis | OEM-Zuordnung und Registerkompatibilität für konkrete Firmware bestätigen |
| Solis S2-WL-ST | Hersteller beschreibt Modbus TCP über Logger, Port 502, WR-Modbus-ID | Tatsächlicher Logger, Firmware und gleichzeitiger Cloudbetrieb |
| Sungrow SG125CX-P2 | RS485_1 für Logger/COM100E; RS485_3 für externen Zähler; WiNet optional | Installierte Module, aktive Regelung und zulässiger gemeinsamer Zugriff |
| Sungrow SG50CX | RS485-Schnittstellen und Loggeranbindung dokumentiert | SG50CX oder SG50CX-P2 identifizieren, nicht austauschbar behandeln |
| Sungrow SH20T / SH25T | COM2 Logger-RS485 und WiNet-S2-LAN Modbus TCP für externe EMS dokumentiert | Aktuelle Registerliste und aktivierter externer Steuerungsmodus |
| Solarman v5 | Eigener Loggertransport über pysolarmanv5 | Loggerfamilie, Serien-/Slaveadressierung und passendes WR-Profil |

## 1. Solis S6 / Bluesun BSE

### Vorhandene lokale Herstellerunterlagen

Geprüft wurden die vom Nutzer bereitgestellten Dokumente: deutsches S6-EH3P(29.9–50)K-H-Handbuch Version 1.0 (08/2024), „RS485_MODBUS RTU Hybrid Inverter Protocol Ver3.2“, öffentliche Non-NDA-Modbus-Dokumentation sowie Loggeranleitungen. Keine privaten Standortdokumente werden hier kopiert.

- S6-Handbuch, gedruckte Seiten 25–29: Batterie-BMS, Zähler, Parallelverbindung und externe Kommunikation haben unterschiedliche Aufgaben. RJ45 bezeichnet nur die Steckerbauform. Ein BMS-Port ist kein Ethernet-/EMS-Port.
- BMS-Kommunikation ist CAN; der separate Meterweg ist RS485. Der externe RS485-Anschluss dient Kommunikation mit Drittgeräten. Parallelports und DIP-Abschluss beziehen sich auf die dokumentierte Parallelverbindung.
- Die ältere deutsche Porttabelle beschreibt EMS als CAN und einen reservierten Anschluss, während andere Revisionen externe EMS-RS485-Anschlüsse benennen können. Deshalb keine pauschale Pin-/Portanleitung für das BSE aus diesem Handbuch ableiten. Aktuelle modellgenaue Unterlage und Anschlussbeschriftung sind erforderlich.
- Ver3.2 enthält ausdrücklich S6-3PH-HV-50-kW-Modellkennungen und unterschiedliche „Setting method“-Varianten. Identifikation muss vor Auswahl eines Registers-/Befehlsprofils erfolgen.
- Dokumentiert sind FC03/04 zum Lesen und FC06/16 zum Schreiben. Die konkrete Tabelle unterscheidet Modellbereiche, Skalierungen und Datentypen. Registerreferenz 3xxxx/4xxxx ist nicht automatisch identisch mit der an die Bibliothek übergebenen 0-basierten PDU-Adresse.
- Ver3.2 nennt als Kommunikationsprofil 9600 Baud, 8N1, Leseabstand über 300 ms, Schreibabstand über 700 ms und weniger als 100 Datenbytes/50 Register je Rahmen. Diese Angaben sind Profilbedingungen dieser Revision, keine allgemeinen Modbus-Grenzen und noch keine bestätigte aktive Gerätekonfiguration.

### Auslesbare Datenklassen im vorliegenden Hybridprotokoll

Modell-/Protokoll-/DSP-/HMI-Kennung; PV-Spannung/Strom/Leistung; AC-Leistung, Spannung, Strom und Frequenz; Wirk-/Blindleistung; Netz-/Zählermessungen; Batterie-Spannung/Strom/Leistung/SOC, BMS-Zustände und Alarme; Energiezähler und Betriebszustände. Haupt-/Zweitbatteriewerte sind enthalten, aber ihre Verfügbarkeit und SOC-Skalierung sind modellabhängig. Nicht einfach den Durchschnitt zweier SOCs als Gesamt-SOC verwenden.

### Steuerung

Das mitgelieferte Ver3.2-Dokument umfasst Einstellbereiche einschließlich Speicher-/Leistungsfunktionen. Die separat öffentliche Non-NDA-Tabelle ist hingegen ausdrücklich eine Variante ohne Control. Das Vorliegen einer lesbaren Tabelle ist keine Freigabe sämtlicher Steuerbefehle. Für Lade-/Entlade-Sollwerte, Betriebsmodus, Exportgrenze und Rückfallverhalten benötigt jedes Modell ein belegtes Profil mit Einheiten, Sequenz, Haltezeit und Rückmeldung. Keine Steuerparameter aus alten RHI-Tabellen auf S6/BSE übertragen.

Die [offizielle S6-Produktseite](https://www.solisinverters.com/global/energy_storage_inverters16/S6-EH) führt aktuelle EUR-Handbücher und zwei Batterieports. Sie ersetzt keinen firmwarebezogenen Registerabgleich. Die behauptete BSE-Umlabelung ist als Nutzerhinweis erfasst, noch nicht als bewiesene Softwarekompatibilität.

## 2. Solis S2-WL-ST ist ein spezifischer Loggerweg

Der [offizielle Modbus-TCP-Leitfaden](https://usservice.solisinverters.com/support/solutions/articles/73000670200-modbus-tcp-communication-guide-for-s2-wl-st-wi-fi-lan-logger) beschreibt lokale WR-Lesewerte über S2-WL-ST und TCP-Port 502. Als Slave-ID wird die Adresse des Wechselrichters genutzt. Registerauswahl bleibt gerätespezifisch; das Grid-Tie-Beispiel ist nicht ungeprüft auf Hybridregister übertragbar.

Die ältere bereitgestellte Anleitung warnt, dass Aktivierung des TCP-Betriebs SolisCloud trennt. Die aktuell online gelesene Anleitung belegt keinen universellen gleichzeitigen Cloud-/EMS-Betrieb. Diese Eigenschaft muss für den konkreten Logger und Firmwarestand geklärt werden. Keine Änderung am Logger vorgenommen. Ein Netzwerkanschluss allein beweist weder Modbus-TCP-Server noch Solarman-v5-Unterstützung.

## 3. Sungrow SH20T / SH25T

Lokales SH5.0–25T-Handbuch, gedruckte S.44–46, 65 und 117:

- COM1 A1/B1: Hybrid-Host-/Client-Parallelkommunikation, nicht der normale externe Loggerport.
- COM2 Logger A1/B1: Monitoring-/Steuergeräte. COM2 Meter A2/B2: Smart-Energy-Meter. Batterie- und Ladestationsanschlüsse besitzen eigene Funktionen.
- LAN/WiNet-S2 Modbus TCP: geeignete Drittanbieter-EMS können Ein/Aus, Leistungsreduzierung und gegebenenfalls Batterie-Laden/-Entladen steuern. Externer Energieplanungsmodus über RTU/TCP ist beschrieben.
- Die Anleitung belegt Fähigkeiten, aber keine hier validierte Registerliste. Im Geräteprofil sind unter anderem PV/AC/Netz/Batterie/SOC/Status zu prüfen; nicht jeder Wert wird ohne zugehörigen Zähler oder angeschlossene Batterie geliefert.

Die aktuelle [offizielle WiNet-S/S2-Sicherheitsanleitung Ver13/202601](https://info-support.sungrowpower.com/product-materials/d0e3a2a8-55d9-4e4b-b0c5-ee3789ecc5ca.pdf) nennt Port 502 als standardmäßig deaktivierten Modbus-TCP-Dienst und 516 als standardmäßig aktiven TLS-Dienst. Abruf über Suche verfügbar, direkter PDF-Abruf zeitweise fehlgeschlagen. Der installierte Firmwarestand muss abgeglichen werden; „jeder WiNet immer auf 502 erreichbar“ ist keine belastbare Annahme.

## 4. Sungrow SG125CX-P2 und SG50CX / P2

- SG125CX-P2-Handbuch gedruckte S.68–75: RS485_1 als Logger-/COM100E-Weg, RS485_3 für externes Messgerät. RJ45 und Klemmen von RS485_1 sind Anschlussformen derselben Schnittstelle, keine zwei unabhängigen Busse. Das Handbuch warnt bei aktivem Kommunikationsmodul vor gleichzeitigem fremdem RS485-Logger.
- SG50CX-Handbuch gedruckte S.45–46, 55: RS485_1-Klemme und RJ45 haben dieselbe Funktion. Es warnt vor gleichzeitigem Kommunikationsmodul- und RS485-Betrieb. SG50CX-P2 benötigt das eigene Modellhandbuch.
- Die bereitgestellte Sungrow Third Party Compatibility Overview vom 26.01.2024 führt Modbus RTU, TCP und SunSpec für SGxxCX/SGxxCX-P2 als Baureihenfähigkeiten. Das sagt nicht, dass jeder Anschluss eine freie TCP-Schnittstelle ist oder alle Firmwarekombinationen dieselben Register bieten.
- Für direkte Messprofile mindestens Modell/Version, AC-/DC-Leistung, Phasenwerte, Energie und Status gegen eine aktuelle Herstellerliste prüfen. Stellfunktionen wie Wirk-/Blindleistungsregelung nur nach passender Protokolldokumentation und Abstimmung mit bestehendem Anlagenregler.

Derzeitiger 50-kW-Typ und tatsächliche Kommunikationsverdrahtung sind offen. Kein Parallelzugriff als vermeintlich harmlose Ergänzung voraussetzen.

## 5. Solarman v5 / pysolarmanv5

[Projekt-README](https://github.com/jmccrohan/pysolarmanv5), geprüft am 03.11.2026: Solarman-v5-Transport kapselt Modbus-RTU-Rahmen und verwendet typischerweise TCP 8899; synchrone und asynchrone APIs sind vorhanden. Das Projekt hat eine Suchhilfe für kompatible Logger. Solis S3-WIFI-ST wird ausdrücklich nicht unterstützt. Manche Ethernet-Logger nutzen stattdessen natives Modbus TCP.

Daraus folgt: eigener Transportadapter für Solarman v5, kein beliebiger Ersatz für native Modbus-TCP-Logger. Das Geräteprofil liefert weiterhin die WR-Register. Loggeridentität, WR-Slaveadresse und Netzwerkendpunkt als getrennte Identitäten modellieren. Kein Scan und keine Bibliotheksinstallation durchgeführt.

## 6. Konsequenzen für die Implementierung

1. Verbindungspfad speichern: direkt RTU, TCP, TCP→RTU-Gateway, Solarman oder Messgateway/Logger. Geräteprofil getrennt vom Transport halten.
2. RTU-Bus bekommt einen Master. Ein Gateway kann Netzwerkabfragen seriell bedienen; es macht zwei konkurrierende physische RTU-Master nicht zulässig.
3. Gateway-Lesewerte sind nicht automatisch transparentes Durchreichen jedes Befehls. Device-ID/Unit-ID, Weiterleitungsmodus, unterstützte FCs und Zeitlimits nachweisen.
4. Zuerst Identifikation und gezielte belegte Lesewerte. Bytefolge, Skalierung, Vorzeichen, Datenalter und Aktualisierungsrate gegen lokale Geräteanzeige prüfen.
5. Gerätesuche ist kein Registerscan; unbekannte Profile unklar lassen. Cloudlogger nicht ohne Prüfung umkonfigurieren.
6. Ein Schreiber pro gesteuerter Funktion; vorhandene Plexlog-Wirk-/Blindleistungsregelung und Einspeisegrenzen müssen in der Zuständigkeit berücksichtigt bleiben.
7. Ausstehend: Typenschilder/Versionswerte, genaue Logger, aktive Ports/Adressen, Zuständigkeiten und tatsächliche Modellregister. Keine Live-Freigabe aus dieser Prüfung ableiten.
