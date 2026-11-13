"""Actual in-process base modules backed by the active SQLite project store."""

import asyncio
import json
from typing import Any

from .adapters.connections import ReadOnlyConnectionManager
from .adapters.modbus_measurement import read_modbus_power_measurement
from .const import NAME, VERSION
from .core.modules import (
    ModuleDependency,
    ModuleExecutionError,
    ModuleManifest,
    ModuleRegistry,
    ModuleUnavailable,
    ModuleVersion,
)
from .project_store import ProjectConflictError, ProjectStore

DATA_BASE_RUNTIME = "pohl_solutions_energiemanager_base_runtime"
CORE_MODULE_VERSION = "0.1.3"
STORAGE_MODULE_VERSION = "0.1.0"
PROJECT_MODULE_VERSION = "0.1.0"


async def _async_drain(job):
    """Complete owned cleanup, including lock waits, before propagating abort."""
    cancelled = False
    while not job.done():
        try:
            await asyncio.shield(job)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            break
    if cancelled:
        if not job.cancelled():
            job.exception()
        raise asyncio.CancelledError
    return job.result()


class BaseRuntime:
    """Base services own lazy read-only transport; setup never reads devices."""

    def __init__(self, store: ProjectStore) -> None:
        self._store = store
        self.registry = ModuleRegistry()
        self._loaded = False
        self._stop_task = None
        self._stopped = False
        self._connection_lock = asyncio.Lock()
        self._connections = None
        self._connection_revision = None
        core_version = ModuleVersion.parse(CORE_MODULE_VERSION)
        storage_version = ModuleVersion.parse(STORAGE_MODULE_VERSION)
        project_version = ModuleVersion.parse(PROJECT_MODULE_VERSION)
        compatible_minimum, compatible_upper = ModuleVersion(0, 1, 0), ModuleVersion(0, 2, 0)
        core_dependency = ModuleDependency("core", compatible_minimum, compatible_upper)
        storage_dependency = ModuleDependency("storage", compatible_minimum, compatible_upper)
        self.registry.register(ModuleManifest("core", "Grundmodul", core_version, 1), self._core)
        self.registry.register(ModuleManifest("storage", "Konfigurationsspeicher", storage_version, 1,
                                              (core_dependency,)), self._storage)
        self.registry.register(ModuleManifest("project", "Projektverwaltung", project_version, 1,
                                              (core_dependency, storage_dependency)), self._project)

    async def _core(self, request):
        return {"name": NAME, "product_version": VERSION, "planning_only": True}

    async def _storage(self, request):
        return await self._store.async_storage_health()

    async def _project(self, request):
        return self._store.snapshot()

    async def async_start(self) -> None:
        if self._stopped:
            raise RuntimeError("Stopped base runtime cannot restart; create a new runtime")
        self._loaded = True
        await self.async_system_status()

    async def _async_close_connections(self):
        if self._connections is None:
            return
        await _async_drain(asyncio.create_task(self._connections.async_close()))
        self._connections = None
        self._connection_revision = None

    async def async_stop(self) -> None:
        self._loaded = False
        self._stopped = True
        for manifest in self.registry.manifests():
            self.registry.set_enabled(manifest.module_id, False)
        if self._stop_task is None:
            self._stop_task = asyncio.create_task(self._async_stop_connections())
        await _async_drain(self._stop_task)

    async def _async_stop_connections(self):
        async with self._connection_lock:
            await self._async_close_connections()

    async def async_read_registers(self, connection_id, *, expected_revision,
                                   unit_id, address, count, function_code=3):
        """Explicit internal read API; no service, polling or automatic activation.

        Bind to the local ProjectStore revision. Configuration changes drain the
        old owner before creating a new one; results from obsolete owners fail.
        This does not certify freshness of external edits or device measurements.
        """
        async with self._connection_lock:
            if not self._loaded:
                raise RuntimeError("Base runtime is not loaded")
            if not isinstance(expected_revision, str) or expected_revision != self._store.revision:
                raise ProjectConflictError("Projektstand vor dem Lesen aktualisieren.")
            if self._connection_revision != expected_revision:
                await self._async_close_connections()
                if not self._loaded or expected_revision != self._store.revision:
                    raise ProjectConflictError("Projektstand während des Verbindungswechsels geändert.")
                raw = self._store.export()["project_json"]
                if raw is None:
                    raise ValueError("A saved project is required before reading")
                project = json.loads(raw)
                self._connections = ReadOnlyConnectionManager(project["connections"])
                self._connection_revision = expected_revision
            manager = self._connections
        result = await manager.read_registers(connection_id, unit_id=unit_id,
                                              address=address, count=count,
                                              function_code=function_code)
        if (not self._loaded or manager is not self._connections
                or expected_revision != self._store.revision):
            raise ProjectConflictError("Leseergebnis gehört zu einem überholten Projektstand.")
        return result

    async def async_read_power_measurement(
        self, measurement_id, *, expected_revision, source_id, byte_order,
        word_order, polarity, max_age, measured_at=None, receipt_clock=None,
    ):
        """Explicitly read and bind one saved Modbus power mapping; no persistence.

        The adapter preserves verified caller-supplied source/time metadata.
        A transport reply alone never supplies a device measurement timestamp.
        """
        if not self._loaded:
            raise RuntimeError("Base runtime is not loaded")
        if not isinstance(expected_revision, str) or expected_revision != self._store.revision:
            raise ProjectConflictError("Projektstand vor dem Lesen aktualisieren.")
        raw = self._store.export()["project_json"]
        if raw is None:
            raise ValueError("A saved project is required before reading")
        project = json.loads(raw)
        runtime = self

        class Reader:
            def __init__(self, connection_id):
                self.connection_id = connection_id

            async def read_registers(self, *, unit_id, address, count, function_code=3):
                return await runtime.async_read_registers(
                    self.connection_id, expected_revision=expected_revision,
                    unit_id=unit_id, address=address, count=count,
                    function_code=function_code)

        result = await read_modbus_power_measurement(
            project, measurement_id, reader_for_connection=Reader,
            source_id=source_id, byte_order=byte_order, word_order=word_order,
            polarity=polarity, max_age=max_age, measured_at=measured_at,
            receipt_clock=receipt_clock)
        if not self._loaded or expected_revision != self._store.revision:
            raise ProjectConflictError("Leseergebnis gehört zu einem überholten Projektstand.")
        return result

    async def async_system_status(self) -> dict[str, Any]:
        if not self._loaded:
            raise RuntimeError("Base runtime is not loaded")
        database = {"backend": "sqlite", "schema_version": 1, "project_persisted": False}
        # Only these built-in handlers are diagnostic reads. Registered feature
        # handlers may perform work; opening status must not call or retry them.
        for module_id in ("core", "storage", "project"):
            if self.registry.states()[module_id].status == "failed":
                self.registry.reset_failure(module_id)
            try:
                result = await self.registry.async_call(module_id)
            except (ModuleExecutionError, ModuleUnavailable):
                continue
            if module_id == "storage":
                database = result
        states = self.registry.states()
        return {
            "product_version": VERSION,
            "database": database,
            "modules": [{"id": manifest.module_id, "name": manifest.name,
                         "version": str(manifest.version),
                         "status": states[manifest.module_id].status,
                         "reasons": list(states[manifest.module_id].reasons)}
                        for manifest in self.registry.manifests()],
            "planning_only": True,
        }
