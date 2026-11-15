"""Yakutia 7-day fire model, v1 (fire patterns only, no weather yet).

Question per 0.25 deg Sakha cell and summer day t:
    will VIIRS see a fire in this cell in the next 7 days (t+1 .. t+7)?
Features use only what is known on day t. Train 2013-2020, test 2021 (and 2022-2025).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import uniform_filter
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

HERE = Path(__file__).parent
SEASON = (5, 1), (9, 30)  # 1 May .. 30 Sep
TRAIN = range(2013, 2021)
TESTS = [2021, 2022, 2023, 2024, 2025]

cells = pd.read_parquet(HERE / "cells.parquet")
fires = pd.read_parquet(HERE / "fires.parquet")
R0, C0 = cells.row.min(), cells.col.min()
NR, NC = cells.row.max() - R0 + 1, cells.col.max() - C0 + 1
mask = np.zeros((NR, NC), bool)
mask[cells.row - R0, cells.col - C0] = True
lat_grid = 90 - (np.arange(NR)[:, None] + R0 + 0.5) * 0.25 + 0 * np.arange(NC)[None, :]
lon_grid = -180 + (np.arange(NC)[None, :] + C0 + 0.5) * 0.25 + 0 * np.arange(NR)[:, None]

fires["r"] = fires.row - R0
fires["c"] = fires.col - C0
fires["y"] = fires.date.dt.year

# Industrial heat (mines, oil and gas): cells with VIIRS "fire" in Nov-Mar of 3+ years. Excluded.
winter = fires[(fires.viirs > 0) & (fires.date.dt.month.isin([11, 12, 1, 2, 3]))]
ind = winter.groupby(["r", "c"]).y.nunique()
industrial = np.zeros((NR, NC), bool)
for (r, c), n in ind.items():
    if n >= 3:
        industrial[r, c] = True
valid = mask & ~industrial
print(f"{mask.sum()} Sakha cells, {industrial.sum()} industrial cells excluded")


def daily(year, col):
    """Binary fire grid per day of `year` (+ 7 days of next year for labels)."""
    start = pd.Timestamp(year, 1, 1)
    n = (pd.Timestamp(year + 1, 1, 8) - start).days
    g = np.zeros((n, NR, NC), np.uint8)
    f = fires[
        (fires.date >= start) & (fires.date < start + pd.Timedelta(days=n)) & (fires[col] > 0)
    ]
    g[(f.date - start).dt.days.values, f.r.values, f.c.values] = 1
    return g


def box(a, k):
    """Sum over a k x k neighbourhood (k odd), per day."""
    return uniform_filter(a.astype(np.float32), size=(1, k, k), mode="constant") * k * k


def past(a, days):
    """Sum over the previous `days` days including today: out[t] = a[t-days+1 .. t]."""
    cs = np.cumsum(a, axis=0, dtype=np.float32)
    out = cs.copy()
    out[days:] -= cs[:-days]
    return out


def future_any(a, days):
    """1 if any fire in t+1 .. t+days."""
    cs = np.cumsum(a, axis=0, dtype=np.float32)
    out = np.zeros_like(cs)
    out[:-days] = cs[days:] - cs[:-days]
    return (out > 0).astype(np.uint8)


# Long-term history from MODIS (2001 onward): years with fire per cell, cumulative.
modis_years = fires[fires.modis > 0].groupby(["r", "c", "y"]).size().reset_index()[["r", "c", "y"]]
viirs_years = (
    fires[(fires.viirs > 0) & fires.date.dt.month.between(4, 10)]
    .groupby(["r", "c", "y"])
    .size()
    .reset_index()[["r", "c", "y"]]
)


def years_grid(df, years):
    g = np.zeros((NR, NC), np.float32)
    d = df[df.y.isin(list(years))]
    np.add.at(g, (d.r.values, d.c.values), 1)
    return g


FEATURES = [
    "cell_1d",
    "cell_7d",
    "n3_1d",
    "n3_7d",
    "n9_7d",
    "n21_7d",
    "n21_season",
    "prev_year_cell",
    "prev_year_n3",
    "hist_freq_cell",
    "hist_freq_n9",
    "doy",
    "lat",
    "lon",
]


def year_rows(year):
    v = daily(year, "viirs")
    y7 = future_any(v, 7)
    n3, n9, n21 = box(v, 3), box(v, 9), box(v, 21)
    feats = {
        "cell_1d": v.astype(np.float32),
        "cell_7d": past(v, 7),
        "n3_1d": n3,
        "n3_7d": past(n3, 7),
        "n9_7d": past(n9, 7),
        "n21_7d": past(n21, 7),
    }
    t0 = (pd.Timestamp(year, *SEASON[0]) - pd.Timestamp(year, 1, 1)).days
    t1 = (pd.Timestamp(year, *SEASON[1]) - pd.Timestamp(year, 1, 1)).days
    season_cum = np.cumsum(n21[t0:], axis=0)
    prev = years_grid(viirs_years, [year - 1])
    prev3 = uniform_filter(prev, 3, mode="constant") * 9
    hist = years_grid(modis_years, range(2001, year))
    hist9 = uniform_filter(hist, 9, mode="constant") * 81
    rr, cc = np.nonzero(valid)
    out = []
    for t in range(t0, t1 + 1):
        d = {k: a[t][rr, cc] for k, a in feats.items()}
        d["n21_season"] = season_cum[t - t0][rr, cc]
        d["prev_year_cell"] = prev[rr, cc]
        d["prev_year_n3"] = prev3[rr, cc]
        d["hist_freq_cell"] = hist[rr, cc]
        d["hist_freq_n9"] = hist9[rr, cc]
        d["doy"] = np.full(len(rr), t + 1, np.float32)
        d["lat"] = lat_grid[rr, cc].astype(np.float32)
        d["lon"] = lon_grid[rr, cc].astype(np.float32)
        d["y"] = y7[t][rr, cc]
        d["year"] = np.full(len(rr), year, np.int16)
        d["t"] = np.full(len(rr), t, np.int16)
        d["r"], d["c"] = rr.astype(np.int16), cc.astype(np.int16)
        out.append(pd.DataFrame(d))
    return pd.concat(out, ignore_index=True)


def topk_recall(df, score, frac):
    """Share of next-7-day fire cells that were inside the top `frac` of cells flagged that day."""
    hit = tot = 0
    for _, g in df.groupby("t"):
        k = max(1, int(len(g) * frac))
        top = g[score].values.argsort()[::-1][:k]
        hit += g.y.values[top].sum()
        tot += g.y.sum()
    return hit / tot if tot else float("nan")


def main():
    rng = np.random.default_rng(0)
    train = []
    for yr in TRAIN:
        d = year_rows(yr)
        keep = (d.y == 1) | (rng.random(len(d)) < 0.1)  # all fires, 10% of no-fire rows
        d = d[keep].copy()
        d["w"] = np.where(d.y == 1, 1.0, 10.0)
        train.append(d)
        print(yr, "train rows", len(d), "positives", int(d.y.sum()))
    train = pd.concat(train, ignore_index=True)
    X, y, w = train[FEATURES].values, train.y.values, train.w.values

    gbm = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.08, max_leaf_nodes=63, l2_regularization=1.0, random_state=0
    )
    gbm.fit(X, y, sample_weight=w)
    mu, sd = X.mean(0), X.std(0) + 1e-6
    lr = LogisticRegression(max_iter=500, C=1.0)
    lr.fit((X - mu) / sd, y, sample_weight=w)

    results = {}
    for yr in TESTS:
        d = year_rows(yr)
        Xt = d[FEATURES].values
        d["gbm"] = gbm.predict_proba(Xt)[:, 1]
        d["lr"] = lr.predict_proba((Xt - mu) / sd)[:, 1]
        d["persist"] = (
            d.n9_7d + 0.001 * d.hist_freq_n9
        )  # baseline: fires nearby this week, then fire history
        d["history"] = d.hist_freq_n9  # baseline: where it burned most since 2001
        new = d[d.n9_7d == 0]  # no fire within ~1 deg in the last 7 days: a new ignition
        res = {
            "rows": len(d),
            "fire_rate": float(d.y.mean()),
            "new_rows": len(new),
            "new_fire_rate": float(new.y.mean()),
        }
        for m in ["gbm", "lr", "persist", "history"]:
            res[m] = {
                "auc": roc_auc_score(d.y, d[m]),
                "ap": average_precision_score(d.y, d[m]),
                "top5": topk_recall(d, m, 0.05),
                "top10": topk_recall(d, m, 0.10),
                "new_auc": roc_auc_score(new.y, new[m]) if new.y.nunique() > 1 else None,
                "new_top10": topk_recall(new, m, 0.10),
            }
        results[yr] = res
        print(
            f"\n== {yr}: {len(d):,} cell-days,"
            f" {100 * d.y.mean():.2f}% have a fire in the next 7 days;"
            f" new-ignition rows {len(new):,} ({100 * new.y.mean():.2f}%)"
        )
        print(
            f"{'model':10}{'AUC':>7}{'AP':>7}{'top5%':>8}{'top10%':>8}"
            f"{'newAUC':>8}{'new top10%':>11}"
        )
        for m in ["gbm", "lr", "persist", "history"]:
            r = res[m]
            print(
                f"{m:10}{r['auc']:7.3f}{r['ap']:7.3f}"
                f"{100 * r['top5']:7.1f}%{100 * r['top10']:7.1f}%"
                f"{(r['new_auc'] or 0):8.3f}{100 * r['new_top10']:10.1f}%"
            )
        if yr == 2021:
            d[["year", "t", "r", "c", "y", "gbm", "n9_7d"]].to_parquet(HERE / "pred_2021.parquet")
    imp = dict(zip(FEATURES, np.round(lr.coef_[0], 3).tolist(), strict=True))
    json.dump(
        {"results": results, "lr_coef": imp, "industrial_cells": int(industrial.sum())},
        open(HERE / "results_v1.json", "w"),
        indent=1,
        default=float,
    )
    print("\nlogistic weights (standardised):", imp)


if __name__ == "__main__":
    main()
