# Grundmodul, Prognosen und Modulversionen

## Ausdrückliches Lastprognose-Fachmodul — 24.11.2026

Seit 25.11.2026 enthält `tools/ha_smoke.py` zusätzlich einen Integrationsablauf für genau dieses Fachmodul: temporäres HA-Projekt, ausdrückliche BaseRuntime-Registrierung, gemeinsame Einstellungen und echter HA-Executor. Die Prüfung verwendet ausschließlich synthetische Lastbeobachtungen. Fehlerisolation, manuelle Fehlerquittierung, ausstehende Berechnung bei Projektänderung und Sperre nach Stop gehören zur Abnahme. Daraus entsteht keine automatische Aktivierung in der Integration.

`load_forecast_module.MANIFEST` beschreibt `load_forecast` 0.1.0, Kernel-API 1 und Abhängigkeiten zu Grundmodul/Speicher im Bereich 0.1.0 bis ausschließlich 0.2.0. `CONFIG_SCHEMA_VERSION` ist 1. Vertrauenswürdiger Anwendungscode kann `LoadForecastModule(executor)` mit der bestehenden `BaseRuntime.async_register_module` registrieren. Das Modul wird durch Import oder HA-Start nicht automatisch aktiviert. Die konkrete HA-Bedienung und automatische Modulverwaltung sind weiterhin offen.

`LoadForecastRequest` kopiert Listen in Tupel und begrenzt Eingaben auf 60000 Beobachtungen und 1–384 Zielintervalle. Messbeobachtungen und Ergebnisse sind unveränderlich. Wissensstand und lokale Zeitzone sind ausdrücklich übergeben. Der vorhandene Kern prüft Zahlen, Zeitqualität und ausreichende Historie; fehlende Werte werden nicht erfunden.

Der Handler prüft Manifest, Speicher-Modulkennung und Schema, liest dann optional das Dokument `settings`. Zulässig sind ausschließlich `lookback_days`, `min_sample_days`, `half_life_days`; ohne Dokument gelten die bestehenden Kernvorgaben 56 Tage, mindestens 3 Vergleichstage und 21 Tage Halbwertszeit. Es werden keine Vorgaben gespeichert und keine Ergebnisse geschrieben. Das Modul besitzt keine separate Datenbank.

Der injizierte asynchrone Executor muss die synchrone Berechnung außerhalb der Eventloop ausführen, in HA etwa über den vorhandenen Executor-Zugang. Der gemeinsame Drain-Helfer wartet bei Abbruch auf bereits übergebene Arbeit. Dies ist keine harte CPU-Unterbrechung oder Prozessisolation; die kooperative Modul-Zeitgrenze kann bei laufendem Worker überschritten werden. Der Runtime-Kontext bleibt für Projekt-/Revisionsschutz zuständig. Keine Providerabfrage, Aktorsteuerung, automatische Planung oder belegte reale Prognosegüte ist enthalten.

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

Die Datenhaltung gehört ebenfalls zum Grundmodul. Eine gemeinsame, projekt-/modulbezogene SQLite-Konfigurationsablage ist nun separat implementiert; HA-Projektübernahme ist ab 0.5.0 angebunden; ein ausdrücklicher asynchroner Projekt-/Modulkontext für Konfiguration ist seit 12.11.2026 implementiert. Automatische Kontextversorgung bei Aktivierung, Historien und Laufzeitdienste folgen. Siehe [CENTRAL_STORAGE.md](CENTRAL_STORAGE.md). Modulregistrierung erzeugt bislang weiterhin keine automatischen Dateien oder Migrationen.

Async-Timeouts funktionieren nur kooperativ. CPU-blockierende Module, fremde gemeinsam veränderte Objekte oder Handler, die Abbruch ignorieren, können andere Arbeit im Prozess beeinträchtigen. Der Kernel ist keine Sicherheits- oder Prozessisolationsgrenze. Blockierende Berechnungen gehören später in geeignete Worker; Live-Aktoren sind keine freigegebenen Handler dieses Kernels.

Eine Registry gehört nach Beginn asynchroner Aufrufe zu genau einer Eventloop/Projektlaufzeit. Wiederverwendung derselben Async-Locks über verschiedene Eventloops ist nicht vorgesehen; bei neuer Laufzeit eine neue Registry anlegen.

