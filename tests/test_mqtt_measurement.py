"""Delivered MQTT payloads only; no broker, subscription or device traffic."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from importlib import import_module
import json
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest

from core.project_v2 import migrate_project_v1_to_v2

NOW = datetime(2026, 11, 17, tzinfo=timezone.utc)


@pytest.fixture(scope='module')
def adapter():
    package = ModuleType('_pohl_mqtt_test')
    package.__path__ = [str(Path(__file__).resolve().parents[1] /
                            'custom_components/pohl_solutions_energiemanager')]
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(sys.modules, package.__name__, package)
        yield import_module(f'{package.__name__}.adapters.mqtt_measurement')


def project(version=2, *, path='power'):
    fixture = json.loads((Path(__file__).resolve().parents[1] / 'examples/simple-project.json').read_text(encoding='utf-8'))
    if version == 2:
        fixture = migrate_project_v1_to_v2(fixture)
    source = {'kind': 'mqtt', 'topic': 'synthetic/meter/power'}
    if path is not None:
        source['json_path'] = path
    fixture['channels'][0].update(unit='W', phase='total', source=source)
    return fixture


def bind(adapter, fixture=None, **overrides):
    values = dict(topic='synthetic/meter/power', payload=b'{"power":2500}',
                  source_id='synthetic-meter-channel', received_at=NOW, now=NOW,
                  max_age=timedelta(seconds=30), polarity=-1, retained=False,
                  measured_at=NOW - timedelta(seconds=2))
    values.update(overrides)
    return adapter.bind_mqtt_power_message(fixture or project(), 'grid_primary', **values)


@pytest.mark.parametrize('version', [1, 2])
@pytest.mark.parametrize('retained', [False, True])
def test_message_binding_preserves_provenance_and_units(adapter, version, retained, monkeypatch):
    connect = Mock(side_effect=AssertionError('MQTT binding tried to connect'))
    monkeypatch.setattr('socket.socket', connect)
    fixture = project(version)
    before = deepcopy(fixture)
    result = bind(adapter, fixture, retained=retained)
    assert result.decoded_value == 2500 and result.retained is retained
    bound = result.measurement
    assert bound.value.valid and bound.value.power_kw == -2.5
    assert bound.scale == 1 and bound.raw_unit == 'W' and bound.polarity == -1
    assert bound.value.sources == ('synthetic-meter-channel',)
    assert bound.value.oldest_measurement == NOW - timedelta(seconds=2)
    assert bound.received_at == NOW
    assert bound.source_config == (('json_path', 'power'), ('kind', 'mqtt'), ('topic', 'synthetic/meter/power'))
    assert fixture == before
    with pytest.raises(FrozenInstanceError):
        result.retained = False
    connect.assert_not_called()


@pytest.mark.parametrize('path', [None, 'nested.power', ' power '])
def test_numeric_root_nested_keys_and_literal_whitespace(adapter, path):
    fixture = project(path=path)
    payload = '2500' if path is None else '{"nested":{"power":2500}}' if path == 'nested.power' else '{" power ":2500}'
    fixture['channels'][0]['source']['topic'] = ' synthetic/topic '
    result = bind(adapter, fixture, payload=payload, topic=' synthetic/topic ')
    assert result.measurement.value.power_kw == -2.5
    fixture['channels'][0]['source']['json_path'] = None
    assert bind(adapter, fixture, topic=' synthetic/topic ', payload='2500').decoded_value == 2500


@pytest.mark.parametrize('measured,received,issue', [
    (None, NOW, 'missing_time'),
    (NOW - timedelta(seconds=31), NOW, 'stale'),
    (NOW + timedelta(seconds=1), NOW, 'invalid_time_order'),
    (NOW, NOW - timedelta(seconds=1), 'invalid_time_order'),
])
@pytest.mark.parametrize('retained', [False, True])
def test_reception_and_retained_delivery_do_not_prove_measurement_freshness(adapter, measured, received, issue, retained):
    value = bind(adapter, measured_at=measured, received_at=received, retained=retained).measurement.value
    assert not value.valid and value.power_kw is None
    assert f'synthetic-meter-channel: {issue}' in value.issues


@pytest.mark.parametrize('payload', [
    b'\xff', b'{broken', '{"power":1,"power":2}', '{"meta":{"x":1,"x":2},"power":1}',
    '{"power":NaN}', '{"power":Infinity}', '{"power":1e400}', '{"power":1,"other":1e400}',
    '{"power":true}', '{"power":"2500"}', '{"power":null}', '{"power":[2500]}',
    '{"wrong":2500}', '[2500]', '\ud800', b'0' * (64 * 1024 + 1),
    '[' * 30 + '0' + ']' * 30,
])
def test_invalid_payloads_never_become_power_and_diagnostics_omit_payload(adapter, payload):
    with pytest.raises(ValueError) as error:
        bind(adapter, payload=payload)
    assert '2500' not in str(error.value) and 'power":' not in str(error.value)


@pytest.mark.parametrize('change', [
    {'topic': 'other/topic'}, {'topic': None}, {'retained': 1}, {'polarity': True},
    {'source_id': ''}, {'received_at': NOW.replace(tzinfo=None)}, {'now': NOW.replace(tzinfo=None)},
    {'max_age': timedelta(seconds=-1)}, {'payload': {'power': 2500}},
])
def test_invalid_delivery_metadata_and_input_types_are_rejected(adapter, change):
    with pytest.raises(ValueError):
        bind(adapter, **change)


@pytest.mark.parametrize('path', ['a..b', '.power', 'nested.0', 'missing'])
def test_unsupported_or_missing_object_paths_fail_without_array_guessing(adapter, path):
    with pytest.raises(ValueError):
        bind(adapter, project(path=path), payload='{"nested":[2500],"power":2500}')


def test_wrong_source_and_wildcards_are_not_silently_matched(adapter):
    fixture = project()
    fixture['channels'][0]['source'] = {'kind': 'ha', 'entity_id': 'sensor.synthetic'}
    with pytest.raises(ValueError):
        bind(adapter, fixture)
    fixture = project()
    fixture['channels'][0]['source']['topic'] = 'synthetic/#'
    with pytest.raises(ValueError, match='exact topic'):
        bind(adapter, fixture, topic='synthetic/#')


def test_unused_metadata_is_not_interpreted_as_configuration_or_time(adapter):
    value = bind(adapter, payload='{"power":1000,"token":"not-a-credential","measured_at":"invented"}',
                 measured_at=None).measurement.value
    assert not value.valid and value.oldest_measurement is None

def test_kw_channel_does_not_apply_w_conversion_twice(adapter):
    fixture = project()
    fixture['channels'][0]['unit'] = 'kW'
    result = bind(adapter, fixture, payload='{"power":2.5}', polarity=1)
    assert result.decoded_value == result.measurement.value.power_kw == 2.5
    assert result.measurement.raw_unit == 'kW'


@pytest.mark.parametrize('payload', [
    '{"power":1,"metadata":"' + 'ü' * 40000 + '"}',
    '[' * 1100 + '0' + ']' * 1100,
])
def test_multibyte_size_and_parser_recursion_are_bounded(adapter, payload):
    with pytest.raises(ValueError, match='bounded'):
        bind(adapter, payload=payload)


@pytest.mark.parametrize('payload', [
    r'{"power":2500,"metadata":"\ud800"}',
    r'{"power":2500,"metadata":["\udfff"]}',
    r'{"power":2500,"metadata":{"\ud800":1}}',
    r'{"power":2500,"metadata":"\ud800\ud800"}',
    r'{"power":2500,"metadata":"\udfff\ud800"}',
])
@pytest.mark.parametrize('as_bytes', [False, True])
def test_escaped_lone_surrogates_rejected_everywhere_without_disclosing_content(adapter, payload, as_bytes):
    with pytest.raises(ValueError) as error:
        bind(adapter, payload=payload.encode('utf-8') if as_bytes else payload)
    assert str(error.value) == 'MQTT payload must be bounded, unambiguous finite UTF-8 JSON'


@pytest.mark.parametrize('as_bytes', [False, True])
def test_valid_surrogate_pairs_and_unicode_keys_remain_supported(adapter, as_bytes):
    fixture = project(path='\U0001f600.Leistung')
    payload = r'{"\ud83d\ude00":{"Leistung":2500},"metadata":["\ud83d\ude00","Größe"]}'
    result = bind(adapter, fixture, payload=payload.encode('utf-8') if as_bytes else payload)
    assert result.measurement.value.valid and result.measurement.value.power_kw == -2.5
    assert result.measurement.value.oldest_measurement == NOW - timedelta(seconds=2)


def connected_project(version=2, *, gateway=False):
    fixture = project(version)
    fixture['connections'][0]['kind'] = 'mqtt'
    meter = fixture['devices'][0]
    if gateway:
        meter['via_device_id'] = 'logger'
        fixture['devices'].append({
            'id': 'logger', 'name': 'Synthetischer Logger', 'kind': 'gateway',
            'area_id': 'area_main', 'node_id': 'storage',
            'connection_id': 'connection_main',
        })
    else:
        meter['connection_id'] = 'connection_main'
    return fixture


def connected_bind(adapter, fixture=None, **overrides):
    return adapter.bind_connected_mqtt_power_message(
        fixture or connected_project(), 'grid_primary', **dict({
            'connection_id': 'connection_main', 'topic': 'synthetic/meter/power',
            'payload': '{"power":2500}', 'source_id': 'synthetic-meter-channel',
            'received_at': NOW, 'now': NOW, 'max_age': timedelta(seconds=30),
            'polarity': -1, 'retained': False, 'measured_at': NOW - timedelta(seconds=2),
        }, **overrides))


@pytest.mark.parametrize('version', [1, 2])
@pytest.mark.parametrize('gateway', [False, True])
def test_connection_binding_uses_communication_path_without_io(adapter, version, gateway, monkeypatch):
    connect = Mock(side_effect=AssertionError('Connection binding opened a socket'))
    monkeypatch.setattr('socket.socket', connect)
    fixture = connected_project(version, gateway=gateway)
    before = deepcopy(fixture)
    result = connected_bind(adapter, fixture)
    assert result.route.connection_id == 'connection_main'
    assert result.message == bind(adapter, fixture)
    assert fixture == before
    with pytest.raises(FrozenInstanceError):
        result.route.connection_id = 'other'
    connect.assert_not_called()


@pytest.mark.parametrize('delivered', ['other_broker', ' connection_main', 'connection_main ', None, 1])
def test_same_topic_on_other_connection_cannot_supply_measurement(adapter, delivered, monkeypatch):
    fixture = connected_project()
    fixture['connections'].append({'id': 'other_broker', 'name': 'Zweiter Broker', 'kind': 'mqtt'})
    parse = Mock(side_effect=AssertionError('Wrong-route payload was parsed'))
    monkeypatch.setattr(adapter, '_parse_payload', parse)
    with pytest.raises(ValueError, match='connection does not match'):
        connected_bind(adapter, fixture, connection_id=delivered)
    parse.assert_not_called()


def test_repeated_reference_and_deep_gateway_path_are_unambiguous(adapter):
    fixture = connected_project(gateway=True)
    fixture['devices'][0]['connection_id'] = 'connection_main'
    fixture['devices'][-1]['via_device_id'] = 'upstream'
    fixture['devices'].append({
        'id': 'upstream', 'name': 'Synthetischer Zugang', 'kind': 'gateway',
        'area_id': 'area_main', 'node_id': 'main', 'connection_id': 'connection_main',
    })
    assert connected_bind(adapter, fixture).message.measurement.value.power_kw == -2.5


@pytest.mark.parametrize('electrical_parent', [False, True])
def test_missing_communication_path_never_uses_electrical_parent(adapter, electrical_parent):
    fixture = connected_project()
    fixture['devices'][0].pop('connection_id')
    if electrical_parent:
        fixture['devices'][0].update(kind='battery', parent_id='hybrid')
    with pytest.raises(ValueError, match='consistent connection'):
        connected_bind(adapter, fixture)


def test_conflicting_ancestor_connections_are_rejected(adapter):
    fixture = connected_project(gateway=True)
    fixture['connections'].append({'id': 'other_broker', 'name': 'Zweiter Broker', 'kind': 'mqtt'})
    # Adjacent device links are individually valid, but the complete path is ambiguous.
    fixture['devices'][-1].pop('connection_id')
    fixture['devices'][0]['connection_id'] = 'connection_main'
    fixture['devices'][-1]['via_device_id'] = 'upstream'
    fixture['devices'].append({
        'id': 'upstream', 'name': 'Synthetischer Zugang', 'kind': 'gateway',
        'area_id': 'area_main', 'node_id': 'main', 'connection_id': 'other_broker',
    })
    with pytest.raises(ValueError, match='consistent connection'):
        connected_bind(adapter, fixture)


@pytest.mark.parametrize('kind', ['modbus_tcp', 'ha', 'solarman'])
def test_non_mqtt_transport_cannot_supply_mqtt_measurement(adapter, kind):
    fixture = connected_project()
    fixture['connections'][0]['kind'] = kind
    with pytest.raises(ValueError, match='not an MQTT transport'):
        connected_bind(adapter, fixture)


@pytest.mark.parametrize('overrides', [
    {'topic': 'wrong'}, {'payload': '{"power":true}'}, {'retained': 1},
])
def test_route_binding_preserves_existing_message_rejections(adapter, overrides):
    with pytest.raises(ValueError):
        connected_bind(adapter, **overrides)


@pytest.mark.parametrize('retained', [False, True])
def test_connected_route_does_not_substitute_receipt_time(adapter, retained):
    result = connected_bind(adapter, measured_at=None, retained=retained)
    assert not result.message.measurement.value.valid
    assert 'synthetic-meter-channel: missing_time' in result.message.measurement.value.issues


def test_connected_binding_requires_selected_mqtt_measurement(adapter):
    fixture = connected_project()
    fixture['measurements'] = []
    with pytest.raises(ValueError, match='Unknown power measurement'):
        connected_bind(adapter, fixture)
    fixture = connected_project()
    fixture['channels'][0]['source'] = {'kind': 'ha', 'entity_id': 'sensor.synthetic'}
    with pytest.raises(ValueError, match='explicit MQTT source'):
        connected_bind(adapter, fixture)


def test_mqtt_route_rejects_unknown_device(adapter):
    with pytest.raises(ValueError, match='Unknown device'):
        adapter.resolve_mqtt_route(connected_project(), 'missing')
