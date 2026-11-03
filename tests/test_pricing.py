from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from pricing import PricePeriod, apply_price_sources, normalize_prices, validate_price_config

UTC = timezone.utc
START = datetime(2026, 11, 3, tzinfo=UTC)


def rows(count=2):
    return [{"start": (START + timedelta(minutes=15 * i)).isoformat(), "duration_hours": .25,
             "pv_kw": 20, "load_kw": 5} for i in range(count)]


def config(mode="url", unit="eur_mwh", **kwargs):
    return {"mode": mode, "unit": unit, "url": "https://example.org/prices.json", **kwargs}


def payload(values):
    return [{"start": (START + timedelta(minutes=15 * i)).isoformat(), "duration_hours": .25,
             "value": value} for i, value in enumerate(values)]


def test_units_and_negative_prices_are_explicit_and_correct():
    for unit, value in [("eur_kwh", -.05), ("ct_kwh", -5), ("eur_mwh", -50)]:
        result = normalize_prices({"prices": payload([value])}, unit)
        assert result[0].price_eur_kwh == -.05
        assert result[0].end - result[0].start == timedelta(minutes=15)


def test_independent_import_and_export_sources_apply_factor_and_adder_once():
    source_rows = rows()
    before = deepcopy(source_rows)
    imports = normalize_prices(payload([100, 200]), "eur_mwh")
    exports = normalize_prices(payload([5, -2]), "ct_kwh")
    result = apply_price_sources(source_rows, imports, exports,
        config(multiplier=1.19, adder_eur_kwh=.15), config(unit="ct_kwh", multiplier=.9, adder_eur_kwh=-.01))
    assert [x["import_price_eur_kwh"] for x in result] == pytest.approx([.269, .388])
    assert [x["export_price_eur_kwh"] for x in result] == pytest.approx([.035, -.028])
    assert source_rows == before


def test_fixed_and_forecast_modes_do_not_require_external_periods():
    inputs = rows()
    for row in inputs:
        row["export_price_eur_kwh"] = -.04
    result = apply_price_sources(inputs, None, None,
        config(mode="fixed", unit="ct_kwh", fixed_price=20, multiplier=1.1, adder_eur_kwh=.01),
        {"mode": "forecast", "multiplier": 20, "adder_eur_kwh": 30})
    assert result[0]["import_price_eur_kwh"] == pytest.approx(.23)
    assert result[0]["export_price_eur_kwh"] == -.04


def test_smard_native_wrapper_skips_null_but_never_fills_gap():
    stamp = int(START.timestamp() * 1000)
    periods = normalize_prices({"series": [[stamp, 100], [stamp + 900000, None], [stamp + 1800000, -50]]},
                               "eur_mwh", smard=True)
    assert len(periods) == 2
    assert periods[-1].price_eur_kwh == -.05
    with pytest.raises(ValueError, match="Lücke"):
        apply_price_sources(rows(3), periods, None, config(mode="smard"),
                            config(mode="fixed", fixed_price=0))


def test_external_coverage_cannot_be_extrapolated_or_forward_filled():
    periods = normalize_prices(payload([100]), "eur_mwh")
    with pytest.raises(ValueError, match="Lücke"):
        apply_price_sources(rows(), periods, None, config(), config(mode="fixed", fixed_price=0))
    earlier = [dict(rows(1)[0], start=(START - timedelta(minutes=15)).isoformat())]
    with pytest.raises(ValueError, match="fehlen"):
        apply_price_sources(earlier, periods, None, config(), config(mode="fixed", fixed_price=0))


def test_gaps_outside_requested_intervals_do_not_invalidate_coverage():
    data = payload([100, 200, 300])
    periods = normalize_prices([data[0], data[2]], "eur_mwh")
    result = apply_price_sources(rows(1), periods, None, config(), config(mode="fixed", fixed_price=0))
    assert result[0]["import_price_eur_kwh"] == .1


def test_explicit_hourly_tariff_covers_quarters_and_weighted_spanning_rows():
    data = [{"start": START.isoformat(), "duration_hours": 1, "value": .1},
            {"start": (START + timedelta(hours=1)).isoformat(), "duration_hours": 1, "value": .3}]
    periods = normalize_prices(data, "eur_kwh")
    result = apply_price_sources(rows(2), periods, None, config(unit="eur_kwh"), config(mode="fixed", fixed_price=0))
    assert result[1]["import_price_eur_kwh"] == .1
    spanning = [dict(rows(1)[0], start=(START + timedelta(minutes=30)).isoformat(), duration_hours=1)]
    result = apply_price_sources(spanning, periods, None, config(unit="eur_kwh"), config(mode="fixed", fixed_price=0))
    assert result[0]["import_price_eur_kwh"] == pytest.approx(.2)


