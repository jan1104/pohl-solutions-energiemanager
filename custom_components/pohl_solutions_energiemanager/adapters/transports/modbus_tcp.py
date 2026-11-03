"""Read-only Modbus TCP, including TCP-to-RTU gateways with explicit Unit IDs.

No scans, writes, retries or background tasks. One instance serializes access to
one endpoint; reuse it for target devices behind the same gateway. This is native
Modbus TCP (MBAP), not a raw RTU-over-TCP tunnel or Solarman framing.
"""

import asyncio
from math import isfinite
import struct


class ModbusError(Exception):
    """Base error; never substitute missing data with a zero measurement."""


class ModbusTimeout(ModbusError):
    """The complete request, including queue/connect time, timed out."""


class ModbusProtocolError(ModbusError):
    """The peer returned an invalid or mismatched frame."""


class ModbusDeviceError(ModbusError):
    """The addressed device returned a complete Modbus exception response."""

    def __init__(self, code: int) -> None:
        self.code = code
        super().__init__(f"Modbus device exception {code}")


def _integer(value: int, low: int, high: int, name: str) -> None:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer between {low} and {high}")


def _finite(value: float) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return isfinite(value)
    except OverflowError:
        return False


class ReadOnlyModbusTCP:
    """A reusable endpoint. Constructing it never initiates network traffic."""

    def __init__(self, host: str, port: int = 502, *, timeout: float = 3.0) -> None:
        if (not isinstance(host, str) or not host or len(host) > 253
                or any(c.isspace() or c in "/@?#" for c in host)):
            raise ValueError("host must be a nonempty hostname or IP")
        _integer(port, 1, 65535, "port")
        if not _finite(timeout) or not 0 < timeout <= 30:
            raise ValueError("timeout must be greater than 0 and at most 30 seconds")
        self.host, self.port, self.timeout = host, port, float(timeout)
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._transaction = 0

    def _disconnect(self) -> None:
        writer = self._writer
        self._reader = self._writer = None
        if writer is not None:
            writer.close()

    async def async_close(self) -> None:
        """Close after any current read finishes; the next explicit read reconnects."""
        async with self._lock:
            writer = self._writer
            self._disconnect()
            if writer is not None:
                try:
                    async with asyncio.timeout(self.timeout):
                        await writer.wait_closed()
                except (OSError, TimeoutError):
                    pass

    async def read_registers(self, *, unit_id: int, address: int, count: int,
                             function_code: int = 3) -> tuple[int, ...]:
        """Read only FC03/FC04; no broadcast Unit ID or write function accepted."""
        _integer(unit_id, 1, 255, "unit_id")
        if 248 <= unit_id <= 254:
            raise ValueError("Use a serial Unit ID 1..247 or direct TCP Unit ID 255")
        _integer(address, 0, 65535, "address")
        _integer(count, 1, 125, "count")
        if address + count > 65536:
            raise ValueError("Register range exceeds address space")
        _integer(function_code, 3, 4, "function_code")
        try:
            async with asyncio.timeout(self.timeout):
                async with self._lock:
                    try:
                        return await self._exchange(unit_id, address, count, function_code)
                    except ModbusDeviceError:
                        # A complete exception frame consumed the transaction.
                        raise
                    except (OSError, asyncio.IncompleteReadError) as err:
                        self._disconnect()
                        raise ModbusError("Modbus connection failed or closed") from err
                    except BaseException:
                        # Cancellation while owning the stream invalidates its
                        # framing. Cancellation while waiting for the lock does not.
                        self._disconnect()
                        raise
        except TimeoutError as err:
            raise ModbusTimeout("Modbus read timed out") from err

    async def _exchange(self, unit: int, address: int, count: int, function: int) -> tuple[int, ...]:
        if self._writer is None or self._writer.is_closing():
            self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        self._transaction = (self._transaction + 1) % 65536
        transaction = self._transaction
        self._writer.write(struct.pack(">HHHBBHH", transaction, 0, 6, unit, function, address, count))
        await self._writer.drain()
        header = await self._reader.readexactly(7)
        reply_transaction, protocol, length, reply_unit = struct.unpack(">HHHB", header)
        if protocol != 0 or reply_transaction != transaction or reply_unit != unit or not 2 <= length <= 254:
            raise ModbusProtocolError("Invalid MBAP header or mismatched transaction/Unit ID")
        pdu = await self._reader.readexactly(length - 1)
        if pdu[0] == function | 0x80:
            if len(pdu) != 2 or pdu[1] == 0:
                raise ModbusProtocolError("Malformed Modbus exception")
            raise ModbusDeviceError(pdu[1])
        if pdu[0] != function or len(pdu) != 2 + count * 2 or pdu[1] != count * 2:
            raise ModbusProtocolError("Invalid function, byte count or response length")
        return struct.unpack(">" + "H" * count, pdu[2:])


def decode_registers(registers: tuple[int, ...], data_type: str, *,
                     byte_order: str = "big", word_order: str = "big", scale: float = 1) -> float:
    """Decode an explicit profile; never guess byte/word order from a value."""
    formats = {"u16": (1, "H"), "s16": (1, "h"), "u32": (2, "I"),
               "s32": (2, "i"), "float32": (2, "f")}
    if not isinstance(data_type, str) or data_type not in formats or byte_order not in ("big", "little") or word_order not in ("big", "little"):
        raise ValueError("Unsupported register type or byte/word order")
    count, code = formats[data_type]
    if len(registers) != count:
        raise ValueError("Wrong register count for data type")
    if not _finite(scale) or scale == 0:
        raise ValueError("Scale must be finite and nonzero")
    for value in registers:
        _integer(value, 0, 65535, "register")
    words = [value.to_bytes(2, "big") for value in registers]
    if byte_order == "little":
        words = [word[::-1] for word in words]
    if word_order == "little":
        words.reverse()
    result = struct.unpack(">" + code, b"".join(words))[0] * scale
    if not _finite(result):
        raise ValueError("Decoded measurement is not finite")
    return float(result)
