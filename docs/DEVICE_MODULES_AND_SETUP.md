# Bedienabläufe und Gerätebausteine

Stand: 04.11.2026. Präzisierter Produkt-/Implementierungsentwurf, noch keine fertige Modulverwaltung oder neue Bedienoberfläche. Ergänzt NAVIGATION_AND_PRODUCT_DESIGN.md und SYSTEM_LOGIC.md. Maßgeblich für weitere Umsetzung: Nutzer richtet Funktionen ein; Programmcode und technische Details bleiben im Hintergrund.

## Drei unabhängige Bausteine statt eines Sonderfalls je Gerät

1. **Fachlicher Gerätebaustein:** Messgerät, PV, Speicher, Wärmeverbraucher, Ladestation oder Anlagenregler. Legt benötigte Werte, Bedienfelder, Regeln und Planungsbeitrag fest. Ein Messgerät liefert Daten und wird dadurch nicht selbst zum steuerbaren Verbraucher.
2. **Geräteprofil:** Hersteller/Modell/Firmware mit belegten Kanälen und Fähigkeiten, Einheiten, Grenzen und dokumentierter Dekodierung. Ein Hybrid-WR kann PV- und Speicherfunktionen bereitstellen, bleibt aber ein physisches Gerät mit gemeinsamen Anschluss-/Leistungsgrenzen.
3. **Anbindung:** Modbus TCP, RS485, Gateway, Solarman, MQTT oder HA. Gemeinsame Verbindungen einmal anlegen; eine Funktion verweist auf Kanal/Aktion/Verbindung. Ein/Aus und Messung können unterschiedliche Anbindungen nutzen.

Die Oberfläche bietet „Gerät hinzufügen“ und verständliche Kategorien. Kein zusätzlicher HACS-Download je Heizstab-/Messgerätekategorie. Intern getrennte, registrierbare Module in derselben Integration; spätere Paketaufteilung nur bei tatsächlichem Nutzen. Ein Modul aktiviert weder Gerätesuche noch Steuerung durch bloßes Laden.

Zielstruktur im Code, ausdrücklich noch nicht vollständig angelegt:

```text
core/                    Projekt, Messung, Bilanz, Kosten, Planung
device_modules/          Fachliche Gerätefunktionen und Einrichtungsdefinitionen
  metering/              Zähler, Phasen-/Gesamtmessung und Messrollen
  pv/                    PV-Geräte, Felder und Prognosezuordnung
  storage/               Speicher-WR, Batterien, Reserven und Herkunft
  heating/               Wärmeverbraucher und gemeinsame Messgruppen
  ev_charging/           Ladepunkte und belegte Ladefähigkeiten
  plant_controller/      Gateway/Logger und externe Vorgaben
adapters/profiles/       Nachgewiesene Geräteprofile
adapters/transports/     Wiederverwendbare Kommunikation
frontend/                Darstellung aus gemeinsamen Formular-/Fähigkeitsdefinitionen
```

## Einrichtungsablauf

| Schritt | Nutzer gibt an | Energiemanager ermittelt/prüft | Ergebnis |
| --- | --- | --- | --- |
| 1. Energiemanager | Nur Projektname | Bestehendes Projekt erhalten | Sofort bedienbares leeres Projekt |
| 2. Standort/Bereich | Name und tatsächlichen Netzanschluss wählen/neu anlegen | Gemeinsame Grenze von räumlicher Gruppe trennen | Benannte Struktur, noch keine erfundenen Geräte |
| 3. Gerät hinzufügen | Kategorie; „Suchen“, „Manuell“ oder „Aus HA“ | Bereits angelegte Geräte und Verbindungen vorschlagen | Ein physisches Gerät, keine Dublette |
| 4. Anbindung | Bestehende Verbindung auswählen oder einmal erstellen, Geräteadresse bei Bedarf | Nur gezielt freigegebene Leseprüfung, belegte Identität/Kanäle zeigen | Lesende Verbindung geprüft oder konkrete Lücke sichtbar |
| 5. Messort/Funktion | Was wird gemessen, wo angeschlossen, welche Geräte enthalten? | Einheit, Richtung, Phasen, Überschneidungen und fehlende Quellen prüfen | Nachvollziehbare Mess-/Funktionszuordnung |
| 6. Fachliche Angaben | Nur nicht belegbar auslesbare Parameter und gewünschte Grenzen | Verifizierte Gerätedaten vorbefüllen, Herkunft sichtbar | Gerätebaustein konfiguriert |
| 7. Regeln/Preise/Prognose | Ziel, Quellen und erlaubte Nutzung wählen | Vollständigkeit je Funktion prüfen | Datenansicht und/oder Plan verfügbar |
| 8. Prüfen | Aufbau, Bilanz und Plan ansehen; später separat Steuerung freigeben | Fehlende Voraussetzungen erklären | Kein ungeprüfter Übergang zur Automatik |

