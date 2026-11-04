# Grundmodul 0.5.0 testen

Testbare Entwicklungsversion für Projektverwaltung, Basis-Module und zentrale Konfigurationsablage. Kein Geräteabruf aus der Projektverwaltung und keine Geräteschaltbefehle. Bestehende explizite Plansimulation bleibt getrennt verfügbar. Keine vollständigen Prognose-/Verbrauchermodule oder gemeinsame Mehrspeicherautomatik behauptet.

## Installation oder Update

1. In HACS auf **0.5.0** aktualisieren und Home Assistant neu starten. Vorhandenen Integrationseintrag behalten.
2. Browser neu laden, bei alter Ansicht einmal vollständig aktualisieren. Als Administrator links **Energiemanager** öffnen.
3. Bei Ersteinrichtung zunächst nur einen Projektnamen angeben; Sensoren und Geräte sind für diesen Test nicht erforderlich.

## Prüfschritte

1. **Grundmodul** öffnen: Produktversion **0.5.0**, Projektablage **SQLite**, Speicherformat **1**. Die tatsächlich registrierten Basisfunktionen heißen **Grundmodul**, **Konfigurationsspeicher** und **Projektverwaltung**. Deren eigene Modulversion ist zunächst **0.1.0**; sie ist bewusst getrennt von der Produktversion.
2. Bei einem bestehenden Projekt prüfen, ob Name, Geräte und Zuordnungen erhalten sind. Nach erfolgreicher Übernahme zeigt die Speicheranzeige den Hinweis auf die erhaltene bisherige Projektdatei. Bei einer leeren Neuinstallation ist kein Migrationshinweis erforderlich.
3. Zu **Projekt** wechseln. Namen ändern oder einen Test-Netzanschluss hinzufügen. **In Home Assistant speichern** anklicken. Anschließend zum Grundmodul wechseln und **Status aktualisieren** wählen. Ein gespeichertes Projekt muss entsprechend angezeigt werden; ungespeicherte Entwürfe sind davon ausdrücklich getrennt.
4. HA neu starten und denselben gespeicherten Projektstand erneut prüfen. Keine Integration löschen oder neu anlegen.
5. Optional zwei Browseransichten öffnen, beide denselben Ausgangsstand laden. In Ansicht A speichern, danach in Ansicht B einen anderen Entwurf speichern. B muss einen Versionskonflikt anzeigen, statt A zu überschreiben. Den eigenen Entwurf erst nach Vergleich des neuen Stands übernehmen.
6. Optional Projekt exportieren und die Datei lokal sichern. Reale Projektdateien und Datenbanken gehören nicht in öffentliche Issues oder Git.

Bei Fehlermeldung helfen Produktversion, betroffener Schritt und eine bereinigte Fehlermeldung. Zugangsdaten, vollständige Standortprojekte und Datenbankdateien nicht ungeprüft veröffentlichen.

## Speicherung und Übernahme

Aktiver Projektstand: HA-Konfigurationsverzeichnis, `.storage/pohl_solutions_energiemanager.sqlite3`. Die SQLite-Projektablage ist nach erfolgreicher Übernahme die einzige Schreibquelle. Die bisherige HA-Datei `.storage/pohl_solutions_energiemanager.project` wird bei Migration nur gelesen und bleibt bytegleich erhalten. Nachfolgende Änderungen werden nicht zusätzlich in diese alte Datei geschrieben.

Die alte Datei ist eine Sicherung des Übernahmezeitpunkts, keine aktuelle Spiegelung. Ein späteres Zurückwechseln zu 0.4 liest daher nicht automatisch neuere Änderungen aus SQLite. Vor einem solchen Versionswechsel den aktuellen Projektstand zusätzlich exportieren bzw. eine passende HA-Sicherung erstellen. Es gibt noch keinen automatischen Downgrade-Assistenten oder vollständigen Datenbank-Backup-/Restore-Dialog.

Unbekannte/neue oder beschädigte Speicherformate werden abgelehnt; sie werden nicht mit einem leeren Projekt überschrieben. Ist bereits ein gültiges SQLite-Projekt vorhanden, bleibt dieses maßgeblich. Abbruch während einer laufenden Speicherung wird erst nach Abschluss der begonnenen Executoroperation behandelt, damit Eigentum und Revisionsstand nicht auseinanderlaufen.

## Tatsächlicher Prüfumfang

- Python-Kern-/Speichertests sowie Node-Oberflächentests werden vor Paketbau ausgeführt.
- Browserprüfung mit simulierter HA-Anbindung: Desktop und 390×844-Mobilformat, Navigation, tatsächliche Statusfelder, Projektentwurf und Speichern nach Statusabruf. Das ist keine Prüfung in der laufenden Nutzeranlage.
- GitHub Actions führt `tools/ha_smoke.py` gegen echte HA-Serverkomponenten aus: Legacy-Übernahme, Originaldateierhalt, Neustart/Reload, Konflikte, fehlerhafte Speicherstände, unterbrochene Schreibvorgänge und Administratorzugriff. Geräteschnittstellen werden dabei nicht geöffnet.
- Das HACS-Archiv enthält dieselben geprüften Frontenddateien, keine privaten Projekte oder Laufzeitdatenbanken.

Die Modulübersicht zeigt Aufrufverfügbarkeit der Basisfunktionen. Sie bestätigt keine angeschlossenen Geräte, Datenfrische, Prognosegüte oder geprüfte Anlagenautomatik. Weitere Module und deren gemeinsame Formulare werden auf dieser Grundlage ergänzt.
