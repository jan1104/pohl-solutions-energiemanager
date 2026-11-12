"""Async, scoped module configuration access through the shared database.

The injected executor owns scheduling. Opening a context is explicit and never
initializes a database, migrates configuration, or opens device connections.
"""

import asyncio
from dataclasses import dataclass
from functools import partial
import json

from .modules import ModuleManifest
from .storage import ModuleStorage, SQLiteStorage, _identifier, _prepare_changes


async def _async_complete(executor, operation):
    """Drain submitted work before propagating cancellation, including writes."""
    job = asyncio.ensure_future(executor(operation))
    cancelled = False
    while not job.done():
        try:
            await asyncio.shield(job)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            break
    if cancelled:
        # Retrieve any worker exception without exposing a spurious late failure.
        if not job.cancelled():
            job.exception()
        raise asyncio.CancelledError
    return job.result()


@dataclass(frozen=True, slots=True)
class AsyncModuleStorage:
    """Fixed namespace; no public SQL, initialization or migration interface."""

    _handle: ModuleStorage
    _executor: object

    @property
    def project_id(self):
        return self._handle.project_id

    @property
    def module_id(self):
        return self._handle.module_id

    @property
    def schema_version(self):
        return self._handle.schema_version

    async def async_get(self, key):
        _identifier(key)
        return await _async_complete(self._executor, partial(self._handle.get, key))

    async def async_put(self, key, data, *, expected_revision):
        return (await self.async_put_many({key: (expected_revision, data)}))[key]

    async def async_put_many(self, changes):
        # Validate and detach JSON before the first await / worker queue entry.
        prepared = _prepare_changes(changes)
        snapshot = {key: (revision, json.loads(encoded))
                    for key, (revision, encoded) in prepared.items()}
        return await _async_complete(self._executor, partial(self._handle.put_many, snapshot))


@dataclass(frozen=True, slots=True)
class ModuleContext:
    """Captured module identity and configuration scope, not active-project proof."""

    manifest: ModuleManifest
    storage: AsyncModuleStorage

    @property
    def project_id(self):
        return self.storage.project_id


async def async_module_context(repository, executor, project_id, manifest, *,
                               schema_version, compatible_versions=()):
    """Explicitly open a module namespace in an already initialized database.

    Built-in module IDs are reserved for their existing owners. Code and storage
    schema versions are independent. Existing contexts never follow a new active
    project ID; migrations remain a separate core-owned operation.
    """
    if not isinstance(repository, SQLiteStorage) or not callable(executor):
        raise ValueError("An existing repository and executor are required")
    if not isinstance(manifest, ModuleManifest):
        raise ValueError("A module manifest is required")
    if manifest.module_id in {"core", "storage", "project"}:
        raise ValueError("Built-in module storage is reserved")
    _identifier(project_id)
    # Freeze iterable input before handing it to another thread.
    compatible_versions = tuple(compatible_versions)
    operation = partial(repository.for_module, project_id, manifest.module_id,
                        schema_version=schema_version, compatible_versions=compatible_versions)
    handle = await _async_complete(executor, operation)
    return ModuleContext(manifest, AsyncModuleStorage(handle, executor))