Nächste zusammenhängende Schritte:

1. Versionierte Ein-/Ausgaben und Konfiguration für Messung, Prognose, Preise und Planung definieren; Formular-/Fähigkeitsdefinitionen aus DEVICE_MODULES_AND_SETUP.md damit verbinden.
2. Konkretes Prognosemodul zunächst als rein lesende/manuell gefütterte Quelle auslagern und gegen bestehende Prognosetests prüfen. Keine Prognosegüte erfinden.
3. Start/Stop, Cache-/Datenalter, Projektinstanzen und HA-Lebensdauer ergänzen; danach Status/Versionen im bestehenden Panel zeigen.
4. Gerätebausteine schrittweise über dieselben Verträge anbinden. Ausfall-, Migrations- und Updatefälle vor Freigabe testen.

18 neue Tests prüfen Versionsgrenzen, fehlende/zyklische Abhängigkeiten, unabhängige Fortführung, Fehlerquittierung, Nebenläufigkeit, Timeout/Abbruch und überholte Ergebnisse/Fehler. Keine unveränderte Betriebsfähigkeit bei beliebigem Pythonfehler behauptet.


## Statusabruf ohne Fachmodul-Aufruf — 12.11.2026

Das Grundmodul 0.1.1 begrenzt die aktive Statusprüfung auf die eigenen Diagnosehandler `core`, `storage` und `project`. Andere registrierte Module werden mit ihren tatsächlichen Registry-Zuständen aufgelistet, dabei aber weder aufgerufen noch bei einem Fehler automatisch quittiert. Bisher erfasste die Schleife auch zusätzliche registrierte Handler. Ein späterer Prognose-/Messbaustein hätte dadurch beim Öffnen des Grundmodulstatus unbeabsichtigt Arbeit ausführen können.

Die vorhandene Erholung der eingebauten Speicherdiagnose bleibt erhalten. Fachmodule benötigen weiterhin ausdrückliche Aufrufe und Fehlerquittierung. `ready` bedeutet ausschließlich kompatibel/aufrufbar, nicht gestartet oder mit aktuellen Messwerten versorgt. Die HA-Laufzeitprüfung registriert synthetische verfügbare, deaktivierte, fehlerhafte und inkompatible Fachmodule und prüft, dass wiederholte Statusabrufe ihre Handler nicht ausführen und Zustände erhalten.


Grundmodul 0.1.2 (13.11.2026) besitzt nun zusätzlich den gemeinsamen, erst bei ausdrücklichem internem Lesen erzeugten Verbindungsmanager. Beim HA-Unload wird dessen Bereinigung einschließlich wartender Besitzersperre abgearbeitet. Dies sind noch keine allgemeinen Fachmodul-Start-/Stop-Hooks und kein automatischer Geräteabruf. Beendete Laufzeiten werden nicht wieder gestartet. Siehe SYSTEM_LOGIC.md.


## Ausdrückliche Fachmodulregistrierung mit Datenbankkontext — 16.11.2026

Grundmodul 0.1.4 bietet intern `BaseRuntime.async_register_module(manifest, handler, schema_version=...)`. Vertrauenswürdiger Anwendungscode registriert damit einen asynchronen Handler mit der Form `handler(context, request)`. Die Grundlaufzeit öffnet den vorhandenen gemeinsamen SQLite-Bereich für das gespeicherte Projekt und Modul und übergibt diesen Kontext bei späteren ausdrücklichen Aufrufen. Es gibt keinen Download, Dateiscan, dynamischen Import, Gerätezugriff oder Handler-Aufruf während der Registrierung. Noch kein Fachmodul wird automatisch entdeckt oder aktiviert.

Die ursprüngliche Handlerfunktion, Duplikate und Kapazitätsgrenzen werden vor Datenbankarbeit geprüft; die endgültige Registrierung prüft erneut. Das Modul muss Kernel-API 1 und eine ausdrückliche, zur vorhandenen Version passende `storage`-Abhängigkeit deklarieren. Deren Abhängigkeit zum Grundmodul gilt weiterhin. Codeversion und Konfigurationsschema bleiben getrennt. Die neue reine Registry-Funktion `validate_registration` führt keinen Handler aus und verändert den Bestand nicht.

