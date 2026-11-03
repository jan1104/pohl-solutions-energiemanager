# Bedienkonzept und fachlicher Aufbau

Stand: 03.11.2026. Überarbeiteter Entwurf auf Grundlage der bestätigten Anforderungen. Beschreibt das Zielprodukt, nicht den bereits implementierten Funktionsumfang. Offene Regeln stehen in REQUIREMENTS.md.

## Navigation

Oben immer sichtbar: Anlagenwahl „Alle Anlagen / Halle 1 / Halle 2“, Betriebsstatus, Hinweise. Einrichtungsassistent bei leerer Installation. Sieben Hauptpunkte; Detailseiten als Reiter statt dauernd aufgeklapptem Menü.

```text
Pohl Solutions Energiemanager
├── Übersicht
│   ├── Energieflüsse und Livewerte
│   ├── Aktueller Betrieb und nächste Aktionen
│   ├── Heutige Energie, Kosten und Erlöse
│   └── Hinweise und Datenqualität
├── Anlagen und Geräte
│   ├── Anlagenübersicht / Anlage hinzufügen
│   ├── Gewählte Anlage
│   │   ├── Aufbau und Netzanschluss
│   │   ├── Geräte und Messstellen
│   │   ├── PV-Felder und Ausrichtung
│   │   └── Anlagenangaben und Grenzen
│   ├── Gerät hinzufügen
│   │   ├── Suchen
│   │   ├── Manuell verbinden
│   │   └── Aus Home Assistant übernehmen
│   └── Gerätedetails
│       ├── Übersicht und Livewerte
│       ├── Verbindung und Erkennung
│       ├── Messkanäle und Zuordnung
│       ├── Fähigkeiten und technische Grenzen
│       └── Diagnose
├── Planung
│   ├── Zeitplan und erwarteter SOC
│   ├── PV-, Last- und Preisprognosen
│   ├── Gründe für Entscheidungen
│   └── Szenarien vergleichen
├── Betriebsregeln
│   ├── Strategie und Vorlagen
│   ├── Prioritäten und erlaubte Energiequellen
│   ├── Speicherreserven
│   ├── Verbraucherziele
│   ├── Manuelle Vorgaben / externe Wünsche
│   └── Automatik und Gerätefreigaben
├── Tarife und Kosten
│   ├── Bezugstarif und Preisquelle
│   ├── Einspeisetarif und Preisquelle
│   ├── Speicher- und Anlagenkosten
│   └── Annahmen und Vollständigkeit
├── Auswertung
│   ├── Energie, Eigenverbrauch und Autarkie
│   ├── Kosten und Erlöse
│   ├── Speicher und Verbraucher
│   ├── Plan / Prognose / Ist
│   └── Berichte und Export
└── Einstellungen
    ├── Gemeinsame Verbindungen und Zugangsdaten
    ├── Prognosedienste
    ├── Home Assistant / MQTT / Node-RED
    ├── Datenhaltung und Sicherung
    ├── Systemdiagnose und Ereignisse
    └── Version und Aktualisierungen
```

Die Anlagenwahl filtert alle fachlichen Seiten. „Alle Anlagen“ zeigt Vergleiche und Summen, aber keine gemeinsame elektrische Bilanz über getrennte Netzanschlüsse. Änderungen gelten für eine ausdrücklich benannte Anlage bzw. Gerätegruppe. Gemeinsame Einstellungen und übergreifende Messgeräte kennzeichnen wir gesondert.

## Fachliche Hierarchie

```text
Installation
├── Anlage A: eigener Netzanschluss, Tarif, Bilanz und Plan
│   ├── Netz- und Hausmessung (dreiphasige Gesamtbilanz)
│   ├── PV-Felder → Prognose, ohne doppelte Erzeugungszählung
│   ├── Wechselrichter A (ein- oder dreiphasig)
│   │   └── Batterieanschluss / Batteriegruppe → Türme / Module
│   ├── Wechselrichter B → eigene Batteriegruppe(n)
│   └── Verbraucher → Messung, Schaltfreigabe, optional Leistungsvorgabe
├── Anlage B: davon getrennte Bilanz und Planung
└── Physische Geräte und Verbindungen
    └── Messkanäle → eindeutig zugeordnete Messrollen in A oder B
```

Jede Batterie gehört zu einem Wechselrichter. Mehrere Türme an einem WR ergeben nicht mehrere unabhängig regelbare Wechselrichter. SOC und Leistung nur entsprechend der tatsächlich verfügbaren Messung/Regelung trennen; gemeinsame WR-Grenzen zusätzlich zu Batteriegrenzen berücksichtigen. Einphasigen WR der tatsächlichen Anschlussphase zuordnen.