Schritte sind fortsetzbar. Projektverwaltung braucht keine Sensoren, Preise oder SOC. Fehlende Tarifdaten blockieren die wirtschaftliche Planung, nicht das Anlegen eines Zählers. Unbekanntes Geräteprofil erlaubt eine manuelle Lesekonfiguration im Expertenbereich, aber keine erfundenen Fähigkeiten. Die spätere Freigabe von Aktoren hängt zusätzlich von tatsächlichen Geräte-/Ausfallprüfungen ab.

## Wer trägt welchen Wert ein, und wo?

| Information | Einziger Bearbeitungsort | Automatisch nur wenn belegt | Nutzerentscheidung |
| --- | --- | --- | --- |
| IP/USB/Broker/Zugang | Einstellungen → Verbindungen | Suchvorschlag oder bestehende Verbindung | Richtige Verbindung bestätigen; Geheimnis separat halten |
| Unit-ID/Profil | Gerät → Anbindung | Gezielte Erkennung mit Nachweis | Zieladresse/Modell bestätigen; nie raten |
| Messkanäle/Einheiten | Gerät → Messung | Unterstütztes Profil/Quellenmetadaten | Quelle und ggf. Skalierung bestätigen |
| Messrolle/Einbauort | Gerät → Messung | Höchstens Vorschläge aus vorhandenem Projekt | Netz/Haus/PV/Nettozweig/Verbraucher und Abdeckung bestimmen |
| Momentanleistung/SOC | Gerät → Werte, nur Anzeige | Frischer Messkanal mit Messzeit/Qualität | Ersatz nicht als Echtmessung eingeben; Simulation separat |
| Batterie-Kapazität/Grenzen | Speicher-WR → Batterien | BMS/Profil, falls nachgewiesen verfügbar | Tatsächliche Installation und betriebliche Grenzen bestätigen |
| Reserve/erlaubte Quellen | Betriebsregeln → Gerät | Keine automatische Betriebsfreigabe | Gewünschte Nutzung und Prioritäten |
| Bezug/Einspeisung | Tarife und Kosten → Netzanschluss | Gewählte Preisquelle, Originaleinheit erhalten | Vertragsaufschläge/-abzüge und Freigaben |
| Kosten/Lebensdauer | Tarife und Kosten → Gerätebezug | Nur belegte Profilvorschläge mit Bedingungen | Kaufpreis, Kostenansatz und Annahmen bestätigen |
| PV-Felder | PV-Gerät → Prognose | Auslesbare Leistung nur als Vorschlag | Ausrichtung/Neigung/Leistung bestätigen, falls benötigt |
| Prognoseanbieter | Planung → Datenquellen | Vorhandene kompatible HA-Prognose vorschlagen | Quelle und richtige Zuordnung wählen |

