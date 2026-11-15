# natoor-api

The bridge between NASA's data and the Beacon apps. It fetches fire detections from NASA FIRMS and weather from Open-Meteo, stores them in PostgreSQL, and serves them to the Beacon website and mobile app through its own API.

Python, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 17 (Docker), uv. Folder layout: the Python variant in `ai automation/application structure/backend-folder-structure.md`.

## Setup guide

The API and the website are two repos that sit side by side; the website gets all its data from this API. Steps below are for Linux and macOS (on Windows, use WSL 2).

### 1. Install the tools

- Git
- Docker with Docker Compose (for PostgreSQL)
- uv, the Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh` (it installs Python 3.12 for you)
- Node.js 20.19 or newer, for the website

### 2. Clone both repos into one folder

```bash
mkdir natoor && cd natoor
git clone https://github.com/yasirkhan54/natoor-api.git
git clone https://github.com/yasirkhan54/natoor-website.git
cd natoor-api
git checkout develop
```

### 3. Create the database password

The password lives in a file outside the repo; Docker and the API both read it from there. This generates a random one:

```bash
mkdir -p ~/.config/natoor
openssl rand -base64 24 | tr -d '\n' > ~/.config/natoor/postgres-password
chmod 600 ~/.config/natoor/postgres-password
```

### 4. Start PostgreSQL and create the tables

```bash
docker compose up -d                 # PostgreSQL 17 on 127.0.0.1:5434, container natoor-postgres
cp .env.example .env
uv sync
uv run alembic upgrade head
```

### 5. Load the archive, history and model data

These were built from NASA archives (several GB of downloads), so instead of rebuilding them, take the built files from the website repo's first commit and import them (about a minute):

```bash
cd ../natoor-website
git checkout develop
mkdir -p data-build
git archive $(git rev-list --max-parents=0 HEAD) public/data | tar -x --strip-components=2 -C data-build
cd ../natoor-api
uv run python -m scripts.import_datasets ../natoor-website/data-build
```

It prints the rows stored, e.g. `archive_cells: 185182`, `static_sources: 408355`. To rebuild the data from NASA instead, see the website README (`npm run data`, `data:global`, `data:model`).

### 6. Run the API

```bash
uv run application.py
```

- API: http://localhost:8040, interactive docs: http://localhost:8040/api-docs, health: http://localhost:8040/health
- On the first start it downloads the last 7 days of NASA FIRMS fires in the background (a few minutes, about 700,000 rows); `/fires/live` fills in when that is done. After that it refreshes every hour while it runs.

Then start the website (see its README); it expects the API on port 8040 and runs on port 5173, the origin this API allows (`CORS_ALLOWED_ORIGINS`).

### Daily use

```bash
docker compose up -d && uv run application.py
```

### Troubleshooting

- **`password authentication failed`**: the password file changed after the database was first created. Either put the old password back, or delete the database volume and repeat steps 4 and 5: `docker compose down -v`.
- **Port 5434 or 8040 in use**: change `POSTGRES_PORT` (and the port in `docker-compose.yml`) or `PORT` in `.env`.
- **`/archive/...`, `/history` or `/model` answer 404**: step 5 was skipped.

### Working on the code

Branch from `develop` and open pull requests into `develop`; `master` is updated only through a reviewed pull request from `develop`. Run the checks below before pushing.

## Endpoints

| Method and path | Does |
|---|---|
| `GET /health` | Service and database status |
| `GET /sources` | Every FIRMS source, how it can be fetched, and its last successful fetch |
| `POST /ingestions/firms/near-real-time` | Fetch FIRMS global near-real-time fires (`period`: `24h`, `48h` or `7d`; `sources`: any of `MODIS_NRT`, `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT`). No key needed |
| `POST /ingestions/firms/area` | Fetch one source for a box and 1 to 10 days from the FIRMS Area API. Needs `FIRMS_MAP_KEY` |
| `POST /ingestions/firms/archive` | Fetch one FIRMS yearly country archive (`MODIS_SP` or `VIIRS_SNPP_SP`, `country` like `United_Arab_Emirates`, `year`). No key needed |
| `GET /ingestions`, `GET /ingestions/{id}` | Ingestion runs: status, rows read, rows stored, error |
| `GET /fires` | Stored detections in a box (`west`, `south`, `east`, `north`), newest first |
| `GET /fires/near` | Stored detections within `radius_km` of `latitude`/`longitude` in the last `hours`, nearest first, with `distance_km` |
| `GET /fires/live` | Last 7 days of near-real-time fires in the website's `live.json` shape (binned points, static sources, per-cell counts). Pre-built after each refresh, gzipped, `Cache-Control: max-age=300` with an ETag |
| `POST /ingestions/static-sources` | Replace the static heat source map (gas flares, industry, volcanoes) with `[[latitude, longitude], ...]`, like the website's `public/data/flares.json`, and re-mark stored detections |
| `GET /fires/monthly-counts` | Detections per month and sensor in a box (burning calendar), with each source's share |
| `GET /weather` | Open-Meteo 30 days past + 7 days forecast and dust for a point, cached in the database for `WEATHER_CACHE_MINUTES` |
| `GET /archive/meta` | Harmonized archive years, monthly coverage per sensor and source archives |
| `GET /archive/countries` | Yearly MODIS, VIIRS and harmonized hot spots per country, with calibration ratios |
| `GET /archive/validation` | How the MODIS-to-VIIRS harmonization holds up on held-out data |
| `GET /archive/tiles/{tile_row}/{tile_col}` | One 10° tile (rows 0 to 17 from 90°N, columns 0 to 35 from 180°W) of 0.25° archive cells with sparse monthly MODIS and VIIRS counts since 2000 |
| `GET /archive/grid` | 0.5° harmonized hot spots per year for the globe layer, as the binary `grid.bin` format |
| `GET /history` | GCC burn history per country and per 0.25° cell |
| `GET /model`, `GET /model/sample` | The fire-risk model (design, features, weights, scores) and a sample of its training table |

Fire queries share these filters: `sensor` (`MODIS` or `VIIRS`), `min_confidence` (`low`, `nominal` default, `high`), `include_static` (gas flares, volcanoes, offshore; default `false`), `start`, `end`, `limit` (default 5000, up to 50000).

All responses use `{"success", "data", "error"}`.

## How ingestion works

1. A `POST /ingestions/...` call creates one ingestion run per source and answers at once (202) with the run ids.
2. After the response, each source is fetched in its own thread: the CSV is streamed, each row is parsed (`utilities/firms_parser_util.py`) and stored in batches of 5000.
3. MODIS confidence 0 to 100 is mapped to low/nominal/high (below 30, 30 to 79, 80 and above) to match VIIRS. Archive rows carry the FIRMS `type`, so gas flares, volcanoes and offshore sources are marked `is_static_source`.
4. A detection is stored once per source (unique on source, latitude, longitude, time), so overlapping fetches don't duplicate rows.
5. Poll `GET /ingestions/{id}` until `status` is `succeeded` or `failed`.

## Live refresh

While the API runs, a background thread fetches the FIRMS near-real-time files every `LIVE_REFRESH_MINUTES` (default 60). It picks the 24h, 48h or 7d files to cover the gap since the last successful fetch, so after downtime the week fills back in by itself. After each fetch it marks new detections that sit on known static sources, rebuilds the `/fires/live` body and deletes near-real-time detections older than `NRT_RETENTION_DAYS` (default 30). This needs a long-running server; on a serverless host, call `services/refresh_service.refresh_once` from a scheduled job instead.

Near-real-time files have no FIRMS `type`, so gas flares are recognised with the static source map: a detection is static when a known source is in its 0.01° cell or one of the 8 around it (the same rule as the website). Load the map once:

```bash
curl -X POST http://localhost:8040/ingestions/static-sources -H 'Content-Type: application/json' \
  --data-binary @../natoor-website/public/data/flares.json
