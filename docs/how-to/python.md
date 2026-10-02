# Use the Python API

The scripts call functions you can use directly, in a notebook for example.

## Detect the stake in one photo

```python
from staketracker import detect_stakes, stakes_vertical_size

params = {"wx": 0.9, "threshold": 140, "ksize": 1, "clahe_clip": 1.0, "clahe_tile": 2}
roi = (1820, 310, 50, 140)  # x, y, width, height

detected = detect_stakes("tests/data/linceul_20250401-20251010/RCNX2325.JPG", roi, params)
print(stakes_vertical_size(detected))  # {'y_min': 333, 'y_max': 409, 'height_px': 77}
```

## Turn detection results into a snow level

```python
from staketracker import add_moving_average, apply_filters, convert_px_to_metres, load_data

results = load_data(["results/period1/detection_results.csv", "results/period2/detection_results.csv"])
results = apply_filters(results)
results = add_moving_average(results, rolling_window="24h")
results = convert_px_to_metres(results, px_per_metre=177)

height = results["balise_height_m_moving_average"]
results["snow_level_m"] = height.max() - height
```

## Fetch weather data

```python
from staketracker import fetch_weather_data

weather = fetch_weather_data(
    latitude=45.8698, longitude=6.9871,
    start_date="2024-07-17", end_date="2025-11-10",
)
```

All functions are listed in the [API reference](../api/index.md).
