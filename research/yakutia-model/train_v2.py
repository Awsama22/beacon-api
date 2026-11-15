"""Yakutia 7-day fire model, v2: v1 fire features + NASA POWER weather known on day t.

No future weather is used.
"""

import json

import numpy as np
import pandas as pd
import train as v1
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

w = pd.read_parquet(v1.HERE / "weather.parquet").sort_values(["lat", "lon", "date"])
pts = w[["lat", "lon"]].drop_duplicates().reset_index(drop=True)
pts["p"] = np.arange(len(pts))
w = w.merge(pts, on=["lat", "lon"])

# Rolling weather per point (computed on the full daily series, so day t uses days <= t only)
g = w.groupby("p", group_keys=False)
w["tmax_7d"] = g.tmax.transform(lambda s: s.rolling(7, 1).mean())
w["rh_min_7d"] = g.rh.transform(lambda s: s.rolling(7, 1).min())
w["rain_7d"] = g.rain.transform(lambda s: s.rolling(7, 1).sum())
w["rain_30d"] = g.rain.transform(lambda s: s.rolling(30, 1).sum())
w["wind_7d"] = g.wind_max.transform(lambda s: s.rolling(7, 1).max())
wet = (w.rain >= 2).astype(int)
w["dry_days"] = wet.groupby(w.p).transform(lambda s: s.groupby(s.cumsum()).cumcount())
w["soil_30d_change"] = w.soil - g.soil.transform(lambda s: s.shift(30))
WFEAT = [
    "tmax",
    "rh",
    "wind_max",
    "rain",
    "soil",
    "tmax_7d",
    "rh_min_7d",
    "rain_7d",
    "rain_30d",
    "wind_7d",
    "dry_days",
    "soil_30d_change",
]

# map each grid cell to its 1 deg weather point
cell_lat = v1.lat_grid
cell_lon = v1.lon_grid
key = pd.DataFrame({"lat": ((cell_lat // 1) + 0.5).ravel(), "lon": ((cell_lon // 1) + 0.5).ravel()})
pidx = (
    key.merge(pts, on=["lat", "lon"], how="left")
    .p.fillna(-1)
    .astype(int)
    .values.reshape(cell_lat.shape)
)


def weather_rows(year, d):
    yw = w[w.date.dt.year == year]
    arr = {k: np.full((367, len(pts)), np.nan, np.float32) for k in WFEAT}
    t = (yw.date.dt.dayofyear - 1).values
    for k in WFEAT:
        arr[k][t, yw.p.values] = yw[k].values
    p = pidx[d.r.values, d.c.values]
    for k in WFEAT:
        d["w_" + k] = np.where(p >= 0, arr[k][d.t.values, np.clip(p, 0, None)], np.nan)
    return d


FEATS = v1.FEATURES + ["w_" + k for k in WFEAT]


def main():
    rng = np.random.default_rng(0)
    train = []
    for yr in v1.TRAIN:
        d = v1.year_rows(yr)
        keep = (d.y == 1) | (rng.random(len(d)) < 0.1)
        d = weather_rows(yr, d[keep].copy())
        d["wt"] = np.where(d.y == 1, 1.0, 10.0)
        train.append(d)
    train = pd.concat(train, ignore_index=True)
    models = {
        "fire_only": (
            v1.FEATURES,
            HistGradientBoostingClassifier(
                max_iter=300,
                learning_rate=0.08,
                max_leaf_nodes=63,
                l2_regularization=1.0,
                random_state=0,
            ),
        ),
        "fire_weather": (
            FEATS,
            HistGradientBoostingClassifier(
                max_iter=400,
                learning_rate=0.06,
                max_leaf_nodes=63,
                l2_regularization=1.0,
                random_state=0,
            ),
        ),
        "weather_only": (
            ["w_" + k for k in WFEAT] + ["doy", "lat", "lon"],
            HistGradientBoostingClassifier(
                max_iter=300, learning_rate=0.08, max_leaf_nodes=63, random_state=0
            ),
        ),
    }
    for cols, m in models.values():
        m.fit(train[cols].values, train.y.values, sample_weight=train.wt.values)
    results = {}
    for yr in v1.TESTS:
        d = weather_rows(yr, v1.year_rows(yr))
        for name, (cols, m) in models.items():
            d[name] = m.predict_proba(d[cols].values)[:, 1]
        new = d[d.n9_7d == 0]
        res = {}
        print(
            f"\n== {yr}: {100 * d.y.mean():.2f}% fire rate;"
            f" new-ignition rows {100 * new.y.mean():.2f}%"
        )
        print(
            f"{'model':14}{'AUC':>7}{'AP':>7}{'top5%':>8}{'top10%':>8}"
            f"{'newAUC':>8}{'newAP':>8}{'new top10%':>11}"
        )
        for name in models:
            r = {
                "auc": roc_auc_score(d.y, d[name]),
                "ap": average_precision_score(d.y, d[name]),
                "top5": v1.topk_recall(d, name, 0.05),
                "top10": v1.topk_recall(d, name, 0.10),
                "new_auc": roc_auc_score(new.y, new[name]),
                "new_ap": average_precision_score(new.y, new[name]),
                "new_top10": v1.topk_recall(new, name, 0.10),
            }
            res[name] = r
            print(
                f"{name:14}{r['auc']:7.3f}{r['ap']:7.3f}"
                f"{100 * r['top5']:7.1f}%{100 * r['top10']:7.1f}%"
                f"{r['new_auc']:8.3f}{r['new_ap']:8.3f}{100 * r['new_top10']:10.1f}%"
            )
        results[yr] = res
        if yr == 2021:
            d[["t", "r", "c", "y", "fire_only", "fire_weather", "n9_7d"]].to_parquet(
                v1.HERE / "pred_2021_v2.parquet"
            )
    json.dump(results, open(v1.HERE / "results_v2.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
