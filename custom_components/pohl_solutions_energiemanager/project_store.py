"""Persist one validated planning project, without opening any connections."""

import asyncio
import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .core.project import export_project_json, load_project_json, project_summary, validate_project

DATA_PROJECT_STORE = f"{DOMAIN}_project_store"


class ProjectStore:
    """Swap active data only after a validated candidate was saved successfully."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.project", atomic_writes=True)
        self._project: dict[str, Any] | None = None
        self._lock = asyncio.Lock()
        self._loaded = False

    async def async_load(self) -> None:
        """Validate storage as strictly as an imported project."""
        async with self._lock:
            if self._loaded:
                return
            stored = await self._store.async_load()
            self._project = validate_project(stored) if stored is not None else None
            self._loaded = True

    async def async_import(self, project_json: str) -> dict[str, Any]:
        """Reject invalid input without touching disk or the active project."""
        candidate = await self._hass.async_add_executor_job(load_project_json, project_json)
        async with self._lock:
            await self._store.async_save(candidate)
            # HA Store logs some write errors instead of raising them. Verify
            # the actual file, not Store's in-memory/cache state, before swapping.
            persisted = await self._hass.async_add_executor_job(self._read_persisted)
            if persisted != candidate:
                raise OSError("Project could not be confirmed in persistent storage")
            self._project = candidate
            return self.status()

    def _read_persisted(self) -> dict[str, Any]:
        envelope = json.loads(Path(self._store.path).read_text(encoding="utf-8"))
        return validate_project(envelope["data"])

    def export(self) -> dict[str, Any]:
        """Return an independent serialized snapshot, never mutable internals."""
        return {
            "planning_only": True,
            "project_json": export_project_json(self._project) if self._project is not None else None,
        }

    def status(self) -> dict[str, Any]:
        """Distinguish empty project storage from a configured simulation."""
        return {
            "planning_only": True,
            "has_project": self._project is not None,
            "summary": project_summary(self._project) if self._project is not None else None,
        }
