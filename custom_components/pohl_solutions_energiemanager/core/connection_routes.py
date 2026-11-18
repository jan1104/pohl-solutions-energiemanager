"""Resolve configuration references only; never construct or open a transport."""

from dataclasses import dataclass

from .project_v2 import validate_project_document


@dataclass(frozen=True, slots=True)
class ModbusRoute:
    connection_id: str
    unit_id: int


@dataclass(frozen=True, slots=True)
class MQTTRoute:
    connection_id: str


def _device_connection(snapshot, device_id, *, require_unit_id=False):
    """Follow communication ancestry only; electrical parents are unrelated."""
    devices = {d["id"]: d for d in snapshot["devices"]}
    if device_id not in devices:
        raise ValueError(f"Unknown device: {device_id}")
    device = devices[device_id]
    if require_unit_id and device.get("unit_id") is None:
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
    return device, connection


def resolve_mqtt_route(project, device_id) -> MQTTRoute:
    """Resolve one saved MQTT connection; no broker access or topic guessing."""
    snapshot = validate_project_document(project)
    _, connection = _device_connection(snapshot, device_id)
    if connection["kind"] != "mqtt":
        raise ValueError("Device connection is not an MQTT transport")
    return MQTTRoute(connection["id"])


def resolve_modbus_route(project, device_id) -> ModbusRoute:
    """Resolve gateway ancestry separately from electrical location/parent.

    This resolves TCP, serial and raw TCP configuration equally; it does not
    claim that all of those transports already have an implemented reader.
    """
    snapshot = validate_project_document(project)
    device, connection = _device_connection(snapshot, device_id, require_unit_id=True)
    unit = device.get("unit_id")
    if connection["kind"] not in ("modbus_tcp", "modbus_tcp_rtu_gateway", "modbus_rtu_usb", "rtu_over_tcp"):
        raise ValueError("Device connection is not a Modbus transport")
    return ModbusRoute(connection["id"], int(unit))
