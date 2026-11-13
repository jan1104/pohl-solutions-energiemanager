"""Explicit read-only Modbus power binding through a caller-owned reader."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..core.connection_routes import ModbusRoute, resolve_modbus_route
from ..core.measurement_binding import BoundPowerMeasurement, RawPowerReading, bind_power_measurement
from ..core.metering import _instant
from ..core.project_v2 import validate_project_document
from .transports.base import RegisterReader
from .transports.modbus_tcp import decode_registers, register_count


@dataclass(frozen=True, slots=True)
class ModbusPowerRead:
    route: ModbusRoute
    decoded_value: float
    measurement: BoundPowerMeasurement


async def read_modbus_power_measurement(
    project: dict,
    measurement_id: str,
    *,
    reader_for_connection: Callable[[str], RegisterReader],
    source_id: str,
    byte_order: str,
    word_order: str,
    polarity: int,
    max_age: timedelta,
    measured_at: datetime | None = None,
    receipt_clock: Callable[[], datetime] | None = None,
) -> ModbusPowerRead:
    """Read one configured channel, decode, then normalize with the project binder.

    The caller supplies reader ownership, verified ordering, orientation and
    source identity. The caller may supply a measurement timestamp obtained
    independently from the device. A register reply supplies no such timestamp.
    """
    snapshot = validate_project_document(project)
    measurement = next((m for m in snapshot["measurements"] if m["id"] == measurement_id), None)
    if measurement is None:
        raise ValueError(f"Unknown measurement: {measurement_id}")
    channel = next(c for c in snapshot["channels"] if c["id"] == measurement["channel_id"])
    source = channel["source"]
    if source["kind"] != "modbus":
        raise ValueError("Measurement requires an explicit Modbus source")
    if byte_order not in ("big", "little") or word_order not in ("big", "little"):
        raise ValueError("Explicit byte and word order must be big or little")
    if type(polarity) is not int or polarity not in (-1, 1):
        raise ValueError("An explicit polarity of +1 or -1 is required")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("A canonical source ID is required")
    if not isinstance(max_age, timedelta) or max_age < timedelta(0):
        raise ValueError("Age limit must be a nonnegative timedelta")
    if receipt_clock is not None and not callable(receipt_clock):
        raise ValueError("Receipt clock must be callable")
    if measured_at is not None:
        measured_at = _instant(measured_at)

    route = resolve_modbus_route(snapshot, channel["device_id"])
    count = register_count(source["data_type"])
    address = int(source["address"])
    if address + count > 65536:
        raise ValueError("Register range exceeds address space")
    reader = reader_for_connection(route.connection_id)
    registers = await reader.read_registers(unit_id=route.unit_id, address=address, count=count,
                                           function_code=int(source["function_code"]))
    received_at = _instant(receipt_clock() if receipt_clock is not None else datetime.now(timezone.utc))
    decoded = decode_registers(registers, source["data_type"], byte_order=byte_order, word_order=word_order)
    bound = bind_power_measurement(
        snapshot, measurement_id, RawPowerReading(source_id, decoded, measured_at, received_at),
        polarity=polarity, now=received_at, max_age=max_age, max_skew=timedelta(0),
    )
    return ModbusPowerRead(route, decoded, bound)
