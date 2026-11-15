"""Extract daily fire counts per 0.25 deg cell for Sakha (Yakutia) from the natoor DB.

Writes:
  cells.parquet   row, col, lat, lon of every 0.25 deg cell whose centre is inside Sakha
  fires.parquet   row, col, date, viirs (count), modis (count)  [nominal/high, not static]
"""

import json
import math
import os
from pathlib import Path

import pandas as pd
import psycopg

HERE = Path(__file__).parent
# Sakha Republic border from geoBoundaries RUS ADM1 (gbOpen, CC BY 4.0)
GEO = HERE / "sakha.geojson"
RES = 0.25


def sakha_rings():
    g = json.load(open(GEO))
    f = g["features"][0]
    geom = f["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    return [p[0] for p in polys]


def inside(x, y, ring):
    ins, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ins = not ins
        j = i
    return ins


def sakha_cells():
    rings = sakha_rings()
    boxes = [
        (min(p[0] for p in r), max(p[0] for p in r), min(p[1] for p in r), max(p[1] for p in r), r)
        for r in rings
    ]
    out = []
    for row in range(int((90 - 77.5) / RES), int((90 - 55) / RES)):
        lat = 90 - (row + 0.5) * RES
        for col in range(int((180 + 105) / RES), int((180 + 163.5) / RES)):
            lon = -180 + (col + 0.5) * RES
            if any(
                a <= lon <= b and c <= lat <= d and inside(lon, lat, r) for a, b, c, d, r in boxes
            ):
                out.append((row, col, lat, lon))
    return pd.DataFrame(out, columns=["row", "col", "lat", "lon"])


SQL = """
select floor((90 - latitude) / 0.25)::int as row,
       floor((longitude + 180) / 0.25)::int as col,
       acquired_at::date as date,
       sum((sensor = 'VIIRS' and source in ('VIIRS_SNPP_SP', 'VIIRS_SNPP_NRT', 'VIIRS_NOAA20_SP',
                                            'VIIRS_NOAA20_NRT', 'VIIRS_NOAA21_NRT'))::int) as viirs,
       sum((sensor = 'MODIS')::int) as modis
from fire_detections
where latitude between 55.0 and 77.5 and longitude between 105.0 and 163.5
  and confidence_level <> 'low'
  and not coalesce(is_static_source, false)
group by 1, 2, 3
"""


def cell_km2(lat):
    return (RES * 111.32) ** 2 * math.cos(math.radians(lat))


def main():
    cells = sakha_cells()
    cells.to_parquet(HERE / "cells.parquet")
    print(
        len(cells),
        "Sakha cells,",
        f"{cells.lat.apply(cell_km2).sum():,.0f} km2",
    )
    # Same settings and defaults as natoor-api (.env.example)
    env = os.environ.get
    pw = (
        Path(env("POSTGRES_PASSWORD_FILE", "~/.config/natoor/postgres-password"))
        .expanduser()
        .read_text()
        .strip()
    )
    with psycopg.connect(
        host=env("POSTGRES_HOST", "localhost"),
        port=int(env("POSTGRES_PORT", "5434")),
        user=env("POSTGRES_USER", "natoor"),
        dbname=env("POSTGRES_DB", "natoor"),
        password=pw,
    ) as conn:
        conn.execute("set statement_timeout = 0")
        fires = pd.read_sql(SQL, conn)
    fires = fires.merge(cells[["row", "col"]], on=["row", "col"])
    fires["date"] = pd.to_datetime(fires["date"])
    fires.to_parquet(HERE / "fires.parquet")
    print(
        len(fires),
        "cell-days with fire;",
        fires.viirs.sum(),
        "VIIRS,",
        fires.modis.sum(),
        "MODIS detections inside Sakha",
    )
    print(fires.groupby(fires.date.dt.year)[["viirs", "modis"]].sum().to_string())


if __name__ == "__main__":
    main()
