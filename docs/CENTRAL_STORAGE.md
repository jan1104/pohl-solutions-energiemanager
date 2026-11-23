# Zentrale Datenhaltung im Grundmodul

## Gespeicherte Dokumentkennungen auflisten — 24.11.2026

`list_keys(after=None, limit=50)` beziehungsweise `async_list_keys(...)` liefert ein Tupel gespeicherter Kennungen im fest gebundenen Projekt-/Modulbereich. So können Fachmodule dynamisch benannte Konfigurationen nach einem Neustart wiederfinden. Die Abfrage lädt keine Dokumentkörper. Erlaubt sind ganzzahlige Seitengrößen von 1 bis 128; Boolean ist ungültig. `after` ist eine gültige Dokumentkennung und wird exklusiv verglichen. Sie muss nicht mehr existieren.

Kennungen sind binär aufsteigend sortiert. Für die nächste Seite die letzte zurückgegebene Kennung als `after` verwenden; ein leeres Tupel beendet die Auflistung. Jede Seite prüft Datenbank und Namensraumschema in einer eigenen Lesetransaktion. Zwischen Seiten können neue Dokumente entstehen oder Änderungen erfolgen: Es gibt keinen eingefrorenen Gesamtbestand. Einträge, die später vor dem Cursor eingefügt werden, erfordern eine neue Auflistung ab Beginn. Inhalte können anschließend über `get_many` in einem neuen konsistenten Lesestand gelesen werden. Der bestehende asynchrone Abbruchvertrag bleibt erhalten.

## Gemeinsamer Lesestand für mehrere Dokumente — 23.11.2026

`ModuleStorage.get_many(keys)` und `AsyncModuleStorage.async_get_many(keys)` liefern ein Dictionary der ausdrücklich angeforderten Schlüssel mit `StoredDocument` oder `None`. Erlaubt sind Listen/Tupel mit 1 bis 128 eindeutigen gültigen Dokumentkennungen. Die asynchrone Variante kopiert und prüft die Schlüssel vor Übergabe an den Executor. Kein fremder Projekt-/Modulbereich kann ausgewählt werden.

Alle Dokumente stammen aus derselben SQLite-Lesetransaktion einschließlich Datenbank-/Schemaprüfung. Ein parallel bestätigter Mehrdokument-Schreibvorgang kann dadurch keine Mischung alter und neuer Konfigurationen innerhalb eines Ergebnisses erzeugen. Einzelne spätere Leseaufrufe sind neue Lesestände. Fehlende Schlüssel werden nicht als leere Konfiguration erfunden. Rückgabedaten sind vom Speicher getrennt; ein Schemawechsel macht veraltete Handles wie bisher unbrauchbar.

Dies ist Konfigurationszugriff für Fachmodule, keine Zeitreihendatenbank, globale SQL-Schnittstelle oder automatische Messwerterfassung. Der bestehende asynchrone Drain-Vertrag gilt auch für Sammellesungen. Speicherformat und öffentliche HA-Oberfläche ändern sich nicht.

Stand: 12.11.2026. Die gemeinsame SQLite-Konfigurationsablage ist an HA angeschlossen. Neue Fachmodule können nun ausdrücklich einen festen Projekt-/Modulkontext mit asynchronem Speicherzugang erhalten. Eine ausdrücklich aufgerufene, überschreibungsfreie Datenbanksicherung ist im Kern verfügbar. Historien, automatische Modulaktivierung, Sicherungsbedienung/Wiederherstellung und vollständige Laufzeitkontexte bleiben offen. Aktueller Prüfablauf: TESTING_0_6.md.

## Eigentum und Aufteilung

Das Grundmodul besitzt die Datenhaltung. Fachmodule erhalten einen Speicherzugang mit festem Projekt-, Modul- und Konfigurationsschema-Bezug, keine eigene Datenbankdatei und keinen allgemeinen SQL-Zugang über diesen Vertrag. Ein neuer Baustein verwendet dieselbe Speicherschnittstelle. Physisch bleibt die Konfiguration in einer gemeinsamen Energiemanager-Datenbank; logische Bereiche bleiben getrennt:

