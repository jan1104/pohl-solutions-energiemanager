"""Loopback-only protocol tests: no site addresses, devices or write requests."""

import asyncio
from contextlib import asynccontextmanager
import inspect
import struct

import pytest

from adapters.profiles.janitza_103_cbm import read_power
from adapters.transports.modbus_tcp import (
    ModbusDeviceError, ModbusError, ModbusProtocolError, ModbusTimeout,
    ReadOnlyModbusTCP, decode_registers,
)


def frame(transaction, unit, pdu, *, protocol=0, length=None):
    return struct.pack(">HHHB", transaction, protocol, len(pdu) + 1 if length is None else length, unit) + pdu


@asynccontextmanager
async def simulator(respond):
    requests, connections, tasks, writers = [], [], set(), set()

    async def handler(reader, writer):
        task = asyncio.current_task()
        tasks.add(task)
        writers.add(writer)
        connections.append(writer)
        try:
            while True:
                header = await reader.readexactly(7)
                tid, protocol, length, unit = struct.unpack(">HHHB", header)
                function, address, count = struct.unpack(">BHH", await reader.readexactly(length - 1))
                assert protocol == 0 and function in (3, 4)
                request = (tid, unit, function, address, count)
                requests.append(request)
                result = respond(request, len(requests))
                if inspect.isawaitable(result):
                    result = await result
                if result is None:
                    await reader.read()  # Wait for client timeout/cancellation to close.
                    return
                if result == b"":
                    return
                # Deliberately fragment responses across writes.
                writer.write(result[:3])
                await writer.drain()
                await asyncio.sleep(0)
                writer.write(result[3:])
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass
            writers.discard(writer)
            tasks.discard(task)

    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    try:
        yield server.sockets[0].getsockname()[1], requests, connections
    finally:
        server.close()
        await server.wait_closed()
        for writer in tuple(writers):
            writer.close()
        for task in tuple(tasks):
            task.cancel()
        if tasks:
            await asyncio.gather(*tuple(tasks), return_exceptions=True)


def good(request, index):
    tid, unit, function, _, count = request
    return frame(tid, unit, bytes((function, count * 2)) + struct.pack(">" + "H" * count, *range(count)))


def test_gateway_two_targets_reuse_stream_and_janitza_units():
    async def run():
        def respond(request, index):
            tid, unit, function, address, count = request
            assert address == 19020 and count == 8
            watts = (1000, 2000, 3000, 6000) if unit == 3 else (-500, -750, -250, -1500)
            return frame(tid, unit, bytes((function, 16)) + struct.pack(">ffff", *watts))

        async with simulator(respond) as (port, requests, connections):
            client = ReadOnlyModbusTCP("127.0.0.1", port)
            try:
                first, second = await asyncio.gather(read_power(client, unit_id=3), read_power(client, unit_id=4))
                assert (first.l1_kw, first.l2_kw, first.l3_kw, first.total_kw) == (1, 2, 3, 6)
                assert second.total_kw == -1.5
                assert first.acquired_at.utcoffset().total_seconds() == 0
                assert len(connections) == 1
                assert [r[1] for r in requests] == [3, 4]
                assert requests[0][0] != requests[1][0]
                flipped = await read_power(client, unit_id=4, power_sign=-1)
                assert flipped.total_kw == 1.5
            finally:
                await client.async_close()
    asyncio.run(run())


@pytest.mark.parametrize("unit,function", [(255, 3), (1, 4), (247, 3)])
def test_direct_or_gateway_ids_and_read_functions(unit, function):
    async def run():
        async with simulator(good) as (port, requests, _):
            client = ReadOnlyModbusTCP("127.0.0.1", port)
            try:
                assert await client.read_registers(unit_id=unit, address=10, count=2, function_code=function) == (0, 1)
                assert requests[0][1:] == (unit, function, 10, 2)
            finally:
                await client.async_close()
    asyncio.run(run())


@pytest.mark.parametrize("override", [
    {"unit_id": 0}, {"unit_id": 248}, {"unit_id": True}, {"address": -1},
    {"address": 65535, "count": 2}, {"count": 126}, {"count": 0},
    {"function_code": 6}, {"function_code": 16},
])
def test_invalid_or_write_request_never_connects(override):
    async def run():
        from unittest.mock import AsyncMock, patch
        client = ReadOnlyModbusTCP("127.0.0.1", 502)
        with patch("asyncio.open_connection", new=AsyncMock()) as connect:
            with pytest.raises(ValueError):
                await client.read_registers(**{"unit_id": 3, "address": 0, "count": 2, **override})
            connect.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize("bad", ["transaction", "unit", "protocol", "length", "function", "bytecount", "exception"])
def test_invalid_response_closes_stream_and_next_read_reconnects(bad):
    async def run():
        def respond(request, index):
            if index > 1:
                return good(request, index)
            tid, unit, function, _, _ = request
            pdu = bytes((function, 4, 0, 0, 0, 1))
            return frame(tid + (bad == "transaction"), unit + (bad == "unit"),
                         bytes((4, 4, 0, 0, 0, 1)) if bad == "function" else
                         bytes((function, 2, 0, 0, 0, 1)) if bad == "bytecount" else
                         bytes((function | 0x80, 0)) if bad == "exception" else pdu,
                         protocol=1 if bad == "protocol" else 0,
                         length=300 if bad == "length" else None)
        async with simulator(respond) as (port, _, connections):
            client = ReadOnlyModbusTCP("127.0.0.1", port)
            try:
                with pytest.raises(ModbusProtocolError):
                    await client.read_registers(unit_id=3, address=0, count=2)
                assert await client.read_registers(unit_id=3, address=0, count=2) == (0, 1)
                assert len(connections) == 2
            finally:
                await client.async_close()
    asyncio.run(run())


