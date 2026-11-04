"""Module/version fault boundaries using synthetic handlers, never devices."""

import asyncio
from dataclasses import FrozenInstanceError

import pytest

from core.modules import (ModuleDependency, ModuleExecutionError, ModuleManifest,
                          ModuleRegistry, ModuleUnavailable, ModuleVersion)


def version(text="1.0.0"):
    return ModuleVersion.parse(text)


def depends(key, low="1.0.0", high="2.0.0"):
    return ModuleDependency(key, version(low), version(high))


def manifest(key, dependencies=(), **kwargs):
    return ModuleManifest(key, key, kwargs.get("version", version()),
                          kwargs.get("api_major", 1), dependencies)


async def echo(request):
    return request


def test_registration_is_inert_versions_are_numeric_and_manifests_immutable():
    registry = ModuleRegistry()
    dependencies = [depends("forecast", "1.2.0", "1.11.0")]
    item = manifest("planner", dependencies)
    dependencies.clear()
    assert len(item.dependencies) == 1
    with pytest.raises(FrozenInstanceError):
        item.api_major = 2
    registry.register(item, echo)
    assert registry.states()["planner"].status == "blocked"
    registry.register(manifest("forecast", version=version("1.10.0")), echo)
    assert registry.states()["planner"].status == "ready"
    assert tuple(m.module_id for m in registry.manifests()) == ("planner", "forecast")


@pytest.mark.parametrize("text", ["1.2", "v1.2.0", "01.2.0", "1.0.0-beta", "-1.0.0", "1.0.000", "1000000.0.0", True])
def test_invalid_versions_fail_explicitly(text):
    with pytest.raises(ValueError):
        version(text)


def test_missing_incompatible_api_and_dependency_cycles_do_not_block_independent_modules():
    registry = ModuleRegistry()
    registry.register(manifest("ui"), echo)
    registry.register(manifest("missing", (depends("absent"),)), echo)
    registry.register(manifest("new_api", api_major=2), echo)
    registry.register(manifest("new_release", version=version("2.0.0")), echo)
    registry.register(manifest("old_consumer", (depends("new_release"),)), echo)
    registry.register(manifest("a", (depends("b"),)), echo)
    registry.register(manifest("b", (depends("a"),)), echo)
    registry.register(manifest("downstream", (depends("a"),)), echo)
    states = registry.states()
    assert states["ui"].status == "ready"
    assert states["missing"].reasons == ("missing_dependency:absent",)
    assert states["new_api"].reasons == ("incompatible_api",)
    assert states["old_consumer"].reasons == ("incompatible_dependency:new_release",)
    assert all(states[key].status == "blocked" and "dependency_cycle" in states[key].reasons
               for key in ("a", "b", "downstream"))


def test_forecast_failure_blocks_dependent_planner_but_other_modules_keep_working():
    async def run():
        async def fail(_):
            raise RuntimeError("sensitive-handler-payload")
        registry = ModuleRegistry()
        registry.register(manifest("project"), echo)
        registry.register(manifest("forecast"), fail)
        registry.register(manifest("planner", (depends("forecast"),)), echo)
        registry.register(manifest("metering"), echo)
        with pytest.raises(ModuleExecutionError) as error:
            await registry.async_call("forecast")
        assert "sensitive-handler-payload" not in str(error.value)
        assert registry.states()["forecast"].status == "failed"
        with pytest.raises(ModuleUnavailable):
            await registry.async_call("planner")
        assert await registry.async_call("metering", 42) == 42
        assert await registry.async_call("project", "open") == "open"
        registry.set_enabled("planner", False)
        registry.reset_failure("forecast")
        assert registry.states()["forecast"].status == "ready"
        assert registry.states()["planner"].status == "disabled"
    asyncio.run(run())


def test_same_module_serializes_while_independent_module_continues_and_queue_timeout_is_not_fault():
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def waiting(value):
            entered.set()
            await release.wait()
            return value
        registry = ModuleRegistry()
        registry.register(manifest("forecast"), waiting)
        registry.register(manifest("project"), echo)
        task = asyncio.create_task(registry.async_call("forecast", "first"))
        await entered.wait()
        assert await registry.async_call("project", "alive") == "alive"
        with pytest.raises(ModuleExecutionError, match="timed out"):
            await registry.async_call("forecast", "queued", timeout=.01)
        assert registry.states()["forecast"].status == "ready"
        release.set()
        assert await task == "first"
        assert await registry.async_call("forecast", "second") == "second"
    asyncio.run(run())


