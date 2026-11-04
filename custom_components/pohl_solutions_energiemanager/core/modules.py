"""Versioned in-process module kernel. Registration never runs module code.

This is cooperative async isolation, not a security boundary or hot updater.
No package downloads, dynamic imports, devices or Home Assistant dependencies.
"""

import asyncio
from dataclasses import dataclass, field
import inspect
import re
from typing import Awaitable, Callable


def _module_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value):
        raise ValueError("Module ID must be a stable lowercase identifier")


@dataclass(frozen=True, order=True, slots=True)
class ModuleVersion:
    major: int
    minor: int
    patch: int

    def __post_init__(self):
        if any(type(v) is not int or not 0 <= v <= 999999 for v in (self.major, self.minor, self.patch)):
            raise ValueError("Version parts must be nonnegative bounded integers")

    @classmethod
    def parse(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r"(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})", value):
            raise ValueError("Use a stable major.minor.patch version without prerelease labels")
        return cls(*(int(part) for part in value.split(".")))

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass(frozen=True, slots=True)
class ModuleDependency:
    module_id: str
    minimum: ModuleVersion
    maximum_exclusive: ModuleVersion

    def __post_init__(self):
        _module_id(self.module_id)
        if not isinstance(self.minimum, ModuleVersion) or not isinstance(self.maximum_exclusive, ModuleVersion) or self.minimum >= self.maximum_exclusive:
            raise ValueError("Dependency requires a nonempty explicit version range")


@dataclass(frozen=True, slots=True)
class ModuleManifest:
    module_id: str
    name: str
    version: ModuleVersion
    api_major: int
    dependencies: tuple[ModuleDependency, ...] = ()

    def __post_init__(self):
        _module_id(self.module_id)
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 160:
            raise ValueError("Module name is required")
        if not isinstance(self.version, ModuleVersion) or type(self.api_major) is not int or self.api_major < 1:
            raise ValueError("Explicit module and API versions are required")
        object.__setattr__(self, "dependencies", tuple(self.dependencies))
        ids = []
        for dependency in self.dependencies:
            if not isinstance(dependency, ModuleDependency) or dependency.module_id == self.module_id:
                raise ValueError("Invalid or self-referencing dependency")
            ids.append(dependency.module_id)
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate module dependency")


@dataclass(frozen=True, slots=True)
class ModuleState:
    status: str
    reasons: tuple[str, ...] = ()


@dataclass(slots=True)
class _Entry:
    manifest: ModuleManifest
    handler: Callable[[object], Awaitable[object]]
    enabled: bool = True
    failed: bool = False
    state: ModuleState = field(default_factory=lambda: ModuleState("new"))
    generation: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class ModuleUnavailable(RuntimeError):
    """Module is unavailable or changed while computing; do not use old output."""


class ModuleExecutionError(RuntimeError):
    """Module failed/timed out; errors are deliberately free of handler payloads."""


class ModuleRegistry:
    """One active version per module ID. Changing code requires a new runtime.

    Handlers must cooperate with async cancellation and must not block the event
    loop. No guarantee of isolation from CPU hangs, arbitrary shared mutations
    or a handler swallowing cancellation is made. No live actuator handlers.
    """

    API_MAJOR = 1

    def __init__(self):
        self._entries: dict[str, _Entry] = {}

    def register(self, manifest: ModuleManifest, handler):
        if not isinstance(manifest, ModuleManifest):
            raise ValueError("Module manifest required")
        if manifest.module_id in self._entries:
            raise ValueError("Module already registered; no in-place hot replacement")
        if len(self._entries) >= 128:
            raise ValueError("Module registry limit is 128")
        if not (inspect.iscoroutinefunction(handler) or inspect.iscoroutinefunction(getattr(handler, "__call__", None))):
            raise ValueError("Module handler must be async")
        self._entries[manifest.module_id] = _Entry(manifest, handler)
        self._reconcile()

    def _entry(self, module_id):
        if module_id not in self._entries:
            raise ValueError(f"Unknown module: {module_id}")
        return self._entries[module_id]

    def states(self):
        return {key: entry.state for key, entry in self._entries.items()}

    def manifests(self):
        return tuple(entry.manifest for entry in self._entries.values())

    def set_enabled(self, module_id, enabled):
        if type(enabled) is not bool:
            raise ValueError("enabled must be boolean")
        self._entry(module_id).enabled = enabled
        self._reconcile()

    def reset_failure(self, module_id):
        self._entry(module_id).failed = False
        self._reconcile()

    def _reconcile(self):
        resolved = {}

        def resolve(key, visiting):
            if key in resolved:
                return resolved[key]
            if key in visiting:
                return ModuleState("blocked", ("dependency_cycle",))
            entry = self._entries[key]
            if not entry.enabled:
                state = ModuleState("disabled")
            elif entry.failed:
                state = ModuleState("failed", ("execution_failed",))
            elif entry.manifest.api_major != self.API_MAJOR:
                state = ModuleState("blocked", ("incompatible_api",))
            else:
                reasons = []
                for dependency in entry.manifest.dependencies:
                    target = self._entries.get(dependency.module_id)
                    if target is None:
                        reasons.append(f"missing_dependency:{dependency.module_id}")
                    elif not dependency.minimum <= target.manifest.version < dependency.maximum_exclusive:
                        reasons.append(f"incompatible_dependency:{dependency.module_id}")
                    else:
                        dependency_state = resolve(dependency.module_id, visiting | {key})
                        if dependency_state.status != "ready":
                            reasons.append(f"unavailable_dependency:{dependency.module_id}")
                            if "dependency_cycle" in dependency_state.reasons:
                                reasons.append("dependency_cycle")
                state = ModuleState("blocked", tuple(dict.fromkeys(reasons))) if reasons else ModuleState("ready")
            resolved[key] = state
            return state

        for key in self._entries:
            resolve(key, set())
        for key, state in resolved.items():
            entry = self._entries[key]
            if entry.state != state:
                entry.generation += 1
                entry.state = state

    async def async_call(self, module_id, request=None, *, timeout=5.0):
        if type(timeout) not in (int, float) or not 0 < timeout <= 30:
            raise ValueError("Timeout must be greater than zero and at most 30 seconds")
        entry = self._entry(module_id)
        if entry.state.status != "ready":
            raise ModuleUnavailable(f"Module unavailable: {module_id}")
        generation = entry.generation
        acquired = False
        try:
            async with asyncio.timeout(timeout):
                async with entry.lock:
                    if entry.generation != generation or entry.state.status != "ready":
                        raise ModuleUnavailable(f"Module changed: {module_id}")
                    acquired = True
                    try:
                        result = await entry.handler(request)
                    except Exception:
                        if entry.generation != generation or entry.state.status != "ready":
                            raise ModuleUnavailable(f"Module changed: {module_id}") from None
                        entry.failed = True
                        self._reconcile()
                        raise ModuleExecutionError(f"Module execution failed: {module_id}") from None
                    if entry.generation != generation or entry.state.status != "ready":
                        raise ModuleUnavailable(f"Module changed: {module_id}")
                    return result
        except TimeoutError:
            # A queue timeout is a busy caller, not evidence of a broken handler.
            if entry.generation != generation or entry.state.status != "ready":
                raise ModuleUnavailable(f"Module changed: {module_id}") from None
            if acquired:
                entry.failed = True
                self._reconcile()
            raise ModuleExecutionError(f"Module request timed out: {module_id}") from None
