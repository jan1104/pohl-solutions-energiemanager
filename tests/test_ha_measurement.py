"""Delivered state boundaries, with synthetic identity/time and no HA runtime."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from importlib import import_module
import json
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest

from core.project_v2 import migrate_project_v1_to_v2

NOW = datetime(2026, 11, 18, tzinfo=timezone.utc)


@pytest.fixture(scope='module')
def adapter():
    package = ModuleType('_pohl_ha_state_test')
    package.__path__ = [str(Path(__file__).resolve().parents[1] /
                            'custom_components/pohl_solutions_energiemanager')]
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(sys.modules, package.__name__, package)
        yield import_module(f'{package.__name__}.adapters.ha_measurement')


def project(version=2, unit='W'):
    fixture = json.loads((Path(__file__).resolve().parents[1] / 'examples/simple-project.json').read_text(encoding='utf-8'))
    if version == 2:
        fixture = migrate_project_v1_to_v2(fixture)
    fixture['channels'][0].update(unit=unit, phase='total', source={
        'kind': 'ha', 'entity_id': 'sensor.synthetic_power'})
    return fixture


def bind(adapter, fixture=None, **overrides):
    return adapter.bind_ha_power_state(fixture or project(), 'grid_primary', **dict({
        'entity_id': 'sensor.synthetic_power', 'state': '2500', 'unit': 'W',
        'source_id': 'synthetic-meter', 'received_at': NOW, 'now': NOW,
        'max_age': timedelta(seconds=30), 'polarity': -1,
        'measured_at': NOW - timedelta(seconds=2),
    }, **overrides))


@pytest.mark.parametrize('version', [1, 2])
@pytest.mark.parametrize('unit,state', [('W', '2500'), ('kW', '+2.5e0')])
def test_units_identity_and_provenance_without_io(adapter, version, unit, state, monkeypatch):
    connect = Mock(side_effect=AssertionError('HA binding opened a socket'))
    monkeypatch.setattr('socket.socket', connect)
    fixture = project(version, unit)
    before = deepcopy(fixture)
    result = bind(adapter, fixture, state=state, unit=unit)
    assert result.value.valid and result.value.power_kw == -2.5
    assert result.value.sources == ('synthetic-meter',)
    assert result.value.oldest_measurement == NOW - timedelta(seconds=2)
    assert result.received_at == NOW and result.raw_unit == unit and result.scale == 1
    assert result.source_config == (('entity_id', 'sensor.synthetic_power'), ('kind', 'ha'))
    assert fixture == before
    connect.assert_not_called()


@pytest.mark.parametrize('state', [
    'unknown', 'unavailable', '', ' ', 'NaN', 'inf', '-Infinity', '1e400',
    '2,5', '1_000', '２５００', '0x10', 'true', '2500 W', '0' * 129,
    None, True, 2500, {},
])
def test_unavailable_or_ambiguous_states_never_become_zero(adapter, state):
    with pytest.raises(ValueError) as error:
        bind(adapter, state=state)
    assert str(error.value) == 'HA power state must be bounded finite numeric text'


@pytest.mark.parametrize('changes', [
    {'entity_id': 'sensor.other'}, {'entity_id': None},
    {'entity_id': ' sensor.synthetic_power'}, {'unit': 'kW'},
    {'unit': 'w'}, {'unit': None}, {'unit': 'Wh'}, {'unit': {}},
])
def test_metadata_must_match_exactly(adapter, changes):
    with pytest.raises(ValueError):
        bind(adapter, **changes)


@pytest.mark.parametrize('measured,issue', [
    (None, 'missing_time'), (NOW - timedelta(seconds=31), 'stale'),
    (NOW + timedelta(seconds=1), 'invalid_time_order'),
])
def test_receipt_is_not_a_measurement_time(adapter, measured, issue):
    result = bind(adapter, measured_at=measured)
    assert not result.value.valid and result.value.power_kw is None
    assert f'synthetic-meter: {issue}' in result.value.issues


@pytest.mark.parametrize('state,expected', [(' -2500 ', 2.5), ('0', 0), ('.5e3', -.5)])
def test_signed_zero_and_decimal_states(adapter, state, expected):
    assert bind(adapter, state=state).value.power_kw == expected


def test_wrong_source_and_missing_measurement_rejected(adapter):
    fixture = project()
    fixture['channels'][0]['source'] = {'kind': 'mqtt', 'topic': 'synthetic/power'}
    with pytest.raises(ValueError, match='explicit HA source'):
        bind(adapter, fixture)
    fixture = project()
    fixture['measurements'] = []
    with pytest.raises(ValueError, match='Unknown power measurement'):
        bind(adapter, fixture)