```text
Energiemanager-Datenhaltung
├── Globale Kernangaben und Modulbestand                 (nächste Anbindung)
├── Projekt A
│   ├── Kern: Zuordnungen und gemeinsame Einstellungen  (SQLite ab 0.5.0)
│   ├── Prognosemodul: Quellen und Konfiguration        (neue Modulablage)
│   └── Weitere Module: eigene Konfigurationsbereiche
└── Projekt B: getrennte Modulbereiche

Weitere Datengruppen: Messhistorie, Prognoseläufe, Pläne, Ist-Auswertungen
```

Ein Modul darf nicht beliebige lokale Variablen automatisch als dauerhafte Daten betrachten. Es deklariert, was Konfiguration, Historie, Cache oder flüchtiger Laufzeitzustand ist. Das Grundmodul übernimmt deren Speicherung über passende gemeinsame Dienste. Dasselbe Messgerät oder derselbe Messwert wird nicht je Verbraucher erneut gespeichert; Beziehungen verwenden stabile IDs.

## Bereits implementierter Speicherdienst

- `SQLiteStorage(path)` merkt nur den Pfad. Konstruktion erzeugt keine Datei. `initialize()` legt bewusst eine eigene, markierte SQLite-Datenbank an; kein Netzwerk und kein Gerätezugriff. Elternverzeichnis muss bereits vorhanden sein.
- Datenbankkennzeichen und Datenbank-Schemaversion werden geprüft. Eine fremde, neuere oder nicht unterstützte Datenbank wird nicht übernommen oder zurückgestuft; auch eine fremde reine View-Datenbank gilt nicht als leer.
- `for_module(project_id, module_id, schema_version=...)` registriert einen Modulbereich. Neue Module nutzen dieselben Tabellen, ohne eigene Tabellenmigration. Ein bestehender Bereich mit anderer Konfigurationsversion wird ausdrücklich abgelehnt, nicht still umbenannt oder überschrieben.
- Ein Modulzugang bietet `get`, `put` und `put_many`. Schlüssel sind innerhalb seines Projekt-/Modulbereichs eindeutig. Gleiche Schlüssel in zwei Projekten oder Modulen bleiben unabhängig.
- Dokumente sind JSON-Objekte, auf 2 MiB/Tiefe begrenzt und auf ungültige Zahlen/Feldtypen geprüft. Bekannte Geheimnis-/Steuerfreigabefelder werden entsprechend der bestehenden Projektregeln abgelehnt. Keine Gerätebefehle beim Speichern.
- Jede Änderung verlangt die gelesene Revision. `expected_revision=None` bedeutet ausschließlich Neuanlage; es ist keine Erlaubnis zum Überschreiben. Konflikte verändern keine Daten. `put_many` speichert bis zu 128 Dokumentänderungen gemeinsam oder rollt alle zurück.
- Transaktionen verwenden gebundene SQL-Parameter und serialisierte Schreibaufnahme; Sperrwartezeit ist begrenzt. Verbindungen werden nach jeder Operation geschlossen, nicht zwischen Async-/Executor-Threads geteilt. Standardmäßiges SQLite-Rollback-Journal, noch keine für Historien optimierte WAL-Ablage.
- Es gibt bewusst noch keine Lösch-/Neu-anlegen-Funktion mit wiederverwendeten Revisionen. Deaktivieren eines Moduls soll seine Daten erhalten. Bereinigung braucht einen getrennten, überprüfbaren Ablauf.

Dieser Dienst ist synchron. HA muss Aufrufe später in einem Executor ausführen; er darf nicht im HA-Eventloop blockieren. Mehrere Repositoryinstanzen verwenden dieselbe Datenbank sicher über SQLite-Transaktionen, nicht über einen nur pro Pythonobjekt wirksamen Lock.

