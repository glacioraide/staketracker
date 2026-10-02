# Output files

CSV files start with `#` comment lines that record how they were made (staketracker version,
date, inputs, parameters). [`load_data`][staketracker.io.load_data] skips them.

Both scripts refuse to write into an existing directory unless you pass `--overwrite`.

## detect_stakes.py

| File | Content |
| --- | --- |
| `detection_results.csv` | One row per photo |
| `annotated/<photo>_detected.png` | Photo with the detected pixels, with `--save-annotated` |

Columns of `detection_results.csv`:

| Column | Meaning |
| --- | --- |
| `image` | Photo file name |
| `detected_pixels` | Number of pixels kept as stake |
| `balise_height_px` | Visible stake height, in pixels. 0 if nothing was detected |
| `y_min`, `y_max` | Top and bottom rows of the stake in the image. Empty if nothing was detected |
| `creation_date` | Capture time, from the EXIF `DateTimeOriginal` tag |

## analyze_results.py

| File | Content |
| --- | --- |
| `filtered_results.csv` | Detection rows kept by the filters, with the moving average |
| `results_with_snow_level.csv` | The same rows, converted to metres, with the snow level |
| `balise_height_vs_time.png` | Raw and filtered heights |
| `snow_level_vs_time.png` | Snow level |
| `snow_level_with_precipitation.png` | Snow level and precipitation, with `--meteo` |

Columns added to the detection columns:

| Column | Meaning |
| --- | --- |
| `balise_height_px_moving_average` | Height averaged over 24 h, in pixels |
| `balise_height_m` | `balise_height_px` in metres |
| `balise_height_m_moving_average` | Moving average in metres |
| `snow_level_m` | Snow level in metres, relative to the lowest snow surface of the series |
