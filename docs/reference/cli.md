# Command line

The scripts are in `scripts/`. Run them from the repository root. The options below
are generated from each script's `--help`.

## detect_stakes.py

Detects the stake in every photo of a folder and writes `detection_results.csv`.

```bash exec="on" result="text"
python scripts/detect_stakes.py --help
```

## analyze_results.py

Filters detection results, converts them to metres and computes the snow level.

```bash exec="on" result="text"
python scripts/analyze_results.py --help
```

## fetch_meteo.py

Downloads daily weather data from Open-Meteo.

```bash exec="on" result="text"
python scripts/fetch_meteo.py --help
```
