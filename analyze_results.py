#!/usr/bin/env python3
"""
Analyze staketracker detection results.

This script:
- Loads detection results from CSV files
- Applies filtering and moving average smoothing
- Converts pixel measurements to metres
- Calculates snow level estimates
- Saves processed results and generates plots
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================================
# Processing Functions
# ============================================================================


def filter_rapid_changes(results, window_size=10, rapid_change_threshold_px=10, inplace=False):
    """
    Filter out rapid changes in detected height that exceed a threshold.

    Parameters:
    - results: DataFrame with 'balise_height_px' column
    - window_size: Window size for local median calculation
    - rapid_change_threshold_px: Maximum allowed deviation from local median (in pixels)
    - inplace: If True, modify the original DataFrame

    Returns:
    - Filtered DataFrame
    """
    local_median = results["balise_height_px"].rolling(window=window_size, center=True, min_periods=1).median()
    filtered_results = results.copy() if not inplace else results
    filtered_results = filtered_results[filtered_results["balise_height_px"].sub(local_median).abs().le(rapid_change_threshold_px)]
    return filtered_results


def filter_min_max_height(results, min_height=10, max_height=67, inplace=False):
    """
    Filter out measurements outside acceptable height range.

    Parameters:
    - results: DataFrame with 'balise_height_px' column
    - min_height: Minimum acceptable height (pixels)
    - max_height: Maximum acceptable height (pixels)
    - inplace: If True, modify the original DataFrame

    Returns:
    - Filtered DataFrame
    """
    filtered_results = results.copy() if not inplace else results
    filtered_results = filtered_results[
        (filtered_results["balise_height_px"] > min_height) & (filtered_results["balise_height_px"] < max_height)
    ]
    return filtered_results


def apply_filters(results, inplace=False):
    """
    Apply all filters to the results.

    Applies:
    1. Remove rows with missing dates
    2. Filter by minimum/maximum height range
    3. Filter rapid changes

    Parameters:
    - results: DataFrame with detection results
    - inplace: If True, modify the original DataFrame

    Returns:
    - Filtered DataFrame
    """
    filtered_results = results.dropna(subset=["creation_date"])
    filtered_results = filter_min_max_height(filtered_results, inplace=inplace)
    filtered_results = filter_rapid_changes(filtered_results, inplace=inplace)
    return filtered_results


def add_moving_average(results, rolling_window="24h", inplace=False):
    """
    Add a moving average column to the results DataFrame.

    Parameters:
    - results: DataFrame with 'creation_date' and 'balise_height_px' columns
    - rolling_window: Window size for moving average (e.g., '24h' for 24 hours)
    - inplace: If True, modify the original DataFrame

    Returns:
    - DataFrame with added 'balise_height_px_moving_average' column
    """
    average_results = results.copy() if not inplace else results
    average_results["creation_date"] = pd.to_datetime(average_results["creation_date"], errors="coerce")
    average_results["balise_height_px_moving_average"] = (
        average_results.set_index("creation_date")["balise_height_px"].rolling(window=rolling_window, min_periods=1).mean().to_numpy()
    )
    return average_results


def convert_px_to_metres(results, px_per_metre, inplace=False):
    """
    Convert balise height from pixels to metres.

    The scale factor (px_per_metre) must be calibrated from a reference object
    of known real-world size visible in the images.

    Parameters:
    - results: DataFrame with 'balise_height_px' column
    - px_per_metre: Number of pixels per metre (calibration factor)
    - inplace: If True, modify the original DataFrame

    Returns:
    - DataFrame with added 'balise_height_m' and optionally
      'balise_height_m_moving_average' columns
    """
    converted = results.copy() if not inplace else results
    converted["balise_height_m"] = converted["balise_height_px"] / px_per_metre
    if "balise_height_px_moving_average" in converted.columns:
        converted["balise_height_m_moving_average"] = converted["balise_height_px_moving_average"] / px_per_metre
    return converted


# ============================================================================
# I/O Functions
# ============================================================================


def load_data(input_files):
    """
    Load and concatenate detection results from multiple CSV files.

    Parameters:
    - input_files: List of file paths to load

    Returns:
    - Concatenated DataFrame
    """
    dfs = []
    for file_path in input_files:
        print(f"Loading {file_path}...")
        df = pd.read_csv(file_path)
        df["creation_date"] = pd.to_datetime(df["creation_date"], errors="coerce")
        dfs.append(df)

    if not dfs:
        raise ValueError("No data loaded from input files")

    return pd.concat(dfs, ignore_index=True)


def save_results(df, output_file):
    """
    Save processed results to CSV file.

    Parameters:
    - df: DataFrame to save
    - output_file: Output file path
    """
    print(f"Saving results to {output_file}...")
    df.to_csv(output_file, index=False)
    print(f"✓ Saved {len(df)} rows to {output_file}")


# ============================================================================
# Plotting Functions
# ============================================================================


def plot_height_vs_time(raw_results, filtered_results, output_file=None):
    """
    Create plot comparing raw and filtered balise height over time.

    Parameters:
    - raw_results: DataFrame with raw measurements
    - filtered_results: DataFrame with filtered measurements (with moving average)
    - output_file: Optional file path to save plot
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    raw_results.plot(
        x="creation_date",
        y="balise_height_px",
        ax=ax,
        alpha=0.35,
        linewidth=1,
        label="Hauteur détectée (brute)",
    )

    filtered_results.plot(
        x="creation_date",
        y="balise_height_px_moving_average",
        ax=ax,
        linewidth=2.5,
        label="Hauteur filtrée (moyenne mobile 24h)",
        color="orange",
    )

    ax.invert_yaxis()
    ax.set_title("Hauteur de la balise au fil du temps")
    ax.set_xlabel("Date")
    ax.set_ylabel("Hauteur de la balise (px)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right")
    plt.tight_layout()

    if output_file:
        print(f"Saving plot to {output_file}...")
        plt.savefig(output_file, dpi=300)
        print(f"✓ Saved plot to {output_file}")

    plt.show()


