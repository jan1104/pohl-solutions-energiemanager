"""Actual in-process base modules backed by the active SQLite project store."""

from typing import Any

from .const import NAME, VERSION
from .core.modules import (
    ModuleDependency,
    ModuleExecutionError,
    ModuleManifest,
    ModuleRegistry,
    ModuleUnavailable,
    ModuleVersion,
)
from .project_store import ProjectStore

DATA_BASE_RUNTIME = "pohl_solutions_energiemanager_base_runtime"
CORE_MODULE_VERSION = "0.1.0"
STORAGE_MODULE_VERSION = "0.1.0"
PROJECT_MODULE_VERSION = "0.1.0"


class BaseRuntime:
    """Base availability is independent of forecasts and has no device transport."""

    def __init__(self, store: ProjectStore) -> None:
        self._store = store
        self.registry = ModuleRegistry()
        self._loaded = False
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
        self._loaded = True
        await self.async_system_status()

    async def async_stop(self) -> None:
        self._loaded = False
        for manifest in self.registry.manifests():
            self.registry.set_enabled(manifest.module_id, False)

    async def async_system_status(self) -> dict[str, Any]:
        if not self._loaded:
            raise RuntimeError("Base runtime is not loaded")
        database = {"backend": "sqlite", "schema_version": 1, "project_persisted": False}
        # A failed storage health check must not prevent returning diagnostic state.
        for manifest in self.registry.manifests():
            if self.registry.states()[manifest.module_id].status == "failed":
                self.registry.reset_failure(manifest.module_id)
            try:
                result = await self.registry.async_call(manifest.module_id)
            except (ModuleExecutionError, ModuleUnavailable):
                continue
            if manifest.module_id == "storage":
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