Registrierungen sind serialisiert. Nach dem Öffnen des Kontexts müssen Laufzeit, Projekt-ID und Projektrevision unverändert sein. Bei Abbruch oder zwischenzeitlichem Wechsel kann ein leerer Datenbank-Namensbereich bestehen bleiben; es wird aber kein Handler nachträglich aktiviert. Stop sperrt neue Registrierungen sofort und wartet auch bei Taskabbruch auf bereits laufende Vorbereitungen, bevor die Bereinigung endet.

Der Kontext bleibt an seine ursprüngliche Projekt-ID gebunden. Änderungen derselben Projekt-ID zwischen zwei Aufrufen sind erlaubt. Ändert sich der Projektstand während eines Handler-Aufrufs, wird dessen Ergebnis verworfen und das Modul deaktiviert, ohne einen Ausführungsfehler zu erfinden. Ein neuer Aufruf erfordert dann ausdrückliche Wiederfreigabe durch Anwendungscode. Bei einer fremden aktiven Projekt-ID wird der Handler gar nicht erst aufgerufen; ein neuer Kontext benötigt eine neue Laufzeit. Eine Rückkehr zur ursprünglichen Projekt-ID kann dieselbe Bindung nach ausdrücklicher Wiederfreigabe weiterverwenden. Die Registry bleibt auf genau eine Implementierung pro Modul-ID begrenzt.

Bereits abgeschlossene Konfigurationsschreibvorgänge werden durch diese Ergebnisprüfung nicht rückgängig gemacht; sie bleiben ausschließlich im ursprünglichen Projektbereich. Die kooperative Registry ersetzt weiterhin keine Prozessisolation oder allgemeinen Gerätetreiber-Start-/Stop-Hooks. Diese API enthält keine Aktorfreigabe.

Die HA-Prüfung verwendet echte temporäre SQLite-Projekte und synthetische Handler. Sie prüft Kontextübergabe, gemeinsame Ablage, keine Ausführung bei Registrierung/Status, Prüfung vor Speicherzugriff, Wiederverwendung bei gleichbleibender Projekt-ID, Ablehnung überholter Ergebnisse und fremder Bindung sowie Stop während einer wartenden Vorbereitung.


Stop wartet in diesem Schritt auf Registrierungsvorbereitung und Transportbereinigung, aber nicht automatisch auf beliebige bereits laufende Fachhandler. Diese müssen ihren eigenen kooperativen Taskablauf beachten. Deren überholte Ausgaben werden verworfen; bereits erfolgte Schreibvorgänge im ursprünglichen Konfigurationsbereich bleiben bestehen. Allgemeine Fachmodul-Taskbesitzer und Gerätetreiber-Hooks sind weiterhin offen.


## Gemeinsame HA-Bereinigung bei Fehlern — 16.11.2026

Grundmodul 0.1.5 entfernt die gemeinsamen Panel-, Dienst- und Speicherreferenzen auch dann, wenn der Stop der letzten Grundlaufzeit einen Fehler oder Abbruch weitergibt. Die letzte Coordinator-Abmeldung ruft die gemeinsame Bereinigung ebenfalls in einem `finally` auf. Bisher konnte nach dem Entfernen des Runtime-/Coordinator-Eintrags der übrige Abbau übersprungen werden; das Panel und Dienste blieben dann ohne vollständige Laufzeit zurück.

Andere noch aktive Integrationseinträge behalten ihre gemeinsamen Ressourcen. Scheitert bereits die Plattformabmeldung mit `False`, bleibt der bisherige Bestand weiterhin erhalten. Statische Routen und registrierte WebSocket-Handler bleiben wie bisher für einen erneuten Start bestehen; nach vollständigem Entladen antworten diese mit `not_loaded`. Die Projektdateien werden nicht entfernt und Fehler-/Abbruchsignale nicht als erfolgreicher Unload ausgegeben.

Die HA-Prüfung injiziert Fehler und Abbruchsignale nach dem tatsächlichen Runtime-/Coordinator-Abbau und prüft die gemeinsame Bereinigung sowie einen weiterhin aktiven zweiten Eintrag. Dies belegt den Schutz der gemeinsamen Registrierungen, keine allgemeine Fehlerfreiheit beliebiger fremder Coordinator-Implementierungen oder beliebiger gleichzeitiger Bereinigungsfehler.
