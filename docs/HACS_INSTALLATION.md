# Installation und Updates über HACS

HACS verwendet öffentliche GitHub-Repositories. Das Repository wurde vom Nutzer öffentlich gestellt; Sichtbarkeit am 03.11.2026 bestätigt. Persönliche Konfiguration bleibt außerhalb des Repositorys. [Offizielle HACS-Einschränkung](https://hacs.xyz/docs/faq/private_repositories/), geprüft am 03.11.2026.

## Nach öffentlicher Freigabe

1. In HACS das Menü „Benutzerdefinierte Repositories“ öffnen.
2. `https://github.com/jan1104/pohl-solutions-energiemanager` eintragen, Typ „Integration“ auswählen.
3. Pohl Solutions Energiemanager herunterladen und das aktuelle Release auswählen.
4. Home Assistant neu starten.
5. Unter Einstellungen → Geräte & Dienste die Integration hinzufügen. Ab 0.3.1 zunächst nur den Namen des Energiemanagers eingeben. Sensorbasierte Testsimulation ist anschließend optional in den Integrationseinstellungen erreichbar.
6. Ab 0.4 als Administrator links „Energiemanager“ öffnen. Vorhandene Einträge beim Update erhalten; nach Neustart Browser neu laden, falls der Menüpunkt noch fehlt. Siehe HA_PANEL.md.

Aktualisierungen werden über weitere GitHub-Releases bereitgestellt. Es gibt keine behauptete Aufnahme in den HACS-Standardkatalog. Die genaue Menübezeichnung kann je nach HACS-/HA-Version abweichen.

## Releasepaket

`hacs.json` benennt das Releaseasset `pohl_solutions_energiemanager.zip`. Darin liegen `manifest.json`, Pythonmodule, Services und Übersetzungen direkt im ZIP-Wurzelverzeichnis. HACS installiert sie in den Komponentenordner. Quellstruktur und Releaseformat gemäß [Integrationsanforderungen](https://www.hacs.dev/docs/publish/integration/) und [hacs.json-Dokumentation](https://www.hacs.dev/docs/publish/start/).

```powershell
python tools/build_release.py
```

Das Paket enthält die Integration einschließlich eingebauter Projektoberfläche: keine privaten Projektdateien, Zugangsdaten, Standortunterlagen oder Browserprofile. Keine Live-Gerätesteuerung oder gemeinsame Mehrspeicheroptimierung. Aktuelle Bedienung: HA_PANEL.md; historische erste Testversion: TESTING_0_3.md.
