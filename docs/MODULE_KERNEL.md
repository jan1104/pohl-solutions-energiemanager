# Grundmodul, Prognosen und Modulversionen

Stand: 04.11.2026. Die erste reine Laufzeitgrundlage ist in `core/modules.py` implementiert und separat getestet. Ab 0.5.0 sind Grundmodul, Konfigurationsspeicher und Projektverwaltung als tatsächliche Basisfunktionen in HA registriert und im Panel sichtbar. Allgemeine Modulverwaltung, konkrete Prognoseanbieter und unabhängige Aktualisierung bleiben weitere Schritte. Keine Live-Steuerung. Aktueller Testablauf: TESTING_0_5.md.

## Aufteilung des Produkts

```text
Grundmodul
├── Projekt, IDs, gemeinsame Dienste und Bedienrahmen
├── Modulregister, Versions-/Abhängigkeitsprüfung und Zustände
└── Gemeinsame Datenverträge und gezielte Funktionsaufrufe
    ├── Messung / Geräteanbindung
    ├── Prognosen: PV und Last, mit austauschbaren Quellen
    ├── Tarife und Kosten
    ├── Planung
    └── Gerätebausteine: Speicher, Wärme, Ladestationen, Anlagenregler
```

Fachmodule nutzen gemeinsame Dienste, statt für jeden Heizstab einen eigenen Zählerabruf, Preisabruf oder Planer zu starten. Herstellerprofile und Transporttreiber bleiben zusätzliche wiederverwendbare Bausteine. Die erste ausgelieferte Integrationsversion soll diese Module gemeinsam enthalten; keine Pflicht zu einem separaten HACS-Download je Funktion.

Die Prognose ist ein eigenständiges Fachmodul, nicht fest im Speicher- oder Heizstabcode eingebaut. Es kann HA-Prognosen oder direkte Anbieter nutzen; PV und Last sowie ihre Herkunft/Qualität bleiben unterscheidbar. Ein Prognoseanbieter wird dadurch austauschbar, ohne die Gerätezuordnung neu einzurichten. Mehrere Anbieterinstanzen brauchen getrennte Identitäten und Zustände; deren konkrete Umsetzung steht noch aus.

## Implementierter Kernelvertrag

- `ModuleManifest`: stabile ID, Anzeigename, eigene numerische Modulversion, benötigte Kernel-API-Hauptversion und unveränderliche Abhängigkeiten.
- `ModuleDependency`: erforderliches Modul mit inklusive Mindestversion und exklusiver Obergrenze. Versionsvergleich ist numerisch, etwa 1.10.0 größer als 1.2.0. Unterstützt werden vorerst stabile `major.minor.patch`-Versionen, keine Vorabversionsetiketten.
- `ModuleRegistry.register`: ausdrücklich übergebenen vertrauenswürdigen Async-Handler registrieren, ohne ihn auszuführen. Kein Download, Dateiscan, dynamischer Import, Gerätezugriff oder paralleles Ersetzen derselben ID. Höchstens 128 registrierte Module.
- `states`: verfügbare, deaktivierte, fehlgeschlagene oder wegen Abhängigkeit/API/Version/Kreis gesperrte Module und konkrete Gründe. Fehlerhafte Abhängigkeiten sperren nur den betroffenen Teilgraphen.
- `async_call`: einzelne Module asynchron aufrufen; pro Modul serialisierte Aufrufe, unabhängige Module können parallel fortfahren. Aufrufzeit einschließlich Warteschlange ist begrenzt. Fehlertexte übernehmen keine vertraulichen Handler-Payloads.
- `set_enabled` und `reset_failure`: ausdrückliche Zustandsänderung/Wiederfreigabe. Kein automatischer Wiederholungssturm. Die Fehlerquittierung schaltet nicht zusätzlich vom Nutzer deaktivierte Module ein.

Wenn sich ein benötigtes Modul während eines laufenden oder wartenden Aufrufs ändert, wird das überholte Ergebnis verworfen. Auch ein verspäteter Fehler oder Timeout dieses alten Aufrufs darf den inzwischen wieder verfügbaren Zustand nicht erneut sperren. Ein Wartezeitlimit vor Erlangen der Modulwarteschlange gilt als beschäftigter Aufruf, nicht als Nachweis eines kaputten Handlers. Externer Taskabbruch beim Herunterfahren wird nicht als Modulfehler ausgegeben.

`ready` bedeutet hier nur: Versionen/Abhängigkeiten erlauben den Aufruf. Es beweist weder vollständige Konfiguration noch frische Messwerte, Prognosegüte oder Steuerfreigabe. Diese Fachprüfungen bleiben eigenständige Verträge. Der erste Kernel führt noch keine Start-/Stop-Hooks für lang laufende Gerätetreiber aus und speichert keine Ergebnis-Caches. Deren Eigentum, Bereinigung und Datenalter müssen vor HA-Anbindung ergänzt werden.

## Was bei einem Ausfall weiterläuft

| Beispiel | Bleibt nutzbar | Betroffene Funktion |
| --- | --- | --- |
| Prognosemodul schlägt fehl | Projektverwaltung, unabhängige Messwerterfassung, Diagnose | Automatische Planung mit erforderlicher Prognose wird gesperrt/ungültig |
| Preisquelle fehlt | Messwerte und Projekt | Wirtschaftlicher Preisplan bleibt unvollständig |
| Ein Geräteadapter fällt aus | Andere unabhängige Geräte/Funktionen | Zugehörige Messungen und davon abhängige Bilanzen/Pläne |
| Neuer Modulstand passt nicht zur API | Andere kompatible Module | Nur inkompatibles Modul und erforderliche Abnehmer |

