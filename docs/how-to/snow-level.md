# Compute the snow level

This turns the detection results of a season into a snow level time series, in metres.

## 1. Run the detection on each period

The ROI and threshold change when the camera moves, so run `detect_stakes.py` once per period:

```bash
python scripts/detect_stakes.py --input-dir photos/period1 --roi 1535 330 30 80 --threshold 140 --output results/period1
python scripts/detect_stakes.py --input-dir photos/period2 --roi 1510 330 40 100 --threshold 200 --output results/period2
```

## 2. Measure the pixels per metre

Find something of known length in the image, at the distance of the stake. The stake itself works
when you know how much of it sticks out on a given day. Then:

```text
px_per_metre = length in pixels / length in metres
```

For example, 1.5 m of stake measured at 265 pixels gives 177 px/m.

## 3. Analyse

Pass all the detection files together:

```bash
python scripts/analyze_results.py \
    --input results/period1/detection_results.csv results/period2/detection_results.csv \
    --px-per-metre 177 \
    --output results/analysis
```

The snow level is in `results/analysis/results_with_snow_level.csv`, column `snow_level_m`,
with plots next to it. See [Output files](../reference/output-files.md).

To add precipitation to the plots, [fetch weather data](weather.md) and pass it with
`--meteo weather.csv`.

!!! warning
    The filters compare each point with its neighbours, so they need many photos.
    With only a handful, they can remove every point and leave the output empty.
