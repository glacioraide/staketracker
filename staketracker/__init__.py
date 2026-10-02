"""Top-level package for *staketracker*.

The public API is organised into five focused sub-modules:

* [`staketracker.detection`][] — image loading, edge detection, pixel
  detection, and parameter optimisation.
* [`staketracker.filters`][] — time-series filtering, smoothing, and
  unit conversion for detection results.
* [`staketracker.io`][] — loading and saving detection result CSV files.
* [`staketracker.meteo`][] — meteorological data retrieval via Open-Meteo.
* [`staketracker.plot`][] — detection overlays and time-series plots.

The functions of a normal workflow (detect, filter, convert, plot) are
re-exported here, so ``from staketracker import detect_stakes`` works.
The individual detection steps, the filters and the parameter optimisation
stay in their sub-module, e.g. ``from staketracker.detection import close_gaps``.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("staketracker")
except PackageNotFoundError:
    __version__ = "0+unknown"

from .detection import detect_stakes, read_image_date, stakes_vertical_size
from .filters import add_moving_average, apply_filters, convert_px_to_metres
from .io import load_data, save_results
from .meteo import fetch_weather_data
from .plot import visualize

__all__ = [
    "__version__",
    # detection
    "detect_stakes",
    "read_image_date",
    "stakes_vertical_size",
    # filters
    "apply_filters",
    "add_moving_average",
    "convert_px_to_metres",
    # io
    "load_data",
    "save_results",
    # meteo
    "fetch_weather_data",
    # plot
    "visualize",
]
