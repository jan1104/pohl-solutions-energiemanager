"""Project-to-reading mapping, synthetic values only, no transport imports."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from core.measurement_binding import RawPowerReading, bind_power_measurement
from core.metering import PowerSample, evaluate_power

NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


def project(unit="kW", source=None):
    data = json.loads((Path(__file__).resolve().parents[1] / "examples/simple-project.json").read_text(encoding="utf-8"))
    data["channels"][0].update(unit=unit, source=source or {"kind": "ha", "entity_id": "sensor.synthetic_power"})
    return data


def reading(value, **changes):
    return replace(RawPowerReading("canonical-grid-channel", value, NOW, NOW), **changes)


def bind(data, raw, **kwargs):
    return bind_power_measurement(data, kwargs.get("measurement_id", "grid_primary"), raw,
                                  polarity=kwargs.get("polarity", 1), now=NOW,
                                  max_age=timedelta(seconds=30), max_skew=timedelta(seconds=5))


@pytest.mark.parametrize("unit,raw,expected", [("W", 2500, 2.5), ("kW", 2.5, 2.5), ("W", -2500, -2.5)])
def test_unit_and_explicit_polarity(unit, raw, expected):
    positive = bind(project(unit), reading(raw))
    negative = bind(project(unit), reading(raw), polarity=-1)
    assert positive.value.valid and positive.value.power_kw == expected
    assert negative.value.power_kw == -expected
    assert positive.value.sources == ("canonical-grid-channel",)
    assert positive.value.grid_id == "grid_main"


def test_scale_is_applied_once_before_returning_normalized_kw():
    data = project("W", {"kind": "modbus", "address": 100, "function_code": 3,
                         "data_type": "s16", "scale": -0.1})
    result = bind(data, reading(10000), polarity=-1)
    assert result.value.power_kw == 1
    assert result.scale == -0.1 and result.polarity == -1 and result.raw_unit == "W"
    assert dict(result.source_config) == data["channels"][0]["source"]
    assert result.channel_id == "power_grid" and result.device_id == "meter_grid"
    assert result.role == "grid" and result.node_id == "main"


def test_numeric_zero_remains_valid_and_is_not_missing():
    assert bind(project(), reading(0)).value.power_kw == 0
    assert bind(project(), reading(0)).value.valid


def test_missing_reading_has_no_fabricated_timestamps_or_zero():
    result = bind(project(), None)
    assert result.value.power_kw is None and not result.value.valid
    assert result.received_at is None
    assert result.value.oldest_measurement is None and result.value.newest_measurement is None
    assert any("missing_time" in issue for issue in result.value.issues)


def test_unknown_measurement_time_cannot_be_replaced_with_transport_receipt():
    result = bind(project(), reading(3, measured_at=None))
    assert result.received_at == NOW and result.value.power_kw is None
    assert result.value.oldest_measurement is None


def test_stale_reading_keeps_original_timestamp_despite_new_receipt():
    measured = NOW - timedelta(seconds=31)
    result = bind(project(), reading(3, measured_at=measured))
    assert result.value.power_kw is None
    assert result.value.oldest_measurement == measured
    assert result.received_at == NOW
    assert "canonical-grid-channel: stale" in result.value.issues


def test_unconfigured_source_does_not_accept_plausible_raw_reading():
    result = bind(project(source={"kind": "unconfigured"}), reading(123))
    assert not result.value.valid and result.value.power_kw is None
    assert "power_grid: source_unconfigured" in result.value.issues


@pytest.mark.parametrize("raw", [True, None, float("inf"), float("nan"), 10**400])
def test_invalid_numbers_are_not_coerced_to_valid_power(raw):
    result = bind(project(), reading(raw))
    assert not result.value.valid and result.value.power_kw is None


def test_normalization_overflow_is_invalid_and_not_infinite():
    data = project(source={"kind": "modbus", "address": 0, "function_code": 4,
                           "data_type": "float32", "scale": 1e308})
    assert not bind(data, reading(1e308)).value.valid


@pytest.mark.parametrize("polarity", [True, 0, 2, "-1", None, 1.0])
def test_polarity_is_always_explicit_and_strict(polarity):
    with pytest.raises(ValueError, match="polarity"):
        bind(project(), reading(3), polarity=polarity)


def test_unknown_measurement_and_invalid_project_are_rejected():
    with pytest.raises(ValueError, match="Unknown measurement"):
        bind(project(), reading(3), measurement_id="other")
    data = project()
    data["measurements"][0]["node_id"] = "not-found"
    with pytest.raises(ValueError, match="node_id"):
        bind(data, reading(3))
    with pytest.raises(ValueError, match="canonical source ID"):
        bind(project(), reading(3, source_id=""))


def test_metadata_retains_mqtt_path_without_guessing_individual_consumers():
    data = project(source={"kind": "mqtt", "topic": "synthetic/meter", "json_path": "power.total"})
    data["channels"][0]["phase"] = "total"
    result = bind(data, reading(12))
    assert result.phase == "total" and result.value.power_kw == 12
    assert dict(result.source_config)["json_path"] == "power.total"
    assert result.measurement_id == "grid_primary"


def test_import_and_evaluation_never_modify_input_or_result():
    data, raw = project(), reading(3)
    before = deepcopy(data)
    result = bind(data, raw)
    assert data == before and raw == reading(3)
    with pytest.raises(FrozenInstanceError):
        result.scale = 2


def test_missing_time_propagates_through_a_formula_without_fake_time():
    from core.metering import PowerFormula
    result = evaluate_power("derived", {"known": PowerSample("grid", 3, None, NOW)},
                            {"derived": PowerFormula("grid", (("known", 1),))},
                            now=NOW, max_age=timedelta(seconds=30), max_skew=timedelta(seconds=5))
    assert not result.valid and result.oldest_measurement is None


def test_unknown_receipt_time_and_invalid_known_times_are_not_accepted():
    assert not bind(project(), reading(3, received_at=None)).value.valid
    with pytest.raises(ValueError, match="timezone-aware"):
        bind(project(), reading(3, measured_at=NOW.replace(tzinfo=None)))
