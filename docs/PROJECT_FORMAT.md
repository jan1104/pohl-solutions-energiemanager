# Projekte und vollständiger Konfigurationstransfer

Stand: 03.11.2026. Export/Import für Projektformat 1 ist mit Version 0.3 implementiert; siehe PROJECT_SCHEMA_V1.md und TESTING_0_3.md. Weitergehende Funktionen dieses Entwurfs (z.B. Migration zukünftiger Versionen, verschlüsselte Vollsicherung, Konfliktzusammenführung) sind noch offen. Der erste Stand ersetzt nach Prüfung ein Projekt; keine automatischen Gerätezugriffe.

## Umfang

Ein Projekt ist die oberste fachliche Konfigurationseinheit. Darunter liegen alle zugehörigen Anlagen, deren Netzanschlüsse/Tarife, Geräte und Batteriegruppen, Verbindungen/Gateways, Messkanäle, Zuordnungen, Ableitungsformeln, Prognosekonfiguration und Betriebsregeln. Gemeinsame Verbindungen/physische Messgeräte werden im Projekt einmal geführt und über stabile IDs referenziert.

```text
Projekt
├── Anlagen
│   ├── Halle 1 → eigener Netzanschluss, Bilanz und Plan
│   └── Halle 2 → eigener Netzanschluss, Bilanz und Plan
├── Geräte und Batteriezuordnungen
├── Verbindungen / Gateways / Zieladressen
├── Messkanäle / Messrollen / berechnete Werte
├── Tarif-, Prognose- und Kosteneinstellungen
└── Betriebsregeln / Prioritäten / Reserven
```

Ein gemeinsames Projekt verbindet getrennte Netzanschlüsse organisatorisch, nicht elektrisch. Kommunikationshierarchie, elektrische Topologie und Herkunft der Messwerte bleiben getrennte Beziehungen. Die letzte Chatklärung zur Herkunft ist als Grundlage umzusetzen: Hauptquelle je Bilanzgröße, Quellenvergleich statt Doppelzählung, Formel und Quellen für abgeleitete Größen anzeigen, Zirkelschlüsse ablehnen.

Die obige Darstellung zeigt den Fall getrennter Anschlüsse. Zusätzlich mehrere benannte Anlagen/Bereiche unter einem gemeinsamen Netzanschluss unterstützen: Der Anschluss bildet die gemeinsame Optimierungs-/Tarifgrenze, Bereiche die organisatorische Untergliederung. Netzanschlüsse und elektrische Zweige deshalb mit eigenen IDs exportieren und Bereichszuordnungen davon unabhängig erhalten. Ein Bereich darf aus seinem Namen allein keinen neuen Netzanschluss erzeugen. Einzubeziehen sind verschachtelte Nettozweigmessungen und aggregierte Verbrauchermessungen; siehe METERING_TOPOLOGY.md.

## Referenz für die weitere Entwicklung

Vincents Anlage dient als durchgängiger Fall vom Geräteanschluss bis zum Plan. Bestätigte Geräte/Verbindungen berücksichtigen: mehrere PV-WR, Speicher-WR mit zugehörigen Türmen, Janitza-Gateway mit 103-CBM-Untergeräten, Netz-/Haus-/Zweigmessung und bestehender Anlagenregler. Ungeklärte Modelle/Parameter bleiben unbekannt.

Zwei getrennte Artefakte führen:

- Privates reales Projekt lokal unter private/: tatsächliche Namen, Adressen, Identitäten und Zuordnungen; nie ungeprüft nach Git übernehmen.
- Anonymisiertes Referenzprojekt im Repository: gleiche fachliche Struktur mit neutralen Namen und ausdrücklich fiktiven Verbindungsangaben. Synthetische Messverläufe gesondert kennzeichnen. Keine realen Netzadressen oder privaten Originalunterlagen.

Der allgemeine Projektmechanismus darf weder Referenzgerätezahl noch Standort noch Batteriegröße fest einbauen. Zusätzlich mindestens eine abweichende einfache Anlage und zwei getrennte Netzanschlüsse als Testfälle verwenden, damit die Verallgemeinerung nachweisbar ist.

