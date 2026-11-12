"""Shared ownership and pure route resolution, loopback-only traffic."""

import asyncio
from copy import deepcopy
import json
from pathlib import Path
import struct
from unittest.mock import patch

import pytest

from adapters.connections import ReadOnlyConnectionManager, UnsupportedTransportError
from adapters.profiles.janitza_103_cbm import read_power
from core.connection_routes import resolve_modbus_route
from core.project_v2 import migrate_project_v1_to_v2
from test_modbus_tcp import simulator, frame, good


def connection(key, port, **extra):
    return {"id": key, "name": key, "kind": "modbus_tcp_rtu_gateway",
            "host": "127.0.0.1", "port": port, **extra}


def read(pool, key="shared", unit=1):
    return pool.read_registers(key, unit_id=unit, address=100, count=1)


def test_alias_connection_ids_share_one_stream_and_keep_distinct_targets():
    async def run():
        def respond(request, _):
            tid, unit, fn, _, _ = request
            return frame(tid, unit, bytes((fn, 2)) + struct.pack(">H", unit * 100))
        async with simulator(respond) as (port, requests, connections):
            pool = ReadOnlyConnectionManager([connection("shared", port), connection("alias", float(port), kind="modbus_tcp")])
            try:
                assert await asyncio.gather(read(pool, unit=2), read(pool, "alias", 3)) == [(200,), (300,)]
                assert len(connections) == 1
                assert [r[1] for r in requests] == [2, 3]
            finally:
                await pool.async_close()
    asyncio.run(run())


def test_distinct_ports_are_distinct_resources():
    async def run():
        async with simulator(good) as (p1, _, c1), simulator(good) as (p2, _, c2):
            pool = ReadOnlyConnectionManager([connection("a", p1), connection("b", p2)])
            await asyncio.gather(read(pool, "a"), read(pool, "b"))
            await pool.async_close()
            assert len(c1) == len(c2) == 1
    asyncio.run(run())


def test_profiles_use_common_reader_contract_without_owning_shared_connection():
    async def run():
        def respond(request, _):
            tid, unit, fn, address, count = request
            assert address == 19020 and count == 8
            return frame(tid, unit, bytes((fn, 16)) + struct.pack(">ffff", 100, 200, 300, unit * 1000))
        async with simulator(respond) as (port, _, connections):
            pool = ReadOnlyConnectionManager([connection("shared", port)])
            reader = pool.for_connection("shared")
            assert not hasattr(reader, "async_close") and not connections
            first, second = await asyncio.gather(read_power(reader, unit_id=2), read_power(reader, unit_id=3))
            assert first.total_kw == 2 and second.total_kw == 3
            assert len(connections) == 1
            await pool.async_close()
            with pytest.raises(RuntimeError, match="closed"):
                await read_power(reader, unit_id=2)
    asyncio.run(run())


@pytest.mark.parametrize("hosts", [("LOCALHOST.", "localhost"), ("::1", "0:0:0:0:0:0:0:1")])
def test_syntax_equivalent_hosts_share_client_without_dns_lookup(hosts):
    async def run():
        configs = [connection("a", 502, host=hosts[0]), connection("b", 502, host=hosts[1])]
        pool = ReadOnlyConnectionManager(configs)
        from unittest.mock import AsyncMock
        with patch("asyncio.open_connection", side_effect=AssertionError("unexpected traffic")), patch(
            "adapters.connections.ReadOnlyModbusTCP.read_registers", new=AsyncMock(return_value=(1,)),
        ):
            assert await read(pool, "a") == await read(pool, "b") == (1,)
            assert len(pool._clients) == 1
            await pool.async_close()
    asyncio.run(run())


def test_construct_and_close_idle_manager_never_open_network_or_mutate_config():
    async def run():
        configs = [connection("shared", 502)]
        before = deepcopy(configs)
        with patch("asyncio.open_connection", side_effect=AssertionError("unexpected traffic")):
            pool = ReadOnlyConnectionManager(configs)
            configs[0]["host"] = "changed.invalid"
            assert pool._connections["shared"]["host"] == before[0]["host"]
            await pool.async_close()
            with pytest.raises(RuntimeError, match="closed"):
                await read(pool)
    asyncio.run(run())


@pytest.mark.parametrize("kind", ["modbus_rtu_usb", "solarman", "mqtt", "ha"])
def test_unimplemented_transports_never_fall_back_to_tcp(kind):
    async def run():
        pool = ReadOnlyConnectionManager([connection("shared", 502, kind=kind)])
        with patch("asyncio.open_connection", side_effect=AssertionError("unexpected traffic")):
            with pytest.raises(UnsupportedTransportError):
                await read(pool)
            await pool.async_close()
    asyncio.run(run())


