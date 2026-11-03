# Plexlog PL500+: Protokoll- und Schnittstellenprüfung

Stand: 03.11.2026. Dokumentenprüfung, keine Verbindung mit einer Anlage, keine Konfigurationsänderung oder Schreibprobe. Herstellerunterlagen sind technische Quellen, keine Anweisung zur Aktivierung von Schnittstellen.

## Ergebnis

Plexlog kann als Messgateway und vorhandener Anlagenregler eingebunden werden. **Lesbare Rückmeldungen zu Wirk-/Blindleistungsvorgaben und marktbasierter Abregelung sind tatsächlich dokumentiert** – im separaten ThirdPartyClient-/Fernwirkprofil. Sie stehen nicht automatisch in den OpenGateway-V2-Gerätemodellen. Ob diese Profile in der konkreten Installation gleichzeitig mit der vorhandenen Fernwirkanbindung verfügbar sind, bleibt zu prüfen.

## Drei unterschiedliche Schnittstellenrollen

| Rolle | Zweck | Bedeutung für den Energiemanager |
|---|---|---|
| Gerätekommunikation | Plexlog fragt WR/Zähler ab und führt ggf. Regelung aus | Keine zweite RTU-Masterinstanz auf denselben Bus setzen |
| OpenGateway V2 | Einheitliche externe Messmodelle für System und Komponenten | Messdaten über logische Gerätezuordnung lesen |
| ThirdPartyClient/Fernwirkanbindung | Übergabe von Messungen, Regler-Rückmeldungen und Steuerung | Eigenes Profil; lesende Integration getrennt von Schreibrechten |

