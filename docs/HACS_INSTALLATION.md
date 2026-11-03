# Installation und Updates über HACS

HACS verwendet öffentliche GitHub-Repositories. Ein privater Release ist für angemeldete berechtigte GitHub-Nutzer herunterladbar, aber nicht dadurch automatisch über HACS installierbar. Das Entwicklungsrepository bleibt privat, bis eine Änderung der Sichtbarkeit ausdrücklich freigegeben wurde. [Offizielle HACS-Einschränkung](https://hacs.xyz/docs/faq/private_repositories/), geprüft am 03.11.2026.

## Nach öffentlicher Freigabe

1. In HACS das Menü „Benutzerdefinierte Repositories“ öffnen.
2. `https://github.com/jan1104/pohl-solutions-energiemanager` eintragen, Typ „Integration“ auswählen.
3. Pohl Solutions Energiemanager herunterladen und Release `v0.3.0` auswählen.
4. Home Assistant neu starten.
5. Unter Einstellungen → Geräte & Dienste die Integration hinzufügen. Zum Einstieg „Nur Projektverwaltung (ohne Prognose und SOC)“ aktivieren.

Aktualisierungen werden über weitere GitHub-Releases bereitgestellt. Es gibt keine behauptete Aufnahme in den HACS-Standardkatalog. Die genaue Menübezeichnung kann je nach HACS-/HA-Version abweichen.

## Releasepaket

`hacs.json` benennt das Releaseasset `pohl_solutions_energiemanager.zip`. Darin liegen `manifest.json`, Pythonmodule, Services und Übersetzungen direkt im ZIP-Wurzelverzeichnis. HACS installiert sie in den Komponentenordner. Quellstruktur und Releaseformat gemäß [Integrationsanforderungen](https://www.hacs.dev/docs/publish/integration/) und [hacs.json-Dokumentation](https://www.hacs.dev/docs/publish/start/).

```powershell
python tools/build_release.py
```

Das Paket enthält ausschließlich die Integration: keine privaten Projektdateien, Zugangsdaten, Standortunterlagen oder Browserprofile. Die lokale Browser-Projektoberfläche gehört in 0.3 nicht zum installierten HA-Panel; sie bleibt separat. HA bietet zunächst Projektimport/-export/-status über Aktionen und lesbare Statussensoren. Keine Live-Gerätesteuerung oder gemeinsame Mehrspeicheroptimierung. Details: TESTING_0_3.md.
