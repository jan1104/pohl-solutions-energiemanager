"""Bind supplied decoded readings to project measurements, without any I/O."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from .metering import PowerSample, PowerValue, _finite_number, evaluate_power
from .project import validate_project


@dataclass(frozen=True, slots=True)
class RawPowerReading:
    """Decoded number BEFORE channel scale and unit conversion.

    source_id is a canonical opaque adapter identifier, not a connection secret.
    Aliases of one physical channel must share this ID. Device measurement time
    can be unknown; transport receipt time must never be substituted for it.
    """

    source_id: str
    value: float | None
    measured_at: datetime | None
    received_at: datetime | None


@dataclass(frozen=True, slots=True)
class BoundPowerMeasurement:
    measurement_id: str
    channel_id: str
    device_id: str
    node_id: str
    role: str
    phase: str | None
    source_kind: str
    source_config: tuple[tuple[str, object], ...]
    raw_unit: str
    scale: float
    polarity: int
    received_at: datetime | None
    value: PowerValue


def bind_power_measurement(
    project: dict,
    measurement_id: str,
    reading: RawPowerReading | None,
    *,
    polarity: int,
    now: datetime,
    max_age: timedelta,
    max_skew: timedelta,
) -> BoundPowerMeasurement:
    """Normalize one selected primary measurement and retain its exact mapping.

    Explicit polarity (+1 or -1) describes sensor orientation. It is independent
    of the configured numeric scale and never inferred from role or device.
    No sampling, register decode, JSON extraction, discovery, aggregation or
    device access occurs here. The caller supplies the selected channel's value.
    """
    if type(polarity) is not int or polarity not in (-1, 1):
        raise ValueError("An explicit polarity of +1 or -1 is required")
    validated = validate_project(project)
    measurement = next((m for m in validated["measurements"] if m["id"] == measurement_id), None)
    if measurement is None:
        raise ValueError(f"Unknown measurement: {measurement_id}")
    channel = next(c for c in validated["channels"] if c["id"] == measurement["channel_id"])
    node = next(n for n in validated["nodes"] if n["id"] == measurement["node_id"])
    source = channel["source"]
    scale = source.get("scale")
    scale = 1.0 if scale is None else float(scale)
    if reading is not None and (not isinstance(reading.source_id, str) or not reading.source_id.strip()):
        raise ValueError("Supplied readings require a canonical source ID")
    key = reading.source_id if reading is not None else channel["id"]
    number = None
    if reading is not None and _finite_number(reading.value):
        # Convert W first to avoid an unnecessary intermediate overflow where
        # the final kW value is representable. Each configured factor occurs once.
        number = float(reading.value) / (1000 if channel["unit"] == "W" else 1)
        number *= scale * polarity
    sample = PowerSample(node["grid_id"], number,
                         reading.measured_at if reading else None,
                         reading.received_at if reading else None)
    value = evaluate_power(key, {key: sample}, {}, now=now, max_age=max_age, max_skew=max_skew)
    if source["kind"] == "unconfigured":
        # A plausible supplied number is not evidence of a configured source.
        value = PowerValue(value.grid_id, None, value.origin, value.sources,
                           value.oldest_measurement, value.newest_measurement, (),
                           (*value.issues, f"{channel['id']}: source_unconfigured"))
    return BoundPowerMeasurement(
        measurement["id"], channel["id"], channel["device_id"], measurement["node_id"],
        measurement["role"], channel.get("phase"), source["kind"],
        tuple(sorted(source.items())), channel["unit"], scale, polarity,
        reading.received_at if reading else None, value,
    )
