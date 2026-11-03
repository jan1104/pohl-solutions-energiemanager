"""Explainable load forecasts from measured interval averages; no live fetching.

This first baseline deliberately does not invent weather or PV predictions. It can
be evaluated against history before it is used to populate planning inputs.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo
from math import isfinite


@dataclass(frozen=True)
class LoadObservation:
    start: datetime
    load_kw: float


@dataclass(frozen=True)
class LoadForecast:
    start: datetime
    p10_kw: float
    p50_kw: float
    p90_kw: float
    sample_days: int
    method: str


def _aware(value: datetime, *, aligned: bool = True) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Zeitstempel benötigen eine Zeitzone.")
    if aligned and (value.minute % 15 or value.second or value.microsecond):
        raise ValueError("Messwerte müssen an Viertelstunden beginnen.")


def _weighted_quantile(values: list[tuple[float, float]], quantile: float) -> float:
    ranked = sorted(values)
    threshold = sum(weight for _, weight in ranked) * quantile
    cumulative = 0.0
    for value, weight in ranked:
        cumulative += weight
        if cumulative >= threshold:
            return value
    return ranked[-1][0]


def predict_load(
    observations: list[LoadObservation],
    starts: list[datetime],
    *,
    as_of: datetime,
    local_zone: tzinfo,
    lookback_days: int = 56,
    min_sample_days: int = 3,
    half_life_days: float = 21.0,
) -> list[LoadForecast]:
    """Forecast 15-minute mean kW using recency-weighted historical quantiles.

    Prefer the same weekday. Fall back to workday/weekend, then same clock time.
    All input measurements must have ended by as_of. Future measurements never
    train the model. The bands describe historical variation, not calibrated
    probability guarantees. Missing history raises instead of supplying zero.
    """
    _aware(as_of, aligned=False)
    as_of = as_of.astimezone(timezone.utc)
    if lookback_days < 1 or min_sample_days < 1:
        raise ValueError("Historie und Mindestanzahl der Tage müssen positiv sein.")
    if not isfinite(half_life_days) or half_life_days <= 0:
        raise ValueError("Die zeitliche Gewichtung muss positiv sein.")
    history: list[LoadObservation] = []
    seen: set[datetime] = set()
    lower = as_of - timedelta(days=lookback_days)
    for item in observations:
        _aware(item.start)
        if not isfinite(item.load_kw) or item.load_kw < 0:
            raise ValueError("Hauslast muss eine endliche, nichtnegative Zahl sein.")
        instant = item.start.astimezone(timezone.utc)
        if instant in seen:
            raise ValueError("Doppelte Messintervalle sind nicht erlaubt.")
        seen.add(instant)
        if lower <= instant and instant + timedelta(minutes=15) <= as_of:
            history.append(LoadObservation(instant, item.load_kw))
    result = []
    previous: datetime | None = None
    for start in starts:
        _aware(start)
        instant = start.astimezone(timezone.utc)
        if instant < as_of:
            raise ValueError("Prognosen dürfen nicht vor dem Planungszeitpunkt liegen.")
        if previous is not None and instant <= previous:
            raise ValueError("Prognoseintervalle müssen zeitlich aufsteigend sein.")
        previous = instant
        target = start.astimezone(local_zone)
        same_time = [
            item for item in history
            if (item.start.astimezone(local_zone).hour,
                item.start.astimezone(local_zone).minute) == (target.hour, target.minute)
        ]
        groups = [
            ("gleicher Wochentag", [x for x in same_time
              if x.start.astimezone(local_zone).weekday() == target.weekday()]),
            ("Werktag/Wochenende", [x for x in same_time
              if (x.start.astimezone(local_zone).weekday() < 5) == (target.weekday() < 5)]),
            ("gleiche Ortszeit", same_time),
        ]
        for method, candidates in groups:
            day_count = len({x.start.astimezone(local_zone).date() for x in candidates})
            if day_count >= min_sample_days:
                break
        else:
            raise ValueError(f"Zu wenig Lastmessungen für {start.isoformat()}.")
        weighted = [(x.load_kw, 0.5 ** ((as_of - x.start).total_seconds()
                    / 86400 / half_life_days)) for x in candidates]
        result.append(LoadForecast(
            start, _weighted_quantile(weighted, .1), _weighted_quantile(weighted, .5),
            _weighted_quantile(weighted, .9), day_count, method,
        ))
    return result


def evaluate_load_forecast(
    predictions: list[LoadForecast], observations: list[LoadObservation]
) -> dict[str, float | int]:
    """Evaluate matching intervals; caller must construct predictions without leakage."""
    for item in observations:
        _aware(item.start)
        if not isfinite(item.load_kw) or item.load_kw < 0:
            raise ValueError("Ungültige Lastmessung.")
    actuals = {item.start.astimezone(timezone.utc): item.load_kw for item in observations}
    if len(actuals) != len(observations):
        raise ValueError("Doppelte Messintervalle sind nicht erlaubt.")
    errors = []
    seen = set()
    for predicted in predictions:
        _aware(predicted.start)
        instant = predicted.start.astimezone(timezone.utc)
        if instant in seen:
            raise ValueError("Doppelte Prognoseintervalle sind nicht erlaubt.")
        seen.add(instant)
        bands = (predicted.p10_kw, predicted.p50_kw, predicted.p90_kw)
        if not all(isfinite(x) and x >= 0 for x in bands) or not bands[0] <= bands[1] <= bands[2]:
            raise ValueError("Prognosebänder müssen endlich, nichtnegativ und geordnet sein.")
        if instant in actuals:
            actual = actuals[instant]
            errors.append(predicted.p50_kw - actual)
    if not errors:
        raise ValueError("Keine gemeinsamen Mess- und Prognoseintervalle.")
    return {
        "intervals": len(errors),
        "mae_kw": sum(abs(x) for x in errors) / len(errors),
        "bias_kw": sum(errors) / len(errors),
    }
