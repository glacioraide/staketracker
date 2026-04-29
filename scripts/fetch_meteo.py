#!/usr/bin/env python3
"""Fetch historical daily weather data from the Open-Meteo archive API.

This script is a thin command-line wrapper around
:func:`staketracker.meteo.fetch_weather_data` and is intended to be run
directly::

    python scripts/fetch_meteo.py \\
        --lat 45.8698 --lon 6.9871 \\
        --start 2024-07-17 --end 2025-11-10 \\
        --output analysis/weather.csv

Data are cached on disk (default: ``.cache/``) so repeated calls for the same
date range do not incur extra network requests.
"""

import argparse

from staketracker.meteo import fetch_weather_data


def main() -> None:
    """Entry point for the meteorological data fetch script."""
    parser = argparse.ArgumentParser(
        description="Fetch daily weather data from the Open-Meteo historical archive",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--lat",
        type=float,
        required=True,
        help="Station latitude in decimal degrees (positive = North)",
    )
    parser.add_argument(
        "--lon",
        type=float,
        required=True,
        help="Station longitude in decimal degrees (positive = East)",
    )
    parser.add_argument(
        "--start",
        required=True,
        metavar="YYYY-MM-DD",
        help="First day of the requested period",
    )
    parser.add_argument(
        "--end",
        required=True,
        metavar="YYYY-MM-DD",
        help="Last day of the requested period",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="Destination CSV file (default: weather_data_lat<lat>_lon<lon>_<start>_to_<end>.csv)",
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache",
        metavar="DIR",
        help="Directory used for on-disk HTTP caching",
    )
    args = parser.parse_args()

    output_path = args.output
    if output_path is None:
        output_path = f"weather_data_lat{args.lat}_lon{args.lon}_{args.start}_to_{args.end}.csv"

    df = fetch_weather_data(
        latitude=args.lat,
        longitude=args.lon,
        start_date=args.start,
        end_date=args.end,
        output_path=output_path,
        cache_dir=args.cache_dir,
    )

    print(f"\nDaily data ({len(df)} rows):\n{df.head()}")


if __name__ == "__main__":
    main()