Diese Tabelle beschreibt die künftige Produktverdrahtung. Kerneltests belegen die entsprechende Fehler-/Abhängigkeitsbehandlung mit synthetischen Handlern, zusätzlich werden Basis-Speicherfehler und deren abhängige Projektfunktion im HA-Laufzeittest geprüft; allgemeine Fachmodulisolation fehlt noch. Ein bewusstes Szenario mit manuell gelieferten Prognosen darf einen eigenen, ausdrücklich gekennzeichneten Weg haben; es wird bei fehlenden Echtdaten nicht automatisch als Ersatz aktiviert. Bestehende Pläne dürfen bei Wegfall einer Quelle nicht ohne Alters-/Gültigkeitsprüfung weiter als aktuell gelten.

## Versionen und Weiterentwicklung

1. **Produkt-/HACS-Version:** identifiziert ein gemeinsam geprüftes Installationspaket, ab dem Grundmodul-Testpaket 0.5.0.
2. **Modulversion:** identifiziert den konkreten Implementierungsstand eines Fachmoduls.
3. **Schnittstellenversion:** bestimmt, welche Daten und Aufrufe kompatibel sind; im ersten Kernel API-Hauptversion 1. Konkrete Prognose-/Mess-/Plan-Datenverträge müssen zusätzlich festgelegt werden.
4. **Konfigurationsschema:** beschreibt gespeicherte Daten. Es ist nicht dieselbe Versionsnummer; Migration vor Versionswechsel ist ausdrücklich zu entwickeln. Bestehendes Projektformat 1 wird durch bloßes Hinzufügen des Kernels nicht verändert.

Ein neuer Prognosestand soll zuerst gegen denselben Datenvertrag, synthetische Fälle und historische Rücktests geprüft werden. Erst ein passendes, gemeinsam getestetes Paket wird zum Update angeboten. Ein Modulupdate darf Nutzerwerte, Gerätezuordnungen oder Freigaben nicht unbemerkt verändern. Im ersten Kernel ist pro ID genau eine aktive Version erlaubt; parallele Versionsverwaltung oder Austausch während eines laufenden Aufrufs sind nicht implementiert.

Getrennte Modulversionen bedeuten **noch kein unterbrechungsfreies Update** in HA. Module im selben Python-Prozess teilen dessen Laufzeit. Ein HA-Neustart kann weiterhin nötig sein. Wirklich unabhängig aktualisierbare Module benötigen später einen getrennten Dienst/Worker mit versioniertem Kommunikationsvertrag, Zustandsübergabe und geprüftem Wiederanlauf. Das darf nicht durch einfaches Nachladen von Pythondateien vorgetäuscht werden.

## Grenzen und nächste Schritte

Die Datenhaltung gehört ebenfalls zum Grundmodul. Eine gemeinsame, projekt-/modulbezogene SQLite-Konfigurationsablage ist nun separat implementiert; HA-Projektübernahme ist ab 0.5.0 angebunden; allgemeine Kontextinjektion und Historien folgen. Siehe [CENTRAL_STORAGE.md](CENTRAL_STORAGE.md). Modulregistrierung erzeugt bislang weiterhin keine automatischen Dateien oder Migrationen.

Async-Timeouts funktionieren nur kooperativ. CPU-blockierende Module, fremde gemeinsam veränderte Objekte oder Handler, die Abbruch ignorieren, können andere Arbeit im Prozess beeinträchtigen. Der Kernel ist keine Sicherheits- oder Prozessisolationsgrenze. Blockierende Berechnungen gehören später in geeignete Worker; Live-Aktoren sind keine freigegebenen Handler dieses Kernels.

Eine Registry gehört nach Beginn asynchroner Aufrufe zu genau einer Eventloop/Projektlaufzeit. Wiederverwendung derselben Async-Locks über verschiedene Eventloops ist nicht vorgesehen; bei neuer Laufzeit eine neue Registry anlegen.

Nächste zusammenhängende Schritte:

1. Versionierte Ein-/Ausgaben und Konfiguration für Messung, Prognose, Preise und Planung definieren; Formular-/Fähigkeitsdefinitionen aus DEVICE_MODULES_AND_SETUP.md damit verbinden.
2. Konkretes Prognosemodul zunächst als rein lesende/manuell gefütterte Quelle auslagern und gegen bestehende Prognosetests prüfen. Keine Prognosegüte erfinden.
3. Start/Stop, Cache-/Datenalter, Projektinstanzen und HA-Lebensdauer ergänzen; danach Status/Versionen im bestehenden Panel zeigen.
4. Gerätebausteine schrittweise über dieselben Verträge anbinden. Ausfall-, Migrations- und Updatefälle vor Freigabe testen.

18 neue Tests prüfen Versionsgrenzen, fehlende/zyklische Abhängigkeiten, unabhängige Fortführung, Fehlerquittierung, Nebenläufigkeit, Timeout/Abbruch und überholte Ergebnisse/Fehler. Keine unveränderte Betriebsfähigkeit bei beliebigem Pythonfehler behauptet.