Andere Seiten verlinken auf diesen Bearbeitungsort. Eine Reserve wird nicht unabhängig im Geräteformular und in Betriebsregeln doppelt geführt. Gleiches gilt für Tarife und Verbindungsparameter. Gerätedaten und vom Nutzer gewünschte Werte getrennt speichern: Das effektive Limit ergibt sich aus den geltenden technischen und betrieblichen Grenzen, nicht durch Überschreiben des BMS-Werts.

Herkunft an jedem Wert: „gemessen“, „berechnet“, „aus Profil vorgeschlagen“ oder „manuell bestätigt“; Quelle, Zeitpunkt und ggf. Formel anzeigen. Automatisch gelesene Werte dürfen vom Nutzer bestätigte Konfiguration nicht stillschweigend ersetzen. Verändert sich ein ausgelesenes Gerätekennzeichen, ist die Zuordnung erneut zu prüfen.

## Gerätebausteine konkret

| Baustein | Wenige Angaben im einfachen Ablauf | Quellen/Fähigkeiten | Was daraus entsteht |
| --- | --- | --- | --- |
| Messgerät | Name, Messort/Rolle, Kanalgruppe, enthaltene Geräte | Leistung, optionale Energie-/Phasenwerte | Bilanzquelle oder Vergleichsmessung; kein eigener Stellwert |
| PV | Physisches Gerät, Messquelle, optional Felder | Erzeugungsleistung und passende Prognosequelle | Prognosebeitrag, keine Verdopplung von Hybrid-/Gatewaywerten |
| Speicher | WR wählen, Batteriegruppe zuordnen, Kapazität/SOC-Quelle und bestätigte Grenzen | SOC, Lade-/Entladeleistung, technische Grenzen; spätere Sollwertfähigkeit getrennt | Speicherzustand und Planungsressource mit gemeinsamer WR-Grenze |
| Heizstab/Wärme | Name, Schaltquelle und Rückmeldung, Messquelle/Messgruppe, erlaubte Quellen/Priorität | Ein/Aus; Leistungsvorgabe nur wenn tatsächlich vorhanden | Nicht beliebig teilbare Last bzw. belegter Leistungsregler |
| Ladestation | Ladepunkt, Messung, bestätigte Steuerfähigkeit und Netzzuordnung | Istleistung, optional Status/Ladestrom/Phasen | Passendes Lastmodell; Zeit-/Energieziele erst bei unterstützten Angaben |
| Anlagenregler/Logger | Identität, Verbindung, Rollen und gelieferte Werte/Vorgaben | Gatewaymessungen, dokumentierte externe Vorgaben | Herkunft/Konfliktprüfung; kein automatischer Wechsel der Regelzuständigkeit |

Vorhandener WR ohne Batterie bietet zunächst PV-Funktion, keinen nutzbaren Speicher. Messung, Schalten und Leistungsregelung sind einzelne Fähigkeiten, keine zwangsläufige Kombination. Ein physischer Hybrid-WR erhält mehrere Funktionen am selben Geräteobjekt, keine zwei vermeintlich unabhängigen Geräte. Batterie und Türme bleiben unter dem tatsächlichen WR; gemeinsame Grenzen gelten zusätzlich.

### Beispiel Wärme mit separater Messung

Vier dreiphasige intern geregelte Heizstäbe erhalten je eine belegte Freigabe-/Rückmeldezuordnung, beispielsweise HA oder später Modbus/MQTT. Ein gemeinsamer Shelly-Zähler wird einmal als physisches Messgerät angelegt und misst die Wärmegruppe insgesamt. Die vier Verbraucher verweisen auf diese Gruppe; sie bekommen nicht jeweils deren vollständige Leistung als eigene Messung. Die drei Phasen werden nicht zu drei Heizstäben umgedeutet. Einzel-Istverbrauch bleibt unbekannt, solange keine Einzelmessung vorhanden ist. Eine eingeschaltete Freigabe bedeutet noch nicht, dass ein intern geregelter Heizstab tatsächlich heizt. Ohne eigene Temperatur-/Bedarfsmessung wird keine garantierte Wärmebereitstellung behauptet. Nennleistung ist nur eine bestätigte Grenze/Annahme, keine Einzel-Istmessung. Ohne belegte externe Leistungsregelung zeigt die Bedienung Ein/Aus, keinen scheinbar funktionierenden kW-Schieberegler.

