"""Shared module configuration access with temporary SQLite, never devices."""

import asyncio
from dataclasses import FrozenInstanceError
import sqlite3
from threading import Event, get_ident

import pytest

from core.module_context import async_module_context
from core.modules import ModuleManifest, ModuleVersion
from core.storage import SQLiteStorage, StorageConflict, StorageSchemaError


def manifest(name='forecast'):
    return ModuleManifest(name, name, ModuleVersion(1, 0, 0), 1)


def repository(tmp_path):
    result = SQLiteStorage(tmp_path / 'shared.sqlite')
    result.initialize()
    return result


def test_open_never_initializes_or_migrates_database(tmp_path):
    async def run():
        repo = SQLiteStorage(tmp_path / 'missing.sqlite')
        with pytest.raises(sqlite3.OperationalError):
            await async_module_context(repo, asyncio.to_thread, 'a', manifest(), schema_version=1)
        assert not repo.path.exists()
        repo.initialize()
        await async_module_context(repo, asyncio.to_thread, 'a', manifest(), schema_version=1)
        with pytest.raises(StorageSchemaError):
            await async_module_context(repo, asyncio.to_thread, 'a', manifest(), schema_version=2)
        opened = await async_module_context(repo, asyncio.to_thread, 'a', manifest(),
                                            schema_version=2, compatible_versions=(1,))
        assert opened.storage.schema_version == 1
    asyncio.run(run())


def test_fixed_scopes_reopen_and_conflicts(tmp_path):
    repo = repository(tmp_path)

    async def run():
        contexts = [await async_module_context(repo, asyncio.to_thread, project, manifest(module), schema_version=1)
                    for project, module in [('a', 'forecast'), ('b', 'forecast'), ('a', 'metering')]]
        for i, context in enumerate(contexts):
            result = await context.storage.async_put('settings', {'value': i}, expected_revision=None)
            assert result.revision == 1
        assert [(await c.storage.async_get('settings')).data for c in contexts] == [{'value': i} for i in range(3)]
        other = await async_module_context(SQLiteStorage(repo.path), asyncio.to_thread, 'a', manifest(), schema_version=1)
        await other.storage.async_put('settings', {'value': 4}, expected_revision=1)
        with pytest.raises(StorageConflict):
            await contexts[0].storage.async_put('settings', {'value': 5}, expected_revision=1)
        result = await contexts[0].storage.async_get('settings')
        result.data['value'] = 999
        assert (await other.storage.async_get('settings')).data == {'value': 4}
        with pytest.raises(FrozenInstanceError):
            contexts[0].storage = contexts[1].storage
        assert contexts[0].project_id == 'a'
        assert contexts[0].storage.module_id == 'forecast'
    asyncio.run(run())


def test_arguments_are_detached_before_worker_queue_and_batch_rolls_back(tmp_path):
    repo = repository(tmp_path)

    async def run():
        ready, release = asyncio.Event(), asyncio.Event()

        async def queued(operation):
            ready.set()
            await release.wait()
            return await asyncio.to_thread(operation)

        release.set()
        context = await async_module_context(repo, queued, 'a', manifest(), schema_version=1)
        release.clear()
        ready.clear()
        changes = {'first': (None, {'nested': [1]}), 'second': (None, {'value': 2})}
        task = asyncio.create_task(context.storage.async_put_many(changes))
        await ready.wait()
        changes['first'][1]['nested'].append(99)
        changes.clear()
        release.set()
        await task
        assert (await context.storage.async_get('first')).data == {'nested': [1]}
        with pytest.raises(StorageConflict):
            await context.storage.async_put_many({'first': (1, {'value': 3}), 'second': (None, {'value': 4})})
        assert (await context.storage.async_get('first')).revision == 1
    asyncio.run(run())


@pytest.mark.parametrize('worker_fails', [False, True])
def test_cancelled_write_drains_worker_before_return(tmp_path, monkeypatch, worker_fails):
    repo = repository(tmp_path)

    async def run():
        context = await async_module_context(repo, asyncio.to_thread, 'a', manifest(), schema_version=1)
        started, release = Event(), Event()
        original = type(context.storage._handle).put_many
        loop_thread = get_ident()

        def delayed(handle, changes):
            assert get_ident() != loop_thread
            started.set()
            assert release.wait(5)
            if worker_fails:
                raise OSError('synthetic worker failure')
            return original(handle, changes)

        with monkeypatch.context() as patch:
            patch.setattr(type(context.storage._handle), 'put_many', delayed)
            task = asyncio.create_task(context.storage.async_put('settings', {'value': 1}, expected_revision=None))
            assert await asyncio.to_thread(started.wait, 5)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            task.cancel()  # Repeated cancellation must not release the worker.
            await asyncio.sleep(0)
            assert not task.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
        result = await context.storage.async_get('settings')
        assert (result is None) == worker_fails
        if result:
            assert result.data == {'value': 1}
    asyncio.run(run())


def test_reserved_module_ids_and_invalid_json_never_schedule_work(tmp_path):
    repo = repository(tmp_path)

    async def run():
        calls = []

        async def executor(operation):
            calls.append(operation)
            return await asyncio.to_thread(operation)

        for name in ['core', 'storage', 'project']:
            with pytest.raises(ValueError, match='reserved'):
                await async_module_context(repo, executor, 'global', manifest(name), schema_version=1)
        assert not calls
        context = await async_module_context(repo, executor, 'a', manifest(), schema_version=1)
        calls.clear()
        with pytest.raises(ValueError):
            await context.storage.async_put('settings', {'value': float('nan')}, expected_revision=None)
        with pytest.raises(ValueError):
            await context.storage.async_put('settings', {}, expected_revision=True)
        assert not calls
    asyncio.run(run())

def test_cancelled_namespace_open_finishes_before_caller_returns(tmp_path, monkeypatch):
    repo = repository(tmp_path)

    async def run():
        started, release = Event(), Event()
        original = SQLiteStorage.for_module

        def delayed(store, *args, **kwargs):
            started.set()
            assert release.wait(5)
            return original(store, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(SQLiteStorage, 'for_module', delayed)
            task = asyncio.create_task(async_module_context(repo, asyncio.to_thread, 'a', manifest(), schema_version=1))
            assert await asyncio.to_thread(started.wait, 5)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
        # The completed create is harmless and can be reopened explicitly.
        context = await async_module_context(repo, asyncio.to_thread, 'a', manifest(), schema_version=1)
        assert await context.storage.async_get('settings') is None
        await context.storage.async_put('settings', {'ready': True}, expected_revision=None)
    asyncio.run(run())
