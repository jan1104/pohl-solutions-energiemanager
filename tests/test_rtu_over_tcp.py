"""Raw RTU-over-TCP tests, synthetic loopback peers only."""

import asyncio
from contextlib import asynccontextmanager
import inspect
import struct
from unittest.mock import AsyncMock, patch

import pytest

from adapters.connections import ReadOnlyConnectionManager
from adapters.transports.modbus_tcp import ModbusDeviceError, ModbusProtocolError, ModbusTimeout
from adapters.transports.rtu_over_tcp import ReadOnlyRTUOverTCP, crc16


def packet(payload):
    return payload + crc16(payload)


def good(request, index):
    unit, function, address, count = request
    return packet(bytes([unit, function, count * 2]) + struct.pack('>' + 'H' * count, *range(count)))


@asynccontextmanager
async def tunnel(respond=good):
    requests, connections, writers, tasks = [], [], set(), set()

    async def handler(reader, writer):
        task = asyncio.current_task()
        tasks.add(task)
        writers.add(writer)
        connections.append(writer)
        try:
            while True:
                raw = await reader.readexactly(8)
                assert crc16(raw[:-2]) == raw[-2:]
                request = struct.unpack('>BBHH', raw[:-2])
                assert request[1] in (3, 4)
                requests.append(request)
                reply = respond(request, len(requests))
                if inspect.isawaitable(reply):
                    reply = await reply
                if reply is None:
                    await reader.read()
                    return
                writer.write(reply[:2])
                await writer.drain()
                await asyncio.sleep(0)
                writer.write(reply[2:])
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            writers.discard(writer)
            tasks.discard(task)

    server = await asyncio.start_server(handler, '127.0.0.1', 0)
    try:
        yield server.sockets[0].getsockname()[1], requests, connections
    finally:
        server.close()
        await server.wait_closed()
        for writer in tuple(writers):
            writer.close()
        for task in tuple(tasks):
            task.cancel()
        await asyncio.gather(*tuple(tasks), return_exceptions=True)


def test_crc_known_vectors_and_wire_byte_order():
    assert crc16(b'123456789') == bytes.fromhex('374b')
    assert packet(bytes.fromhex('01030000000a')) == bytes.fromhex('01030000000ac5cd')


@pytest.mark.parametrize('function,count,address', [(3, 1, 65535), (4, 125, 65411)])
def test_fragmented_reads_and_shared_alias_stream(function, count, address):
    async def run():
        async with tunnel() as (port, requests, connections):
            config = [{'id': key, 'kind': 'rtu_over_tcp', 'host': '127.0.0.1', 'port': port} for key in ['a', 'b']]
            pool = ReadOnlyConnectionManager(config)
            try:
                results = await asyncio.gather(*[pool.for_connection(key).read_registers(
                    unit_id=unit, address=address, count=count, function_code=function)
                    for key, unit in [('a', 1), ('b', 247)]])
                assert results == [tuple(range(count))] * 2
                assert requests == [(1, function, address, count), (247, function, address, count)]
                assert len(connections) == 1
            finally:
                await pool.async_close()
    asyncio.run(run())


@pytest.mark.parametrize('reply', [
    bytes.fromhex('01030200000000'),  # Bad CRC.
    packet(bytes.fromhex('0203020000')),  # Wrong unit.
    packet(bytes.fromhex('0104020000')),  # Wrong function.
    packet(bytes.fromhex('01030400000000')),  # Wrong byte count.
    packet(bytes.fromhex('018300')),  # Zero exception code.
    bytes.fromhex('0183020000'),  # Exception with bad CRC.
])
def test_invalid_reply_disconnects_before_explicit_reconnect(reply):
    async def run():
        async with tunnel(lambda req, index: reply if index == 1 else good(req, index)) as (port, _, connections):
            client = ReadOnlyRTUOverTCP('127.0.0.1', port)
            try:
                with pytest.raises(ModbusProtocolError):
                    await client.read_registers(unit_id=1, address=0, count=1)
                assert await client.read_registers(unit_id=1, address=0, count=1) == (0,)
                assert len(connections) == 2
            finally:
                await client.async_close()
    asyncio.run(run())


def test_complete_exception_retains_stream():
    async def run():
        async with tunnel(lambda req, index: packet(bytes([req[0], req[1] | 0x80, 2])) if index == 1 else good(req, index)) as (port, _, connections):
            client = ReadOnlyRTUOverTCP('127.0.0.1', port)
            try:
                with pytest.raises(ModbusDeviceError) as error:
                    await client.read_registers(unit_id=1, address=0, count=1)
                assert error.value.code == 2
                assert await client.read_registers(unit_id=1, address=0, count=1) == (0,)
                assert len(connections) == 1
            finally:
                await client.async_close()
    asyncio.run(run())


@pytest.mark.parametrize('cancel', [False, True])
def test_timeout_or_cancellation_drops_stream_without_retry(cancel):
    async def run():
        started = asyncio.Event()

        def respond(req, index):
            started.set()
            return None if index == 1 else good(req, index)

        async with tunnel(respond) as (port, requests, connections):
            client = ReadOnlyRTUOverTCP('127.0.0.1', port, timeout=0.2)
            try:
                task = asyncio.create_task(client.read_registers(unit_id=1, address=0, count=1))
                await started.wait()
                if cancel:
                    task.cancel()
                with pytest.raises(asyncio.CancelledError if cancel else ModbusTimeout):
                    await task
                assert len(requests) == 1
                assert await client.read_registers(unit_id=1, address=0, count=1) == (0,)
                assert len(connections) == 2
            finally:
                await client.async_close()
    asyncio.run(run())


def test_invalid_configuration_and_framing_conflicts_never_connect():
    async def run():
        with patch('asyncio.open_connection', new_callable=AsyncMock) as connect:
            client = ReadOnlyRTUOverTCP('localhost', 1502)
            for unit in [0, 248, 255, True]:
                with pytest.raises(ValueError):
                    await client.read_registers(unit_id=unit, address=0, count=1)
            for values in [{'count': 126}, {'address': 65535, 'count': 2}, {'function_code': 6}]:
                with pytest.raises(ValueError):
                    await client.read_registers(**({'unit_id': 1, 'address': 0, 'count': 1} | values))
            for raw_first in [True, False]:
                pool = ReadOnlyConnectionManager([
                    {'id': 'raw', 'kind': 'rtu_over_tcp', 'host': 'LOCALHOST.', 'port': 1502},
                    {'id': 'mbap', 'kind': 'modbus_tcp', 'host': 'localhost', 'port': 1502},
                ])
                with pytest.raises(ValueError, match='Conflicting'):
                    await pool.read_registers('raw' if raw_first else 'mbap', unit_id=1, address=0, count=1)
                await pool.async_close()
            pool = ReadOnlyConnectionManager([{'id': 'draft', 'kind': 'rtu_over_tcp', 'host': 'localhost'}])
            with pytest.raises(ValueError, match='explicit TCP tunnel port'):
                await pool.read_registers('draft', unit_id=1, address=0, count=1)
            await pool.async_close()
            connect.assert_not_called()
    asyncio.run(run())