## Modulvertrag und Zustände

Jeder Gerätebaustein muss dieselben Grundaufgaben erfüllen:

- Stabile Modulkennung, Version, unterstützte Fähigkeiten und Datenanforderungen deklarieren.
- Formularfelder mit Einheit, Herkunft, Pflichtbedingung und verständlicher Hilfe beschreiben. Backend und Oberfläche müssen dieselben Definitionen/Validierungsregeln verwenden; keine doppelte fachliche Logik.
- Eingaben lokal validieren und fehlende Zuordnungen als strukturierte Hinweise liefern. Keine Verbindung als Seiteneffekt dieser Prüfung.
- Messwert-/Aktionsreferenzen auf gemeinsame Geräte/Verbindungen verwenden. Vorhandene Geräte auswählen und nur fehlende Quellen ergänzen.
- Einen normalisierten Beitrag für Bilanz/Prognose/Planer liefern, inklusive Datenqualität und Grenzen; weder eigenen Optimierer noch eigenen parallelen Regler starten.
- Konfiguration versioniert migrieren/exportieren. Geheimnisse nur referenzieren; keine Freigaben auf fremde Hardware übertragen.

Status je Fähigkeit statt eines pauschalen grünen Gerätestatus: `Entwurf`, `Lesen geprüft`, `Daten gültig/ungültig`, `Planung vollständig/unvollständig`. `Steuerung unterstützt` und `Automatik freigegeben` sind getrennte Merkmale. Ein Ausfall macht nicht das gespeicherte Projekt ungültig; er begrenzt betroffene Bilanz-/Planfunktionen. Ausfallreaktionen für reale Aktoren bleiben gerätespezifisch zu klären.

Die zentrale Abhängigkeitslogik prüft, welche Funktion welche Quellen braucht. Hauslast direkt aus Messung oder aus vollständiger, nicht doppelt gezählter Bilanz; kein Automatismus „jeder Messwert ist Hausverbrauch“. Ein nicht verfügbarer Preis macht einen Preisplan unvollständig, nicht einen Messwert ungültig. Fehlender Einzelverbrauch einer gemeinsam gemessenen Wärmegruppe muss nicht deren zulässige Gesamtmessung verwerfen.

## Reihenfolge der Umsetzung und Abnahme

1. Gemeinsamen Modul-/Feld-/Fähigkeitsvertrag und Zuordnungsmodell implementieren, inklusive Migration des aktuellen Projektformats. Noch keine weiteren parallelen Einzelformulare bauen.
2. Messgerätebaustein durchgängig: Quelle auswählen, Messort bestätigen, Qualität/Abdeckung sehen. Bestehende direkte Verbindung und HA-Quelle gleichwertig behandeln.
3. Speicher-/PV-Funktionen auf demselben Vertrag mit Batterien und gemeinsamen Grenzen ergänzen.
4. Wärmebaustein mit Ein/Aus und gemeinsamer Messgruppe umsetzen; spätere stufenlose Funktion nur mit belegtem Profil.
5. Ladestationen/Regler integrieren und Mehrgeräteplaner anschließen. Darstellung fehlender Voraussetzungen zuerst, keine vorgetäuschte Automatik.

Bedienabnahmen: leeres Projekt ohne Sensoren; vorhandenen Zähler wiederverwenden; zweites Gerät am selben Gateway; physischer Hybrid mit PV und Batterie; Wärmegruppe mit vier Schaltern/einer Gesamtmessung; fehlende Preise bei gültigen Messwerten; Vorzeichenfehler; ausgefallene Quelle; Export/Import ohne Gerätezugriff. Danach Desktop/Mobil/Tastatur prüfen. Der Entwurf allein ist noch kein Bedienbarkeitstest.
