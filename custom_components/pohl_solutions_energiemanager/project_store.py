"""Persist the single active project in SQLite; retain legacy HA storage read-only."""

import asyncio
import json
from hashlib import sha256
from os import fstat
from pathlib import Path
import sqlite3
from typing import Any, NoReturn

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .core.project import COLLECTIONS, MAX_BYTES, export_project_json, load_project_json, project_summary, validate_project
from .core.project_migration import commit_project_v2, preview_project_v2
from .core.project_v2 import export_project_v2_json, load_project_v2_json, project_summary_v2, validate_project_v2
from .core.storage import SQLiteStorage, StorageConflict, StorageSchemaError

DATA_PROJECT_STORE = f"{DOMAIN}_project_store"
# Old HA Store envelopes use indentation. At the supported JSON depth (24),
# whitespace can expand a valid 2 MiB project considerably. This bound is only
# for reading that trusted local legacy envelope; canonical limits stay 2 MiB.
MAX_LEGACY_ENVELOPE_BYTES = 64 * MAX_BYTES + 65536


class ProjectConflictError(ValueError):
    """The caller edited an obsolete project revision."""


def _legacy_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Legacy project storage contains duplicate keys")
        result[key] = value
    return result


def _legacy_constant(value):
    raise ValueError("Legacy project storage contains a non-finite number")


def _validate_stored(data, namespace):
    validator = validate_project_v2 if namespace.schema_version == 2 else validate_project
    return validator(data)


