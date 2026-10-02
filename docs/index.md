# staketracker

Python package for detecting glacier stake pixels in images, building time-series
of stake height, and estimating snow level through filtering and calibration.

Alpha version under rapid changes. Installation, scripts and examples are in the
[README](https://github.com/glacioraide/staketracker#readme).

[Detection step by step](notebooks/pipeline_step_by_step.md) runs the detection on the test images one step
at a time and shows the intermediate images. It is the notebook `notebooks/pipeline_step_by_step.ipynb`,
executed when the site is built.

## API reference

The most used functions are re-exported at the top level, so `from staketracker import detect_stakes`
works without knowing which sub-module owns it.

| Module | Content |
| --- | --- |
| [`detection`](api/detection.md) | Image loading, Sobel edge detection, stake height, parameter optimisation |
| [`filters`](api/filters.md) | Time-series filtering, smoothing, pixel to metre conversion |
| [`io`](api/io.md) | Loading and saving detection result CSV files |
| [`meteo`](api/meteo.md) | Weather data from Open-Meteo |
| [`plot`](api/plot.md) | Detection overlays and time-series plots |
