"""Top-level package for *staketracker*.

The public API is organised into four focused sub-modules:

* :mod:`staketracker.detection` — image loading, edge detection, pixel
  detection, parameter optimisation, and visualisation.
* :mod:`staketracker.filters` — time-series filtering, smoothing, and
  unit conversion for detection results.
* :mod:`staketracker.io` — loading and saving detection result CSV files.
* :mod:`staketracker.meteo` — meteorological data retrieval via Open-Meteo.

The most commonly used symbols are re-exported here for convenience so that
``import staketracker; staketracker.detect_balise(...)`` works without
knowing which sub-module owns a function.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("staketracker")
except PackageNotFoundError:
    __version__ = "0+unknown"

from .detection import (
    load_gray,
    apply_weighted_sobel,
    crop_roi,
    detect_pixels,
    apply_opening,
    balise_vertical_size,
    read_image_date,
    detect_balise,
    pixel_iou,
    objective,
    optimize_params,
    visualize,
)
from .filters import (
    filter_rapid_changes,
    filter_min_max_height,
    apply_filters,
    add_moving_average,
    convert_px_to_metres,
)
from .io import load_data, save_results
from .meteo import fetch_weather_data

__all__ = [
    "__version__",
    # detection
    "load_gray",
    "apply_weighted_sobel",
    "crop_roi",
    "detect_pixels",
    "apply_opening",
    "balise_vertical_size",
    "read_image_date",
    "detect_balise",
    "pixel_iou",
    "objective",
    "optimize_params",
    "visualize",
    # filters
    "filter_rapid_changes",
    "filter_min_max_height",
    "apply_filters",
    "add_moving_average",
    "convert_px_to_metres",
    # io
    "load_data",
    "save_results",
    # meteo
    "fetch_weather_data",
]