Physische Messgeräte nur einmal anlegen. Messkanäle dürfen unterschiedliche Einzelverbraucher bzw. Anlagen messen, wenn die Hardware/Verdrahtung dies tatsächlich abbildet. Dreiphasige Hausmessung gruppiert alle drei Phasen am selben Netzanschluss. Kanalnummer und Anschlussphase getrennt speichern. Physische Verdrahtung nicht aus einer Softwarezuordnung ableiten.

Ein Messwert hat Rolle, Einheit, Vorzeichen, Messzeit, Quelle und Qualität. Eine primäre Bilanzquelle auswählen; zusätzliche Zähler dienen Kontrolle oder Untergliederung. Unterzähler werden nicht nochmals auf den gemessenen Gesamtverbrauch addiert. Summen über verschiedene Anlagen nur mit passender zeitlicher Abdeckung bilden.

## Einrichtung

1. Anlage benennen und Netzanschluss festlegen.
2. Einfache Vorlage mit einem WR und Batterie oder vorhandene Konfiguration wählen.
3. Geräte suchen/manuell anbinden/aus HA auswählen; Verbindungen und Profile überprüfen.
4. Messrollen zuordnen: Netz, PV, Haus, Speicher, Zweig oder Einzelverbraucher. Hauslast direkt messen oder aus vollständiger Bilanz ableiten.
5. Batterien dem WR und ggf. dokumentierten Batterieanschluss zuordnen; Kapazität, SOC-Fenster und belegte Grenzen prüfen.
6. Tarife und Prognosen auswählen; fehlende Bestandteile sichtbar lassen.
7. Strategie und Reserven einstellen, weitere Geräte optional ergänzen.
8. Livebilanz und Beispielplan prüfen; Steuerfunktionen im selben Ablauf erklären, aber später gesondert aktivieren.

Fehlende optionale Geräte verhindern nicht den Einstieg. Fehlende entscheidende Eingänge verhindern einen scheinbar gültigen Plan bzw. eine ungeprüfte Steuerung. Es muss erkennbar sein, welche Funktion bereits verfügbar ist: verbunden, Messung geprüft, planbar, steuerfähig, Automatik freigegeben. Demo-/Szenariowerte klar kennzeichnen.

## Geräte und Suche

- Modbus TCP, RTU/RS485, Solarman v5 und MQTT als getrennte Transportwege; gerätespezifische Profile für Werte und Befehle.
- Netzwerkbereich/Verbindung auswählen, begrenzt suchen, Funde mit verfügbaren IP-/Hostnamen und Erkennungsgrund anzeigen, anschließend geführt zuordnen.
- MQTT über eingetragenen Broker; unbekannte Topics benötigen Mapping. Serielle Geräte über gewählten Port/Gateway und passende Parameter, nicht über eine IP-Suche erwarten.
- Unklare Profile bleiben unklar; kein Raten von Registern oder Schreiben zur Erkennung. Manuelle Einrichtung bleibt verfügbar.
- Messung, Ein/Aus und stufenlose Regelung als separate Fähigkeiten. Bestehender Heizstab: HA-Freigabe, interne Regelung, Shelly-Messung. Diese drei Zuordnungen dürfen ein logisches Verbrauchergerät bilden, ohne fiktive Leistungsregelung anzubieten.
- Erst belegte Modelle und Funktionen anbieten. Transportunterstützung ist keine universelle Geräteunterstützung.

## Planung und Betriebsregeln

