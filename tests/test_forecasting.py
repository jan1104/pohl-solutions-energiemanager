from datetime import datetime, timedelta, timezone

import pytest

from forecasting import LoadForecast, LoadObservation, evaluate_load_forecast, predict_load

UTC = timezone.utc
NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


def history(value=10):
    return [LoadObservation(NOW - timedelta(days=i), value) for i in range(1, 43)]


def test_constant_load_and_future_outlier_are_not_leaked():
    values = history() + [LoadObservation(NOW, 1000)]
    plan = predict_load(values, [NOW], as_of=NOW, local_zone=UTC)
    assert plan[0].p50_kw == 10
    assert plan[0].p10_kw == plan[0].p90_kw == 10
    assert plan[0].method == "gleicher Wochentag"


def test_weekday_and_weekend_patterns_remain_distinct():
    values = [LoadObservation(x.start, 30 if x.start.weekday() < 5 else 5)
              for x in history()]
    starts = [NOW, NOW + timedelta(days=4)]
    plan = predict_load(values, starts, as_of=NOW, local_zone=UTC)
    assert [x.p50_kw for x in plan] == [30, 5]


def test_not_enough_history_is_an_error_not_a_zero_forecast():
    with pytest.raises(ValueError, match="Zu wenig"):
        predict_load([], [NOW], as_of=NOW, local_zone=UTC)


def test_timezone_is_required():
    with pytest.raises(ValueError, match="Zeitzone"):
        predict_load(history(), [NOW.replace(tzinfo=None)], as_of=NOW, local_zone=UTC)


def test_duplicate_history_is_rejected():
    values = history()
    with pytest.raises(ValueError, match="Doppelte"):
        predict_load(values + [values[0]], [NOW], as_of=NOW, local_zone=UTC)


def test_load_cannot_be_nan_or_negative():
    for value in [float("nan"), float("inf"), -1]:
        with pytest.raises(ValueError):
            predict_load(history(value), [NOW], as_of=NOW, local_zone=UTC)


def test_local_clock_time_matching():
    local = timezone(timedelta(hours=1))
    result = predict_load(history(), [NOW.astimezone(local)], as_of=NOW, local_zone=local)
    assert result[0].p50_kw == 10


def test_forecast_evaluation_reports_mae_and_signed_bias():
    predictions = [LoadForecast(NOW, 5, 8, 11, 4, "Test")]
    result = evaluate_load_forecast(predictions, [LoadObservation(NOW, 10)])
    assert result == {"intervals": 1, "mae_kw": 2, "bias_kw": -2}


@pytest.fixture
def berlin():
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        return ZoneInfo("Europe/Berlin")
    except ZoneInfoNotFoundError:
        pytest.skip("Europe/Berlin timezone data is not installed")


def test_autumn_clock_repeat_is_two_distinct_history_intervals(berlin):
    first = datetime(2026, 10, 25, 2, 0, tzinfo=berlin, fold=0)
    second = datetime(2026, 10, 25, 2, 0, tzinfo=berlin, fold=1)
    values = [LoadObservation(first, 10), LoadObservation(second, 20)]
    # Both share the wall-clock label, but are separated by a physical hour.
    assert predict_load(values, [], as_of=datetime(2026, 10, 26, tzinfo=berlin), local_zone=berlin) == []


def test_autumn_future_fold_cannot_leak_into_training(berlin):
    as_of = datetime(2026, 10, 25, 2, 15, tzinfo=berlin, fold=0)
    future_observation = LoadObservation(datetime(2026, 10, 25, 2, 0, tzinfo=berlin, fold=1), 1000)
    historical = [LoadObservation(datetime(2026, 10, 25, 2, 0, tzinfo=berlin) - timedelta(weeks=i), 10)
                  for i in range(1, 5)]
    target = datetime(2026, 11, 1, 2, 0, tzinfo=berlin)
    result = predict_load(historical + [future_observation], [target], as_of=as_of, local_zone=berlin)
    assert result[0].p10_kw == result[0].p50_kw == result[0].p90_kw == 10
    assert result[0].sample_days == 4


def test_autumn_completed_first_fold_is_available_during_second_fold(berlin):
    # At the second 02:15, the first 02:30 interval ended 30 physical minutes ago.
    as_of = datetime(2026, 10, 25, 2, 15, tzinfo=berlin, fold=1)
    observed = LoadObservation(datetime(2026, 10, 25, 2, 30, tzinfo=berlin, fold=0), 12)
    result = predict_load([observed], [datetime(2026, 11, 1, 2, 30, tzinfo=berlin)],
                          as_of=as_of, local_zone=berlin, min_sample_days=1)
    assert result[0].p50_kw == 12


def test_autumn_forecast_order_uses_physical_time(berlin):
    first = datetime(2026, 10, 25, 2, 45, tzinfo=berlin, fold=0)
    second = datetime(2026, 10, 25, 2, 0, tzinfo=berlin, fold=1)
    observations = [LoadObservation(datetime(2026, 10, 25, 2, minute, tzinfo=berlin) - timedelta(weeks=i), 10)
                    for i in range(1, 5) for minute in (0, 45)]
    result = predict_load(observations, [first, second],
                          as_of=datetime(2026, 10, 25, 0, 30, tzinfo=UTC), local_zone=berlin)
    assert len(result) == 2
    assert [x.start.astimezone(UTC) for x in result] == [
        datetime(2026, 10, 25, 0, 45, tzinfo=UTC), datetime(2026, 10, 25, 1, 0, tzinfo=UTC)]


def test_autumn_past_forecast_rejected_even_if_wall_label_is_later(berlin):
    with pytest.raises(ValueError, match="vor dem Planungszeitpunkt"):
        predict_load([], [datetime(2026, 10, 25, 2, 30, tzinfo=berlin, fold=0)],
                     as_of=datetime(2026, 10, 25, 2, 15, tzinfo=berlin, fold=1), local_zone=berlin)


def test_evaluation_matches_both_folds_separately_and_matches_offset_aliases(berlin):
    starts = [datetime(2026, 10, 25, 2, 0, tzinfo=berlin, fold=fold) for fold in (0, 1)]
    predictions = [LoadForecast(start, value, value, value, 4, "Test")
                   for start, value in zip(starts, (10, 20))]
    actuals = [LoadObservation(start.astimezone(UTC), value)
               for start, value in zip(starts, (10, 20))]
    assert evaluate_load_forecast(predictions, actuals) == {"intervals": 2, "mae_kw": 0, "bias_kw": 0}


def test_as_of_accepts_normal_nonquarterhour_execution_time():
    target = NOW + timedelta(minutes=15)
    observations = [LoadObservation(target - timedelta(days=i), 10) for i in range(1, 43)]
    result = predict_load(observations, [target], as_of=NOW + timedelta(minutes=3), local_zone=UTC)
    assert result[0].p50_kw == 10


@pytest.mark.parametrize("bands", [(0, float("nan"), 10), (0, 2, float("inf")), (-1, 2, 3), (3, 2, 1)])
def test_evaluation_rejects_invalid_prediction_bands(bands):
    with pytest.raises(ValueError, match="Prognosebänder"):
        evaluate_load_forecast([LoadForecast(NOW, *bands, 4, "Test")], [LoadObservation(NOW, 10)])


def test_evaluation_rejects_duplicate_physical_predictions():
    predicted = LoadForecast(NOW, 0, 5, 10, 4, "Test")
    with pytest.raises(ValueError, match="Doppelte Prognoseintervalle"):
        evaluate_load_forecast([predicted, predicted], [LoadObservation(NOW, 10)])
