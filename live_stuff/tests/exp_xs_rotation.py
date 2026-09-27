"""PARADIGM 2 — CROSS-SECTIONAL 16-ALT ROTATION (descriptive screen, Phase 1).

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

Origin: user-selected paradigm #2 of the "outside the v18 model" batch.
Everything in this repo so far is SINGLE-INSTRUMENT time-series (v18 entries
on BTC/ETH, stat-arb a fixed 2-leg spread). Nothing has tested the
CROSS-SECTIONAL axis: does RELATIVE strength between Binance perps carry
forward-return information, and would a rotation book trade it?

DATA (backfilled this session by scripts/backfill_scanfut_oos.py, integrity
checked: sorted, 0 dups, 0 bad files):
  - data/scan-fut/{SYM}_15m.csv x 16 symbols, IST wall-clock (UTC+5:30),
    format timestamp,open,high,low,close,x,y (x=y=0 - no volume; close-only
    study). 11 symbols from 2021-01-01 (ADA AVAX BNB DOGE DOT LINK LTC MATIC
    NEAR SOL XRP), OP 2022-06, APT 2022-10, ARB 2023-03, SUI 2023-05,
    WIF 2024-01; MATIC ends 2024-09 (delisted). File ends 2026-09-10.
  - Daily bar = UTC day (rows grouped after subtracting 5:30); daily close =
    last 15m bar of the UTC day. A symbol-day needs >= 90 of 96 bars or it
    is dropped (partial days from fetch edges / delistings excluded).

FEATURES (fixed, no additions):
  mom_7d       close(t)/close(t-7) - 1
  mom_30d      close(t)/close(t-30) - 1
  mom_90d      close(t)/close(t-90) - 1
  rev_1d       -(close(t)/close(t-1) - 1)   [1-day reversal, sign explicit]
  mvola_30d    mom_30d / stdev(daily ret, 30d)

METHOD: each day with >= 8 eligible symbols (else the day is skipped),
rank the cross-section on the feature (pct rank), split into terciles
(equal-weight by construction - we report MEAN per-symbol forward return of
each tercile). Descriptive: era-local ranks? NO - ranks are same-day
cross-sectional only (no future info within the day), forward returns are
from the day's close - no lookahead by construction.

HORIZONS: fwd 1d and fwd 7d (close(t+h)/close(t) - 1).

ERAS (house results windows, day-close assignment):
  OOS = [2021-07-01, 2023-01-01), IS = [2023-07-01, 2026-09-10)

CELLS: feature x horizon x era = 5 x 2 x 2; per cell report tercile mean
fwd returns (Q1 bottom .. Q3 top), spread Q3-Q1, monotone flag, n (symbol-
days per tercile).

SURVIVOR RULE (pre-registered, per feature; all must hold):
  S1  spread Q3-Q1 SAME SIGN in all 4 cells (2 horizons x 2 eras)
  S2  terciles monotone (Q1<Q2<Q3 or Q1>Q2>Q3 by mean fwd) in >= 3 of 4 cells
  S3  every tercile in every cell has n >= 100 symbol-days
Survivor -> Phase 2 path-true rotation book (separate pre-registration;
costs NOT modelled here). Fails -> feature dead on this axis; if ALL fail,
cross-sectional momentum/reversal on this universe is recorded DEAD without
Phase 2.

RESEARCH_POLICY: all 5 features x both horizons x both eras reported, no
best-of, no auto-adopt, descriptive (no costs) is NOT a pass.

Output: live_stuff/tests/_xs_rotation_results.json
Run: python -u live_stuff/tests/exp_xs_rotation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "scan-fut"
OUT = ROOT / "live_stuff" / "tests" / "_xs_rotation_results.json"

FEATURES = ["mom_7d", "mom_30d", "mom_90d", "rev_1d", "mvola_30d"]
HORIZONS = {"f1": 1, "f7": 7}
ERAS = {"oos": ("2021-07-01", "2023-01-01"), "is": ("2023-07-01", "2026-09-10")}
MIN_SYM_DAY = 8
MIN_BARS_DAY = 90
MIN_N = 100
WARMUP = 90


def load_daily() -> pd.DataFrame:
    """Daily close matrix: index = UTC-day close date, columns = symbols."""
    cols = {}
    for f in sorted(DATA.glob("*_15m.csv")):
        sym = f.name.rsplit("_", 1)[0].replace("USDT", "")
        df = pd.read_csv(f, usecols=["timestamp", "close"],
                         parse_dates=["timestamp"])
        df["date"] = df["timestamp"] - pd.Timedelta(hours=5, minutes=30)
        df["date"] = df["date"].dt.date
        cnt = df.groupby("date").size()
        close = df.groupby("date")["close"].last()
        keep = cnt[cnt >= MIN_BARS_DAY].index
        cols[sym] = close.loc[keep]
    px = pd.DataFrame(cols).sort_index()
    return px


def features(px: pd.DataFrame) -> dict:
    """{feature: DataFrame(date x symbol)} of the fixed feature set."""
    r1 = px.pct_change(1)
    return {
        "mom_7d": px.pct_change(7),
        "mom_30d": px.pct_change(30),
        "mom_90d": px.pct_change(90),
        "rev_1d": -r1,
        "mvola_30d": px.pct_change(30) / r1.rolling(30).std(),
    }


def cell_stats(xday: pd.Series, fday: pd.Series) -> dict:
    """Terciles of cross-section xday vs forward fday (aligned, no NaN)."""
    j = pd.concat([xday, fday], axis=1).dropna()
    j.columns = ["x", "y"]
    if len(j) < MIN_SYM_DAY:
        return {"n": 0, "skipped": True}
    j = j.sort_values("x")
    q = len(j) // 3
    # ranks with ties broken by symbol order (deterministic)
    parts = [j.iloc[:q], j.iloc[q:2 * q], j.iloc[2 * q:]]
    means = [float(p["y"].mean()) for p in parts]
    ns = [int(len(p)) for p in parts]
    mono = (means[0] < means[1] < means[2]) or (means[0] > means[1] > means[2])
    direction = "up" if means[0] < means[1] < means[2] else (
        "down" if means[0] > means[1] > means[2] else "none")
    return {"Q1": means[0], "Q2": means[1], "Q3": means[2],
            "spread": means[2] - means[0], "monotone": mono,
            "direction": direction, "n": sum(ns), "n_each": ns,
            "skipped": False}


def main() -> int:
    px = load_daily()
    ft = features(px)
    # forward returns from close
    fwd = {h: px.pct_change(h).shift(-h) for h in HORIZONS.values()}
    # symbol universe evolves: only use feature row if symbol present
    meta = {"symbols": list(px.columns), "days": int(len(px)),
            "range": [str(px.index[0]), str(px.index[-1])]}

    res = {"meta": {**meta, "features": FEATURES, "horizons": list(HORIZONS),
                    "eras": {k: list(v) for k, v in ERAS.items()},
                    "min_sym_day": MIN_SYM_DAY, "min_bars_day": MIN_BARS_DAY,
                    "min_n_tercile": MIN_N},
           "cells": {}, "verdicts": {}}

    days = px.index
    for feat in FEATURES:
        cells = {}
        for era, (a, b) in ERAS.items():
            in_era = [(i, d) for i, d in enumerate(days)
                      if pd.Timestamp(a) <= pd.Timestamp(d) < pd.Timestamp(b)]
            for hname, h in HORIZONS.items():
                acc = {1: [], 2: [], 3: []}
                skipped = 0
                for i, d in in_era:
                    xday = ft[feat].loc[d] if d in ft[feat].index else None
                    if xday is None:
                        skipped += 1
                        continue
                    fday = fwd[h].loc[d] if d in fwd[h].index else None
                    st = cell_stats(xday, fday)
                    if st.get("skipped"):
                        skipped += 1
                        continue
                    acc[1].append((st["Q1"], st["n_each"][0]))
                    acc[2].append((st["Q2"], st["n_each"][1]))
                    acc[3].append((st["Q3"], st["n_each"][2]))
                if not acc[1]:
                    cells[f"{era}_{hname}"] = {"n": 0, "skipped_days": skipped}
                    continue
                means, ns = {}, {}
                for k in (1, 2, 3):
                    tw = sum(w for _, w in acc[k])
                    means[f"Q{k}"] = (sum(m * w for m, w in acc[k]) / tw
                                      if tw else float("nan"))
                    ns[k] = tw
                m1, m2, m3 = means["Q1"], means["Q2"], means["Q3"]
                mono = (m1 < m2 < m3) or (m1 > m2 > m3)
                cells[f"{era}_{hname}"] = {
                    **means, "spread": m3 - m1, "monotone": bool(mono),
                    "direction": ("up" if m1 < m2 < m3 else
                                  ("down" if m1 > m2 > m3 else "none")),
                    "n": sum(ns.values()), "n_each": ns,
                    "rebalances": len(acc[1]), "skipped_days": skipped,
                }
        res["cells"][feat] = cells
        ok_cells = [c for c in cells.values() if c.get("n", 0) > 0]
        signs = {(1 if c["spread"] > 0 else -1) for c in ok_cells}
        s1 = (len(ok_cells) == 4 and len(signs) == 1 and
              all(c["spread"] != 0 for c in ok_cells))
        s2 = sum(1 for c in ok_cells if c["monotone"]) >= 3
        s3 = (len(ok_cells) == 4 and
              all(all(c["n_each"][k] >= MIN_N for k in (1, 2, 3))
                  for c in ok_cells))
        res["verdicts"][feat] = {
            "S1_same_sign": bool(s1), "S2_monotone_ge3": bool(s2),
            "S3_n_ok": bool(s3), "survives": bool(s1 and s2 and s3),
            "spreads": {k: c.get("spread") for k, c in cells.items()},
            "mono": {k: c.get("monotone") for k, c in cells.items()},
        }

    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"symbols={meta['symbols']}")
    print(f"days={meta['days']} range={meta['range']}")
    print(f"{'feature':12s} {'S1':>5s} {'S2':>5s} {'S3':>5s}  verdict  "
          "spreads f1/oos f1/is f7/oos f7/is (%)")
    for feat in FEATURES:
        v = res["verdicts"][feat]
        sp = " ".join(
            (f"{v['spreads'][k]*100:+.2f}" if v["spreads"][k] is not None
             else "  n/a ")
            for k in ("oos_f1", "is_f1", "oos_f7", "is_f7"))
        print(f"{feat:12s} {str(v['S1_same_sign']):>5s} "
              f"{str(v['S2_monotone_ge3']):>5s} {str(v['S3_n_ok']):>5s}  "
              f"{'SURVIVE' if v['survives'] else 'FAIL':7s}  {sp}")
    surv = [f for f in FEATURES if res["verdicts"][f]["survives"]]
    print("SURVIVORS:", surv if surv else "none")
    print("JSON:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