## Export – vorgeschlagener Datenvertrag

- Versioniertes, maschinenlesbares Konfigurationsdokument, zunächst JSON als Entwurf. Produkt-/Formatversion und stabile Objekt-IDs mitführen.
- Alle fachlichen Objekte und Referenzen zusammen exportieren. Geräteprofile mit eindeutiger Kennung/Version referenzieren; benutzerdefinierte Register-/Topiczuordnungen mitführen. Fehlende/unbekannte Profile beim Import anzeigen.
- Verbindungsangaben, Zieladressen und HA-Entitätszuordnungen gehören zur vollständigen privaten Konfiguration, müssen beim Wechsel auf ein anderes System neu geprüft werden können.
- Zugangsdaten nicht im Klartext in den normalen Export schreiben. Geheimnisreferenzen und Hinweise auf nachzutragende Zugangsdaten mitführen. Ob zusätzlich verschlüsselte Vollsicherung gewünscht ist, bleibt offen.
- Keine flüchtigen Livewerte, gerade laufenden Befehle oder ausstehenden Sollwertwarteschlangen als wiederherstellbare Konfiguration behandeln.
- Messhistorien und Berichte sind gesonderte optionale Datenpakete; ihr Umfang wurde noch nicht festgelegt. „Projekt exportieren“ muss den gewählten Umfang verständlich nennen.

## Import – vorgeschlagener Ablauf

1. Datei lokal einlesen; Format, Version, Größe, Feldtypen und Objektgrenzen prüfen. Importdaten sind Konfiguration, kein auszuführender Code.
2. Unterstützte Formatmigration vorbereiten; neuere/ungeeignete Versionen mit verständlicher Meldung ablehnen.
3. Vorschau: Anlagen/Geräte/Zuordnungen, fehlende Profile, Zugangsdaten und nicht vorhandene HA-/USB-Verweise zeigen. Import löst keine Netzwerkverbindung oder Gerätesuche aus.
4. Referenzen und Topologie prüfen: eindeutige IDs, gültige Batterie-WR-Zuordnung, Gatewayzieladressen, Hauptmessungen, phasenrichtige Rollen und keine Kreisabhängigkeit berechneter Werte.
5. Übernahme als separate Projektkopie anbieten. Wenn später Ersetzen/Zusammenführen angeboten wird, Änderungen und Konflikte vorher zeigen; bestehende Konfiguration nicht stillschweigend überschreiben. Exakte Konflikt-UX noch offen.
6. Gesamten Import atomar übernehmen oder vorherigen Stand erhalten. Ursprüngliche IDs intern erhalten bzw. bei Kopie konsistent umschlüsseln; alle Beziehungen müssen intakt bleiben.
7. Projekt als zu prüfende Konfiguration öffnen. Laufende manuelle Befehle oder frühere Aktorfreigaben nicht automatisch auf fremde Hardware übertragen. Verbindungen, Messbilanz und aktuelle Steuerzuständigkeit vor späterem Betrieb erneut prüfen.

## Abnahme

- Export → Import → Export erhält fachliche Inhalte und Beziehungen, abgesehen von ausdrücklich ausgewiesenen Kopie-/Versionsmetadaten.
- Referenzprojekt mit Gateway und mehreren Batteriegruppen sowie zwei getrennte Anlagen bestehen den Rundlauf.
- Fehlendes Profil, veränderte IP/USB/HA-Entität, doppelte IDs, verwaiste Batterie, ungültige Formel und inkompatible Version ergeben nachvollziehbare Ergebnisse.
- Ungültiger/abgebrochener Import lässt bestehendes Projekt unverändert.
- Kein Klartextgeheimnis im Standardexport; Import sendet keine Befehle und aktiviert keine alte Steuerwarteschlange.

## Noch offen

Verschlüsselte Vollsicherung einschließlich Zugangsdaten; optionale Historienmitnahme; mehrere gleichzeitig aktive Projekte in einer Installation; genaue Konfliktbedienung beim Ersetzen/Zusammenführen. Nicht mit bestätigter Mehranlagenfähigkeit innerhalb eines Projekts verwechseln.