## Was als Nächstes zentral angebunden wird

| Datengruppe | Geplante Behandlung | Heutiger Stand |
| --- | --- | --- |
| Kernprojekt/Zuordnungen | Zentrale Konfigurationsquelle mit Revision | SQLite ab 0.5.0 maßgeblich; Legacy-Datei bleibt Sicherung |
| Moduleinstellungen | Projekt-/Modulbereich, eigene Konfigurationsversion | Neue SQLite-API separat getestet |
| Modulversionen/Aktivierung | Kern verwaltet Bestand und kompatible Konfiguration | Basisfunktionen in HA registriert; allgemeine Fachmodulkontexte fehlen |
| Messhistorie | Zeitreihen mit Quelle, Mess-/Empfangszeit, Einheit und Qualität | Noch kein Historienrepository |
| Prognosen/Pläne | Versionierte Läufe mit Eingangsrevisionen, Gültigkeit und Herkunft | Noch keine zentrale Laufablage |
| Cache/Laufzeit | Begrenzte Lebensdauer, nicht automatisch als Ist-Nachweis sichern | Noch kein gemeinsamer Cachevertrag |
| Geheimnisse | Eigener Zugangsdaten-/Referenzdienst, getrennt vom Standardexport | Noch keine neue Geheimnisablage implementiert |

„Global gespeichert“ heißt gemeinsamer Dienst und gesicherte Beziehungen, nicht unbeschränkte Historie oder Klartextgeheimnisse in jedem Export. Häufige Messwerte gehören später in geeignete Zeitreihentabellen mit Sammelschreiben und konfigurierbarer Aufbewahrung, nicht in ständig neu geschriebene große JSON-Konfigurationsobjekte. Historienbedarf und Pi-5-Ressourcen müssen dafür gemessen werden.

## Versionierung, Migration und Sicherung

Datenbankformat, Modulcodeversion und Modulkonfigurationsversion sind getrennt. Ein neues Modul legt einen neuen Namensbereich an; eine neue Version eines bestehenden Moduls darf vorhandene Daten erst nach ausdrücklicher, getesteter Migration übernehmen. Beim Öffnen akzeptiert der Speicher die angeforderte Version und optional explizit kompatible vorhandene Versionen. Der ProjectStore erstellt Version 1 und unterstützt bestehende Namespaces in Version 2. Die explizite Entwicklungs-API `ModuleStorage.migrate(target_schema_version, changes)` ersetzt alle Dokumente und die Namespace-Version atomar. Jede bestehende Dokumentkennung muss enthalten sein, jede Revision stimmen; neue Dokumente sind ausschließlich create-only. Es laufen keine Migrations-Callbacks. Andere Namensbereiche bleiben unverändert, alte Handles werden ungültig. Vollständige Migrationen können mehr als 128 Dokumente enthalten, weil ein Namespace über mehrere normale Schreibbatches wachsen kann; jeder Dokumentinhalt bleibt auf 2 MiB begrenzt. Alle Ersatzdaten werden vorab geprüft und im Speicher gehalten, daher ist dies ein Konfigurationswerkzeug und keine Massendaten-/Historienmigration. Rücksicherung und automatische Downgrades sind nicht implementiert.

Ab 0.5.0 übernimmt ProjectStore beim ausdrücklichen HA-Setup einmalig den validierten Legacy-Projektstand. Migration und Herkunftsmetadaten werden gemeinsam gespeichert; vorhandenes gültiges SQLite-Projekt hat Vorrang. Die Originaldatei bleibt bytegleich erhalten. Danach gibt es keine parallelen Schreibquellen. Allgemeine Fachmodul-Migration und ein automatischer Downgrade bleiben offen; Register-/Importoperationen öffnen keine Geräteverbindungen.

