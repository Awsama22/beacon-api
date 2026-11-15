"""Extra robustness tests for the Yakutia v2 model (fire clues + weather)."""

import json

import numpy as np
import pandas as pd
import train as v1
import train_v2 as v2
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score

COLS = v2.FEATS
rng = np.random.default_rng(1)
OUT = {}


def model():
    return HistGradientBoostingClassifier(
        max_iter=400, learning_rate=0.06, max_leaf_nodes=63, l2_regularization=1.0, random_state=0
    )


def train_rows(years, label_fn=None):
    parts = []
    for yr in years:
        d = v1.year_rows(yr)
        if label_fn is not None:
            d["y"] = label_fn(yr, d)
        keep = (d.y == 1) | (rng.random(len(d)) < 0.1)
        d = v2.weather_rows(yr, d[keep].copy())
        d["wt"] = np.where(d.y == 1, 1.0, 10.0)
        parts.append(d)
    return pd.concat(parts, ignore_index=True)


def test_rows(yr, label_fn=None):
    d = v1.year_rows(yr)
    if label_fn is not None:
        d["y"] = label_fn(yr, d)
    return v2.weather_rows(yr, d)


def score(d, col="p"):
    new = d[d.n9_7d == 0]
    return {
        "fire_rate": float(d.y.mean()),
        "auc": roc_auc_score(d.y, d[col]),
        "ap": average_precision_score(d.y, d[col]),
        "top5": v1.topk_recall(d, col, 0.05),
        "top10": v1.topk_recall(d, col, 0.10),
        "new_top10": v1.topk_recall(new, col, 0.10),
        "base_nearby_top10": v1.topk_recall(
            d.assign(b=d.n9_7d + 0.001 * d.hist_freq_n9), "b", 0.10
        ),
    }


def show(name, r):
    print(
        f"{name:34} fire rate {100 * r['fire_rate']:5.2f}% | AUC {r['auc']:.3f} AP {r['ap']:.3f}"
        f" | top5 {100 * r['top5']:4.1f}% top10 {100 * r['top10']:4.1f}%"
        f" | new fires top10 {100 * r['new_top10']:4.1f}%"
        f" | simple guess top10 {100 * r['base_nearby_top10']:4.1f}%",
        flush=True,
    )


def week2_label(yr, d):
    """fire in days t+8 .. t+14"""
    v = v1.daily(yr, "viirs")
    cs = np.cumsum(v, axis=0, dtype=np.float32)
    out = np.zeros_like(cs)
    out[:-14] = cs[14:] - cs[7:-7]
    lab = (out > 0).astype(np.uint8)
    return lab[d.t.values, d.r.values, d.c.values]