def plot_snow_level(results_m, output_file=None):
    """
    Create plot of estimated snow level over time.

    Parameters:
    - results_m: DataFrame with height in metres
    - output_file: Optional file path to save plot
    """
    fig, ax = plt.subplots(figsize=(16, 6))

    results_m.plot(
        x="creation_date",
        y="snow_level_m",
        ax=ax,
        linewidth=2.5,
        label="Niveau de neige estimé",
        color="steelblue",
    )

    ax.set_title("Niveau de neige estimé au fil du temps")
    ax.set_xlabel("Date")
    ax.set_ylabel("Niveau de neige (m)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right")
    plt.tight_layout()

    if output_file:
        print(f"Saving plot to {output_file}...")
        plt.savefig(output_file, dpi=300)
        print(f"✓ Saved plot to {output_file}")

    plt.show()


def plot_snow_level_with_meteo(results_m, meteo_file, output_file=None):
    """
    Create plot comparing snow level with precipitation data.

    Parameters:
    - results_m: DataFrame with height in metres
    - meteo_file: Path to meteorological CSV file
    - output_file: Optional file path to save plot
    """
    try:
        meteo = pd.read_csv(meteo_file, skiprows=3)
        meteo["time"] = pd.to_datetime(meteo["time"], errors="coerce")
    except FileNotFoundError:
        print(f"Warning: Meteorological file not found: {meteo_file}")
        return

    fig, ax = plt.subplots(figsize=(16, 6))

    results_m.plot(
        x="creation_date",
        y="snow_level_m",
        ax=ax,
        linewidth=2.5,
        label="Niveau de neige (balise)",
        color="steelblue",
    )

    ax2 = ax.twinx()
    if "precipitation_sum (mm)" in meteo.columns:
        meteo.plot(
            x="time",
            y="precipitation_sum (mm)",
            ax=ax2,
            color="red",
            label="Précipitations totales (mm)",
            linewidth=2,
        )

    ax.set_title("Niveau de neige vs Précipitations")
    ax.set_xlabel("Date")
    ax.set_ylabel("Niveau de neige (m)", color="steelblue")
    ax2.set_ylabel("Précipitations (mm)", color="red")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left")
    ax2.legend(loc="upper right")
    plt.tight_layout()

    if output_file:
        print(f"Saving plot to {output_file}...")
        plt.savefig(output_file, dpi=300)
        print(f"✓ Saved plot to {output_file}")

    plt.show()


# ============================================================================
# Main Processing Pipeline
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Analyze stake tracker detection results and generate plots")
    parser.add_argument(
        "--input",
        "-i",
        nargs="+",
        default=[
            "2024_linceul_results/detection_results.csv",
            "2024-2025_linceul_results_part1/detection_results.csv",
            "2024-2025_linceul_results_part2/detection_results.csv",
        ],
        help="Input CSV files with detection results",
    )
    parser.add_argument(
        "--output", "-o", default="analysis_results", help="Output directory for results and plots (default: analysis_results)"
    )
    parser.add_argument("--px-per-metre", type=float, default=177.0, help="Calibration factor: pixels per metre (default: 177)")
    parser.add_argument("--meteo", help="Path to meteorological CSV file for comparison plots", default=None)
    parser.add_argument("--no-plots", action="store_true", help="Skip generating plots")

    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    # Load data
    print("=" * 70)
    print("LOADING DATA")
    print("=" * 70)
    results = load_data(args.input)
    print(f"✓ Loaded {len(results)} total rows\n")

    # Apply filters and moving average
    print("=" * 70)
    print("PROCESSING DATA")
    print("=" * 70)
    print("Applying filters...")
    filtered_results = apply_filters(results)
    print(f"✓ After filtering: {len(filtered_results)} rows")

    print("Adding moving average (24h window)...")
    filtered_results = add_moving_average(filtered_results)
    print("✓ Moving average added\n")

    # Convert to metres
    print("=" * 70)
    print("CONVERTING TO METRES")
    print("=" * 70)
    print(f"Using calibration factor: {args.px_per_metre} px/m")
    results_m = convert_px_to_metres(filtered_results, px_per_metre=args.px_per_metre)

    # Calculate snow level
    max_balise_height = results_m["balise_height_m_moving_average"].max()
    results_m["snow_level_m"] = max_balise_height - results_m["balise_height_m_moving_average"]
    print(f"✓ Maximum balise height: {max_balise_height:.3f} m")
    print(f"✓ Snow level calculated\n")

    # Save results
    print("=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)

    filtered_csv = output_dir / "filtered_results.csv"
    save_results(filtered_results, filtered_csv)

    results_m_csv = output_dir / "results_with_snow_level.csv"
    save_results(results_m, results_m_csv)
    print()

    # Generate plots
    if not args.no_plots:
        print("=" * 70)
        print("GENERATING PLOTS")
        print("=" * 70)

        height_plot = output_dir / "balise_height_vs_time.png"
        print("Creating height comparison plot...")
        plot_height_vs_time(results, filtered_results, output_file=height_plot)
        print()

        snow_plot = output_dir / "snow_level_vs_time.png"
        print("Creating snow level plot...")
        plot_snow_level(results_m, output_file=snow_plot)
        print()

        if args.meteo:
            meteo_plot = output_dir / "snow_level_with_precipitation.png"
            print("Creating snow level + precipitation plot...")
            plot_snow_level_with_meteo(results_m, args.meteo, output_file=meteo_plot)
            print()

    print("=" * 70)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