Zentrale Sicherung muss künftig Konfiguration, Modulversionen und gewünschte Historien konsistent aufnehmen. Eine laufende SQLite-Datenbank soll über deren Backup-API gesichert werden, statt nur eine möglicherweise unvollständige Hauptdatei zu kopieren. Die Kern-API für eine solche Sicherung ist seit 12.11.2026 implementiert (siehe unten); Wiederherstellung und HA-Bedienung fehlen noch. Normale Projekteexporte bleiben ohne Klartextzugangsdaten. Feldnamenprüfungen können nicht jedes Geheimnis in beliebigen Texten erkennen; konkrete Modulschemata und separater Geheimnisdienst bleiben erforderlich.

Die Datenbank liegt künftig im privaten HA-Konfigurationsbereich, nicht im Git-Repository. Datenbank-, Journal- und mögliche WAL/SHM-Dateien sind vorsorglich in Git ausgeschlossen. Pythonmodule laufen als vertrauenswürdiger Code im selben Prozess: Namensbereiche sind fachliche Trennung, keine Sicherheitsgrenze gegen bösartige Module mit direktem Dateisystemzugriff.

## Nachweis und nächste Umsetzung

21 neue Tests mit temporären Datenbanken: Wiederöffnen, Projekt-/Modultrennung, zwei konkurrierende Schreiber, Revisionskonflikte, Batch-Rollback, ungültige/geheime Dokumentfelder, Schema-/Fremddatenbankerhalt, Sperrkonflikte, unveränderte Ein-/Ausgaben und Windows-/Unicode-Dateipfade. Kein Nachweis für Hardware-Stromausfall, Dateisystemkorruption oder Historienlast.

Der ausdrücklich geöffnete asynchrone Speicherzugang ist inzwischen implementiert (siehe unten). Als Nächstes folgen konkrete Fachmodulschemas und deren Aktivierungsablauf; neue Module sollen dabei denselben Zugang erhalten, statt eigene Datenbankanbindungen zu programmieren.


Entwicklung 06.11.2026: Format-1→2-Projektwechsel mit expliziter Vorschau, Quell-SHA/Revision und erhaltenen Originaldaten vorbereitet; siehe PROJECT_SCHEMA_V2_DRAFT.md. Keine HA-Aktivierung. Temporäre Datenbanktests prüfen Neustart, konkurrierende Migrationen, ABA-/Metadatenkonflikte, Backupkollisionen und Rollback nach injiziertem Fehler beim abschließenden Schemawechsel. Kein Hardware-Stromausfallnachweis.


## Asynchroner Modulkontext — 12.11.2026

`core/module_context.py` stellt `ModuleContext` und `AsyncModuleStorage` bereit. Das Grundmodul übergibt eine bereits initialisierte `SQLiteStorage` und einen Executor. Der ausdrückliche Aufruf `async_module_context(...)` öffnet den Namensbereich; Konstruktion und Registrierung erzeugen keine Datei. Es gibt keine automatische Initialisierung oder Migration. Manifest-Codeversion und Konfigurationsschema bleiben unabhängig. Die eingebauten Modul-IDs `core`, `storage` und `project` bleiben ihren bisherigen Besitzern vorbehalten.

`ProjectStore.async_module_context(manifest, schema_version=...)` stellt diesen Zugang für die ID des geladenen, gespeicherten Projekts mit dem HA-Executor bereit. Ein Kontext behält seine Projekt-ID, auch wenn anschließend ein anderes Projekt importiert wird. Er ist kein Nachweis, dass dieses Projekt gerade aktiv ist. Noch kein Fachmodul wird dadurch automatisch gestartet oder registriert.

Die gewöhnliche Modulschnittstelle bietet `async_get`, `async_put` und `async_put_many`. Sie verwendet dieselbe Datenbank, Revisionsprüfung und Transaktionen wie die Projektablage. JSON-Schreibdaten werden vor Übergabe an die Worker-Warteschlange geprüft und unabhängig kopiert. Ein Taskabbruch wartet auf bereits übergebene Arbeit und wird danach weitergegeben; ein abgeschlossener Schreibvorgang kann daher trotz Abbruch gespeichert sein. Vor erneutem Schreiben den Stand lesen und dessen Revision verwenden. Kein allgemeiner SQL- oder Migrationsaufruf wird über diese Schnittstelle angeboten. Pythoncode im selben Prozess bleibt vertrauenswürdig; die Kapselung ist keine Sicherheitsgrenze.