def main():
    # 1. Newest season: train 2013-2025, test 2026
    print("\n[1] 2026 season, trained on 2013-2025", flush=True)
    tr = train_rows(range(2013, 2026))
    m = model().fit(tr[COLS].values, tr.y.values, sample_weight=tr.wt.values)
    d26 = test_rows(2026)
    d26["p"] = m.predict_proba(d26[COLS].values)[:, 1]
    OUT["2026"] = score(d26)
    show("2026 (trained 2013-2025)", OUT["2026"])

    # base model on 2013-2020 for the 2021 tests
    tr20 = tr[tr.year <= 2020]
    base = model().fit(tr20[COLS].values, tr20.y.values, sample_weight=tr20.wt.values)
    d21 = test_rows(2021)
    d21["p"] = base.predict_proba(d21[COLS].values)[:, 1]
    show("2021 reference (days 1-7)", score(d21))

    # 2. Week 2 horizon
    print("\n[2] Week 2 ahead (days 8-14), 2021", flush=True)
    trw2 = train_rows(range(2013, 2021), week2_label)
    mw2 = model().fit(trw2[COLS].values, trw2.y.values, sample_weight=trw2.wt.values)
    dw2 = test_rows(2021, week2_label)
    dw2["p"] = mw2.predict_proba(dw2[COLS].values)[:, 1]
    OUT["week2_2021"] = score(dw2)
    show("2021, days 8-14", OUT["week2_2021"])

    # 3. Spatial holdout at 130E
    print("\n[3] Unseen areas, split at 130E (trained 2013-2020, tested 2021)", flush=True)
    for name, trm, tem in [
        ("train west, test east", tr20.lon < 130, d21.lon >= 130),
        ("train east, test west", tr20.lon >= 130, d21.lon < 130),
    ]:
        ms = model().fit(
            tr20[trm][COLS].values, tr20[trm].y.values, sample_weight=tr20[trm].wt.values
        )
        dt = d21[tem].copy()
        dt["p"] = ms.predict_proba(dt[COLS].values)[:, 1]
        dt["p_full"] = d21.loc[tem, "p"]
        OUT[name] = score(dt)
        OUT[name + " (model that saw both halves)"] = score(dt, "p_full")
        show(name, OUT[name])
        show("  same squares, model trained on all", OUT[name + " (model that saw both halves)"])

    # 4. Early warning: each square's first fire of the 2021 season
    #    (no fire in that square earlier in the season)
    print("\n[4] Early warning before each square's first fire of the 2021 season", flush=True)
    v = v1.daily(2021, "viirs")
    t0 = int(d21.t.min())
    first = {}
    season = v[t0 + 7 : int(d21.t.max()) + 1]
    tt, rr, cc = np.nonzero(season)
    for t, r, c in zip(tt + t0 + 7, rr, cc, strict=True):
        if (r, c) not in first and v1.valid[r, c] and v[t0:t, r, c].sum() == 0:
            first[(r, c)] = t
    d21["rank_pct"] = d21.groupby("t").p.rank(pct=True, ascending=False)
    idx = d21.set_index(["t", "r", "c"])
    ew = {}
    for lead in [1, 3, 7, 14]:
        keys = [(t - lead, r, c) for (r, c), t in first.items() if t - lead >= t0]
        ranks = idx.loc[keys, "rank_pct"].values
        ew[lead] = {
            "squares": len(keys),
            "top10": float((ranks <= 0.10).mean()),
            "top20": float((ranks <= 0.20).mean()),
        }
        print(
            f"  {lead:2} days before first fire: {100 * ew[lead]['top10']:4.1f}% were already in"
            f" the top 10%, {100 * ew[lead]['top20']:4.1f}% in the top 20%  ({len(keys)} squares)",
            flush=True,
        )
    OUT["early_warning_2021"] = ew

    # 5. Calibration
    print("\n[5] Calibration, 2021", flush=True)
    bins = [0, 0.01, 0.05, 0.1, 0.2, 0.4, 0.6, 1.0]
    d21["bin"] = pd.cut(d21.p, bins, include_lowest=True)
    cal = d21.groupby("bin", observed=True).agg(
        n=("y", "size"), predicted=("p", "mean"), observed=("y", "mean")
    )
    print(cal.to_string(float_format=lambda x: f"{x:.3f}"), flush=True)
    OUT["calibration_2021"] = {
        str(k): {kk: float(vv) for kk, vv in row.items()} for k, row in cal.iterrows()
    }

    # 6. Group importance: shuffle each group on a 2021 sample and measure the drop
    print("\n[6] What matters (2021, shuffle one group at a time)", flush=True)
    groups = {
        "fire in the square now": ["cell_1d", "cell_7d"],
        "fire in nearby squares": ["n3_1d", "n3_7d", "n9_7d", "n21_7d", "n21_season"],
        "last year and 25-year history": [
            "prev_year_cell",
            "prev_year_n3",
            "hist_freq_cell",
            "hist_freq_n9",
        ],
        "weather": [c for c in COLS if c.startswith("w_")],
        "season and location": ["doy", "lat", "lon"],
    }
    s = d21.sample(400_000, random_state=0).reset_index(drop=True)
    base_ap = average_precision_score(s.y, base.predict_proba(s[COLS].values)[:, 1])
    imp = {}
    for g, cols in groups.items():
        x = s[COLS].copy()
        perm = rng.permutation(len(x))
        x[cols] = x[cols].values[perm]
        ap = average_precision_score(s.y, base.predict_proba(x.values)[:, 1])
        imp[g] = {"ap": ap, "drop": base_ap - ap}
        print(f"  without {g:32} AP {ap:.3f} (drop {base_ap - ap:+.3f})", flush=True)
    OUT["importance_2021"] = {"base_ap": base_ap, **imp}
    json.dump(OUT, open(v1.HERE / "results_more.json", "w"), indent=1, default=float)
    print("\nDONE", flush=True)


if __name__ == "__main__":
    main()
