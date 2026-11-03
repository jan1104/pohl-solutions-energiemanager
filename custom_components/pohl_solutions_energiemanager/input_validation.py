"""Pure input validation; never substitute synthetic data for missing forecasts."""

from datetime import datetime, timedelta, timezone
import math
from typing import Any


def finite_number(value: Any, name: str) -> float:
    """Read a finite number without treating a boolean as a numeric value."""
    if isinstance(value, bool):
        raise ValueError(f"{name}: boolean is not a number")
    try:
        result = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{name}: expected a number") from err
    if not math.isfinite(result):
        raise ValueError(f"{name}: expected a finite number")
    return result


def validate_battery_settings(values: dict[str, Any]) -> dict[str, Any]:
    """Validate UI values before storing or passing them to the optimizer."""
    result = dict(values)
    positive = ("capacity_kwh", "soc_step_kwh", "max_charge_kw", "max_discharge_kw")
    for key in positive:
        result[key] = finite_number(values[key], key)
        if result[key] <= 0:
            raise ValueError(f"{key}: must be greater than zero")
    for key in ("min_soc_pct", "max_soc_pct"):
        result[key] = finite_number(values[key], key)
    if not 0 <= result["min_soc_pct"] < result["max_soc_pct"] <= 100:
        raise ValueError("SOC limits must satisfy 0 <= minimum < maximum <= 100")
    for key in ("charge_efficiency", "discharge_efficiency"):
        result[key] = finite_number(values[key], key)
        if not 0 < result[key] <= 1:
            raise ValueError(f"{key}: must be greater than zero and at most one")
    result["wear_cost_eur_per_kwh"] = finite_number(values["wear_cost_eur_per_kwh"], "wear_cost_eur_per_kwh")
    if result["wear_cost_eur_per_kwh"] < 0:
        raise ValueError("Wear cost must not be negative")
    for key in ("allow_grid_charge", "allow_battery_export"):
        if not isinstance(values[key], bool):
            raise ValueError(f"{key}: expected true or false")
    if result["soc_step_kwh"] > result["capacity_kwh"]:
        raise ValueError("SOC step must not exceed capacity")
    # Bound the state space: HA should never be frozen by an accidentally tiny step.
    if result["capacity_kwh"] / result["soc_step_kwh"] > 1000:
        raise ValueError("Choose a coarser SOC step (at most 1000 capacity steps)")
    return result


def parse_forecast_rows(rows: Any, now: datetime | None = None) -> list[dict[str, Any]]:
    """Validate an explicit forecast and select its unelapsed intervals.

    All timestamps must include an offset. UTC continuity naturally supports DST.
    A source must supply enough remaining data for a useful plan (at least two slots).
    Past rows are validated too so bad input is never silently accepted. The
    ongoing slot is clipped to now, using its average forecast power for the
    remaining duration, so the current measured SOC and horizon start agree.
    """
    if not isinstance(rows, list) or not 2 <= len(rows) <= 400:
        raise ValueError("Forecast must contain between 2 and 400 slots")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Current time must include a UTC offset")
    result = []
    previous_end = None
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Slot {index}: expected an object")
        raw_start = row.get("start")
        try:
            start = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError) as err:
            raise ValueError(f"Slot {index}: invalid ISO timestamp") from err
        if start.tzinfo is None or start.utcoffset() is None:
            raise ValueError(f"Slot {index}: timestamp needs a UTC offset")
        start = start.astimezone(timezone.utc)
        duration = finite_number(row.get("duration_hours"), "duration_hours")
        if abs(duration - 0.25) > 1e-9:
            raise ValueError(f"Slot {index}: this version requires 15-minute slots")
        if start.minute % 15 or start.second or start.microsecond:
            raise ValueError(f"Slot {index}: start must be on a quarter-hour boundary")
        if previous_end is not None and start != previous_end:
            raise ValueError(f"Slot {index}: forecasts must be contiguous and ordered")
        previous_end = start + timedelta(hours=duration)
        clean = {"start": start, "duration_hours": duration}
        for key in ("pv_kw", "load_kw", "import_price_eur_kwh", "export_price_eur_kwh"):
            clean[key] = finite_number(row.get(key), f"Slot {index} {key}")
        if clean["pv_kw"] < 0 or clean["load_kw"] < 0:
            raise ValueError(f"Slot {index}: PV and load must not be negative")
        current = now.astimezone(timezone.utc)
        if previous_end > current:
            if start < current:
                clean["start"] = current
                clean["duration_hours"] = (previous_end - current).total_seconds() / 3600
            result.append(clean)
    if len(result) < 2:
        raise ValueError("Forecast is stale or has fewer than two remaining slots")
    if result[0]["start"] != now.astimezone(timezone.utc):
        raise ValueError("Forecast must cover the ongoing quarter hour; a gap is not assumed idle")
    return result
