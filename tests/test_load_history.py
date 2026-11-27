"""Synthetic supplied interval means; no file, device or provider reads."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
import sys
from types import ModuleType

import pytest


@pytest.fixture(scope='module')
def adapter():
    package = ModuleType('_pohl_load_history_test')
    package.__path__ = [str(Path(__file__).resolve().parents[1] /
                            'custom_components/pohl_solutions_energiemanager')]
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(sys.modules, package.__name__, package)
        yield import_module(f'{package.__name__}.load_history')


def normalize(adapter, rows=None, **options):
    return adapter.normalize_load_history(rows if rows is not None else [
        {'start': '2026-11-01T00:00:00Z', 'duration_minutes': 15, 'value': 2500}],
        **{'unit': 'W', 'aggregation': 'mean', 'source_id': 'synthetic-meter', **options})


def test_w_conversion_detaches_inputs_and_keeps_source(adapter):
    rows = [{'start': '2026-11-01T00:00:00Z', 'duration_minutes': 15, 'value': 2500}]
    before = deepcopy(rows)
    result = normalize(adapter, rows)
    assert rows == before
    rows[0]['value'] = 999
    assert result.source_id == 'synthetic-meter' and result.observations[0].load_kw == 2.5
    assert result.observations[0].start == datetime(2026, 11, 1, tzinfo=timezone.utc)
    with pytest.raises(FrozenInstanceError):
        result.observations[0].load_kw = 1
    assert normalize(adapter, [dict(before[0], value=2.5)], unit='kW').observations == result.observations


def test_fold_offsets_are_distinct_and_gaps_are_not_filled(adapter):
    rows = [{'start': start, 'duration_minutes': 15, 'value': value} for start, value in [
        ('2026-10-25T02:00:00+02:00', 10), ('2026-10-25T02:00:00+01:00', 20)]]
    result = normalize(adapter, rows, unit='kW')
    assert len(result.observations) == 2
    assert [x.load_kw for x in result.observations] == [10, 20]
    with pytest.raises(ValueError, match='ascending'):
        normalize(adapter, rows[::-1])
    with pytest.raises(ValueError, match='ascending'):
        normalize(adapter, [rows[0], rows[0]])


@pytest.mark.parametrize('options', [{'unit': 'Wh'}, {'aggregation': 'instant'},
                                     {'aggregation': None}, {'source_id': ''}, {'source_id': 'x' * 129}])
def test_no_implicit_units_or_aggregation(adapter, options):
    with pytest.raises(ValueError):
        normalize(adapter, **options)


@pytest.mark.parametrize('change', [
    {'value': True}, {'value': -1}, {'value': '2500'}, {'value': float('nan')}, {'value': 10 ** 400},
    {'value': 5e-324}, {'duration_minutes': 5}, {'duration_minutes': True},
    {'start': '2026-11-01T00:00:00'}, {'start': '2026-11-01T00:01:00Z'}, {'start': None},
    {'unverified': True},
])
def test_invalid_intervals_are_rejected_without_guessing(adapter, change):
    with pytest.raises(ValueError):
        normalize(adapter, [{'start': '2026-11-01T00:00:00Z', 'duration_minutes': 15, 'value': 2500, **change}])


def test_imported_means_can_feed_existing_backtest(adapter):
    forecasting = import_module(f'{adapter.__package__}.forecasting')
    rows = [{'start': f'2026-11-{day:02d}T00:00:00Z', 'duration_minutes': 15, 'value': 1000}
            for day in (1, 8, 15, 22)]
    history = normalize(adapter, rows)
    result = forecasting.compare_load_forecast(list(history.observations),
        [history.observations[-1].start], local_zone=timezone.utc)
    assert result.model.mae_kw == result.baseline.mae_kw == 0