Der [Plexlog-Master-Modus](https://doc.plexlog.de/de/dokumentation/plexlog-hardware/konfiguration/master-modus/) koordiniert mehrere PL100/PL500+ für Leistungsreduzierung und Blindleistung. Diese Bezeichnung ist nicht gleichbedeutend mit einem transparenten TCP-RTU-Gateway für beliebige untergeordnete Geräte. Aus OpenGateway-Datenmodellen folgt keine Durchleitung aller Originalregister eines angeschlossenen WR.

## OpenGateway V2: dokumentierte Messdaten

Die [Modellbeschreibung](https://www.plexlog.de/web/sites/default/files/2025-10/OpenGateway%20Version%202.0%20-%20DataModels_2.pdf) verlangt Aktivierung von Version 2 und logische Adresszuordnung unter Device Mapping. Big Endian ist angegeben; Systemmodell laut Dokument unter UnitID 0 oder 253. Den tatsächlichen Endpunkt und die aktive Konfiguration prüfen, nicht allein daraus Port/Erreichbarkeit ableiten.

- System: Erzeugungs-/Verbrauchsleistung und Energien, Netzleistung, Batteriesummenleistung, durchschnittlicher SOC, Alarmzahl und aktueller Tarifzonenpreis.
- WR: Wirk-/Blindleistung, AC-Spannung, Temperatur, Isolation, Batterieinformationen und DC-Kanalwerte, sofern vom Treiber geliefert.
- Zähler: Gesamt-/Phasenleistungen, Spannungen, Ströme, Schein-/Blindleistung, cos phi, Frequenz und THD.
- Speicher: Leistung, SOC/SOH, DC-Strom/-Spannung; Sensor-/BHKW-Modelle zusätzlich vorhanden.

Wichtige Normalisierung: Netzleistung negativ bei Einspeisung; Batterieleistung negativ beim Laden, somit gegenüber dem internen EMS-Batterievorzeichen invertieren. Durchschnitts-SOC ist keine nachgewiesene kapazitätsgewichtete Gesamtenergie. Tarifzonenpreis in Cent ist nicht automatisch der tatsächliche Direktvermarktungserlös. Diese Modelle belegen keine Herkunfts-/Prioritätsinformation aller externen Vorgaben.

## ThirdPartyClient Modbus TCP: belegte Regler-Rückmeldungen

Das [TCP-Profil V1.1.0, Seite 1](https://www.plexlog.de/web/sites/default/files/2025-10/ModBusTCP%20ThirdPartyClient%20V1_1_0.pdf) nennt `DynModbusTCP_Profil_26` unter Port C/Fernwirkanbindung, Port 1502 und UnitID 1 jeweils einstellbar, Big Endian. Auswahl relevanter **dezimaler Register wie im Dokument**, keine bereits validierte Treiberimplementierung:

| Register | Lesbarer Inhalt | Einheit |
|---|---|---|
| 1002 | Rückmeldung Wirkleistungsvorgabe EA1 | % |
| 1004 | Wirkleistung EA1 | MW |
| 1010 | Marktbasierte Abregelung; 100 bedeutet keine DV-Reduktion | % |
| 1012 / 1014 | Blindleistung / cos phi EA1 | Mvar / dimensionslos |
| 1019 / 1022 | Fester cos phi: Aktivstatus / Vorgaberückgabe | 0–1 / cos phi |
| 1025 / 1028 | Festes Q: Aktivstatus / Vorgaberückgabe | 0–1 / Mvar |
| 1037 / 1043 / 1049 | Aktivrückmeldungen Q(U), Q mit Spannungsbegrenzung, Q(P) | 0–1 |

Netz-Übergabemessungen und konfigurierbare Eingänge sind ebenfalls vorgesehen. Verfügbare Leistungswerte benötigen teilweise Einstrahlungssensorik. Wirkleistungsvorgabe ist zusätzlich als schreibbarer Punkt dokumentiert und erfordert Slave-Modus – **diesen Modus nicht für eine Leseintegration ungeprüft aktivieren**. Die Tabelle beweist weder uneingeschränkte Parallelverbindungen noch vollständige Prioritäts-/Herkunftsauflösung aller Reglerquellen.

## RTU und IEC104 sind getrennte Varianten

Das [RTU-Profil V1.1.0](https://www.plexlog.de/web/sites/default/files/2025-10/ModBusRTU%20ThirdPartyClient%20V1_1_0.pdf) bietet vergleichbare Datenpunkte, erfordert aber `DynModbusRTU_Profil_39`, dokumentiert Adresse 1 einstellbar und 9600,8E1. Das ist eine serielle Fernwirkschnittstelle, keine Aussage über einen gemeinsamen Multi-Master-Bus. Adressbasis, Float-Anordnung und tatsächliche Werte zunächst lesend bestätigen. Die Dokumentnotation „x3 Holding (W)“ ist kein hinreichender Nachweis des zu verwendenden Schreib-Funktionscodes.

Das [IEC104-Profil V1.1.0](https://www.plexlog.de/web/sites/default/files/2025-10/IEC104%20ThirdPartyClient%20V1_1_0.pdf) verwendet `DynIEC60870_5_104_Profil_8`, ASDU/IOA und Typkennungen statt Modbusregistern. Beispiel: Rückmeldung Wirkleistung IOA 0-1-2, marktbasierte Abregelung 0-1-7, jeweils Typ 13; Leistungsvorgabe 0-1-1 Typ 50. Ein Modbus-Client kann solche IOAs nicht direkt abfragen. Ein eigenständiger IEC104-Adapter wäre zusätzliche Arbeit; kein bestehender Implementierungsumfang behauptet.

## Was Diagnose und Direktvermarktungsport belegen

Die [Diagnoseseite](https://doc.plexlog.de/de/dokumentation/plexlog-hardware/diagnose/) beschreibt die Anzeige von Reduktionsquelle/-stufe, Blindleistungsvorgabe und Direktvermarktungsverbindung in der Plexlog-Oberfläche. Daraus folgt keine externe Lesbarkeit jedes dieser Felder. Insbesondere sind Verbindungsstatus und vollständiger Ursprung der wirksamen Grenze in den oben geprüften Modbusmodellen nicht vollständig belegt.

Die [Direktvermarktungskonfiguration](https://doc.plexlog.de/de/dokumentation/plexlog-hardware/konfiguration/direktvermarktung/) beschreibt Port 502 und einen Tunnel auf externem Router. **Dieser DV-Endpunkt ist nicht ohne Weiteres das ThirdPartyClient-Profil auf Port 1502.** Der offizielle [Downloadbereich](https://www.plexlog.de/web/service/downloads) führt OpenGateway V2 und ThirdPartyClient getrennt auf.

## Konsequenzen für das Produkt

1. Separate Profile für OpenGateway-Messungen und ThirdPartyClient-Rückmeldungen anlegen; Ziel, Port, UnitID, Version und Feldquelle speichern.
2. Eine Messgröße nur einmal für die Bilanz verwenden, auch wenn sie direkt und über Plexlog erreichbar ist. Alter der zugrunde liegenden Messung nicht mit erfolgreichem Lesezeitpunkt verwechseln.
3. Externe Grenzen mit Bezugsgröße (Erzeugung/Netzanschluss/EA1), Gültigkeit und bekannter Herkunft führen. Unbekannte Grenze ist nicht „unbegrenzt“.
4. Bestehende Wirk-/Blindleistungsregelung erhalten; Zuständigkeit je Stellgröße klären. Wirtschaftliche Batterie-/Lastplanung muss deren Vorgaben berücksichtigen und darf Abregelung nicht ungeprüft umgehen.
5. Lesende Simulatoren zuerst: korrekte Einheit MW→kW, Mvar→kvar, Vorzeichen, Float-Decodierung, fehlende Werte, ausgelaufene Vorgaben und Wiederanlauf testen.

## Vor einer realen Anbindung offen

- Firmware, aktivierte Profile/Ports und Device Mapping; tatsächliche Lizenzen/Zugriffsmöglichkeiten.
- Nutzt die vorhandene Fernwirkanbindung bereits Port C? Können gewünschte Profile koexistieren? Welche parallelen Leseclients sind zulässig?
- Welche Vorgabe ist nach interner Priorisierung tatsächlich wirksam, und für welche Geräte/Bezugsgröße gilt sie?
- Datenfrische/ungültige Werte/Fehlermeldungen und Zeitverhalten; Unterstützung der vorhandenen WR/BMS-Treiber.
- Direktvermarktungsverbindung, Kommunikationsausfall und Herkunft der EVU-/DV-Vorgaben über weitere freigegebene Punkte verfügbar?

Kein Netz gescannt, keine privaten Originalunterlagen kopiert und keine Gerätesteuerung implementiert. Öffentliche Herstellerdokumente mit den bereitgestellten gleichnamigen Unterlagen verglichen.
