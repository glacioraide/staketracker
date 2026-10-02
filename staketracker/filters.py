"""Time-series filtering and unit-conversion functions for stake measurements.

This module operates on [`pandas.DataFrame`][] objects produced by the
detection pipeline.  All functions are **pure** (they return new DataFrames)
and can therefore be chained without side effects.
"""

import pandas as pd

# ---------------------------------------------------------------------------
# Row-level filters
# ---------------------------------------------------------------------------


def filter_rapid_changes(
    results: pd.DataFrame,
    window_size: int = 10,
    rapid_change_threshold_px: int = 10,
) -> pd.DataFrame:
    """Remove rows whose height deviates sharply from the local median.

    A measurement is discarded when its ``balise_height_px`` value differs
    from the rolling median by more than ``rapid_change_threshold_px`` pixels.
    This rejects camera shake, misdetections, and sudden illumination jumps.

    Parameters
    ----------
    results : pandas.DataFrame
        DataFrame with a ``balise_height_px`` column.
    window_size : int, default 10
        Half-window size (in rows) used for the rolling median.
    rapid_change_threshold_px : int, default 10
        Maximum allowed deviation from the local median (pixels).

    Returns
    -------
    pandas.DataFrame
        Filtered DataFrame with outlier rows removed.
    """
    local_median = results["balise_height_px"].rolling(window=window_size, center=True, min_periods=1).median()
    return results[results["balise_height_px"].sub(local_median).abs().le(rapid_change_threshold_px)]


def filter_min_max_height(
    results: pd.DataFrame,
    min_height: int = 10,
    max_height: int = 100,
) -> pd.DataFrame:
    """Remove rows outside the physically plausible height range.

    Parameters
    ----------
    results : pandas.DataFrame
        DataFrame with a ``balise_height_px`` column.
    min_height : int, default 10
        Minimum acceptable height (pixels).
    max_height : int, default 100
        Maximum acceptable height (pixels).

    Returns
    -------
    pandas.DataFrame
        Filtered DataFrame with out-of-range rows removed.
    """
    return results[(results["balise_height_px"] > min_height) & (results["balise_height_px"] < max_height)]


# ---------------------------------------------------------------------------
# Composite filter pipeline
# ---------------------------------------------------------------------------


def apply_filters(results: pd.DataFrame) -> pd.DataFrame:
    """Apply the full filtering pipeline to raw detection results.

    The pipeline (in order):

    1. Drop rows with a missing ``creation_date``.
    2. Remove rows outside the physically plausible height range
       ([`filter_min_max_height`][]).
    3. Remove rows with rapid, non-physical height jumps
       ([`filter_rapid_changes`][]).

    Parameters
    ----------
    results : pandas.DataFrame
        Raw detection results with ``creation_date`` and ``balise_height_px``
        columns.

    Returns
    -------
    pandas.DataFrame
        Cleaned DataFrame ready for time-series analysis.
    """
    filtered = results.dropna(subset=["creation_date"]).copy()
    filtered = filter_min_max_height(filtered)
    filtered = filter_rapid_changes(filtered)
    return filtered


# ---------------------------------------------------------------------------
# Temporal smoothing
# ---------------------------------------------------------------------------


def add_moving_average(
    results: pd.DataFrame,
    rolling_window: str = "24h",
) -> pd.DataFrame:
    """Append a time-indexed moving-average column to the results DataFrame.

    Parameters
    ----------
    results : pandas.DataFrame
        Must contain ``creation_date`` and ``balise_height_px`` columns.
        ``creation_date`` is coerced to [`pandas.Timestamp`][] if needed.
    rolling_window : str, default "24h"
        Pandas offset string defining the rolling window (e.g. ``"24h"``,
        ``"7D"``).

    Returns
    -------
    pandas.DataFrame
        DataFrame with an additional ``balise_height_px_moving_average``
        column.
    """
    averaged = results.copy()
    averaged["creation_date"] = pd.to_datetime(averaged["creation_date"], errors="coerce")
    averaged["balise_height_px_moving_average"] = (
        averaged.set_index("creation_date")["balise_height_px"]
        .rolling(window=rolling_window, min_periods=1)
        .mean()
        .to_numpy()
    )
    return averaged


# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------


def convert_px_to_metres(
    results: pd.DataFrame,
    px_per_metre: float,
) -> pd.DataFrame:
    """Convert pixel-unit height columns to metres using a calibration factor.

    Parameters
    ----------
    results : pandas.DataFrame
        Must contain a ``balise_height_px`` column.  If
        ``balise_height_px_moving_average`` is also present it is converted
        too.
    px_per_metre : float
        Number of pixels that correspond to one metre in the image.

    Returns
    -------
    pandas.DataFrame
        DataFrame with additional ``balise_height_m`` (and optionally
        ``balise_height_m_moving_average``) columns.
    """
    converted = results.copy()
    converted["balise_height_m"] = converted["balise_height_px"] / px_per_metre
    if "balise_height_px_moving_average" in converted.columns:
        converted["balise_height_m_moving_average"] = converted["balise_height_px_moving_average"] / px_per_metre
    return converted
