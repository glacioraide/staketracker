# staketracker

Python package for detecting glacier stake pixels in images, building time-series
of stake height, and estimating snow level through filtering and calibration.

Alpha version under rapid changes.

## Installation

Requires Python 3.12 or later. Pick one of the two options below.

Optional extras:
- `dev`: ruff and pytest
- `jupyter`: JupyterLab and ipywidgets, needed for the notebooks

### Option A: uv (recommended)

Install uv first: https://docs.astral.sh/uv/#installation

```bash
uv sync --all-extras
source .venv/bin/activate
```

This creates `.venv`, installs the exact versions pinned in `uv.lock`, and installs staketracker in editable mode with all extras.

### Option B: venv and pip

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,jupyter]"
```

`-e` installs in editable mode, so changes to the code apply without reinstalling. If you only want to use the package, drop `-e` and the extras: `pip install .`

pip ignores `uv.lock`, so you may get newer dependency versions than the ones tested.


## Script usage

Scripts are under `scripts/`.

### 1. Detect stakes in images (pixel heights CSV)

```bash
python scripts/detect_stakes.py \
	--input-dir analysis/photo_fixe_linceul \
	--roi 1835 330 20 80 \
	--output analysis/detection_run
```

Optional quality-control overlays:

```bash
python scripts/detect_stakes.py \
	--input-dir analysis/photo_fixe_linceul \
	--roi 1835 330 20 80 \
	--output analysis/detection_run \
	--save-annotated
```

Main output is `detection_results.csv` (with a provenance comment header), written to the `--output` directory. Both `detect_stakes.py` and `analyze_results.py` refuse to write into an existing directory unless you pass `--overwrite`.


> Note: To find the ROI, select an image where the stake is the longest and open it with an image viewer (Paint, Preview, https://pixspy.com/, ...) that displays pixel coordinates. Pixel coordinates are defined from the top-left corner (0,0).


### 2. Fetch meteorological data from Open-Meteo

```bash
python scripts/fetch_meteo.py \
	--lat 45.8698 \
	--lon 6.9871 \
	--start 2024-07-17 \
	--end 2025-11-10 \
	--output analysis/weather_data.csv
```

If `--output` is omitted, the script auto-generates:

`weather_data_lat<lat>_lon<lon>_<start>_to_<end>.csv`

### 3. Analyze detection CSVs into snow-level outputs

```bash
python scripts/analyze_results.py \
	--input analysis/detection_run/detection_results.csv \
	--output analysis/run_01 \
	--px-per-metre 177
```

Optional meteorological overlay plot:

```bash
python scripts/analyze_results.py \
	--input analysis/detection_run/detection_results.csv \
	--output analysis/run_with_meteo \
	--px-per-metre 177 \
	--meteo analysis/weather_data.csv
```

Disable plots (CSV outputs only):

```bash
python scripts/analyze_results.py --input analysis/detection_run/detection_results.csv --no-plots
```


## Python API usage

### Check package version

```python
import staketracker
print(staketracker.__version__)
```

### Detection on one image

```python
from staketracker import detect_stakes, stakes_vertical_size

best = {
		"wx": 0.9,
		"threshold": 60,
		"ksize": 1,
		"clahe_clip": 1.0,
		"clahe_tile": 8,
}
roi = (1835, 330, 20, 80)  # x, y, width, height

detected = detect_stakes("photo_fixe_linceul/RCNX0094.JPG", roi, best)
size = stakes_vertical_size(detected)
print(size)
```

### Process detection CSVs into snow-level estimates

```python
from staketracker import load_data, apply_filters, add_moving_average, convert_px_to_metres

results = load_data([
		"analysis/2024_linceul_results/detection_results.csv",
		"analysis/2024-2025_linceul_results_part1/detection_results.csv",
])

filtered = apply_filters(results)
filtered = add_moving_average(filtered, rolling_window="24h")
results_m = convert_px_to_metres(filtered, px_per_metre=177.0)

max_height = results_m["balise_height_m_moving_average"].max()
results_m["snow_level_m"] = max_height - results_m["balise_height_m_moving_average"]
```

### Fetch meteo data from Python

```python
from staketracker import fetch_weather_data

df = fetch_weather_data(
		latitude=45.8698,
		longitude=6.9871,
		start_date="2024-07-17",
		end_date="2025-11-10",
		output_path="analysis/weather_data.csv",
)
print(df.head())
```

## Running tests

```bash
pytest -v
```

## Notes

- Stake detection depends on ROI placement and calibration parameters.
- The `px_per_metre` value should be measured for your camera configuration.
- Meteorological data retrieval uses Open-Meteo historical APIs with local HTTP caching.


