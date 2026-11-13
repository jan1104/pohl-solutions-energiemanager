"""Read, decode and bind synthetic replies, including one loopback route."""

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from importlib import import_module
import json
from pathlib import Path
import struct
import sys
from types import ModuleType
from unittest.mock import AsyncMock, Mock

import pytest

from adapters.connections import ReadOnlyConnectionManager
from adapters.transports.modbus_tcp import ModbusDeviceError
from core.project_v2 import migrate_project_v1_to_v2
from test_modbus_tcp import frame, simulator

NOW = datetime(2026, 11, 10, tzinfo=timezone.utc)


def fixture():
    path = Path(__file__).resolve().parents[1] / "examples/simple-project.json"
    project = migrate_project_v1_to_v2(json.loads(path.read_text(encoding="utf-8")))
    project["devices"][0].update(unit_id=2, via_device_id="gateway")
    project["devices"].append({"id": "gateway", "name": "Testgateway", "kind": "gateway",
                               "area_id": "area_main", "node_id": "storage",
                               "connection_id": "connection_main", "unit_id": 7})
    project["connections"][0].update(kind="modbus_tcp_rtu_gateway", host="127.0.0.1")
    project["channels"][0].update(unit="W", phase="total", source={
        "kind": "modbus", "address": 100, "function_code": 4, "data_type": "s32", "scale": 0.5,
    })
    return project


@pytest.fixture(scope="module")
def read():
    # Import the composition with its normal sibling-package layout while
    # leaving the Home Assistant entry point out of the pure Python suite.
    package = ModuleType("_pohl_adapter_test")
    package.__path__ = [str(Path(__file__).resolve().parents[1] /
                            "custom_components/pohl_solutions_energiemanager")]
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(sys.modules, package.__name__, package)
        adapter = import_module(f"{package.__name__}.adapters.modbus_measurement")

        async def run(project, reader_for_connection, **overrides):
            return await adapter.read_modbus_power_measurement(
                project, "grid_primary", reader_for_connection=reader_for_connection,
                **{"source_id": "synthetic-meter", "byte_order": "little", "word_order": "little",
                   "polarity": -1, "max_age": timedelta(seconds=30), "receipt_clock": lambda: NOW,
                   **overrides},
            )

        yield run


def test_loopback_routes_to_meter_decodes_registers_and_normalizes_once(read):
    async def run():
        def respond(request, _):
            tid, unit, fn, _, _ = request
            return frame(tid, unit, bytes((fn, 4)) + struct.pack(">HH", 0x3CF6, 0xFFFF))
        async with simulator(respond) as (port, requests, streams):
            project = fixture()
            project["connections"][0]["port"] = port
            before = deepcopy(project)
            manager = ReadOnlyConnectionManager(project["connections"])
            try:
                assert not streams
                measured_at = NOW - timedelta(seconds=2)
                result = await read(project, manager.for_connection, measured_at=measured_at)
                assert [r[1:] for r in requests] == [(2, 4, 100, 2)]
                assert result.route.connection_id == "connection_main" and result.route.unit_id == 2
                assert result.decoded_value == -2500
                bound = result.measurement
                assert bound.value.valid and bound.value.power_kw == 1.25
                assert bound.value.sources == ("synthetic-meter",)
                assert bound.value.grid_id == "grid_main"
                assert bound.node_id == "main" and bound.device_id == "meter_grid"
                assert bound.value.oldest_measurement == measured_at
                assert bound.received_at == NOW
                assert project == before
            finally:
                await manager.async_close()
    asyncio.run(run())


@pytest.mark.parametrize(("measured_at", "issue"), [
    (None, "missing_time"),
    (NOW - timedelta(seconds=31), "stale"),
    (NOW + timedelta(seconds=1), "invalid_time_order"),
])
def test_receipt_time_never_makes_missing_or_invalid_measurement_time_valid(read, measured_at, issue):
    reader = Mock(read_registers=AsyncMock(return_value=(0x3CF6, 0xFFFF)))
    result = asyncio.run(read(fixture(), lambda _: reader, measured_at=measured_at))
    assert result.decoded_value == -2500
    assert result.measurement.received_at == NOW
    assert result.measurement.value.oldest_measurement == measured_at
    assert result.measurement.value.power_kw is None
    assert f"synthetic-meter: {issue}" in result.measurement.value.issues


@pytest.mark.parametrize("case", ["source", "unit", "range", "order", "polarity", "clock", "receipt_clock", "source_id"])
def test_invalid_mapping_rejected_before_getting_reader(read, case):
    project = fixture()
    kwargs = {}
    if case == "source":
        project["channels"][0]["source"] = {"kind": "ha", "entity_id": "sensor.synthetic"}
    elif case == "unit":
        project["devices"][0].pop("unit_id")
    elif case == "range":
        project["channels"][0]["source"]["address"] = 65535
    elif case == "order":
        kwargs["word_order"] = "auto"
    elif case == "polarity":
        kwargs["polarity"] = True
    elif case == "clock":
        kwargs["measured_at"] = NOW.replace(tzinfo=None)
    elif case == "receipt_clock":
        kwargs["receipt_clock"] = NOW
    elif case == "source_id":
        kwargs["source_id"] = ""
    factory = Mock()
    with pytest.raises(ValueError):
        asyncio.run(read(project, factory, **kwargs))
    factory.assert_not_called()


def test_reader_failure_and_malformed_response_do_not_produce_power(read):
    error = ModbusDeviceError(2)
    failing = Mock(read_registers=AsyncMock(side_effect=error))
    with pytest.raises(ModbusDeviceError) as caught:
        asyncio.run(read(fixture(), lambda _: failing, measured_at=NOW))
    assert caught.value is error
    malformed = Mock(read_registers=AsyncMock(return_value=(2500,)))
    with pytest.raises(ValueError, match="Wrong register count"):
        asyncio.run(read(fixture(), lambda _: malformed, measured_at=NOW))