def test_bad_connection_and_request_are_rejected_before_network():
    async def run():
        for params in ({"host": None}, {"host": "bad host"}, {"port": True}):
            pool = ReadOnlyConnectionManager([connection("shared", 502, **params)] if "port" not in params else [connection("shared", params["port"])])
            with patch("asyncio.open_connection", side_effect=AssertionError("unexpected traffic")):
                with pytest.raises(ValueError):
                    await read(pool)
                await pool.async_close()
        pool = ReadOnlyConnectionManager([connection("shared", 502)])
        with patch("asyncio.open_connection", side_effect=AssertionError("unexpected traffic")):
            with pytest.raises(ValueError):
                await read(pool, "missing")
            with pytest.raises(ValueError):
                await pool.read_registers("shared", unit_id=1, address=100, count=1, function_code=6)
            await pool.async_close()
    asyncio.run(run())


def test_shutdown_drains_accepted_reads_and_cancelled_close_caller_cannot_interrupt_it():
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def respond(request, index):
            if index == 1:
                entered.set()
                await release.wait()
            return good(request, index)
        async with simulator(respond) as (port, requests, connections):
            pool = ReadOnlyConnectionManager([connection("shared", port)])
            first = asyncio.create_task(read(pool, unit=2))
            await entered.wait()
            second = asyncio.create_task(read(pool, unit=3))
            await asyncio.sleep(0)  # allow second request into shared-client queue
            closing = asyncio.create_task(pool.async_close())
            await asyncio.sleep(0)
            with pytest.raises(RuntimeError, match="closed"):
                await read(pool)
            closing.cancel()
            with pytest.raises(asyncio.CancelledError):
                await closing
            release.set()
            assert await first == await second == (0,)
            await asyncio.gather(pool.async_close(), pool.async_close())
            assert len(connections) == 1 and [r[1] for r in requests] == [2, 3]
    asyncio.run(run())


def test_cancelled_queued_device_does_not_close_active_shared_request():
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def respond(request, index):
            entered.set()
            await release.wait()
            return good(request, index)
        async with simulator(respond) as (port, requests, connections):
            pool = ReadOnlyConnectionManager([connection("shared", port)])
            first = asyncio.create_task(read(pool, unit=2))
            await entered.wait()
            queued = asyncio.create_task(read(pool, unit=3))
            await asyncio.sleep(0)
            queued.cancel()
            with pytest.raises(asyncio.CancelledError):
                await queued
            release.set()
            assert await first == (0,)
            assert await read(pool, unit=4) == (0,)
            await pool.async_close()
            assert len(connections) == 1 and [r[1] for r in requests] == [2, 4]
    asyncio.run(run())


def project():
    p = json.loads((Path(__file__).resolve().parents[1] / "examples/simple-project.json").read_text(encoding="utf-8"))
    p["devices"][0].update(kind="gateway", connection_id="connection_main", unit_id=7)
    p["devices"][1].update(via_device_id="meter_grid", unit_id=2)
    return p


def test_route_uses_communication_gateway_not_battery_or_electrical_parent():
    p = project()
    p["devices"][1].pop("connection_id")
    before = deepcopy(p)
    route = resolve_modbus_route(p, "hybrid")
    assert route.connection_id == "connection_main" and route.unit_id == 2
    assert p == before
    with pytest.raises(ValueError, match="own explicit Unit ID"):
        resolve_modbus_route(p, "battery")
    with pytest.raises(ValueError, match="Unknown device"):
        resolve_modbus_route(p, "missing")


def test_route_rejects_unresolved_and_conflicting_paths():
    p = project()
    for d in p["devices"]:
        d.pop("connection_id", None)
    with pytest.raises(ValueError, match="consistent connection"):
        resolve_modbus_route(p, "hybrid")
    p = project()
    p["connections"].append(connection("other", 502))
    p["devices"][1]["connection_id"] = "other"
    with pytest.raises(ValueError):
        resolve_modbus_route(p, "hybrid")


def test_serial_route_is_resolvable_without_claiming_transport_implementation():
    p = project()
    p["connections"][0].update(kind="modbus_rtu_usb", serial_port="synthetic-usb")
    route = resolve_modbus_route(p, "hybrid")
    assert route.unit_id == 2
    p["connections"][0]["kind"] = "mqtt"
    with pytest.raises(ValueError, match="not a Modbus"):
        resolve_modbus_route(p, "hybrid")


def test_v2_route_resolves_on_a_grid_without_a_primary_measurement():
    data = migrate_project_v1_to_v2(project())
    data["measurements"] = []
    data["devices"][1].pop("connection_id")
    before = deepcopy(data)
    route = resolve_modbus_route(data, "hybrid")
    assert route.connection_id == "connection_main" and route.unit_id == 2
    assert data == before
    data["devices"][1].pop("unit_id")
    with pytest.raises(ValueError, match="own explicit Unit ID"):
        resolve_modbus_route(data, "hybrid")
    data["devices"][1]["unit_id"] = 248
    with pytest.raises(ValueError, match="unit_id"):
        resolve_modbus_route(data, "hybrid")


@pytest.mark.parametrize("version", [True, "2", 3])
def test_route_rejects_invalid_or_unsupported_project_versions(version):
    data = project() if version is True else migrate_project_v1_to_v2(project())
    data["schema_version"] = version
    with pytest.raises(ValueError):
        resolve_modbus_route(data, "hybrid")
