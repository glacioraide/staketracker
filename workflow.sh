## Fetch weather data for the entire period and analyze results with meteorological data
# python scripts/fetch_meteo.py --lat 45.8698 --lon 6.9871 --start 2024-07-17 --end 2025-11-10 --output analysis/weather_data.csv

TODAY=$(date +"%Y-%m-%d")

## linceul 17/07/2024 - 10/11/2024
INPUT_DIR="../../EDYTEM/Traitement_Images/linceul_20240717-20241110"
DIR_NAME=$(basename "$INPUT_DIR")
OUTPUT_DIR="../../EDYTEM/Traitement_Images/RESULTS/${DIR_NAME}_${TODAY}"
ROI="1535 330 30 80"
THRESHOLD=140
PX_PER_METER=177.0

python scripts/detect_stakes.py --input-dir "$INPUT_DIR" --roi $ROI --output "$OUTPUT_DIR" --save-annotated --threshold $THRESHOLD
python scripts/analyze_results.py --input "$OUTPUT_DIR/detection_results.csv" --output "$OUTPUT_DIR/analysis" --px-per-metre $PX_PER_METER --meteo analysis/weather_data.csv


## linceul 10/11/2024 - 31/03/2025
INPUT_DIR="../../EDYTEM/Traitement_Images/linceul_20241111-20250331"
DIR_NAME=$(basename "$INPUT_DIR")
OUTPUT_DIR="../../EDYTEM/Traitement_Images/RESULTS/${DIR_NAME}_${TODAY}"
ROI="1510 330 40 100"
THRESHOLD=200
PX_PER_METER=177.0

python scripts/detect_stakes.py --input-dir "$INPUT_DIR" --roi $ROI --output "$OUTPUT_DIR" --save-annotated --threshold $THRESHOLD --overwrite
python scripts/analyze_results.py --input "$OUTPUT_DIR/detection_results.csv" --output "$OUTPUT_DIR/analysis" --px-per-metre $PX_PER_METER --meteo analysis/weather_data.csv


## linceul 01/04/2025 - 10/10/2025
INPUT_DIR="../../EDYTEM/Traitement_Images/linceul_20250401-20251010"
DIR_NAME=$(basename "$INPUT_DIR")
OUTPUT_DIR="../../EDYTEM/Traitement_Images/RESULTS/${DIR_NAME}_${TODAY}"
ROI="1820 310 50 140"
THRESHOLD=140
PX_PER_METER=177.0

python scripts/detect_stakes.py --input-dir "$INPUT_DIR" --roi $ROI --output "$OUTPUT_DIR" --save-annotated --threshold $THRESHOLD --overwrite
python scripts/analyze_results.py --input "$OUTPUT_DIR/detection_results.csv" --output "$OUTPUT_DIR/analysis" --px-per-metre $PX_PER_METER --meteo analysis/weather_data.csv