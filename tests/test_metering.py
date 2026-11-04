"""Synthetic AC balance and provenance regressions; never open a connection."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import math

import pytest

from core.metering import PowerFormula, PowerSample, evaluate_power

NOW = datetime(2026, 11, 4, tzinfo=timezone.utc)


def sample(power, seconds=0, grid="main"):
    return PowerSample(grid, power, NOW - timedelta(seconds=seconds), NOW)


def evaluate(name, samples, formulas=None, **options):
    return evaluate_power(name, samples, formulas or {}, now=NOW,
                          max_age=options.get("max_age", timedelta(seconds=30)),
                          max_skew=options.get("max_skew", timedelta(seconds=5)))


def test_total_house_consumption_from_net_pv_and_battery_conserves_balance():
    # G=house-PV+battery. Battery is positive charging; PV is positive generation.
    formula = {"house": PowerFormula("main", (("grid", 1), ("pv", 1), ("battery", -1)))}
    for battery in (20, -20):
        for pv in (0, 80):
            sources = {"grid": sample(30 - pv + battery), "pv": sample(pv),
                       "battery": sample(battery)}
            result = evaluate("house", sources, formula)
            assert result.valid and result.power_kw == 30
            assert result.origin == "calculated"
            assert result.sources == ("battery", "grid", "pv")
            assert result.formula == formula["house"].terms


def test_mixed_branch_and_heater_change_do_not_become_pv_generation():
    formulas = {"residual": PowerFormula("main", (("grid", 1), ("house", -1), ("branch", -1)))}
    for heat in (0, 12):
        # Branch contains heaters, PV and battery, so its sign can be negative.
        branch = heat - 60 + 20
        sources = {"grid": sample(10 + branch), "house": sample(10), "branch": sample(branch)}
        assert evaluate("residual", sources, formulas).power_kw == 0
    sources["grid"] = sample(-1 + 10 + branch)
    assert evaluate("residual", sources, formulas).power_kw == -1  # no clamp


def test_derived_grid_cannot_independently_verify_its_own_inputs():
    samples = {"house": sample(10), "branch": sample(-30)}
    formulas = {"grid": PowerFormula("main", (("house", 1), ("branch", 1))),
                "residual": PowerFormula("main", (("grid", 1), ("house", -1), ("branch", -1)))}
    assert evaluate("grid", samples, formulas).power_kw == -20
    with pytest.raises(ValueError, match="repeated underlying"):
        evaluate("residual", samples, formulas)


@pytest.mark.parametrize("bad", [None, True, math.nan, math.inf, -math.inf, 10**400])
def test_unusable_sample_is_not_replaced_by_zero(bad):
    result = evaluate("load", {"load": sample(bad)})
    assert not result.valid and result.power_kw is None
    assert result.issues == ("load: missing_or_nonfinite",)


def test_new_receipt_does_not_refresh_old_measurement_or_derived_time():
    samples = {"a": sample(3, 31), "b": sample(2)}
    result = evaluate("sum", samples, {"sum": PowerFormula("main", (("a", 1), ("b", 1)))})
    assert result.power_kw is None and "a: stale" in result.issues
    assert "sum: time_skew" in result.issues
    assert result.oldest_measurement == NOW - timedelta(seconds=31)
    assert result.newest_measurement == NOW


def test_exact_age_and_skew_limits_are_valid_and_timezone_normalized():
    sources = {"a": sample(3, 30), "b": sample(2, 25)}
    sources["a"] = replace(sources["a"], measured_at=sources["a"].measured_at.astimezone(timezone(timedelta(hours=2))))
    result = evaluate("sum", sources, {"sum": PowerFormula("main", (("a", 1), ("b", 1)))})
    assert result.valid and result.power_kw == 5
    assert result.oldest_measurement == NOW - timedelta(seconds=30)


@pytest.mark.parametrize("measured,received", [(1, 0), (0, 1), (0, -1)])
def test_future_or_reversed_time_is_invalid(measured, received):
    result = evaluate("a", {"a": replace(sample(1), measured_at=NOW + timedelta(seconds=measured),
                                        received_at=NOW + timedelta(seconds=received))})
    assert not result.valid and "a: invalid_time_order" in result.issues


def test_nested_skew_uses_original_leaf_times_and_failure_propagates():
    formulas = {"first": PowerFormula("main", (("a", 1),)),
                "second": PowerFormula("main", (("first", 1), ("b", -1)))}
    result = evaluate("second", {"a": sample(4, 6), "b": sample(2)}, formulas)
    assert not result.valid and result.power_kw is None
    assert result.sources == ("a", "b") and "second: time_skew" in result.issues


@pytest.mark.parametrize("coefficient", [0, True, math.nan, math.inf])
def test_invalid_coefficients_rejected(coefficient):
    with pytest.raises(ValueError, match="coefficients"):
        evaluate("sum", {"a": sample(1)}, {"sum": PowerFormula("main", (("a", coefficient),))})


def test_invalid_configuration_cross_grid_cycles_missing_and_aliases():
    for formulas in (
        {"x": PowerFormula("main", (("unknown", 1),))},
        {"x": PowerFormula("main", (("x", 1),))},
        {"x": PowerFormula("main", (("y", 1),)), "y": PowerFormula("main", (("x", 1),))},
        {"x": PowerFormula("other", (("a", 1),))},
        {"x": PowerFormula("main", ())},
        {"x": PowerFormula("main", (("a", 1), ("a", -1)))},
        {"x": PowerFormula("main", (("a", 1),)), "a": PowerFormula("main", (("x", 1),))},
    ):
        with pytest.raises(ValueError):
            evaluate("x", {"a": sample(1)}, formulas)
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate("a", {"a": replace(sample(1), measured_at=NOW.replace(tzinfo=None))})
    with pytest.raises(ValueError, match="nonnegative"):
        evaluate("a", {"a": sample(1)}, max_age=timedelta(seconds=-1))


def test_overflow_is_invalid_instead_of_infinite_power():
    result = evaluate("x", {"a": sample(1e308)}, {"x": PowerFormula("main", (("a", 10),))})
    assert not result.valid and result.power_kw is None
    assert "x: nonfinite_result" in result.issues


def test_depth_limit_is_explicit_and_does_not_depend_on_python_stack_limit():
    formulas = {f"f{i}": PowerFormula("main", ((f"f{i+1}", 1),)) for i in range(70)}
    with pytest.raises(ValueError, match="depth or term limit"):
        evaluate("f0", {}, formulas)


def test_diamond_duplicate_is_rejected_but_independent_queries_can_reuse_sources():
    samples = {"a": sample(4), "b": sample(1)}
    formulas = {"left": PowerFormula("main", (("a", 1),)),
                "right": PowerFormula("main", (("a", -1), ("b", 1))),
                "total": PowerFormula("main", (("left", 1), ("right", 1)))}
    assert evaluate("left", samples, formulas).power_kw == 4
    assert evaluate("right", samples, formulas).power_kw == -3
    with pytest.raises(ValueError, match="repeated underlying"):
        evaluate("total", samples, formulas)
