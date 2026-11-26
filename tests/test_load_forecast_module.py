"""Explicit feature calls with temporary SQLite and synthetic history only."""

import asyncio
from datetime import datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.fixture(scope='module')
def feature():
    package = ModuleType('_pohl_forecast_feature')
    package.__path__ = [str(Path(__file__).resolve().parents[1] /
                            'custom_components/pohl_solutions_energiemanager')]
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(sys.modules, package.__name__, package)
        yield import_module(f'{package.__name__}.load_forecast_module')


def test_explicit_module_uses_scoped_settings_and_preserves_request(feature, tmp_path):
    async def run():
        storage = import_module(f'{feature.__package__}.core.storage')
        contexts = import_module(f'{feature.__package__}.core.module_context')
        repo = storage.SQLiteStorage(tmp_path / 'shared.sqlite')
        repo.initialize()
        context = await contexts.async_module_context(repo, asyncio.to_thread, 'synthetic',
            feature.MANIFEST, schema_version=feature.CONFIG_SCHEMA_VERSION)
        now = datetime(2026, 11, 24, tzinfo=timezone.utc)
        history = [feature.LoadObservation(now - timedelta(days=1), 12)]
        starts = [now]
        request = feature.LoadForecastRequest(history, starts, now, timezone.utc)
        history.clear()
        starts.clear()
        calls = []
        async def executor(operation):
            calls.append(True)
            return await asyncio.to_thread(operation)
        handler = feature.LoadForecastModule(executor)
        assert not calls
        # Without enough history, default settings fail instead of inventing data.
        with pytest.raises(ValueError, match='Zu wenig'):
            await handler(context, request)
        await context.storage.async_put('settings', {'min_sample_days': 1}, expected_revision=None)
        result = await handler(context, request)
        assert isinstance(result, tuple) and result[0].p50_kw == 12
        assert (await context.storage.async_get('settings')).revision == 1
        await context.storage.async_put('settings', {'invented': True}, expected_revision=1)
        before = len(calls)
        with pytest.raises(ValueError, match='Unknown'):
            await handler(context, request)
        assert len(calls) == before
    asyncio.run(run())


def test_request_limits_and_executor_are_explicit(feature):
    now = datetime(2026, 11, 24, tzinfo=timezone.utc)
    for observations, starts in [([], []), ([], [now] * 385),
                                 ([None], [now]), ([feature.LoadObservation(now, 1)] * 60001, [now])]:
        with pytest.raises(ValueError):
            feature.LoadForecastRequest(observations, starts, now, timezone.utc)
    with pytest.raises(ValueError):
        feature.LoadForecastModule(None)


@pytest.mark.parametrize('existing', [False, True])
def test_changed_settings_discard_old_forecast_and_allow_explicit_retry(feature, tmp_path, existing):
    async def run():
        storage = import_module(f'{feature.__package__}.core.storage')
        contexts = import_module(f'{feature.__package__}.core.module_context')
        repo = storage.SQLiteStorage(tmp_path / 'shared.sqlite')
        repo.initialize()
        context = await contexts.async_module_context(repo, asyncio.to_thread, 'synthetic',
            feature.MANIFEST, schema_version=feature.CONFIG_SCHEMA_VERSION)
        if existing:
            await context.storage.async_put('settings', {'min_sample_days': 3}, expected_revision=None)
        now = datetime(2026, 11, 24, tzinfo=timezone.utc)
        request = feature.LoadForecastRequest(
            [feature.LoadObservation(now - timedelta(weeks=i), value) for i, value in [(1, 30), (2, 10), (3, 10)]],
            [now], now, timezone.utc)
        entered, release = asyncio.Event(), asyncio.Event()
        async def executor(operation):
            entered.set()
            await release.wait()
            return await asyncio.to_thread(operation)
        handler = feature.LoadForecastModule(executor)
        task = asyncio.create_task(handler(context, request))
        try:
            await asyncio.wait_for(entered.wait(), 5)
            await context.storage.async_put('settings', {'half_life_days': 1}, expected_revision=1 if existing else None)
            release.set()
            with pytest.raises(feature.ModuleUnavailable):
                await task
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
        assert (await handler(context, request))[0].p50_kw == 30
    asyncio.run(run())


@pytest.mark.parametrize('patch,expected', [(5, 'blocked'), (6, 'ready')])
def test_feature_requires_kernel_with_transient_unavailability_semantics(feature, patch, expected):
    modules = import_module(f'{feature.__package__}.core.modules')
    registry = modules.ModuleRegistry()
    async def echo(request):
        return request
    for key, version in [('core', modules.ModuleVersion(0, 1, patch)), ('storage', modules.ModuleVersion(0, 1, 0))]:
        registry.register(modules.ModuleManifest(key, key, version, 1), echo)
    registry.register(feature.MANIFEST, echo)
    assert registry.states()['load_forecast'].status == expected


def test_module_does_not_read_foreign_context_and_drains_cancelled_work(feature):
    async def run():
        now = datetime(2026, 11, 24, tzinfo=timezone.utc)
        request = feature.LoadForecastRequest(
            [feature.LoadObservation(now - timedelta(weeks=i), 10) for i in range(1, 4)],
            [now], now, timezone.utc)
        get = AsyncMock(return_value=None)
        context = SimpleNamespace(manifest=None, storage=SimpleNamespace(
            schema_version=1, module_id='other', async_get=get))
        handler = feature.LoadForecastModule(asyncio.to_thread)
        with pytest.raises(ValueError, match='matching'):
            await handler(context, request)
        get.assert_not_called()
        context.manifest = feature.MANIFEST
        with pytest.raises(ValueError, match='matching'):
            await handler(context, request)
        get.assert_not_called()
        context.storage.module_id = feature.MANIFEST.module_id
        entered, release, completed = asyncio.Event(), asyncio.Event(), []
        async def executor(operation):
            entered.set()
            await release.wait()
            result = await asyncio.to_thread(operation)
            completed.append(True)
            return result
        handler = feature.LoadForecastModule(executor)
        task = asyncio.create_task(handler(context, request))
        await entered.wait()
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert completed == [True]
    asyncio.run(run())