def test_device_exception_preserves_clean_connection():
    async def run():
        def respond(request, index):
            return frame(request[0], request[1], bytes((request[2] | 0x80, 2))) if index == 1 else good(request, index)
        async with simulator(respond) as (port, _, connections):
            client = ReadOnlyModbusTCP("127.0.0.1", port)
            try:
                with pytest.raises(ModbusDeviceError) as error:
                    await client.read_registers(unit_id=3, address=0, count=2)
                assert error.value.code == 2
                assert await client.read_registers(unit_id=4, address=0, count=2) == (0, 1)
                assert len(connections) == 1
            finally:
                await client.async_close()
    asyncio.run(run())


def test_timeout_has_no_zero_fallback_and_reconnects():
    async def run():
        async with simulator(lambda r, i: None if i == 1 else good(r, i)) as (port, _, connections):
            client = ReadOnlyModbusTCP("127.0.0.1", port, timeout=.05)
            try:
                with pytest.raises(ModbusTimeout):
                    await client.read_registers(unit_id=3, address=0, count=2)
                assert await client.read_registers(unit_id=4, address=0, count=2) == (0, 1)
                assert len(connections) == 2
            finally:
                await client.async_close()
    asyncio.run(run())


def test_cancelled_queued_request_does_not_break_active_transaction():
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def respond(request, index):
            if index == 1:
                entered.set()
                await release.wait()
            return good(request, index)
        async with simulator(respond) as (port, requests, connections):
            client = ReadOnlyModbusTCP("127.0.0.1", port, timeout=2)
            try:
                active = asyncio.create_task(client.read_registers(unit_id=3, address=0, count=2))
                await asyncio.wait_for(entered.wait(), 1)
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(client.read_registers(unit_id=4, address=0, count=2), .02)
                release.set()
                assert await active == (0, 1)
                assert len(requests) == len(connections) == 1
            finally:
                release.set()
                await client.async_close()
    asyncio.run(run())


def test_eof_is_not_a_measurement():
    async def run():
        async with simulator(lambda r, i: b"") as (port, _, _):
            client = ReadOnlyModbusTCP("127.0.0.1", port, timeout=.05)
            try:
                with pytest.raises(ModbusError) as error:
                    await client.read_registers(unit_id=3, address=0, count=2)
                assert not isinstance(error.value, ModbusTimeout)
            finally:
                await client.async_close()
    asyncio.run(run())


@pytest.mark.parametrize("registers,byte_order,word_order", [
    ((0x422A, 0), "big", "big"), ((0, 0x422A), "big", "little"),
    ((0x2A42, 0), "little", "big"), ((0, 0x2A42), "little", "little"),
])
def test_explicit_float_orders(registers, byte_order, word_order):
    assert decode_registers(registers, "float32", byte_order=byte_order, word_order=word_order, scale=.001) == .0425


@pytest.mark.parametrize("data_type,registers,result", [
    ("u16", (65535,), 65535), ("s16", (65535,), -1),
    ("u32", (1, 2), 65538), ("s32", (65535, 65534), -2),
])
def test_integer_decoding(data_type, registers, result):
    assert decode_registers(registers, data_type) == result


@pytest.mark.parametrize("registers", [(0x7FC0, 0), (0x7F80, 0)])
def test_nonfinite_device_value_is_rejected(registers):
    with pytest.raises(ValueError, match="finite"):
        decode_registers(registers, "float32")


def test_inflight_cancellation_reconnects_without_reusing_partial_frame():
    async def run():
        entered = asyncio.Event()
        def respond(request, index):
            entered.set()
            return None if index == 1 else good(request, index)
        async with simulator(respond) as (port, _, connections):
            client = ReadOnlyModbusTCP("127.0.0.1", port)
            try:
                active = asyncio.create_task(client.read_registers(unit_id=3, address=0, count=2))
                await asyncio.wait_for(entered.wait(), 1)
                active.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await active
                assert await client.read_registers(unit_id=4, address=0, count=2) == (0, 1)
                assert len(connections) == 2
            finally:
                await client.async_close()
    asyncio.run(run())


@pytest.mark.parametrize("kwargs", [
    {"timeout": 0}, {"timeout": float("nan")}, {"timeout": 10 ** 400},
    {"port": True}, {"host": "http://127.0.0.1"}, {"host": "bad host"},
])
def test_invalid_connection_settings(kwargs):
    with pytest.raises(ValueError):
        ReadOnlyModbusTCP(**{"host": "127.0.0.1", **kwargs})


@pytest.mark.parametrize("kwargs", [
    {"scale": True}, {"scale": 0}, {"scale": 10 ** 400}, {"data_type": []},
    {"word_order": "auto"}, {"byte_order": "auto"},
])
def test_invalid_decoder_settings(kwargs):
    with pytest.raises(ValueError):
        decode_registers((0, 0), **{"data_type": "float32", **kwargs})
