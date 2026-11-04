# Zentrale Datenhaltung im Grundmodul

Stand: 04.11.2026. Erste zentrale SQLite-Ablage für Modulkonfiguration ist implementiert (`core/storage.py`). Noch keine Umstellung der laufenden HA-Integration und keine automatische Speicherung aller Module. Historien, Migration, Sicherung und Anbindung an Modulkontexte sind folgende Schritte.

## Eigentum und Aufteilung

Das Grundmodul besitzt die Datenhaltung. Fachmodule erhalten einen Speicherzugang mit festem Projekt-, Modul- und Konfigurationsschema-Bezug, keine eigene Datenbankdatei und keinen allgemeinen SQL-Zugang über diesen Vertrag. Ein neuer Baustein verwendet dieselbe Speicherschnittstelle. Physisch bleibt die Konfiguration in einer gemeinsamen Energiemanager-Datenbank; logische Bereiche bleiben getrennt:

```text
Energiemanager-Datenhaltung
├── Globale Kernangaben und Modulbestand                 (nächste Anbindung)
├── Projekt A
│   ├── Kern: Zuordnungen und gemeinsame Einstellungen  (bestehender HA-Store)
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
| Kernprojekt/Zuordnungen | Zentrale Konfigurationsquelle mit Revision | Bestehender HA-Projektspeicher bleibt maßgeblich |
| Moduleinstellungen | Projekt-/Modulbereich, eigene Konfigurationsversion | Neue SQLite-API separat getestet |
| Modulversionen/Aktivierung | Kern verwaltet Bestand und kompatible Konfiguration | Kernel bisher nur im Speicher; Kontextanbindung fehlt |
| Messhistorie | Zeitreihen mit Quelle, Mess-/Empfangszeit, Einheit und Qualität | Noch kein Historienrepository |
| Prognosen/Pläne | Versionierte Läufe mit Eingangsrevisionen, Gültigkeit und Herkunft | Noch keine zentrale Laufablage |
| Cache/Laufzeit | Begrenzte Lebensdauer, nicht automatisch als Ist-Nachweis sichern | Noch kein gemeinsamer Cachevertrag |
| Geheimnisse | Eigener Zugangsdaten-/Referenzdienst, getrennt vom Standardexport | Noch keine neue Geheimnisablage implementiert |

„Global gespeichert“ heißt gemeinsamer Dienst und gesicherte Beziehungen, nicht unbeschränkte Historie oder Klartextgeheimnisse in jedem Export. Häufige Messwerte gehören später in geeignete Zeitreihentabellen mit Sammelschreiben und konfigurierbarer Aufbewahrung, nicht in ständig neu geschriebene große JSON-Konfigurationsobjekte. Historienbedarf und Pi-5-Ressourcen müssen dafür gemessen werden.

## Versionierung, Migration und Sicherung

Datenbankformat, Modulcodeversion und Modulkonfigurationsversion sind getrennt. Ein neues Modul legt einen neuen Namensbereich an; eine neue Version eines bestehenden Moduls darf vorhandene Daten erst nach ausdrücklicher, getesteter Migration übernehmen. Der erste Dienst lehnt unterschiedliche Schemaversionen ab; Migrations-Callbacks und Rücksicherung sind noch nicht implementiert.

Der heutige `ProjectStore` wird nicht parallel automatisch in SQLite geschrieben. Erst eine geprüfte Übernahme mit Versions-/Konfliktprüfung, Inhaltsvergleich und Rückfallweg darf die maßgebliche Quelle wechseln. Kein vorhandener Projektname, Import oder Modulregister-Aufruf startet diese Migration als Nebenwirkung.

Zentrale Sicherung muss künftig Konfiguration, Modulversionen und gewünschte Historien konsistent aufnehmen. Eine laufende SQLite-Datenbank soll über deren Backup-API gesichert werden, statt nur eine möglicherweise unvollständige Hauptdatei zu kopieren. Eine solche Backup-/Restore-Funktion ist noch zu implementieren. Normale Projekteexporte bleiben ohne Klartextzugangsdaten. Feldnamenprüfungen können nicht jedes Geheimnis in beliebigen Texten erkennen; konkrete Modulschemata und separater Geheimnisdienst bleiben erforderlich.

Die Datenbank liegt künftig im privaten HA-Konfigurationsbereich, nicht im Git-Repository. Datenbank-, Journal- und mögliche WAL/SHM-Dateien sind vorsorglich in Git ausgeschlossen. Pythonmodule laufen als vertrauenswürdiger Code im selben Prozess: Namensbereiche sind fachliche Trennung, keine Sicherheitsgrenze gegen bösartige Module mit direktem Dateisystemzugriff.

## Nachweis und nächste Umsetzung

21 neue Tests mit temporären Datenbanken: Wiederöffnen, Projekt-/Modultrennung, zwei konkurrierende Schreiber, Revisionskonflikte, Batch-Rollback, ungültige/geheime Dokumentfelder, Schema-/Fremddatenbankerhalt, Sperrkonflikte, unveränderte Ein-/Ausgaben und Windows-/Unicode-Dateipfade. Kein Nachweis für Hardware-Stromausfall, Dateisystemkorruption oder Historienlast.

Nächster Schritt: zentralen Speicherdienst als ausdrücklich initialisierten Dienst in den Modulkontext injizieren, konkrete Konfigurationsschemas definieren und danach den bisherigen HA-Projektspeicher kontrolliert migrieren. Neue Fachmodule erhalten dann automatisch ihren Zugang beim Aktivieren; sie programmieren keine eigenen Datenbankanbindungen.
