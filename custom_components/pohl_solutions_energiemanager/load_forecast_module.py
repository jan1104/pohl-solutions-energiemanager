"""Explicit load-forecast feature; no discovery, providers or automatic planning."""

from dataclasses import dataclass
from datetime import datetime, tzinfo
from functools import partial

from .core.module_context import _async_complete
from .core.modules import ModuleDependency, ModuleManifest, ModuleUnavailable, ModuleVersion
from .forecasting import LoadObservation, predict_load

MANIFEST = ModuleManifest(
    'load_forecast', 'Lastprognose', ModuleVersion(0, 1, 1), 1,
    tuple(ModuleDependency(key, ModuleVersion(0, 1, 6 if key == 'core' else 0), ModuleVersion(0, 2, 0))
          for key in ('core', 'storage')))
CONFIG_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class LoadForecastRequest:
    observations: tuple[LoadObservation, ...]
    starts: tuple[datetime, ...]
    as_of: datetime
    local_zone: tzinfo

    def __post_init__(self):
        if (not isinstance(self.observations, (list, tuple)) or len(self.observations) > 60_000
                or not all(isinstance(x, LoadObservation) for x in self.observations)):
            raise ValueError('Provide at most 60000 interval observations')
        if not isinstance(self.starts, (list, tuple)) or not 1 <= len(self.starts) <= 384:
            raise ValueError('Provide between 1 and 384 forecast targets')
        object.__setattr__(self, 'observations', tuple(self.observations))
        object.__setattr__(self, 'starts', tuple(self.starts))


class LoadForecastModule:
    """Trusted handler for BaseRuntime.async_register_module, manually registered.

    The injected executor must schedule synchronous work off the event loop.
    The existing drain helper waits for submitted work even on cancellation.
    Results are scenarios, never a claim of verified forecast accuracy.
    """

    def __init__(self, executor):
        if not callable(executor):
            raise ValueError('An explicit async executor is required')
        self._executor = executor

    async def __call__(self, context, request):
        if (context.manifest != MANIFEST or context.storage.schema_version != CONFIG_SCHEMA_VERSION
                or context.storage.module_id != MANIFEST.module_id):
            raise ValueError('A matching load forecast module context is required')
        if not isinstance(request, LoadForecastRequest):
            raise ValueError('A load forecast request is required')
        document = await context.storage.async_get('settings')
        settings = document.data if document is not None else {}
        if set(settings) - {'lookback_days', 'min_sample_days', 'half_life_days'}:
            raise ValueError('Unknown load forecast setting')
        operation = partial(predict_load, list(request.observations), list(request.starts),
                            as_of=request.as_of, local_zone=request.local_zone, **settings)
        result = tuple(await _async_complete(self._executor, operation))
        latest = await context.storage.async_get('settings')
        if (latest.revision if latest is not None else None) != (document.revision if document is not None else None):
            raise ModuleUnavailable('Load forecast settings changed during computation')
        return result
