"""Read-only RTU frames through an explicitly configured transparent TCP tunnel.

This is not MBAP and does not implement USB/serial timing. The external tunnel
must handle its serial bus. No discovery, broadcast, write or automatic retry.
"""

import asyncio
import struct

from .modbus_tcp import ModbusDeviceError, ModbusProtocolError, ReadOnlyModbusTCP, _integer


def crc16(data: bytes) -> bytes:
    """Modbus RTU CRC, low byte first (Serial Line Guide V1.02, section 2.5.1.2)."""
    value = 0xFFFF
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ (0xA001 if value & 1 else 0)
    return value.to_bytes(2, 'little')


class ReadOnlyRTUOverTCP(ReadOnlyModbusTCP):
    """Reuse stream ownership/timeout handling, with RTU framing and serial IDs."""

    def __init__(self, host: str, port: int, *, timeout: float = 3.0):
        # Transparent tunnels have no assumed standard TCP listening port.
        super().__init__(host, port, timeout=timeout)

    async def read_registers(self, *, unit_id: int, address: int, count: int,
                             function_code: int = 3) -> tuple[int, ...]:
        _integer(unit_id, 1, 247, 'unit_id')
        return await super().read_registers(unit_id=unit_id, address=address,
                                             count=count, function_code=function_code)

    async def _exchange(self, unit: int, address: int, count: int, function: int):
        if self._writer is None or self._writer.is_closing():
            self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        request = struct.pack('>BBHH', unit, function, address, count)
        self._writer.write(request + crc16(request))
        await self._writer.drain()
        header = await self._reader.readexactly(3)
        if header[0] != unit or header[1] not in (function, function | 0x80):
            raise ModbusProtocolError('Mismatched RTU Unit ID or function')
        exception = header[1] == function | 0x80
        if not exception and header[2] != count * 2:
            raise ModbusProtocolError('Invalid RTU byte count')
        tail = await self._reader.readexactly(2 if exception else header[2] + 2)
        payload = header + tail[:-2]
        if crc16(payload) != tail[-2:]:
            raise ModbusProtocolError('Invalid RTU CRC')
        if exception:
            if header[2] == 0:
                raise ModbusProtocolError('Malformed RTU exception')
            raise ModbusDeviceError(header[2])
        return struct.unpack('>' + 'H' * count, tail[:-2])
