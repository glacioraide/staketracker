import pandas as pd
import numpy as np
from staketracker.filters import filter_rapid_changes, filter_min_max_height


def test_filter_min_max_height():
    df = pd.DataFrame({"balise_height_px": [5, 15, 30, 70]})
    filtered = filter_min_max_height(df, min_height=10, max_height=67)
    # Should keep 15 and 30 only
    assert list(filtered["balise_height_px"]) == [15, 30]


def test_filter_rapid_changes():
    # Create a series where one point deviates sharply
    heights = [10, 11, 12, 30, 13, 14]
    df = pd.DataFrame({"balise_height_px": heights})
    filtered = filter_rapid_changes(df, window_size=3, rapid_change_threshold_px=5)
    # The outlier (30) should be removed
    assert 30 not in filtered["balise_height_px"].values
