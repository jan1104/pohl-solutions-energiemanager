"""Contract tests for HA input parsing, runnable without a Home Assistant install."""

from datetime import datetime, timedelta, timezone
import math

import pytest

from const import BATTERY_DEFAULTS
from input_validation import finite_number, parse_forecast_rows, validate_battery_settings


def forecast(now, count=4):
    return [
        {
            "start": (now + timedelta(minutes=15 * i)).isoformat(),
            "duration_hours": 0.25,
            "pv_kw": 20.0,
            "load_kw": 8.0,
            "import_price_eur_kwh": 0.25,
            "export_price_eur_kwh": -0.02,
        }
        for i in range(count)
    ]


def test_ongoing_slot_is_clipped_without_skipping_energy():
    start = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    result = parse_forecast_rows(forecast(start), start + timedelta(minutes=7))
    assert len(result) == 4
    assert result[0]["start"] == start + timedelta(minutes=7)
    assert result[0]["duration_hours"] == pytest.approx(8 / 60)
    assert result[0]["pv_kw"] * result[0]["duration_hours"] == pytest.approx(20 * 8 / 60)
    assert result[0]["export_price_eur_kwh"] == -0.02


def test_dst_fall_back_remains_contiguous_in_utc():
    rows = forecast(datetime(2026, 10, 25, 0, 45, tzinfo=timezone.utc))
    rows[0]["start"] = "2026-10-25T02:45:00+02:00"
    rows[1]["start"] = "2026-10-25T02:00:00+01:00"
    assert len(parse_forecast_rows(rows, datetime(2026, 10, 25, 0, 45, tzinfo=timezone.utc))) == 4


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, "unavailable", None])
def test_invalid_numbers_are_rejected(value):
    with pytest.raises(ValueError):
        finite_number(value, "power")


def test_forecast_rejects_a_gap_instead_of_filling_it_with_zero():
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    rows = forecast(now)
    rows.pop(1)
    with pytest.raises(ValueError, match="contiguous"):
        parse_forecast_rows(rows, now)


def test_forecast_rejects_naive_timezone():
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    rows = forecast(now)
    rows[0]["start"] = "2026-11-03T12:00:00"
    with pytest.raises(ValueError, match="offset"):
        parse_forecast_rows(rows, now)


def test_forecast_rejects_stale_or_far_future_data():
    now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="stale"):
        parse_forecast_rows(forecast(now - timedelta(days=1)), now)
    with pytest.raises(ValueError, match="ongoing quarter"):
        parse_forecast_rows(forecast(now + timedelta(hours=1)), now)


@pytest.mark.parametrize("overrides", [
    {"min_soc_pct": 90, "max_soc_pct": 10},
    {"charge_efficiency": 95},
    {"soc_step_kwh": 0.0001},
    {"wear_cost_eur_per_kwh": -0.01},
    {"allow_grid_charge": "false"},
])
def test_bad_settings_never_reach_optimizer(overrides):
    with pytest.raises(ValueError):
        validate_battery_settings({**BATTERY_DEFAULTS, **overrides})


def test_valid_settings_keep_grid_charge_disabled():
    assert validate_battery_settings(BATTERY_DEFAULTS)["allow_grid_charge"] is False