def test_handler_timeout_is_fault_but_external_cancellation_is_not():
    async def run():
        entered = asyncio.Event()
        async def waiting(_):
            entered.set()
            await asyncio.Event().wait()
        registry = ModuleRegistry()
        registry.register(manifest("forecast"), waiting)
        task = asyncio.create_task(registry.async_call("forecast"))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert registry.states()["forecast"].status == "ready"
        with pytest.raises(ModuleExecutionError, match="timed out"):
            await registry.async_call("forecast", timeout=.01)
        assert registry.states()["forecast"].status == "failed"
    asyncio.run(run())


def test_dependency_change_discards_inflight_result_and_prevents_queued_execution():
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        async def waiting(value):
            calls.append(value)
            entered.set()
            await release.wait()
            return value
        registry = ModuleRegistry()
        registry.register(manifest("forecast"), echo)
        registry.register(manifest("planner", (depends("forecast"),)), waiting)
        first = asyncio.create_task(registry.async_call("planner", "first"))
        await entered.wait()
        queued = asyncio.create_task(registry.async_call("planner", "second"))
        await asyncio.sleep(0)
        registry.set_enabled("forecast", False)
        registry.set_enabled("forecast", True)
        release.set()
        for task in (first, queued):
            with pytest.raises(ModuleUnavailable, match="changed"):
                await task
        assert calls == ["first"]
        assert registry.states()["planner"].status == "ready"
    asyncio.run(run())


def test_duplicate_or_invalid_registration_never_replaces_existing_handler():
    async def run():
        registry = ModuleRegistry()
        registry.register(manifest("project"), echo)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(manifest("project", version=version("2.0.0")), echo)
        with pytest.raises(ValueError, match="must be async"):
            registry.register(manifest("sync"), lambda _: 1)
        assert await registry.async_call("project", 1) == 1
        registry.set_enabled("project", False)
        with pytest.raises(ModuleUnavailable):
            await registry.async_call("project")
        assert "sync" not in registry.states()
    asyncio.run(run())


def test_failure_does_not_discard_independent_inflight_work_and_recovery_is_explicit():
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        failed_once = False
        async def forecast(_):
            nonlocal failed_once
            if not failed_once:
                failed_once = True
                raise RuntimeError("synthetic failure")
            return "new forecast"
        async def meter(_):
            entered.set()
            await release.wait()
            return "measurement"
        registry = ModuleRegistry()
        registry.register(manifest("forecast"), forecast)
        registry.register(manifest("planner", (depends("forecast"),)), echo)
        registry.register(manifest("metering"), meter)
        task = asyncio.create_task(registry.async_call("metering"))
        await entered.wait()
        with pytest.raises(ModuleExecutionError):
            await registry.async_call("forecast")
        assert registry.states()["planner"].status == "blocked"
        release.set()
        assert await task == "measurement"
        with pytest.raises(ModuleUnavailable):
            await registry.async_call("forecast")
        registry.reset_failure("forecast")
        assert await registry.async_call("forecast") == "new forecast"
        assert registry.states()["planner"].status == "ready"
    asyncio.run(run())


@pytest.mark.parametrize("outcome", ["exception", "timeout"])
def test_obsolete_failure_cannot_poison_current_module_after_dependency_recovery(outcome):
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def handler(_):
            entered.set()
            await release.wait()
            raise RuntimeError("obsolete failure")
        registry = ModuleRegistry()
        registry.register(manifest("forecast"), echo)
        registry.register(manifest("planner", (depends("forecast"),)), handler)
        registry.register(manifest("report", (depends("planner"),)), echo)
        task = asyncio.create_task(registry.async_call("planner", timeout=.03))
        await entered.wait()
        registry.set_enabled("forecast", False)
        registry.set_enabled("forecast", True)
        if outcome == "exception":
            release.set()
        with pytest.raises(ModuleUnavailable, match="changed"):
            await task
        assert registry.states()["planner"].status == "ready"
        assert registry.states()["report"].status == "ready"
    asyncio.run(run())