```

## Website datasets

The harmonized archive, GCC history and fire-risk model are built by the website's scripts (`npm run data`, `data:global`, `data:model` in natoor-website), which write `natoor-website/data-build/`. Load that folder into the database:

```bash
uv run python -m scripts.import_datasets ../natoor-website/data-build
```

It fills `datasets` (JSONB documents), `archive_cells`, `archive_grid_cells`, `history_cells` and `static_sources`; a missing file is skipped. Every import also writes a `last_import` record. The `/archive`, `/history` and `/model` responses are built once per import, gzipped and sent with an ETag.

## Settings (`.env`)

| Name | Default | Meaning |
|---|---|---|
| `PORT` | `8040` | API port |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | The Beacon website's address (comma-separated) |
| `POSTGRES_*` | see `.env.example` | Database connection; password from `POSTGRES_PASSWORD_FILE` |
| `ADMIN_API_KEY` | empty | When set, `/ingestions` needs it in the `X-Admin-Key` header |
| `FIRMS_MAP_KEY` | empty | Free key from https://firms.modaps.eosdis.nasa.gov/api/map_key/, only for the Area API |
| `WEATHER_CACHE_MINUTES` | `60` | How long a stored forecast is reused |
| `DOWNLOAD_TIMEOUT_SECONDS` | `300` | Timeout for one FIRMS download |
| `LIVE_REFRESH_MINUTES` | `60` | Background near-real-time fetch interval; `0` turns it off |
| `NRT_RETENTION_DAYS` | `30` | How long near-real-time detections are kept |

## Checks

```bash
uv run ruff format . && uv run ruff check .
uv run pytest -q
```

## Database changes

Change a model in `models/`, then:

```bash
uv run alembic revision --autogenerate -m "what changed"
uv run alembic upgrade head
```
