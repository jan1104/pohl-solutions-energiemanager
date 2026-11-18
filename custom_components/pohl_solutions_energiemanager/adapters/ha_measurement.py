"""Bind supplied HA entity states without importing or querying Home Assistant."""

from datetime import datetime, timedelta
import re

from ..core.measurement_binding import BoundPowerMeasurement, RawPowerReading, bind_power_measurement
from ..core.metering import _finite_number
from ..core.project_v2 import validate_project_document

_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
MAX_STATE_LENGTH = 128


def bind_ha_power_state(
    project: dict, measurement_id: str, *, entity_id: str, state: str, unit: str,
    source_id: str, received_at: datetime, now: datetime, max_age: timedelta,
    polarity: int, measured_at: datetime | None = None,
) -> BoundPowerMeasurement:
    """Check identity and unit before decoding one delivered numeric state.

    The caller supplies trusted entity metadata and independently verified
    measurement time. last_changed/last_updated are not inferred here.
    """
    snapshot = validate_project_document(project)
    measurement = next((m for m in snapshot["measurements"] if m["id"] == measurement_id), None)
    if measurement is None:
        raise ValueError("Unknown power measurement")
    channel = next(c for c in snapshot["channels"] if c["id"] == measurement["channel_id"])
    source = channel["source"]
    if source["kind"] != "ha":
        raise ValueError("Power measurement requires an explicit HA source")
    if not isinstance(entity_id, str) or entity_id != source["entity_id"]:
        raise ValueError("Entity does not match the configured source")
    if channel["quantity"] != "active_power" or unit not in ("W", "kW") or unit != channel["unit"]:
        raise ValueError("Delivered power unit must match the configured W/kW channel")
    if (not isinstance(state, str) or len(state) > MAX_STATE_LENGTH
            or _NUMBER.fullmatch(state.strip()) is None):
        raise ValueError("HA power state must be bounded finite numeric text")
    decoded = float(state.strip())
    if not _finite_number(decoded):
        raise ValueError("HA power state must be bounded finite numeric text")
    return bind_power_measurement(
        snapshot, measurement_id, RawPowerReading(source_id, decoded, measured_at, received_at),
        polarity=polarity, now=now, max_age=max_age, max_skew=timedelta(0))
