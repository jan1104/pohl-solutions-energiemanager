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


@dataclass(frozen=True)
class LoadBacktest:
    predictions: tuple[LoadForecast, ...]
    intervals: int
    mae_kw: float
    bias_kw: float


@dataclass(frozen=True)
class LoadBacktestComparison:
    model: LoadBacktest
    baseline: LoadBacktest
    mae_improvement_kw: float


def compare_load_forecast(
    observations: list[LoadObservation], starts: list[datetime], *,
    local_zone: tzinfo, lookback_days: int = 56, min_sample_days: int = 3,
    half_life_days: float = 21.0,
) -> LoadBacktestComparison:
    """Compare identical targets with persistence from exactly 168 hours earlier.

    The baseline uses elapsed UTC time, not a local calendar-week offset. Every
    lagged measurement is required; missing intervals never shrink the cohort.
    Positive improvement means lower model MAE, not an automatic model choice.
    """
    model = backtest_load_forecast(
        observations, starts, local_zone=local_zone, lookback_days=lookback_days,
        min_sample_days=min_sample_days, half_life_days=half_life_days)
    actuals = {item.start.astimezone(timezone.utc): item.load_kw for item in observations}
    predictions = []
    for start in starts:
        lag = start.astimezone(timezone.utc) - timedelta(hours=168)
        if lag not in actuals:
            raise ValueError("Für die Vergleichsprognose fehlt eine Messung genau 168 Stunden zuvor.")
        value = actuals[lag]
        predictions.append(LoadForecast(start, value, value, value, 1, 'Persistenz 168 Stunden UTC'))
    metrics = evaluate_load_forecast(predictions, observations)
    baseline = LoadBacktest(tuple(predictions), metrics['intervals'], metrics['mae_kw'], metrics['bias_kw'])
    return LoadBacktestComparison(model, baseline, baseline.mae_kw - model.mae_kw)


def backtest_load_forecast(
    observations: list[LoadObservation], starts: list[datetime], *,
    local_zone: tzinfo, lookback_days: int = 56, min_sample_days: int = 3,
    half_life_days: float = 21.0,
) -> LoadBacktest:
    """Explicit offline one-step rolling test, using completed intervals only.

    Every requested target must have an actual observation and enough history.
    No interval is silently skipped, and no result is persisted or activated.
    """
    if not starts:
        raise ValueError("Rücktest benötigt mindestens ein Zielintervall.")
    actuals = set()
    for item in observations:
        _aware(item.start)
        instant = item.start.astimezone(timezone.utc)
        if instant in actuals:
            raise ValueError("Doppelte Messintervalle sind nicht erlaubt.")
        actuals.add(instant)
    previous = None
    for start in starts:
        _aware(start)
        instant = start.astimezone(timezone.utc)
        if previous is not None and instant <= previous:
            raise ValueError("Rücktestintervalle müssen zeitlich aufsteigend sein.")
        if instant not in actuals:
            raise ValueError("Für jedes Rücktestintervall ist eine Lastmessung erforderlich.")
        previous = instant
    predictions = tuple(predict_load(
        observations, [start], as_of=start, local_zone=local_zone,
        lookback_days=lookback_days, min_sample_days=min_sample_days,
        half_life_days=half_life_days)[0] for start in starts)
    metrics = evaluate_load_forecast(list(predictions), observations)
    return LoadBacktest(predictions, metrics['intervals'], metrics['mae_kw'], metrics['bias_kw'])


def _aware(value: datetime, *, aligned: bool = True) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Zeitstempel benötigen eine Zeitzone.")
    if aligned and (value.minute % 15 or value.second or value.microsecond):
        raise ValueError("Messwerte müssen an Viertelstunden beginnen.")


def _finite_number(value):
    try:
        return not isinstance(value, bool) and isinstance(value, (int, float)) and isfinite(value)
    except OverflowError:
        return False


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
    if (type(lookback_days) is not int or type(min_sample_days) is not int
            or lookback_days < 1 or min_sample_days < 1):
        raise ValueError("Historie und Mindestanzahl der Tage müssen positiv sein.")
    if not _finite_number(half_life_days) or half_life_days <= 0:
        raise ValueError("Die zeitliche Gewichtung muss positiv sein.")
    if not isinstance(local_zone, tzinfo):
        raise ValueError("Für die Prognose ist eine ausdrückliche lokale Zeitzone erforderlich.")
    history: list[LoadObservation] = []
    seen: set[datetime] = set()
    try:
        lower = as_of - timedelta(days=lookback_days)
    except OverflowError:
        raise ValueError("Der Historienzeitraum ist nicht darstellbar.") from None
    for item in observations:
        _aware(item.start)
        if not _finite_number(item.load_kw) or item.load_kw < 0:
            raise ValueError("Hauslast muss eine endliche, nichtnegative Zahl sein.")
        instant = item.start.astimezone(timezone.utc)
        if instant in seen:
            raise ValueError("Doppelte Messintervalle sind nicht erlaubt.")
        seen.add(instant)
        if lower <= instant and instant + timedelta(minutes=15) <= as_of:
            history.append(LoadObservation(instant, item.load_kw))
    by_clock = {}
    for item in history:
        local = item.start.astimezone(local_zone)
        by_clock.setdefault((local.hour, local.minute), []).append(
            (item, local.weekday(), local.date()))
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
        same_time = by_clock.get((target.hour, target.minute), [])
        groups = [
            ("gleicher Wochentag", [x for x in same_time
              if x[1] == target.weekday()]),
            ("Werktag/Wochenende", [x for x in same_time
              if (x[1] < 5) == (target.weekday() < 5)]),
            ("gleiche Ortszeit", same_time),
        ]
        for method, candidates in groups:
            day_count = len({x[2] for x in candidates})
            if day_count >= min_sample_days:
                break
        else:
            raise ValueError(f"Zu wenig Lastmessungen für {start.isoformat()}.")
        # A common positive factor does not change weighted quantiles. Anchor
        # at the newest candidate so small half-lives cannot erase all weights
        # and accidentally select the smallest load as every forecast band.
        observations_for_target = [x[0] for x in candidates]
        newest = max(x.start for x in observations_for_target)
        weighted = [(x.load_kw, 0.5 ** ((newest - x.start).total_seconds()
                    / 86400 / half_life_days)) for x in observations_for_target]
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
        if not _finite_number(item.load_kw) or item.load_kw < 0:
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
        if not all(_finite_number(x) and x >= 0 for x in bands) or not bands[0] <= bands[1] <= bands[2]:
            raise ValueError("Prognosebänder müssen endlich, nichtnegativ und geordnet sein.")
        if instant in actuals:
            actual = actuals[instant]
            errors.append(predicted.p50_kw - actual)
    if not errors:
        raise ValueError("Keine gemeinsamen Mess- und Prognoseintervalle.")
    mae = sum(abs(x) for x in errors) / len(errors)
    bias = sum(errors) / len(errors)
    if not isfinite(mae) or not isfinite(bias):
        raise ValueError("Prognosefehler überschreiten den unterstützten Zahlenbereich.")
    return {
        "intervals": len(errors),
        "mae_kw": mae,
        "bias_kw": bias,
    }
