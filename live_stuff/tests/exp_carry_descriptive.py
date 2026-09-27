"""PARADIGM 3 — CARRY/FUNDING HARVEST (descriptive screen, Phase 1).

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

Origin: user-selected paradigm #3 of the "outside the v18 model" batch.
v18 never collects funding deliberately (it is a cost line); the carry
question is the opposite: can a book PROFIT from funding settlements +
basis by sitting on the side that GETS PAID, and does that survive price
risk and costs?

DATA (fetched this session by scripts/fetch_binance_flow.py):
  - data/flow/funding/*.zip x 80 (BTCUSDT fundingRate monthly 2020-01..
    2026-08): calc_time(ms UTC), funding_interval_hours, last_funding_rate
    (settled at calc_time; long pays when rate > 0, short pays when < 0).
  - data/flow/premium1h/*.zip x 80 (BTCUSDT premiumIndexKlines 1h): hourly
    open/high/low/close = premium (perp mark vs index basis, fraction).
  - price: data/btc-fut/BTCUSDT_15m.csv (same as Paradigm 1), daily UTC-day
    close (IST rows grouped after -5:30). Funding data ends 2026-08: days
    whose forward window needs settlements after 2026-08-31 are dropped.

FEATURES (fixed, no additions; all causal, computed at day t close from
settlements/premium with times <= end of day t):
  fund_1d   mean funding rate of settlements on day t
  fund_7d   mean funding rate, settlements last 7 days
  fund_30d  mean funding rate, settlements last 30 days
  prem_1d   mean premium close, hours of day t
  prem_7d   mean premium close, last 7 days

POSITION RULE embedded in the forward return (the carry definition, not a
fitted parameter): dir_t = -sign(x_t) - i.e. SHORT when the funding/basis
is positive (get paid the positive funding), LONG when negative. Days with
x == 0 are skipped.

FORWARD RETURN per day t (h in {1 day, 7 days}):
  r_carry(h) = dir_t * price_ret(t -> t+h)  -  dir_t * SumF(t -> t+h]
  where SumF = sum of funding rates settled strictly after end-of-day t
  through end-of-day t+h (money the position actually receives/pays).
  No costs in Phase 1 (descriptive, like Paradigms 1-2).

METHOD: terciles of x WITHIN era across days (era-local, descriptive - the
same convention as Phase 1 of Paradigms 1 and 2). Cells = 2 eras x 2
horizons = 4 per feature; per cell report mean r_carry of Q1/Q2/Q3, spread
Q3-Q1, monotonicity, n (days per tercile).

ERAS (house results windows):
  OOS = [2021-07-01, 2023-01-01), IS = [2023-07-01, 2026-09-10)

SURVIVOR RULE (pre-registered, per feature; all must hold):
  S1  spread Q3-Q1 SAME SIGN in all 4 cells
  S2  terciles monotone in >= 3 of 4 cells
  S3  every tercile in every cell n >= 100 days
Survivor -> Phase 2 path-true carry book (separate pre-registration with
turnover-aware costs: charge 0.095% round trip only on direction CHANGES,
since a carry position is held between flips - the whole point of the
paradigm). No survivor -> carry/funding recorded DEAD without Phase 2.

RESEARCH_POLICY: all 5 features x both horizons x both eras reported, no
best-of, no auto-adopt; descriptive spreads do NOT include costs.

Output: live_stuff/tests/_carry_descriptive_results.json
Run: python -u live_stuff/tests/exp_carry_descriptive.py
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT / "data" / "flow"
OUT = ROOT / "live_stuff" / "tests" / "_carry_descriptive_results.json"

FEATURES = ["fund_1d", "fund_7d", "fund_30d", "prem_1d", "prem_7d"]
HORIZONS = {"h1": 1, "h7": 7}
ERAS = {"oos": ("2021-07-01", "2023-01-01"), "is": ("2023-07-01", "2026-09-10")}
MIN_N = 100


def load_funding() -> pd.DataFrame:
    rows = []
    for z in sorted((FLOW / "funding").glob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            name = zf.namelist()[0]
            data = zf.read(name).decode().splitlines()
        for ln in data[1:]:
            p = ln.split(",")
            rows.append((int(p[0]), float(p[2])))
    df = pd.DataFrame(rows, columns=["ts", "rate"]).drop_duplicates("ts")
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df.sort_values("ts").reset_index(drop=True)


def load_premium_daily() -> pd.Series:
    rows = []
    for z in sorted((FLOW / "premium1h").glob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            name = zf.namelist()[0]
            data = zf.read(name).decode().splitlines()
        for ln in data[1:]:
            p = ln.split(",")
            rows.append((int(p[0]), float(p[4])))
    df = pd.DataFrame(rows, columns=["ts", "close"]).drop_duplicates("ts")
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df["date"] = df["ts"].dt.date
    return df.groupby("date")["close"].mean()


def load_daily_price() -> pd.Series:
    px = pd.read_csv(ROOT / "data" / "btc-fut" / "BTCUSDT_15m.csv",
                     usecols=["timestamp", "close"], parse_dates=["timestamp"])
    px["date"] = (px["timestamp"] - pd.Timedelta(hours=5, minutes=30)).dt.date
    cnt = px.groupby("date").size()
    close = px.groupby("date")["close"].last()
    return close.loc[cnt[cnt >= 90].index]


def build() -> tuple[pd.DataFrame, pd.Series]:
    fund = load_funding()
    fund["date"] = fund["ts"].dt.date
    prem = load_premium_daily()
    px = load_daily_price()

    day_rate = fund.groupby("date")["rate"]          # per-day settlements
    dates = px.index
    f = pd.DataFrame(index=dates)
    dm = day_rate.mean().reindex(dates)
    f["fund_1d"] = dm
    f["fund_7d"] = dm.rolling(7, min_periods=4).mean()
    f["fund_30d"] = dm.rolling(30, min_periods=15).mean()
    pm = prem.reindex(dates)
    f["prem_1d"] = pm
    f["prem_7d"] = pm.rolling(7, min_periods=4).mean()

    # funding sums per day for forward SumF
    daily_sum = day_rate.sum()
    ds = daily_sum.reindex(dates).fillna(0.0)

    # forward: settlement sum in (end of day t, end of day t+h]
    # daily_sum is indexed by settlement DATE: SumF(t -> t+h] = sum over days t+1..t+h
    cum = ds.cumsum()

    fwd = {}
    for h in HORIZONS.values():
        r = pd.DataFrame(index=dates)
        r["price_ret"] = (px.shift(-h) / px - 1.0)
        c_next = cum.shift(-h)
        r["sumf"] = c_next - cum                    # days t+1..t+h sums
        fwd[h] = r

    # last funding date coverage check
    last_fund_day = fund["date"].max()
    return f, px, fwd, ds, last_fund_day  # type: ignore[return-value]


def cell_stats(xs: pd.Series, rs: pd.Series) -> dict:
    j = pd.concat([xs, rs], axis=1).dropna()
    j.columns = ["x", "y"]
    j = j[j["x"] != 0.0]
    j = j.sort_values("x")
    q = len(j) // 3
    if q == 0:
        return {"n": 0, "skipped": True}
    parts = [j.iloc[:q], j.iloc[q:2 * q], j.iloc[2 * q:]]
    means = [float(p["y"].mean()) for p in parts]
    ns = [int(len(p)) for p in parts]
    mono = (means[0] < means[1] < means[2]) or (means[0] > means[1] > means[2])
    return {"Q1": means[0], "Q2": means[1], "Q3": means[2],
            "spread": means[2] - means[0], "monotone": mono,
            "direction": "up" if means[0] < means[1] < means[2] else (
                "down" if means[0] > means[1] > means[2] else "none"),
            "n": sum(ns), "n_each": ns, "skipped": False}


def main() -> int:
    f, px, fwd, ds, last_fund_day = build()
    print(f"[data] price days={len(px)} {px.index[0]}..{px.index[-1]} | "
          f"funding last day={last_fund_day}", flush=True)

    res = {"meta": {"hypothesis": "funding/basis carry position "
                    "(dir=-sign) earns positive spread in both eras",
                    "kind": "descriptive (era-local terciles, no costs)",
                    "features": FEATURES, "horizons": list(HORIZONS),
                    "eras": {k: list(v) for k, v in ERAS.items()},
                    "survivor_rule": "S1 same-sign 4 cells + S2 monotone>=3/4 "
                                     "+ S3 n>=100 days",
                    "funding_last_day": str(last_fund_day),
                    "days": int(len(px)), "range": [str(px.index[0]),
                                                     str(px.index[-1])]},
           "cells": {}, "verdicts": {}}

    for feat in FEATURES:
        cells = {}
        for era, (a, b) in ERAS.items():
            days_era = [d for d in px.index
                        if pd.Timestamp(a) <= pd.Timestamp(d) < pd.Timestamp(b)]
            xser = f[feat]
            for hname, h in HORIZONS.items():
                # carry forward return with dir = -sign(x)
                dirn = -xser.apply(lambda v: 0.0 if v == 0 or pd.isna(v)
                                   else (1.0 if v > 0 else -1.0))
                r_carry = dirn * fwd[h]["price_ret"] - dirn * fwd[h]["sumf"]
                sub_x = xser.loc[days_era]
                sub_r = r_carry.loc[days_era]
                st = cell_stats(sub_x, sub_r)
                cells[f"{era}_{hname}"] = st
        res["cells"][feat] = cells
        ok = [c for c in cells.values() if not c.get("skipped")]
        signs = {(1 if c["spread"] > 0 else -1) for c in ok}
        s1 = len(ok) == 4 and len(signs) == 1 and all(c["spread"] != 0 for c in ok)
        s2 = len(ok) == 4 and sum(1 for c in ok if c["monotone"]) >= 3
        s3 = len(ok) == 4 and all(all(c["n_each"][k] >= MIN_N for k in (0, 1, 2))
                                  for c in ok)
        res["verdicts"][feat] = {
            "S1_same_sign": bool(s1), "S2_monotone_ge3": bool(s2),
            "S3_n_ok": bool(s3), "survives": bool(s1 and s2 and s3),
            "spreads": {k: c.get("spread") for k, c in cells.items()},
            "mono": {k: c.get("monotone") for k, c in cells.items()},
            "q3_mean": {k: c.get("Q3") for k, c in cells.items()},
        }

    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"{'feature':10s} {'S1':>5s} {'S2':>5s} {'S3':>5s}  verdict  "
          "spreads h1/oos h1/is h7/oos h7/is (bp)")
    for feat in FEATURES:
        v = res["verdicts"][feat]
        sp = " ".join(
            (f"{v['spreads'][k]*1e4:+7.1f}" if v["spreads"][k] is not None
             else "    n/a")
            for k in ("oos_h1", "is_h1", "oos_h7", "is_h7"))
        print(f"{feat:10s} {str(v['S1_same_sign']):>5s} "
              f"{str(v['S2_monotone_ge3']):>5s} {str(v['S3_n_ok']):>5s}  "
              f"{'SURVIVE' if v['survives'] else 'FAIL':7s}  {sp}")
    surv = [x for x in FEATURES if res["verdicts"][x]["survives"]]
    print("SURVIVORS:", surv if surv else "none")
    print("JSON:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
