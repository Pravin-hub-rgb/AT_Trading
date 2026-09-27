"""PARADIGM 1 — FLOW/POSITIONING EDGE (descriptive screen, engine untouched).

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

Origin: user round — "soch bahar ke model se". Every prior study varied the
v18 trade list using OHLCV only. This one tests a NEW INFORMATION AXIS:
Binance UM-futures positioning (OI, toptrader L/S, taker buy/sell vol) that
has never been used in this repo.

DATA (fetched by scripts/fetch_binance_flow.py, verified this session):
  - data/flow/BTCUSDT_metrics_5m.csv : 602,471 rows, 2021-01-01 -> 2026-09-25,
    5m snapshots, deduped (Binance ships 40,152 duplicate rows), 0 day-gaps.
  - price: data/btc-fut/BTCUSDT_15m.csv (Binance perp, SAME venue as metrics,
    volume present), 2020-12-31 -> 2026-09-14.
  - ALIGNMENT (measured, not assumed): OI-implied price match gives
    metrics(create_time UTC) + 315 min = price-CSV row label L whose
    close (instant L+15) equals the snapshot instant. Same-instant
    mark-vs-last residual: median ~0.011%, tail to 0.5% (a wrong
    one-bar offset measures >=0.15% median). Price CSV rows are bar
    OPEN in local wall-clock (UTC+5:30); metrics_local = utc + 330min.

CAUSAL ALIGNMENT BUGFIX (2026-09-27, before any commit of this file):
  The FIRST run paired each row with metrics at (open+15) — that is the
  NEXT row's label, i.e. the snapshot at the NEXT row's close, one 15m
  bar AFTER this row's close (one-bar lookahead in every feature). The
  path-true alignment control (implied-price median err limit 0.05%)
  caught it at 0.1597%. Pairing fixed to metrics at the row's own label;
  correct pairing measures ~0.011-0.013% median (mark-vs-last basis).
  Rules/features/kill thresholds UNCHANGED; the run produced by the
  fixed harness supersedes the first, which is discarded.

WHAT IS TESTED (fixed feature set, no additions after this docstring):
  f1 oi_chg_1h   OI % change over last 1h  (4 x 15m bars)
  f2 oi_chg_4h   OI % change over last 4h  (16 bars)
  f3 oi_z_24h    OI z-score vs trailing 24h mean/std (96 bars)
  f4 taker_ls_1h mean taker long/short vol ratio, last 1h (raw, era-ranked)
  f5 top_ls_1h   mean toptrader long/short ratio (sum), last 1h
  f6 div_4h      oi_chg_4h(%) - price_ret_4h(%)  (OI-vs-price divergence)

HORIZONS (forward log-free simple returns from bar close):
  h16  = 4h   and  h96 = 24h

ERAS (house results windows, identical to stat-arb):
  OOS = [2021-07-01 05:30, 2023-01-01 05:30)
  IS  = [2023-07-01 05:30, 2026-09-14 05:30)

METHOD: per feature x horizon, tercile sort WITHIN era (era-local ranking,
descriptive — uses full-era distribution, NOT causal; that is fine for a
screen and is stated here so nobody mistakes it for a tradable rule).
Cells = 2 eras x 2 horizons = 4 per feature.

SURVIVOR RULE (pre-registered, all must hold):
  S1  top-vs-bottom tercile spread SAME SIGN in all 4 cells
  S2  terciles monotone (Q3>Q2>Q1 or Q1>Q2>Q3 by mean fwd ret) in >= 3 of 4
  S3  every tercile n >= 100 (auto — sample is huge; reported anyway)

VERDICTS:
  - Feature FAILS if S1 or S2 fails -> recorded dead for this axis too.
  - Feature SURVIVES -> it is a CANDIDATE for a follow-up path-true strategy
    harness (separate experiment, entry/SL/costs). Survival here is NOT a
    pass, NOT adoption (RESEARCH_POLICY: never auto-adopt).
  - ALL 6 reported regardless (no best-of). No feature may be added.

SCOPE: descriptive, post-process. Engine untouched. Costs NOT modelled
(future strategy harness will). Run n=1, no tuning loops.

OUTPUT: live_stuff/tests/_flow_descriptive_results.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "live_stuff" / "tests" / "_flow_descriptive_results.json"

FEATURES = ["oi_chg_1h", "oi_chg_4h", "oi_z_24h", "taker_ls_1h", "top_ls_1h", "div_4h"]
HORIZONS = {"h16": 16, "h96": 96}
ERAS = {
    "oos": ("2021-07-01 05:30", "2023-01-01 05:30"),
    "is": ("2023-07-01 05:30", "2026-09-14 05:30"),
}
MIN_N = 100


def load() -> pd.DataFrame:
    px = pd.read_csv(ROOT / "data" / "btc-fut" / "BTCUSDT_15m.csv",
                     usecols=["timestamp", "close"], parse_dates=["timestamp"])
    px = px.rename(columns={"timestamp": "ts", "close": "close"}).drop_duplicates("ts")
    px = px.set_index("ts").sort_index()

    m = pd.read_csv(ROOT / "data" / "flow" / "BTCUSDT_metrics_5m.csv",
                    parse_dates=["create_time"])
    m = m.drop_duplicates("create_time").set_index("create_time").sort_index()
    # metrics UTC -> price-CSV clock: +315min maps snapshot to the bar whose
    # CLOSE it equals (bar row = open time; open + 15 = close).
    m.index = m.index + pd.Timedelta(minutes=315)
    m = m.add_prefix("m_")

    # CORRECT PAIRING (bugfix 2026-09-27, see header): row labelled L pairs
    # with the metric whose shifted m_time == L; that snapshot's instant is
    # L+15 = this row's OWN close. (Pairing rows at open+15 instead used
    # the NEXT row's close snapshot = one-bar lookahead; first run invalid.)
    grid = m.reindex(m.index.union(px.index)).sort_index()
    grid = grid.ffill(limit=3)
    merged = grid.reindex(px.index)

    df = px.join(merged, how="inner")
    df["oi"] = df["m_sum_open_interest"]
    df["taker"] = df["m_sum_taker_long_short_vol_ratio"]
    df["top"] = df["m_sum_toptrader_long_short_ratio"]

    # features (all causal: use only rows up to the bar's own close)
    df["oi_chg_1h"] = df["oi"].pct_change(4)
    df["oi_chg_4h"] = df["oi"].pct_change(16)
    mu = df["oi"].rolling(96).mean()
    sd = df["oi"].rolling(96).std()
    df["oi_z_24h"] = (df["oi"] - mu) / sd
    df["taker_ls_1h"] = df["taker"].rolling(4).mean()
    df["top_ls_1h"] = df["top"].rolling(4).mean()
    df["px_ret_4h"] = df["close"].pct_change(16)
    df["div_4h"] = df["oi_chg_4h"] - df["px_ret_4h"]

    for name, nb in HORIZONS.items():
        df[f"fwd_{name}"] = df["close"].pct_change(nb).shift(-nb)

    warm = 96
    return df.iloc[warm:-max(HORIZONS.values())]


def terciles(s: pd.Series, y: pd.Series) -> dict:
    q = pd.qcut(s.rank(method="first"), 3, labels=False)
    out = {}
    for k in (0, 1, 2):
        sel = y[q == k]
        out[f"Q{k + 1}"] = {"n": int(sel.size), "mean": float(sel.mean())}
    means = [out[f"Q{k + 1}"]["mean"] for k in range(3)]
    mono_up = means[0] < means[1] < means[2]
    mono_dn = means[0] > means[1] > means[2]
    out["monotone"] = bool(mono_up or mono_dn)
    out["direction"] = "up" if mono_up else ("down" if mono_dn else "none")
    out["spread"] = means[2] - means[0]
    out["all_n_ok"] = all(out[f"Q{k + 1}"]["n"] >= MIN_N for k in range(3))
    return out


def main() -> int:
    df = load()
    res = {"meta": {
        "hypothesis": "Binance positioning features carry forward-return information",
        "kind": "descriptive screen (era-local terciles, NOT causal, no costs)",
        "features": FEATURES, "horizons": list(HORIZONS),
        "eras": {k: list(v) for k, v in ERAS.items()},
        "survivor_rule": "S1 same-sign all 4 cells AND S2 monotone>=3/4 AND S3 n>=100",
        "rows": int(len(df)),
        "range": [str(df.index[0]), str(df.index[-1])],
    }, "cells": {}, "verdicts": {}}

    for feat in FEATURES:
        cells = {}
        for era, (a, b) in ERAS.items():
            sub = df.loc[a:b]
            for hname in HORIZONS:
                y = sub[f"fwd_{hname}"].dropna()
                x = sub[feat].reindex(y.index).dropna()
                common = x.index.intersection(y.index)
                cells[f"{era}_{hname}"] = terciles(x.loc[common], y.loc[common])
        res["cells"][feat] = cells

        signs = [np.sign(c["spread"]) for c in cells.values()]
        s1 = len(set(signs)) == 1 and signs[0] != 0
        s2 = sum(1 for c in cells.values() if c["monotone"]) >= 3
        s3 = all(c["all_n_ok"] for c in cells.values())
        res["verdicts"][feat] = {
            "S1_same_sign": bool(s1), "S2_monotone_ge3": bool(s2),
            "S3_n_ok": bool(s3),
            "survives": bool(s1 and s2 and s3),
            "spreads": {k: c["spread"] for k, c in cells.items()},
            "mono": {k: c["monotone"] for k, c in cells.items()},
        }

    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"rows={res['meta']['rows']} range={res['meta']['range']}")
    print(f"{'feature':14s} {'S1':>4s} {'S2':>4s} {'S3':>4s}  verdict  spreads(h16/h96 x oos/is)")
    for f in FEATURES:
        v = res["verdicts"][f]
        sp = " ".join(f"{v['spreads'][k]*100:+.2f}" for k in
                      ("oos_h16", "oos_h96", "is_h16", "is_h96"))
        print(f"{f:14s} {str(v['S1_same_sign']):>4s} {str(v['S2_monotone_ge3']):>4s} "
              f"{str(v['S3_n_ok']):>4s}  {'SURVIVE' if v['survives'] else 'FAIL':7s}  {sp} (% fwd)")
    surv = [f for f in FEATURES if res["verdicts"][f]["survives"]]
    print("SURVIVORS:", surv if surv else "none")
    print("JSON:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
