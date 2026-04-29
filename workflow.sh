## linceul 2024
python scripts/detect_stakes.py --input-dir analysis/photo_fixe_linceul --roi 1535 330 30 80 --output analysis/linceul_2024 --save-annotated --threshold 140
# python scripts/fetch_meteo.py --lat 45.8698 --lon 6.9871 --start 2024-07-17 --end 2025-11-10 --output analysis/weather_data.csv
python scripts/analyze_results.py --input analysis/linceul_2024_2026-04-29/detection_results.csv --output analysis/linceul_2024_2026-04-29 --meteo analysis/weather_data.csv


## TBC