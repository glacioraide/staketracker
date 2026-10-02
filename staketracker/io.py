"""Input/output helpers for stake-tracker detection results.

This module handles loading raw detection CSVs and persisting processed
DataFrames to disk.  All functions are intentionally simple so that the data
provenance of every analysis run remains transparent.
"""

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from . import __version__


def load_data(input_files: list[str | Path]) -> pd.DataFrame:
    """Load and concatenate one or more detection result CSV files.

    Each file is expected to contain at least a ``creation_date`` column and a
    ``balise_height_px`` column, as produced by the detection pipeline.

    Parameters
    ----------
    input_files : list of str or pathlib.Path
        Paths to the CSV files to load.

    Returns
    -------
    pandas.DataFrame
        Concatenated DataFrame with ``creation_date`` parsed as
        [`pandas.Timestamp`][].

    Raises
    ------
    ValueError
        Raised when ``input_files`` is empty or no rows could be loaded.
    """
    if not input_files:
        raise ValueError("input_files must contain at least one path")

    dataframes = []
    for file_path in input_files:
        print(f"Loading {file_path}...")
        df = pd.read_csv(file_path, comment="#")
        df["creation_date"] = pd.to_datetime(df["creation_date"], errors="coerce")
        dataframes.append(df)

    if not dataframes:
        raise ValueError("No data loaded from input files")

    return pd.concat(dataframes, ignore_index=True)


def save_results(
    df: pd.DataFrame,
    output_file: str | Path,
    provenance: Mapping[str, str] | None = None,
) -> None:
    """Save a DataFrame to CSV, rounding floating-point columns to two decimals.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame to persist.
    output_file : str or pathlib.Path
        Destination file path.  Parent directories must already exist.
    provenance : mapping of str to str or None, default None
        Additional provenance entries written as CSV comment lines.
    """
    output_file = Path(output_file)
    print(f"Saving results to {output_file}...")
    df_out = df.copy()
    numeric_columns = df_out.select_dtypes(include=["float64", "float32"]).columns
    df_out[numeric_columns] = df_out[numeric_columns].round(2)

    provenance_lines = [f"# staketracker_version: {__version__}"]
    if provenance:
        provenance_lines.extend(f"# {key}: {value}" for key, value in provenance.items())

    with output_file.open("w", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(provenance_lines) + "\n")
        df_out.to_csv(handle, index=False)

    print(f"✓ Saved {len(df)} rows to {output_file}")