def test_overlaps_and_duplicate_instants_rejected_after_utc_conversion():
    duplicate = payload([100])[0]
    alias = dict(duplicate, start="2026-11-03T01:00:00+01:00")
    with pytest.raises(ValueError, match="überlappende"):
        normalize_prices([duplicate, alias], "eur_mwh")
    overlapping = dict(duplicate, start=(START + timedelta(minutes=5)).isoformat())
    with pytest.raises(ValueError, match="überlappende"):
        normalize_prices([duplicate, overlapping], "eur_mwh")


def test_dst_folds_are_distinct_physical_price_periods():
    data = [{"start": "2026-10-25T02:00:00+02:00", "duration_hours": .25, "value": 10},
            {"start": "2026-10-25T02:00:00+01:00", "duration_hours": .25, "value": 20}]
    periods = normalize_prices(data, "ct_kwh")
    requested = [{"start": x["start"], "duration_hours": .25} for x in data]
    result = apply_price_sources(requested, periods, None, config(unit="ct_kwh"), config(mode="fixed", fixed_price=0))
    assert [x["import_price_eur_kwh"] for x in result] == [.1, .2]


@pytest.mark.parametrize("bad", [True, None, float("nan"), float("inf"), "10"])
def test_invalid_prices_rejected(bad):
    with pytest.raises(ValueError):
        normalize_prices(payload([bad]), "eur_kwh")


@pytest.mark.parametrize("change", [{"unit": "EUR"}, {"multiplier": -1}, {"multiplier": True},
    {"adder_eur_kwh": float("nan")}, {"url": "file:///etc/passwd"},
    {"url": "https://user:password@example.org/prices"}, {"url": "https://example.org:99999"},
    {"url": "https://example.org/prices#fragment"}])
def test_bad_source_settings_rejected(change):
    with pytest.raises(ValueError):
        validate_price_config(config(**change))


def test_external_sources_require_units_and_entity_ids():
    with pytest.raises(ValueError, match="Einheit"):
        validate_price_config({"mode": "url", "url": "https://example.org"})
    with pytest.raises(ValueError, match="Entität"):
        validate_price_config({"mode": "entity", "unit": "eur_kwh", "entity_id": "bad"})
    assert validate_price_config({"mode": "entity", "unit": "eur_kwh", "entity": "sensor.prices"})["entity_id"] == "sensor.prices"
    assert validate_price_config({"mode": "smard"})["unit"] == "eur_mwh"


def test_interval_end_or_duration_required_and_consistent():
    with pytest.raises(ValueError):
        normalize_prices([{"start": START.isoformat(), "value": 10}], "ct_kwh")
    with pytest.raises(ValueError):
        normalize_prices([{"start": "2026-11-03T00:00:00", "duration_hours": .25, "value": 10}], "ct_kwh")
    with pytest.raises(ValueError, match="widersprechen"):
        normalize_prices([{**payload([10])[0], "end": (START + timedelta(hours=1)).isoformat()}], "ct_kwh")
    with pytest.raises(ValueError):
        normalize_prices([dict(payload([10])[0], duration_hours=-1)], "ct_kwh")


def test_manual_periods_are_validated_and_forecast_missing_side_is_error():
    bad = [PricePeriod(START, START, .1)]
    with pytest.raises(ValueError):
        apply_price_sources(rows(), bad, None, config(), config(mode="fixed", fixed_price=0))
    with pytest.raises(ValueError, match="export_price"):
        apply_price_sources(rows(), None, None, config(mode="fixed", fixed_price=0), {})


def test_smard_duplicate_null_edges_are_not_silently_combined():
    stamp = int(START.timestamp() * 1000)
    with pytest.raises(ValueError, match="Doppelte SMARD"):
        normalize_prices({"series": [[stamp, None], [stamp, 100]]}, "eur_mwh", smard=True)


def test_partial_ongoing_quarter_gets_its_full_source_period_price():
    requested = [{"start": START + timedelta(minutes=5), "duration_hours": 10 / 60}]
    result = apply_price_sources(requested, normalize_prices(payload([120]), "eur_mwh"), None,
                                 config(), config(mode="fixed", fixed_price=50))
    assert result[0]["import_price_eur_kwh"] == .12
    assert result[0]["duration_hours"] == 10 / 60