class ProjectStore:
    """Use public content-SHA revisions and private SQLite compare-and-swap."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._legacy_path = Path(hass.config.path(".storage", f"{DOMAIN}.project"))
        self._repository = SQLiteStorage(hass.config.path(".storage", f"{DOMAIN}.sqlite3"))
        self._namespace = None
        self._document_revision: int | None = None
        self._project: dict[str, Any] | None = None
        self._lock = asyncio.Lock()
        self._loaded = False
        self._migration_status = "not_needed"
        self._legacy_retained = False

    async def _async_durable_call(self, function, *args):
        """Drain an executor write before releasing ownership, even on cancellation."""
        job = self._hass.async_add_executor_job(function, *args)
        cancelled = False
        try:
            while not job.done():
                try:
                    await asyncio.shield(job)
                except asyncio.CancelledError:
                    cancelled = True
            return job.result(), cancelled
        except sqlite3.Error as err:
            raise OSError("SQLite project storage operation failed") from err

    def _sync_load(self):
        self._repository.path.parent.mkdir(parents=True, exist_ok=True)
        self._repository.initialize()
        namespace = self._repository.for_module("global", "project", schema_version=1, compatible_versions=(2,))
        current = namespace.get("active")
        if current is not None:
            project = _validate_stored(current.data, namespace)
            metadata = namespace.get("migration")
            status = "migrated_legacy" if metadata and metadata.data.get("status") == "migrated_legacy" else "sqlite_existing"
            return namespace, current.revision, project, status, self._legacy_path.exists()
        if namespace.schema_version == 2:
            raise StorageSchemaError("Projektformat 2 ohne aktives Projekt")
        if not self._legacy_path.exists():
            return namespace, None, None, "not_needed", False
        # Do not use Store.async_load: corrupt/unsupported files can become None.
        # The legacy envelope must remain byte-identical, including its version.
        with self._legacy_path.open("rb") as stream:
            length = fstat(stream.fileno()).st_size
            if length > MAX_LEGACY_ENVELOPE_BYTES:
                raise ValueError("Legacy project storage exceeds the size limit")
            # Do not preallocate the full legacy allowance for a tiny project.
            raw = stream.read(length + 1)
            if len(raw) > length:
                raise ValueError("Legacy project storage changed while reading; retry setup")
        if len(raw) > MAX_LEGACY_ENVELOPE_BYTES:
            raise ValueError("Legacy project storage exceeds the size limit")
        try:
            envelope = json.loads(raw.decode("utf-8"), object_pairs_hook=_legacy_object,
                                  parse_constant=_legacy_constant)
        except (UnicodeError, json.JSONDecodeError) as err:
            raise ValueError("Legacy project storage is invalid; original file was retained") from err
        if not isinstance(envelope, dict) or type(envelope.get("version")) is not int or envelope["version"] != 1:
            raise ValueError("Unsupported legacy project storage version")
        if type(envelope.get("minor_version", 1)) is not int or envelope.get("minor_version", 1) != 1:
            raise ValueError("Unsupported legacy project storage minor version")
        if envelope.get("key", f"{DOMAIN}.project") != f"{DOMAIN}.project":
            raise ValueError("Legacy project storage identity does not match")
        project = validate_project(envelope.get("data"))
        metadata = namespace.get("migration")
        try:
            namespace.put_many({
                "active": (None, project),
                "migration": (metadata.revision if metadata else None, {
                    "status": "migrated_legacy", "legacy_sha256": sha256(raw).hexdigest(),
                    "legacy_retained": True,
                }),
            })
        except StorageConflict:
            # Another instance may have completed the create-only transaction.
            winner = namespace.get("active")
            if winner is None:
                raise
            return namespace, winner.revision, validate_project(winner.data), "sqlite_existing", True
        persisted = namespace.get("active")
        if persisted is None or validate_project(persisted.data) != project:
            raise OSError("Migrated project could not be confirmed in SQLite")
        return namespace, persisted.revision, validate_project(persisted.data), "migrated_legacy", True

    async def async_load(self) -> None:
        async with self._lock:
            if self._loaded:
                return
            loaded, cancelled = await self._async_durable_call(self._sync_load)
            self._apply_loaded(loaded)
            self._loaded = True
            if cancelled:
                raise asyncio.CancelledError

    def _apply_loaded(self, loaded):
        self._namespace, self._document_revision, self._project, self._migration_status, self._legacy_retained = loaded

    async def async_import(self, project_json: str, expected_revision: str | None = None) -> dict[str, Any]:
        async with self._lock:
            if not self._loaded:
                raise RuntimeError("Project storage must be loaded before importing")
            if expected_revision is not None and expected_revision != self.revision:
                raise ProjectConflictError("Das Projekt wurde zwischenzeitlich geändert. Neu laden und Änderungen erneut prüfen.")
            loader = load_project_v2_json if self._namespace.schema_version == 2 else load_project_json
            candidate = await self._hass.async_add_executor_job(loader, project_json)
            await self._async_commit(candidate)
            return self.status()

    def _check_migration_source(self, expected_revision: str) -> None:
        if not self._loaded:
            raise RuntimeError("Project storage must be loaded before migration")
        if expected_revision != self.revision:
            raise ProjectConflictError("Das Projekt wurde zwischenzeitlich geändert. Neu laden und die Übernahme erneut prüfen.")
        if self._project is None or self._namespace.schema_version != 1:
            raise ValueError("Für die Übernahme ist ein gespeichertes Projekt im Format 1 erforderlich.")

    def _sync_migration_preview(self, expected_revision):
        preview = preview_project_v2(self._namespace)
        if preview.source_sha256 != expected_revision or preview.source_revision != self._document_revision:
            raise StorageConflict("Project changed before migration preview")
        return {"project_json": export_project_v2_json(preview.project),
                "revision": preview.source_sha256, "source_revision": preview.source_revision}

    async def async_migration_preview(self, expected_revision: str) -> dict[str, Any]:
        """Read the persisted source and return a preview bound to both revisions."""
        async with self._lock:
            self._check_migration_source(expected_revision)
            try:
                preview, cancelled = await self._async_durable_call(self._sync_migration_preview, expected_revision)
            except (StorageConflict, StorageSchemaError) as err:
                await self._async_reload_conflict(err)
            if cancelled:
                raise asyncio.CancelledError
            return preview

    def _sync_migrate_project(self, expected_revision, source_revision):
        commit_project_v2(self._namespace, expected_revision=source_revision, expected_sha256=expected_revision)
        return self._sync_load()

    async def async_migrate_project(self, expected_revision: str, source_revision: int) -> dict[str, Any]:
        """Persist the exact migration of the confirmed source revision."""
        async with self._lock:
            self._check_migration_source(expected_revision)
            try:
                loaded, cancelled = await self._async_durable_call(
                    self._sync_migrate_project, expected_revision, source_revision,
                )
            except (StorageConflict, StorageSchemaError) as err:
                await self._async_reload_conflict(err)
            self._apply_loaded(loaded)
            if cancelled:
                raise asyncio.CancelledError
            return self.snapshot()

    @property
    def revision(self) -> str:
        canonical = json.dumps(self._project, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return sha256(canonical.encode("utf-8")).hexdigest()

    def snapshot(self) -> dict[str, Any]:
        return {**self.export(), **self.status()}

    async def async_ensure_project(self, name: str, project_id: str) -> None:
        async with self._lock:
            if not self._loaded:
                raise RuntimeError("Project storage must be loaded before creating a project")
            if self._project is None:
                candidate = validate_project({
                    "format": "pohl-energy-project", "schema_version": 1,
                    "id": project_id, "name": name, "mode": "planning_only",
                    **{key: [] for key in COLLECTIONS}, "settings": {},
                })
                await self._async_commit(candidate)

    def _sync_commit(self, candidate, expected):
        stored = self._namespace.put("active", candidate, expected_revision=expected)
        persisted = self._namespace.get("active")
        if persisted is None or persisted.revision != stored.revision or _validate_stored(persisted.data, self._namespace) != candidate:
            raise OSError("Project could not be confirmed in persistent SQLite storage")
        return persisted

    async def _async_reload_conflict(self, error: Exception) -> NoReturn:
        loaded, cancelled = await self._async_durable_call(self._sync_load)
        self._apply_loaded(loaded)
        if cancelled:
            raise asyncio.CancelledError from error
        raise ProjectConflictError("Das dauerhaft gespeicherte Projekt wurde geändert. Neu laden und erneut prüfen.") from error

    async def _async_commit(self, candidate: dict[str, Any]) -> None:
        try:
            persisted, cancelled = await self._async_durable_call(self._sync_commit, candidate, self._document_revision)
        except (StorageConflict, StorageSchemaError) as err:
            await self._async_reload_conflict(err)
        self._project = _validate_stored(persisted.data, self._namespace)
        self._document_revision = persisted.revision
        if cancelled:
            raise asyncio.CancelledError

    async def async_storage_health(self) -> dict[str, Any]:
        async with self._lock:
            if not self._loaded or self._namespace is None:
                raise RuntimeError("Project storage is not loaded")
            current, cancelled = await self._async_durable_call(self._namespace.get, "active")
            if current is not None:
                _validate_stored(current.data, self._namespace)
            if cancelled:
                raise asyncio.CancelledError
            return {"backend": "sqlite", "schema_version": self._namespace.schema_version,
                    "project_persisted": current is not None,
                    "migration_status": self._migration_status,
                    "legacy_retained": self._legacy_retained}

    def export(self) -> dict[str, Any]:
        export = export_project_v2_json if self._project and self._project["schema_version"] == 2 else export_project_json
        return {"planning_only": True, "revision": self.revision,
                "project_json": export(self._project) if self._project is not None else None}

    def status(self) -> dict[str, Any]:
        summarize = project_summary_v2 if self._project and self._project["schema_version"] == 2 else project_summary
        return {"planning_only": True, "revision": self.revision,
                "has_project": self._project is not None,
                "summary": summarize(self._project) if self._project is not None else None}
