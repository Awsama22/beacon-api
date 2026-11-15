"""Download NASA POWER daily weather on a 1 deg grid over Sakha, 2012-01-01 .. 2026-11-10.

Writes weather.parquet: lat, lon, date, tmax (C), rh (%), wind_max (m/s), rain (mm),
soil (0-1 topsoil wetness).
"""

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
URL = (
    "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M_MAX,RH2M,WS2M_MAX,PRECTOTCORR,GWETTOP"
    "&community=AG&longitude={lon}&latitude={lat}&start=20120101&end=20261110&format=JSON"
)
NAMES = {
    "T2M_MAX": "tmax",
    "RH2M": "rh",
    "WS2M_MAX": "wind_max",
    "PRECTOTCORR": "rain",
    "GWETTOP": "soil",
}


def points():
    cells = pd.read_parquet(HERE / "cells.parquet")
    g = cells.assign(glat=(cells.lat // 1) + 0.5, glon=(cells.lon // 1) + 0.5)[
        ["glat", "glon"]
    ].drop_duplicates()
    return list(g.itertuples(index=False, name=None))


def fetch(p):
    lat, lon = p
    for attempt in range(6):
        try:
            d = json.load(urllib.request.urlopen(URL.format(lat=lat, lon=lon), timeout=120))
            par = d["properties"]["parameter"]
            df = pd.DataFrame({NAMES[k]: pd.Series(v) for k, v in par.items()})
            df.index = pd.to_datetime(df.index, format="%Y%m%d")
            df = df.replace(-999.0, float("nan")).rename_axis("date").reset_index()
            df["lat"], df["lon"] = lat, lon
            return df
        except Exception as e:  # noqa: BLE001 - retry any network error
            time.sleep(10 * (attempt + 1))
            last = e
    print("FAILED", p, last, flush=True)
    return None


def main():
    pts = points()
    print(len(pts), "weather points", flush=True)
    out = []
    with ThreadPoolExecutor(4) as ex:
        for i, df in enumerate(ex.map(fetch, pts), 1):
            if df is not None:
                out.append(df)
            if i % 50 == 0:
                print(f"{i}/{len(pts)}", flush=True)
    w = pd.concat(out, ignore_index=True)
    w.to_parquet(HERE / "weather.parquet")
    print("DONE", len(out), "points,", len(w), "rows", flush=True)


if __name__ == "__main__":
    main()
