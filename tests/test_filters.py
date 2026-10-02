import numpy as np
import pandas as pd
import pytest

from staketracker.filters import (
    add_moving_average,
    apply_filters,
    convert_px_to_metres,
    filter_min_max_height,
    filter_rapid_changes,
)


def test_filter_min_max_height():
    df = pd.DataFrame({"balise_height_px": [5, 15, 30, 70]})
    filtered = filter_min_max_height(df, min_height=10, max_height=67)
    assert list(filtered["balise_height_px"]) == [15, 30]


def test_filter_rapid_changes():
    heights = [10, 11, 12, 30, 13, 14]
    df = pd.DataFrame({"balise_height_px": heights})
    filtered = filter_rapid_changes(df, window_size=3, rapid_change_threshold_px=5)
    assert list(filtered["balise_height_px"]) == [10, 11, 12, 13, 14]


def test_apply_filters_drops_missing_dates_and_does_not_modify_input():
    df = pd.DataFrame(
        {
            "creation_date": pd.to_datetime(["2024-08-01 10:00", None, "2024-08-01 12:00", "2024-08-01 13:00"]),
            "balise_height_px": [40, 41, 0, 42],
        }
    )
    original = df.copy()

    filtered = apply_filters(df)

    assert list(filtered["balise_height_px"]) == [40, 42]
    pd.testing.assert_frame_equal(df, original)


def test_add_moving_average_uses_time_window():
    df = pd.DataFrame(
        {
            "creation_date": pd.to_datetime(["2024-08-01 10:00", "2024-08-01 11:00", "2024-08-03 10:00"]),
            "balise_height_px": [40, 50, 20],
        }
    )
    averaged = add_moving_average(df, rolling_window="24h")
    # The third point is two days later, so it is averaged alone.
    assert list(averaged["balise_height_px_moving_average"]) == [40, 45, 20]
    assert "balise_height_px_moving_average" not in df.columns


def test_convert_px_to_metres():
    df = pd.DataFrame({"balise_height_px": [177, 354], "balise_height_px_moving_average": [177.0, 88.5]})
    converted = convert_px_to_metres(df, px_per_metre=177)
    np.testing.assert_allclose(converted["balise_height_m"], [1.0, 2.0])
    np.testing.assert_allclose(converted["balise_height_m_moving_average"], [1.0, 0.5])


def test_convert_px_to_metres_without_moving_average():
    converted = convert_px_to_metres(pd.DataFrame({"balise_height_px": [354]}), px_per_metre=177)
    assert converted["balise_height_m"].iloc[0] == pytest.approx(2.0)
    assert "balise_height_m_moving_average" not in converted.columns
