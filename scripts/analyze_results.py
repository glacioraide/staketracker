#!/usr/bin/env python3
"""Analyse detection CSVs: filter, convert to metres, compute snow level.

This script consumes one or more ``detection_results.csv`` files produced by
``scripts/detect_stakes.py``, applies time-series filters, converts pixel
heights to metres, and derives the snow level relative to the maximum observed
stake height.

Results are saved in a date-stamped output directory.  An optional
meteorological CSV (produced by ``scripts/fetch_meteo.py``) can be supplied to
generate combined precipitation + snow-level plots.

Usage example::

    python scripts/analyze_results.py \\
        --input analysis/detection_2026-04-29/detection_results.csv \\
        --output analysis/results \\
        --px-per-metre 177

    python scripts/analyze_results.py \\
        --input detection_part1/detection_results.csv \\
                detection_part2/detection_results.csv \\
        --output analysis/results \\
        --px-per-metre 177 \\
        --meteo analysis/weather.csv
"""

import argparse
from datetime import datetime
from pathlib import Path

from staketracker.filters import apply_filters, add_moving_average, convert_px_to_metres
from staketracker.io import load_data, save_results
from staketracker.plot import plot_height_vs_time, plot_snow_level, plot_snow_level_with_meteo


def main() -> None:
    """Filter detection results, convert to metres, and derive snow level."""
    parser = argparse.ArgumentParser(
        description="Analyse detection CSVs: filter, convert to metres, compute snow level",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        "-i",
        nargs="+",
        required=True,
        metavar="CSV",
        help="One or more detection_results.csv files to process",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="analysis_results",
        metavar="DIR",
        help="Base name for the output directory (run date is appended automatically)",
    )
    parser.add_argument(
        "--px-per-metre",
        type=float,
        default=177.0,
        help="Calibration factor: pixels per metre",
    )
    parser.add_argument(
        "--meteo",
        default=None,
        metavar="CSV",
        help="Path to meteorological CSV for combined precipitation plots",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip generating plots",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output directory if it already exists",
    )

    args = parser.parse_args()

    run_date = datetime.now().strftime("%Y-%m-%d")
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    output_dir = Path(f"{args.output}")
    if output_dir.exists() and not args.overwrite:
        raise ValueError(f"Output directory already exists: {output_dir}. Use --overwrite to overwrite it.")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    print("=" * 70)
    print("LOADING DATA")
    print("=" * 70)
    results = load_data(args.input)
    print(f"✓ Loaded {len(results)} total rows\n")

    print("=" * 70)
    print("PROCESSING DATA")
    print("=" * 70)
    print("Applying filters...")
    filtered_results = apply_filters(results)
    print(f"✓ After filtering: {len(filtered_results)} rows")
    print("Adding moving average (24 h window)...")
    filtered_results = add_moving_average(filtered_results)
    print("✓ Moving average added\n")

    print("=" * 70)
    print("CONVERTING TO METRES")
    print("=" * 70)
    print(f"Using calibration factor: {args.px_per_metre} px/m")
    results_m = convert_px_to_metres(filtered_results, px_per_metre=args.px_per_metre)

    max_balise_height = results_m["balise_height_m_moving_average"].max()
    results_m["snow_level_m"] = max_balise_height - results_m["balise_height_m_moving_average"]
    print(f"✓ Maximum balise height: {max_balise_height:.3f} m")
    print("✓ Snow level calculated\n")

    print("=" * 70)
    print("SAVING RESULTS")
    print("=" * 70)
    provenance = {
        "generated_at": generated_at,
        "px_per_metre": str(args.px_per_metre),
        "input_files": ", ".join(str(p) for p in args.input),
    }
    save_results(filtered_results, output_dir / "filtered_results.csv", provenance=provenance)
    save_results(results_m, output_dir / "results_with_snow_level.csv", provenance=provenance)
    print()

    if not args.no_plots:
        print("=" * 70)
        print("GENERATING PLOTS")
        print("=" * 70)
        print("Creating height comparison plot...")
        plot_height_vs_time(results, filtered_results, output_file=output_dir / "balise_height_vs_time.png")
        print("Creating snow level plot...")
        plot_snow_level(results_m, output_file=output_dir / "snow_level_vs_time.png", s=30, marker=".")
        if args.meteo:
            print("Creating snow level + precipitation plot...")
            plot_snow_level_with_meteo(
                results_m,
                args.meteo,
                output_file=output_dir / "snow_level_with_precipitation.png",
            )
        print()

    print("=" * 70)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
