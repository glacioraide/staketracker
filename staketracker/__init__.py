"""Top-level package for *staketracker*.

The public API is organised into five focused sub-modules:

* :mod:`staketracker.detection` — image loading, edge detection, pixel
  detection, and parameter optimisation.
* :mod:`staketracker.filters` — time-series filtering, smoothing, and
  unit conversion for detection results.
* :mod:`staketracker.io` — loading and saving detection result CSV files.
* :mod:`staketracker.meteo` — meteorological data retrieval via Open-Meteo.
* :mod:`staketracker.plot` — detection overlays and time-series plots.

The most commonly used symbols are re-exported here for convenience so that
``import staketracker; staketracker.detect_stakes(...)`` works without
knowing which sub-module owns a function.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("staketracker")
except PackageNotFoundError:
    __version__ = "0+unknown"

from .detection import (
    load_gray,
    enhance_contrast,
    weighted_gradient,
    normalize_gradient,
    apply_weighted_sobel,
    crop_roi,
    threshold_roi,
    close_gaps,
    keep_largest_component,
    clean_detection,
    mask_to_coords,
    detect_pixels,
    stakes_vertical_size,
    read_image_date,
    detect_stakes,
    pixel_iou,
    objective,
    optimize_params,
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
from .plot import visualize

__all__ = [
    "__version__",
    # detection
    "load_gray",
    "enhance_contrast",
    "weighted_gradient",
    "normalize_gradient",
    "apply_weighted_sobel",
    "crop_roi",
    "threshold_roi",
    "close_gaps",
    "keep_largest_component",
    "clean_detection",
    "mask_to_coords",
    "detect_pixels",
    "stakes_vertical_size",
    "read_image_date",
    "detect_stakes",
    "pixel_iou",
    "objective",
    "optimize_params",
    "filter_rapid_changes",
    "filter_min_max_height",
    "apply_filters",
    "add_moving_average",
    "convert_px_to_metres",
    "load_data",
    "save_results",
    # meteo
    "fetch_weather_data",
    # plot
    "visualize",
]
