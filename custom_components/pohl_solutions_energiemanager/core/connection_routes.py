"""Resolve configuration references only; never construct or open a transport."""

from dataclasses import dataclass

from .project import validate_project


@dataclass(frozen=True, slots=True)
class ModbusRoute:
    connection_id: str
    unit_id: int


def resolve_modbus_route(project, device_id) -> ModbusRoute:
    """Resolve gateway ancestry separately from electrical location/parent.

    This resolves TCP, serial and raw TCP configuration equally; it does not
    claim that all of those transports already have an implemented reader.
    """
    snapshot = validate_project(project)
    devices = {d["id"]: d for d in snapshot["devices"]}
    if device_id not in devices:
        raise ValueError(f"Unknown device: {device_id}")
    device = devices[device_id]
    unit = device.get("unit_id")
    if unit is None:
        raise ValueError("Device requires its own explicit Unit ID")
    connections = set()
    cursor = device
    while cursor is not None:
        if cursor.get("connection_id") is not None:
            connections.add(cursor["connection_id"])
        via = cursor.get("via_device_id")
        cursor = devices[via] if via is not None else None
    if len(connections) != 1:
        raise ValueError("Device path requires exactly one consistent connection reference")
    connection_id = next(iter(connections))
    connection = next(c for c in snapshot["connections"] if c["id"] == connection_id)
    if connection["kind"] not in ("modbus_tcp", "modbus_tcp_rtu_gateway", "modbus_rtu_usb", "rtu_over_tcp"):
        raise ValueError("Device connection is not a Modbus transport")
    return ModbusRoute(connection_id, int(unit))
