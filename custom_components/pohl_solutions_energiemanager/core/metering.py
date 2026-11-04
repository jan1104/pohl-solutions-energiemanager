"""Offline power-value provenance and quality checks; no device access.

Inputs are already normalized AC kW, with canonical source IDs. This layer does
not infer electrical coverage, signs, phases or units from a device's identity.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Mapping


@dataclass(frozen=True, slots=True)
class PowerSample:
    grid_id: str
    power_kw: float | None
    measured_at: datetime | None
    received_at: datetime | None


@dataclass(frozen=True, slots=True)
class PowerFormula:
    grid_id: str
    terms: tuple[tuple[str, float], ...]


@dataclass(frozen=True, slots=True)
class PowerValue:
    grid_id: str
    power_kw: float | None
    origin: str
    sources: tuple[str, ...]
    oldest_measurement: datetime | None
    newest_measurement: datetime | None
    formula: tuple[tuple[str, float], ...]
    issues: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return self.power_kw is not None and not self.issues


def _instant(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Measurement times must be timezone-aware")
    return value.astimezone(timezone.utc)


def _finite_number(value) -> bool:
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)
    except OverflowError:
        return False


def evaluate_power(
    value_id: str,
    samples: Mapping[str, PowerSample],
    formulas: Mapping[str, PowerFormula],
    *,
    now: datetime,
    max_age: timedelta,
    max_skew: timedelta,
) -> PowerValue:
    """Evaluate one value, rejecting unsafe configuration and invalid readings.

    Configuration errors raise ValueError. Missing/stale/nonfinite readings and
    non-simultaneous inputs return an invalid value, never a guessed zero. Age
    uses device measurement time, not the last transport receipt. Negative
    residuals are preserved, not silently clamped. Limits must be chosen by the
    caller; none are claimed to be suitable for a particular control loop.
    """
    now = _instant(now)
    for limit in (max_age, max_skew):
        if not isinstance(limit, timedelta) or limit < timedelta(0):
            raise ValueError("Age and skew limits must be nonnegative timedeltas")
    if samples.keys() & formulas.keys():
        raise ValueError("A value cannot be both measured and calculated")
    cache: dict[str, PowerValue] = {}
    visiting: set[str] = set()

    def resolve(key: str) -> PowerValue:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Source IDs must be nonempty strings")
        if key in visiting:
            raise ValueError(f"Cyclic power formula: {key}")
        if key in cache:
            return cache[key]
        if key in samples:
            sample = samples[key]
            if not isinstance(sample.grid_id, str) or not sample.grid_id.strip():
                raise ValueError(f"{key}: grid ID is required")
            measured = _instant(sample.measured_at) if sample.measured_at is not None else None
            received = _instant(sample.received_at) if sample.received_at is not None else None
            issues = []
            number = sample.power_kw
            if not _finite_number(number):
                issues.append(f"{key}: missing_or_nonfinite")
            if measured is None or received is None:
                issues.append(f"{key}: missing_time")
            if ((measured is not None and measured > now)
                    or (received is not None and received > now)
                    or (measured is not None and received is not None and measured > received)):
                issues.append(f"{key}: invalid_time_order")
            if measured is not None and now - measured > max_age:
                issues.append(f"{key}: stale")
            result = PowerValue(sample.grid_id, None if issues else float(number), "measured",
                                (key,), measured, measured, (), tuple(issues))
        elif key in formulas:
            formula = formulas[key]
            if len(visiting) >= 64 or len(formula.terms) > 128:
                raise ValueError("Power formula exceeds depth or term limit")
            if not isinstance(formula.grid_id, str) or not formula.grid_id.strip() or not formula.terms:
                raise ValueError(f"{key}: grid ID and nonempty terms are required")
            visiting.add(key)
            sources: set[str] = set()
            times = []
            issues = []
            total = 0.0
            for source, coefficient in formula.terms:
                if not _finite_number(coefficient) or coefficient == 0:
                    raise ValueError(f"{key}: coefficients must be finite and nonzero")
                child = resolve(source)
                if child.grid_id != formula.grid_id:
                    raise ValueError(f"{key}: cannot combine separate grid connections")
                if sources.intersection(child.sources):
                    raise ValueError(f"{key}: repeated underlying source; not independent")
                sources.update(child.sources)
                issues.extend(child.issues)
                if child.oldest_measurement is not None:
                    times.extend((child.oldest_measurement, child.newest_measurement))
                if child.valid:
                    total += coefficient * child.power_kw
            visiting.remove(key)
            if times and max(times) - min(times) > max_skew:
                issues.append(f"{key}: time_skew")
            if not isfinite(total):
                issues.append(f"{key}: nonfinite_result")
            result = PowerValue(formula.grid_id, None if issues else total, "calculated",
                                tuple(sorted(sources)), min(times) if times else None,
                                max(times) if times else None, formula.terms,
                                tuple(dict.fromkeys(issues)))
        else:
            # An absent source is unknown configuration, not zero consumption.
            raise ValueError(f"Unknown power source: {key}")
        cache[key] = result
        return result

    return resolve(value_id)
