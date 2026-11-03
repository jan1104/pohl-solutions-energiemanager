# Janitza: UMG 604-PRO als Gateway zu UMG 103-CBM

Stand: 03.11.2026. Dokumentationsprüfung, keine Verbindung zu einer Anlage, keine Geräte- oder Konfigurationsänderung. Exakte installierte Firmware und laufende Konfiguration sind nicht nachgewiesen. Private Standortdaten/Adressen bleiben außerhalb dieses Berichts.

## Ergebnis

**Die vom Nutzer beschriebene Architektur ist grundsätzlich richtig:** Ein UMG 604 bzw. 604-PRO kann über Ethernet erreichbar sein und den Zugriff auf nachgeschaltete RS485-/Modbus-RTU-Messgeräte ermöglichen. Die offiziellen Unterlagen zeigen ausdrücklich UMG 103-CBM hinter einem UMG 604. Ein UMG 103-CBM benötigt dabei keine eigene IP-Adresse. Der Client verwendet die IP des Gateways und die Geräteadresse des nachgeschalteten Messgeräts. Janitzas GridVis-Anleitung nennt hierfür Modbus TCP, Port 502. [UMG-103-CBM-Gateway-Schnelleinstieg](https://assets.janitza.com/ce18jq9ih0x6/90cdeedae75bbe803fa822/f060197f5730bf1a0dbbfc74db944a42/janitza-gv-guide-umg103cbm-de-en.PDF)

```text
Energiemanager (Modbus-TCP-Client)
              │ Ethernet / Gateway-IP
              ▼
UMG 604-PRO: eigenes Messgerät UND Gateway
              │ RS485, Modbus RTU, ein Busmaster
              ├── UMG 103-CBM: eigene Geräteadresse
              └── UMG 103-CBM: andere Geräteadresse
```

Der bereitgestellte Schaltplan benennt UMG 604-PRO und zwei UMG 103-CBM. Der Nutzer bestätigte am 03.11.2026, dass die 103er am 604-PRO hängen und dieser Netzwerk besitzt. Busadressen, aktiver Modus, Firmware und Erreichbarkeit wurden nicht technisch ausgelesen. Die Formulierung „504“ darf nicht automatisch zu einem anderen Gerätetyp führen; das Typenschild bleibt maßgeblich.

## Betriebsarten nicht verwechseln

Das UMG-604-PRO-Handbuch unterscheidet an Parameter 203 RS485 Slave (0), Master (1) und Gateway-transparent (2). Adresse und Baudrate sind eigene Parameter. Ethernet unterstützt Modbus TCP auf Port 502 und eine Gateway-Funktion. Diese Parameterliste beschreibt keine pauschale Umschaltanweisung für die vorhandene Anlage. [604-PRO-Handbuch, Abschnitte 11.7 und 16.10](https://www.janitza.com/files/download/manuals/current/UMG604-PRO/janitza-bhb-umg604pro-en.pdf)

Janitzas GridVis-Hilfe bezeichnet die RS485-Auswahl ausdrücklich als „Modbus-Master (Gateway)“ und führt transparentes Gateway gesondert auf. Für dieses Modell darf der Begriff Gateway deshalb nicht unbesehen mit „Modus 2 einstellen“ übersetzt werden. Firmware und gewünschter Transportweg entscheiden. [GridVis: UMG 604](https://wiki.janitza.de/spaces/GVOH/pages/136189676/UMG%2B604)

| Funktion | Bedeutung für den Energiemanager |
|---|---|
| Eigene 604-PRO-Messwerte | Messung am eigenen Messeingang des 604-PRO; eigenes Modellprofil |
| Gatewayzugriff auf ein 103-CBM | Gateway-IP plus Zieladresse; Registerprofil des 103-CBM, nicht das des 604-PRO |
| JASIC-Abfrage/Aggregation | Optionales Programm fragt Slaves selbst ab und kann Werte in benutzerdefinierten Variablen bereitstellen |
| Transparentes Gateway | Separater Modus; nicht ohne passenden Transportnachweis als Standard-Modbus-TCP-Gateway voraussetzen |

JASIC ist **nicht automatisch für jeden durchgereichten Zugriff erforderlich**. Janitza dokumentiert separat ein Programmbeispiel, das UMG-103-Werte liest und auf globale Variablen im UMG 604 abbildet. Benutzerbereich 20000–32000 ist dort beschrieben. Daraus folgt keine automatische feste Registerabbildung aller angeschlossenen Zähler. [Janitza: Modbus-Slave über JASIC auslesen](https://wiki.janitza.de/plugins/viewsource/viewpagesrc.action?pageId=166702910)

## Modell- und Firmwareprofile

- UMG 604 ohne PRO und UMG 604-PRO als unterschiedliche Profile behandeln. Die 604-PRO-Modbusliste gilt laut Titel für Firmware ab 5.028; Identität und Firmware vor Profilwahl prüfen. [604-PRO-Modbusliste](https://www.janitza.com/files/download/manuals/current/UMG604-PRO/janitza-mal-umg604pro-en.pdf)
- UMG 103 ohne CBM und UMG 103-CBM nicht gleichsetzen. Die herangezogene CBM-Adressenliste gilt ausdrücklich für Firmware ab 2.0. Sie nennt 8 Datenbits, keine Parität, am CBM zwei Stopbits, externe Stopbits 1 oder 2; unterstützte Baudraten 9600 bis 115200. Daten sind Big Endian. Firmware, Wandlerverhältnisse und Format-/Adressbasis müssen im Adapterprofil dokumentiert werden. [103-CBM-Modbusliste](https://www.janitza.com/files/download/manuals/current/UMG103-CBM/janitza-mal-umg103cbm-en.pdf)
- Nicht voraussetzen, dass ein altes 103-Gerät die CBM-Register vollständig identisch interpretiert. Keine Registertests mit Schreibbefehlen zur Identifikation.

## Auslesbare Werte

UMG 103-CBM stellt phasenweise und aufsummierte elektrische Messwerte bereit. Als minimale lesende Profilprüfung eignen sich folgende dokumentierte Register; dies sind keine Live-Ergebnisse:

| Adresse | Inhalt | Datentyp / Einheit |
|---|---|---|
| 19000 / 19002 / 19004 | Spannung L1/L2/L3 gegen N | Float / V |
| 19012 / 19014 / 19016 | Strom L1/L2/L3 | Float / A |
| 19020 / 19022 / 19024 | Wirkleistung L1/L2/L3 | Float / W |
| 19026 | Gesamte Wirkleistung | Float / W |
| 19034 | Gesamte Scheinleistung | Float / VA |
| 19042 | Gesamte Blindleistung | Float / var |
| 19050 | Frequenz | Float / Hz |

Zusätzlich enthält die Liste Energiezähler und weitere Qualitäts-/Konfigurationswerte. Die genannten Float-Werte benötigen jeweils zwei 16-Bit-Register. FC03/FC04 sind lesende Funktionen; nur für das bestätigte Profil zulässige Funktionen verwenden. Registeradresse, Werteformat und Einheit ausdrücklich abbilden; W intern zu kW umrechnen. Energie-/Tarifregister nicht pauschal über alle UMG-Varianten kopieren. [103-CBM-Adressenliste, ab Seite 12](https://www.janitza.com/files/download/manuals/current/UMG103-CBM/janitza-mal-umg103cbm-en.pdf)

Das UMG 604-PRO besitzt eigene Spannungs-, Strom-, Wirk-/Blind-/Scheinleistungs- und Energiegrößen sowie erweiterte Netzqualitätsdaten. Seine Kommunikationsliste beschreibt außerdem Master- und Slavefunktionen. Daraus folgt keine universelle Aktorfähigkeit der nachgeschalteten Geräte: Ein Messgerät bleibt ein Messgerät, auch wenn der Gatewaytransport Schreibfunktionscodes kennt. [604-PRO-Modbusliste](https://www.janitza.com/files/download/manuals/current/UMG604-PRO/janitza-mal-umg604pro-en.pdf)

## Konsequenzen für das Produkt

1. **Physisches Gateway und logische Geräte getrennt anlegen.** Verbindung zum 604-PRO wiederverwenden; jedes Ziel besitzt sein eigenes Profil und seine Unit-ID. Das eigene Messgerät des Gateways ist eine zusätzliche Identität.
2. **Adresse ist keine Messrolle.** Erst danach zuordnen: Netzgesamtbilanz, Halle, PV-Zweig oder Kontrollmessung. Ein PV-Abgang mit Speicher/Verbrauchern misst eine Nettozweigbilanz, nicht automatisch reine PV-Erzeugung.
3. **Ein physischer RTU-Master.** Kein zweiter USB-/RS485-Master parallel auf denselben Bus. Vorhandene Plexlog-/GridVis-/JASIC-Nutzung aufnehmen und Konflikte vermeiden.
4. **Busweise Zugriff koordinieren.** TCP-Clients können dasselbe serielle Nadelöhr teilen. Polling bündeln, gleichzeitige Anfragen begrenzen, Timeout-/Wiederholungsverhalten testen. Erst reale Zykluszeiten messen, keine beliebig schnelle Regelung versprechen.
5. **Vollständigen Messweg speichern.** Gerät → Gateway/Bus → Zieladresse → Registerprofil → Kanal → Messrolle → Anlage. Direkt und über Gateway gelesene identische Messwerte nicht doppelt zählen.
6. **Frische erhalten.** Abfragezeit und ggf. Mess-/Cachezeit unterscheiden. Erfolgreiche Gatewayverbindung bei nicht antwortendem Slave ist kein frischer Slavewert.
7. **Nur lesen bei Erkennung.** Beschränkte, geführte Suche über bekannte Zieladressen/zulässige Identitätsabfragen; keine flächendeckenden Register- oder Schreibversuche.

## Offene Punkte vor Implementierung an der Referenzanlage

- Tatsächliche Typenschilder und Firmware des 604-PRO und der beiden CBM; Modbus-Adressen, aktueller RS485-Modus, Baudrate und Framing.
- Bestätigte Busführung (103er am 604-PRO) bei späterer lesender Bestandsaufnahme verifizieren; weitere Master-/Gatewayverbindungen aufnehmen.
- Bestehende JASIC-Programme, BACnet-/GridVis-/Plexlog-Verbindungen und jeweilige Pollinglast.
- Welcher Zugriff soll erhalten bleiben und welcher Prozess koordiniert künftig alle Anfragen?
- Für den eigenen 604-PRO-Zugriff tatsächliche Geräteadresse und für jeden Slave dessen Zieladresse; keine beispielhafte Unit-ID als festen Standard übernehmen.
- Wandlerverhältnisse, Vorzeichen und enthaltene Verbraucher anhand bekannter Betriebszustände prüfen.
- Grenzwerte von gleichzeitigen TCP-Verbindungen und maximaler serieller Last für die tatsächliche Firmware im Integrationstest verifizieren. Öffentliche Portangaben ersetzen keinen Lasttest.

## Nächster überprüfbarer Entwicklungsschritt

Simulator mit einer Gateway-IP, einer 604-PRO-Identität und zwei CBM-Zieladressen; korrekte Profilwahl, Floatdekodierung, Vorzeichen/Einheiten, Einzel-Slave-Timeout und gemeinsame Buswarteschlange testen. Reale Adressen/Konfiguration anschließend lokal in `private/` erfassen, nicht ins Repository übernehmen.
