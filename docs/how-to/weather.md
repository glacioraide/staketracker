# Fetch weather data

`fetch_meteo.py` downloads daily weather from the [Open-Meteo](https://open-meteo.com/) historical
archive for one location:

```bash
python scripts/fetch_meteo.py \
    --lat 45.8698 --lon 6.9871 \
    --start 2024-07-17 --end 2025-11-10 \
    --output weather.csv
```

You get one row per day with mean temperature, precipitation, rain, snowfall, solar radiation,
weather code and dominant wind direction.
Responses are cached in `.cache/`, so running it again is fast.

Pass the file to `analyze_results.py --meteo weather.csv` to plot precipitation with the snow level.
