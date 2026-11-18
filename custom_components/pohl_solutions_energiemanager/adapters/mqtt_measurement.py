"""Bind explicitly supplied MQTT JSON power messages; never contact a broker."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import json

from ..core.connection_routes import MQTTRoute, resolve_mqtt_route
from ..core.measurement_binding import BoundPowerMeasurement, RawPowerReading, bind_power_measurement
from ..core.metering import _finite_number
from ..core.project_v2 import validate_project_document

MAX_PAYLOAD_BYTES = 64 * 1024
MAX_JSON_DEPTH = 24


@dataclass(frozen=True, slots=True)
class MQTTPowerMessage:
    decoded_value: float
    retained: bool
    measurement: BoundPowerMeasurement


@dataclass(frozen=True, slots=True)
class ConnectedMQTTPowerMessage:
    route: MQTTRoute
    message: MQTTPowerMessage


def bind_connected_mqtt_power_message(
    project: dict, measurement_id: str, *, connection_id: str,
    topic: str, payload: str | bytes, source_id: str, received_at: datetime,
    now: datetime, max_age: timedelta, polarity: int, retained: bool,
    measured_at: datetime | None = None,
) -> ConnectedMQTTPowerMessage:
    """Bind delivered connection identity before topic/value/time processing.

    The caller must obtain connection_id from its trusted connection owner,
    never from the message payload. No broker is contacted or authenticated here.
    """
    snapshot = validate_project_document(project)
    measurement = next((m for m in snapshot["measurements"] if m["id"] == measurement_id), None)
    if measurement is None:
        raise ValueError("Unknown power measurement")
    channel = next(c for c in snapshot["channels"] if c["id"] == measurement["channel_id"])
    if channel["source"]["kind"] != "mqtt":
        raise ValueError("Power measurement requires an explicit MQTT source")
    route = resolve_mqtt_route(snapshot, channel["device_id"])
    if not isinstance(connection_id, str) or connection_id != route.connection_id:
        raise ValueError("Message connection does not match the configured device route")
    message = bind_mqtt_power_message(
        snapshot, measurement_id, topic=topic, payload=payload, source_id=source_id,
        received_at=received_at, now=now, max_age=max_age, polarity=polarity,
        retained=retained, measured_at=measured_at)
    return ConnectedMQTTPowerMessage(route, message)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Nonfinite JSON number")


def _json_float(value):
    number = float(value)
    if not _finite_number(number):
        raise ValueError("Nonfinite JSON number")
    return number


def _parse_payload(payload):
    try:
        if isinstance(payload, bytes):
            if len(payload) > MAX_PAYLOAD_BYTES:
                raise ValueError("Oversized payload")
            text = payload.decode("utf-8")
        elif isinstance(payload, str):
            if len(payload) > MAX_PAYLOAD_BYTES or len(payload.encode("utf-8")) > MAX_PAYLOAD_BYTES:
                raise ValueError("Oversized payload")
            text = payload
        else:
            raise ValueError("Payload must be UTF-8 JSON bytes or text")
        data = json.loads(text, object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant, parse_float=_json_float)
        pending = [(data, 0)]
        while pending:
            value, depth = pending.pop()
            if depth > MAX_JSON_DEPTH:
                raise ValueError("Excessive JSON depth")
            if isinstance(value, dict):
                for key in value:
                    key.encode("utf-8")
                pending.extend((item, depth + 1) for item in value.values())
            elif isinstance(value, list):
                pending.extend((item, depth + 1) for item in value)
            elif isinstance(value, str):
                # JSON escapes can introduce lone surrogates even when the
                # original message consists entirely of valid UTF-8 bytes.
                value.encode("utf-8")
        return data
    except (ValueError, UnicodeError, RecursionError):
        # Do not expose payload, keys or values through diagnostics.
        raise ValueError("MQTT payload must be bounded, unambiguous finite UTF-8 JSON") from None


def bind_mqtt_power_message(
    project: dict, measurement_id: str, *, topic: str, payload: str | bytes,
    source_id: str, received_at: datetime, now: datetime, max_age: timedelta,
    polarity: int, retained: bool, measured_at: datetime | None = None,
) -> MQTTPowerMessage:
    """Decode a delivered message and use existing power/time/provenance checks.

    json_path uses literal dot-separated object keys, no array indices or code.
    Source identity and device time are explicit adapter inputs. Retained delivery
    never substitutes reception time for an unknown device measurement time.
    """
    snapshot = validate_project_document(project)
    measurement = next((m for m in snapshot["measurements"] if m["id"] == measurement_id), None)
    if measurement is None:
        raise ValueError("Unknown power measurement")
    channel = next(c for c in snapshot["channels"] if c["id"] == measurement["channel_id"])
    source = channel["source"]
    if source["kind"] != "mqtt":
        raise ValueError("Power measurement requires an explicit MQTT source")
    if any(character in source["topic"] for character in ("+", "#")):
        raise ValueError("MQTT power binding requires one exact topic, not a wildcard filter")
    if not isinstance(topic, str) or topic != source["topic"]:
        raise ValueError("Message topic does not match the configured source")
    if type(retained) is not bool:
        raise ValueError("Explicit retained-delivery metadata is required")
    value = _parse_payload(payload)
    path = source.get("json_path")
    if path is not None:
        keys = path.split(".")
        if any(not key for key in keys) or len(keys) > MAX_JSON_DEPTH:
            raise ValueError("MQTT JSON path requires bounded nonempty object keys")
        for key in keys:
            if not isinstance(value, dict) or key not in value:
                raise ValueError("Configured MQTT JSON path does not select a value")
            value = value[key]
    if not _finite_number(value):
        raise ValueError("MQTT power value must be a finite JSON number")
    decoded = float(value)
    bound = bind_power_measurement(
        snapshot, measurement_id, RawPowerReading(source_id, decoded, measured_at, received_at),
        polarity=polarity, now=now, max_age=max_age, max_skew=timedelta(0))
    return MQTTPowerMessage(decoded, retained, bound)