Tests mit temporärer SQLite prüfen getrennte Projekte/Module, Wiederöffnen, Schemaablehnung, Konflikte und Batch-Rollback, veränderte Eingaben während wartender Arbeit sowie wiederholten Abbruch bei erfolgreichem und fehlerhaftem Worker. Die echte HA-Laufzeitprüfung ergänzt Zugriff über den HA-Executor und den Wechsel der aktiven Projekt-ID. Messwerthistorien, Cache, Modul-Start/Stop und Versionsaktivierung sind davon getrennte nächste Schritte.


## Ausdrückliche Datenbanksicherung — 12.11.2026

`SQLiteStorage.backup(destination)` erstellt über die SQLite-Backup-API einen konsistenten Stand der gemeinsamen Datenbank mit allen Projekt-/Modulbereichen, Dokumenten und Revisionen. Die Quelldatenbank muss bereits existieren und die unterstützte Kennung/Version besitzen. Der Aufruf initialisiert oder migriert nichts. Ein Lesesnapshot hält die zu sichernde Sicht fest. Bereits bestätigte WAL-Inhalte werden berücksichtigt, unbestätigte Änderungen anderer Verbindungen nicht übernommen.

Die Kopie entsteht zunächst als private temporäre Datei im bestehenden Zielverzeichnis. Die Datenbankkennung und -version werden erneut geprüft; `quick_check` muss vollständig erfolgreich sein. Anschließend wird die fertige Datei mit einem atomaren, überschreibungsfreien Hardlink unter dem gewünschten Namen sichtbar. Existierende Dateien, Verzeichnisse und auch Symlinks bleiben erhalten, ebenso ein während des Kopierens angelegtes Ziel. Unterstützt das Dateisystem keine Hardlinks, schlägt die Sicherung ausdrücklich fehl; es gibt keinen überschreibenden Ersatzweg. Die temporäre Datei wird bei normalen Fehlern entfernt. Ein Prozessabsturz kann eine nicht veröffentlichte temporäre Datei zurücklassen.

Das Speicher-Zeitbudget begrenzt die Wiederholungen des Kopierens; eine SQLite-Fortschrittsfunktion begrenzt auch die anschließende Prüfung. Der synchrone Aufruf gehört in einen Executor. Dies ist eine Kern-API, keine automatisch laufende Sicherung, kein HA-Download und keine Restore-Funktion. Die Sicherung enthält sämtliche Konfiguration dieser Datenbank und gehört wie die aktive Datei ausschließlich in private Ablage. Sie wird nicht in Git aufgenommen. Die veröffentlichte Sicherung wird vom Energiemanager nicht als aktive Datenbank weiter beschrieben.

Tests verwenden temporäre Dateien und synthetische Dokumente. Geprüft werden getrennte Bereiche und Revisionen, spätere Unabhängigkeit vom Original, bestätigte/unbestätigte parallele WAL-Transaktionen, vorhandene und konkurrierend angelegte Ziele, fehlerhafte Quelldatenbanken, Kopier-/Prüf-/Veröffentlichungsfehler und Aufräumen nach Timeout. Der Symlinktest läuft nur auf Systemen mit entsprechender Berechtigung. Kein Nachweis für Hardware-Stromausfall oder Wiederherstellung einer realen Anlage.


## Projektrevision ohne wiederholte Vollserialisierung — 15.11.2026

Projektverwaltung 0.1.1 hält die Inhaltskennung zusammen mit dem privaten Projektstand vor. Die SHA-256-Berechnung verwendet unverändert denselben kanonischen JSON-Vertrag, erfolgt aber nur beim Übernehmen eines geladenen, gespeicherten oder durch eine Messsimulation aufgefrischten Projektstands. Wiederholte Revisionsabfragen, etwa vor/nach einer ausdrücklichen Registerlesung, serialisieren und hashen das Projekt dafür nicht erneut.

