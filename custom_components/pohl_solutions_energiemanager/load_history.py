"""Normalize explicitly supplied interval-average house loads, without I/O."""

from dataclasses import dataclass
from datetime import datetime, timezone

from .forecasting import LoadObservation, _aware, _finite_number


@dataclass(frozen=True, slots=True)
class LoadHistory:
    source_id: str
    observations: tuple[LoadObservation, ...]


def normalize_load_history(rows, *, unit, aggregation, source_id) -> LoadHistory:
    """Convert declared 15-minute means to UTC/kW, never interpolate missing data.

    This accepts delivered records, not instantaneous samples or energy meters.
    Gaps are retained; target coverage is checked by the forecast/backtest caller.
    Source identity is caller-verified provenance, not device authentication.
    """
    if unit not in ('W', 'kW') or aggregation != 'mean':
        raise ValueError('Explicit W/kW units and interval-mean aggregation are required')
    if not isinstance(source_id, str) or not source_id.strip() or len(source_id) > 128:
        raise ValueError('A bounded source identifier is required')
    if not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= 60_000:
        raise ValueError('Provide between 1 and 60000 interval means')
    result = []
    previous = None
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'start', 'duration_minutes', 'value'}:
            raise ValueError('Each interval requires start, duration_minutes and value only')
        duration = row['duration_minutes']
        if type(duration) not in (int, float) or duration != 15:
            raise ValueError('Load history requires complete 15-minute averages')
        value = row['value']
        if not _finite_number(value) or value < 0:
            raise ValueError('House load must be a finite nonnegative number')
        start = row['start']
        try:
            if isinstance(start, str):
                start = datetime.fromisoformat(start.replace('Z', '+00:00'))
            _aware(start)
            start = start.astimezone(timezone.utc)
            _aware(start)
        except (ValueError, OverflowError):
            raise ValueError('History starts must be timezone-aware quarter-hours') from None
        if previous is not None and start <= previous:
            raise ValueError('History intervals must be unique and ascending in UTC')
        normalized = float(value) / (1000 if unit == 'W' else 1)
        if value > 0 and normalized == 0:
            raise ValueError('Load mean is below the supported kW numeric range')
        result.append(LoadObservation(start, normalized))
        previous = start
    return LoadHistory(source_id, tuple(result))
