# Yakutia fire model (research)

For every 0.25° grid square of the Sakha Republic (Yakutia) and every summer day, the model predicts the chance that VIIRS sees a fire in that square in the next 7 days. It is trained on 2013 to 2020 and tested on years it never saw (2021 to 2026).

This is an experiment, not part of the API yet. It reads the fire detections that natoor-api has stored in PostgreSQL.

## Results

Main measure: each day, rank all squares by predicted chance; what share of the squares that caught fire in the next 7 days were in the top 10%? Random ranking gets 10%.

| Test | Fires caught in top 10% | Simple guess* |
| --- | --- | --- |
| 2021 (record year), fire clues only | 74% | 57% |
| 2021, fire clues + weather | **76%** | 57% |
| 2022 / 2023 / 2024 / 2025, with weather | 71% / 76% / 77% / 62% | 50 to 59% |
| 2026, trained on 2013 to 2025 | **80%** | 71% |
| 2021, second week ahead (days 8 to 14) | 61% | 50% |
| 2021, half of Sakha hidden from training (east or west) | 72% / 73% | 52% |
| 2021, new fires only (no fire within ~100 km the week before) | 43% | 39%** |

\* "Fires nearby this week, then fire history". \*\* "Where it burned most since 2001".

- **Early warning (2021):** one week before a square's first fire of the season, 60% of those squares were already in the model's top 20%; 49% two weeks before.
- **Calibration (2021):** predicted chances match observed rates up to about 20%; above that the model runs a little high (says 50%, happens 42%).
- **What matters most:** fire in the square now and fire in nearby squares; history, weather, season and location each add less.

Full numbers: `results_v1.json`, `results_v2.json`, `results_more.json`.

**What it is good for:** where fire will spread or flare up this week. **What it is weak at:** where a brand-new fire will start (most Yakutia fires are lit by lightning, which is not an input).

## How it works

1. `extract.py`: daily VIIRS and MODIS fire counts per square inside Sakha (`sakha.geojson`), nominal and high confidence, static sources removed. 36 squares with "fire" in winter in 3 or more years (mines, oil and gas) are dropped later.
2. `weather.py`: NASA POWER daily weather (max temperature, humidity, max wind, rain, topsoil wetness) on a 1° grid, 697 points, 2012 to 2026.
3. `train.py` (version 1): label = any VIIRS fire in the next 7 days. Clues: fire in the square and its neighbourhoods (about 80, 250 and 600 km) today and this week, season-to-date activity, fire last year, years with fire since 2001 (MODIS), day of year, latitude, longitude. Gradient boosting (scikit-learn), all fire rows plus 10% of no-fire rows reweighted. Compared with logistic regression and two simple guesses.
4. `train_v2.py` (version 2): adds weather known on day t (no forecasts): today's values, 7-day heat and lowest humidity, 7 and 30-day rain, days since real rain, change in soil wetness.
5. `test_more.py`: the extra tests in the table (2026, week 2, spatial holdout, early warning, calibration, feature groups).

## Run it

Needs the natoor-api database with the Yakutia detections loaded (FIRMS archives and the Area API for the Sakha box, 2000 onward). Database settings come from the same `POSTGRES_*` variables as the API.

```bash
cd research/yakutia-model
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python extract.py      # about 2 minutes
.venv/bin/python weather.py      # about 45 minutes (NASA POWER, no key)
.venv/bin/python train.py        # version 1, about 1 minute
.venv/bin/python train_v2.py     # version 2, a few minutes
.venv/bin/python test_more.py    # extra tests, about 10 minutes
```

Data files (`*.parquet`) are rebuilt by the scripts and are not committed.

## Sources

- Fire detections: [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) (MODIS since November 2000; VIIRS S-NPP 2012 to November 2026, NOAA-20 since 2018, NOAA-21 since 2024)
- Weather: [NASA POWER](https://power.larc.nasa.gov/)
- Sakha border: [geoBoundaries](https://www.geoboundaries.org/) RUS ADM1, gbOpen, CC BY 4.0