Alle Übernahmen laufen über einen gemeinsamen internen Pfad. Auch nach einer abgeschlossenen Speicherung mit anschließendem Taskabbruch, einer Migration oder dem Nachladen bei Schreibkonflikten wird die Kennung aktualisiert, bevor das Ergebnis beziehungsweise der Fehler weitergegeben wird. Öffentliche Exporte bleiben Zeichenketten und Zusammenfassungen eigenständige Objekte; ihre Veränderung bearbeitet das private Projekt nicht. Numerische SQLite-Revisionen, Konfliktprüfung und Importformat bleiben unverändert.

Die HA-Prüfung vergleicht gegen unabhängig berechnete kanonische SHA-Werte. Sie zählt Hashaufrufe statt Zeit-/Speicherwerte zu behaupten: wiederholte reine Zugriffe dürfen keine neue Hashberechnung anfordern. Geprüft sind leere, neue, importierte, konkurrierend geänderte und per Simulation aufgefrischte Stände sowie abgebrochene abgeschlossene Schreib-/Migrationsvorgänge. Dies ist kein Raspberry-Pi-Leistungsbenchmark und keine neue Prüfung externer Datenbankänderungen. Export und Strukturprüfung können weiterhin Arbeit benötigen; nur die wiederholte Inhaltskennung wird wiederverwendet.


## Wiederverwendbare Projektansicht — 16.11.2026

Projektverwaltung 0.1.2 ergänzt die vorgehaltene Inhaltskennung um den unveränderlichen Exporttext und eine private Zusammenfassung. Bisher validierten und serialisierten Export-/Statusabfragen den unveränderten Projektbaum weiterhin erneut. Alle drei Darstellungen entstehen nun gemeinsam beim Übernehmen eines Projektstands, bevor dieser veröffentlicht wird. Die gewohnten Funktionen für Format 1 und 2 bestimmen weiterhin den Export und die Hinweise; Einrückung, Zeilenende beziehungsweise kompakte Ausgabe ändern sich nicht.

`export()` liefert den gespeicherten Text in einem neuen Antwortobjekt. `status()` liefert eine unabhängige Kopie der Zusammenfassung einschließlich verschachtelter Zähler, Warnungen und Format-2-Hinweise. Änderungen an zurückgegebenen Objekten dürfen spätere Antworten nicht verändern. Die wiederverwendete Darstellung gehört ausschließlich zum privaten lokalen Projektstand; sie ist keine erneute Prüfung der Datenbank oder externer Geräte.

Die bestehende HA-Prüfung wird auf alle fünf Berechnungsfunktionen erweitert: Hash, beide Exporter und beide Zusammenfassungen. Wiederholte reine Zugriffe dürfen keine dieser Funktionen erneut aufrufen. Ausgaben werden vorher mit den ursprünglichen Funktionen verglichen, und verschachtelte zurückgegebene Strukturen werden gezielt verändert. Laden, Import, Konflikterholung, Simulation und abgebrochene abgeschlossene Speicherung/Migration bleiben abgedeckt. Kein Ressourcenbenchmark oder pauschaler Nachweis für Raspberry-Pi-Leistung.


Seit Grundmodul 0.1.4 kann ausdrücklich registrierter Fachmodulcode seinen asynchronen Konfigurationskontext über `BaseRuntime.async_register_module(...)` erhalten. Der Handler braucht keine eigene SQLite-Anbindung. Vorhandene Namensbereiche werden mit dem verlangten Schema geöffnet, nicht automatisch migriert. Die Bindung an die ursprüngliche Projekt-ID bleibt erhalten; automatische Entdeckung, allgemeine Modulaktivierung und Historien bleiben offen. Lebensdauer und Grenzen stehen in MODULE_KERNEL.md.
