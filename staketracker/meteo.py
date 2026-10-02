"""Meteorological data retrieval via the Open-Meteo historical weather API.

This module wraps the Open-Meteo API client so that weather data for a given
location and date range can be fetched with a single function call and
optionally saved to a CSV file.

References
----------
Zippenfenig, P. (2023). Open-Meteo.com Weather API [Computer software].
    Zenodo. https://doi.org/10.5281/ZENODO.7970649

Hersbach et al. (2023). ERA5 hourly data on single levels from 1940 to present.
    ECMWF. https://doi.org/10.24381/cds.adbb2d47

Muñoz Sabater, J. (2019). ERA5-Land hourly data from 2001 to present.
    ECMWF. https://doi.org/10.24381/CDS.E2161BAC
"""

from pathlib import Path

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

# Open-Meteo API endpoint for historical reanalysis data
_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Daily variables requested from the API (order matters for index-based access)
_DAILY_VARIABLES = [
    "weather_code",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
    "temperature_2m_mean",
    "shortwave_radiation_sum",
    "wind_direction_10m_dominant",
]


def _build_client(cache_dir: str = ".cache") -> openmeteo_requests.Client:
    """Create an Open-Meteo client with on-disk caching and automatic retries.

    Parameters
    ----------
    cache_dir : str, default ".cache"
        Directory used by ``requests_cache`` for persistent response caching.

    Returns
    -------
    openmeteo_requests.Client
    """
    cache_session = requests_cache.CachedSession(cache_dir, expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    return openmeteo_requests.Client(session=retry_session)


def fetch_weather_data(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    output_path: str | Path | None = None,
    cache_dir: str = ".cache",
) -> pd.DataFrame:
    """Fetch daily meteorological data from the Open-Meteo archive.

    Parameters
    ----------
    latitude : float
        Station latitude in decimal degrees (positive = North).
    longitude : float
        Station longitude in decimal degrees (positive = East).
    start_date : str
        First day of the requested period in ISO 8601 format (``YYYY-MM-DD``).
    end_date : str
        Last day of the requested period in ISO 8601 format (``YYYY-MM-DD``).
    output_path : str or pathlib.Path or None, default None
        If provided, the resulting DataFrame is saved to this CSV file.
    cache_dir : str, default ".cache"
        Directory used for on-disk HTTP caching.

    Returns
    -------
    pandas.DataFrame
        Daily weather data with columns: ``date``, ``weather_code``,
        ``precipitation_sum``, ``rain_sum``, ``snowfall_sum``,
        ``precipitation_hours``, ``temperature_2m_mean``.
    """
    client = _build_client(cache_dir=cache_dir)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": _DAILY_VARIABLES,
    }

    responses = client.weather_api(_ARCHIVE_URL, params=params)
    response = responses[0]

    print(f"Coordinates: {response.Latitude():.4f}°N  {response.Longitude():.4f}°E")
    print(f"Elevation:   {response.Elevation():.0f} m asl")
    print(f"UTC offset:  {response.UtcOffsetSeconds()} s")

    daily = response.Daily()
    daily_data = {
        "date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left",
        )
    }
    for i, var in enumerate(_DAILY_VARIABLES):
        daily_data[var] = daily.Variables(i).ValuesAsNumpy()

    df = pd.DataFrame(data=daily_data)

    if output_path is not None:
        output_path = Path(output_path)
        df.to_csv(output_path, index=False)
        print(f"✓ Saved weather data to {output_path}")

    return df
