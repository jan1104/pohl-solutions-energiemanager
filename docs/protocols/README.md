# Protokoll- und Geräteprüfung

Stand: 03.11.2026. Drei parallel arbeitende Prüfagenten und eine ergänzende Transport-/Messgeräteprüfung. Herstellerquellen und bereitgestellte Unterlagen gelesen; keine Gerätezugriffe oder Netzwerk-/Busscans. „Dokumentiert“ bedeutet noch nicht „an der Anlage getestet“.

## Berichte

- [Janitza UMG 604-PRO und 103-CBM](JANITZA_REVIEW.md)
- [Plexlog PL500+](PLEXLOG_REVIEW.md)
- [Solis/BSE, Sungrow und Solarman](INVERTER_REVIEW.md)
- [Modbus, Eastron und Shelly/MQTT](TRANSPORT_AND_METERING_REVIEW.md)

## Wichtigste Ergebnisse

| Verbindung | Dokumentenbefund | Konsequenz |
|---|---|---|
| 604-PRO → RS485 → 103-CBM | Gatewayzugriff offiziell beschrieben; Nutzer bestätigt diese Busführung | Eine Gatewayverbindung, getrennte Zielgeräte/Unit-IDs und Profile |
| Plexlog OpenGateway V2 | Einheitliche Messmodelle | Kein automatisches Durchreichen beliebiger Originalregister |
| Plexlog ThirdPartyClient | Wirk-/Blindleistungsvorgaben als Rückmeldungen und marktbasierte Abregelung dokumentiert | Eigenes Profil und installierte Koexistenz prüfen, nicht mit DV-Port verwechseln |
| Solis S6/BSE | Solis-Hybridprotokoll vorhanden, BSE-Firmwarekompatibilität noch offen | Identifizieren statt aus Umlabelung Register abzuleiten |
| Sungrow Hybrid/String | Unterschiedliche Ports und Einschränkungen paralleler Kommunikation | Modell-/Firmware-/Loggerprofil, kein universeller zusätzlicher RS485-Zugang |
| Solarman v5 | Eigener Loggertransport | Passende Loggerfamilie plus WR-Registerprofil erforderlich |
| Eastron/Shelly | Messwerte dokumentiert, Aktorfähigkeiten modellabhängig | Messung und Schalten separat prüfen; keine erfundene Regelfunktion |

## Referenzstruktur, vom Nutzer bestätigt

```text
Energiemanager
└── Ethernet → UMG 604-PRO
    ├── Eigene 604-Messwerte
    └── RS485 / Modbus RTU
        ├── UMG 103-CBM, Zieladresse noch zu erfassen
        └── UMG 103-CBM, andere Zieladresse noch zu erfassen
```

Eigene IP der CBM ist nicht erforderlich. Betriebsmodus, Gatewayeigenadresse und Slaveadressen sind noch nicht ausgelesen. „Gateway“ ist keine pauschale Anweisung, Parameter 203 auf 2 zu setzen: Janitza bezeichnet auch den Mastermodus als Gateway; Details im Fachbericht.

## Verbindlicher Adapterentwurf

```text
Verbindung / Gateway / gemeinsam genutzter Bus
└── Zielgerät und belegtes Modell-/Firmwareprofil
    ├── Messkanäle → Messrollen → Anlage
    └── Steuerfähigkeiten → Zuständigkeit → gesonderte Freigabe
```

Für jede Größe Quelle, Mess-/Abfragezeit, Einheit, Vorzeichen, Dekodierung und Verfügbarkeit führen. Gleiche Messung direkt und über Gateway nicht doppelt verwenden. Ein Zielgerät kann fehlen, obwohl das Gateway erreichbar bleibt. Abfragen pro serieller Ressource koordinieren; ein physischer RTU-Master. Erfolgreiche Kommunikation beweist weder frische Messwerte noch ausgeführte Sollwerte.

## Nächste Schritte

1. Hersteller-/Firmwareprofile mit Nachweisen und unterstützten Lesefeldern definieren.
2. Gemeinsamen Verbindungsmanager und TCP→RTU-Zieladressierung simuliert prüfen.
3. Janitza-Eigenmessung und zwei getrennte CBM-Ziele einschließlich Teil-Ausfall testen.
4. Plexlog-Messmodell und Fernwirk-Rückmeldungen getrennt normalisieren; Einheiten und wirksame externe Grenzen nicht vermischen.
5. Modell-/Logger-/Firmwarekennung, aktive Profile und bestehende Reglerzuständigkeiten später lesend erfassen. Keine laufende Kommunikation ungeprüft umstellen.
6. Erst danach konkrete Steuerprofile und geräteabhängige Rückfälle abstimmen. Freigabe für aktiven Betrieb steht weiter aus.