- Viertelstundenplan mit Verlusten, getrennten tatsächlichen Bezug-/Einspeisepreisen, Verschleiß, SOC und Leistungslimits. Reserve als Randbedingung, nicht als eigene konkurrierende Strategie.
- Wirtschaftlich oder wenig Netzbezug als Ziel; genaue Gewichtung/Autarkiemehrkosten noch offen. Individuelle Regeln müssen Priorität, Gültigkeit und Konfliktverhalten besitzen, keine unbegrenzte Skriptlogik im einfachen Assistenten.
- Prioritäten und zulässige Quellen je Gerät einstellen. Unmögliche Kombinationen erklären, nicht stillschweigend überschreiben.
- Mehrere Speicher gemeinsam planen, ohne unnötiges gegenseitiges Laden; Energie verschiedener Netzanschlüsse nicht verrechnen.
- Verbraucher nach tatsächlichen Fähigkeiten planen. Ein/Aus-Lasten sind nicht beliebig teilbare Leistung; intern geregelte Geräte benötigen Messrückmeldung. Bereits gemessene Verbraucher nicht erneut zur Prognose addieren.
- Nutzer sieht warum, für welchen Zeitraum und aufgrund welcher Daten geladen/entladen/geschaltet werden soll.
- Wirtschaftlichkeitsplan und schnelle Ist-Nachführung trennen. Neues Szenario bei relevanten Abweichungen, begrenzte Berechnungsfrequenz und keine parallelen widersprüchlichen Pläne. Pi-5-Ressourcenbedarf nachweisen.
- Endenergieziele vermeiden sowohl künstliches Festhalten des Anfangs-SOC als auch Leeren am Horizontende. Kleine Leistungen müssen trotz Näherungsverfahren berücksichtigt werden. Beide bekannten Defizite vor Regelbetrieb beheben.
- Herkunft „gespeicherte PV“ benötigt eine transparente rechnerische Bilanz; SOC allein liefert keinen Nachweis. Physische Netzbilanz und Herkunftszuweisung unterscheiden.
- Gerät-/Anschluss-/Schutzgrenzen begrenzen jede Regel. Notstromreserve ersetzt keine vorhandene Notstromfähigkeit. Geräteabhängiger Rückfall sowie Vorrang manueller/externer Wünsche bleiben bis zur konkreten Abstimmung offen.

## Tarife, Kosten und Auswertung

- Tarife enthalten ihre eigene Preisquelle, Einheit, Auf-/Abschläge und Vollständigkeitsstatus. Keine zweite unabhängige Tarifkonfiguration unter Einstellungen.
- Gemeinsame Anbieterzugänge unter Einstellungen; Tarifzuordnung je Anlage, Geräteeinstellungen am Gerät. Andere Ansichten verlinken diese Stellen statt Kopien zu bearbeiten.
- Investitionsumlage als Auswertung von marginalem Entscheidungsverschleiß trennen. Verluste und entgangene Erlöse jeweils einmal berücksichtigen.
- Tatsächliche Kosten nur bei geeigneten zeitlich zugeordneten Mess-/Tarifdaten berechnen; Börsenpreisszenarien nicht als tatsächlichen Gewinn anzeigen.
- Einsparungen sind ein Vergleich mit offengelegter Baseline und Restenergiebehandlung, kein unmittelbar gemessener Zählerwert.
- Energie, Kosten, Zeitraum und Datenabdeckung gemeinsam anzeigen. Prognose und Ist optisch unterscheiden; fehlende Daten nicht als Null ausgeben.

## Einfache Bedienung und Prüfmaßstab

- Sieben Hauptpunkte, wenige Reiter je Seite; keine Oberfläche voller Registeradressen. Expertenfelder erst bei Bedarf.
- Einzelanlagenansicht als Standard beim Einstieg; Gesamtübersicht, sobald mehrere Anlagen existieren. Klare Namen statt Protokollbezeichnungen.
- Änderungen zeigen betroffene Anlage/Geräte und Konsequenzen; Werte auf Einheit, Widersprüche und Vollständigkeit prüfen. Änderungen an zugeordneten Geräten nicht heimlich laufend auf eine andere Anlage übertragen.
- Konfiguration und Betriebsfreigabe trennen; Entwürfe dürfen unvollständig sein, aktiver Betrieb benötigt validierte Voraussetzungen.
- Status nicht allein über Farbe vermitteln. Tastaturbedienung, lesbare Werte, verständliche Fehler und mobile Nutzung prüfen.
- Gemeinsame Diagnose mit Ereignisquelle, Zeit und hilfreicher Handlung; keine Zugangsdaten im Export/Log.
- Erst mit realistischen Bedienaufgaben prüfen: erste Anlage, zweiter Speicher, zweite Halle, geteilter Messkanal, Heizstab, falsches Vorzeichen, fehlende Preise und Messausfall. Ein Entwurf allein beweist keine gute Bedienbarkeit.

## Noch zu entscheiden

Konkrete Gerätemodelle/Firmware/Register; zulässiger Rückfall; manueller/externer Vorrang; Vertragsformeln; genaue dynamische Reserve-/Endenergiepolitik; Prognoseanbieter; Pi-5-RAM und Laufzeitbudget; zielabhängige Verbraucherregeln etwa E-Auto-Abfahrtszeit. Diese Punkte verhindern den Entwurf nicht, müssen aber vor betroffener aktiver Funktion geklärt sein.
