"""PARADIGM 4 - EVENT-DRIVEN TRADES (descriptive screen, Phase 1).

THIS DOCSTRING IS THE BINDING PRE-REGISTRATION. Written BEFORE any run.

Origin: user-selected paradigm #4 of the "outside the v18 model" batch.
v18 is blind to the calendar; the question is whether SCHEDULED macro
releases (CPI, FOMC, NFP...) leave a repeatable, tradeable drift around
BTC that is KNOWN IN ADVANCE (you know WHEN, never WHAT - no surprise
values are used, only timestamps).

DATA (fetched 2026-09-25, data/scheduled_events/):
  - official_us_events_2021_2026.json: 386 events, 382 with exact UTC
    timestamps, ALL known_in_advance=true, evidence
    scheduled_exact_utc(_current_api). event_type counts (OOS/IS era):
      employment 77 (19/41)  cpi 71 (18/37)  ppi 71 (18/37)
      jolts 71 (18/38)  fomc_statement 46 (12/25)
      gdp 23 (0/19, data starts 2025-01)  pce 23 (0/19, starts 2025-01)
  - EXCLUDED up front (documented): date_only families - political (4
    events, no exact time) and official_fed_speech_archive (62 speeches,
    file's own eligibility field says "archive_date_only_excluded_from_
    pre_announced_study"). No exact timestamp => window anchor undefined.
  - price: data/btc-fut/BTCUSDT_15m.csv, IST wall-clock labels (UTC+5:30).

CANDIDATES (fixed): 7 event_types x 4 windows = 28, ALL reported:
  pre24  return T-24h -> T      (drift into the release)
  post1  return T -> T+1h       (immediate reaction)
  post4  return T -> T+4h
  post24 return T -> T+24h      (slow reaction)
Anchor price for an instant A = close of the first 15m bar whose END
  (label + 15m) >= A converted to IST (entry delayed up to 15m - causal,
  same convention in Phase 2). Windows whose anchor exceeds the last
  price bar are NaN-dropped per event.

METHOD: per candidate, split events by ERA (era by event UTC date):
  OOS = [2021-07-01, 2023-01-01), IS = [2023-07-01, 2026-09-10).
  Per era: n events, mean r, median r, share same-sign as the OOS mean.

SURVIVOR RULE (pre-registered, per candidate; all must hold):
  S1  n >= 10 events in BOTH eras
  S2  sign(mean_r OOS) == sign(mean_r IS), both nonzero
  S3  consistency >= 0.60 in BOTH eras, consistency = share of events
      whose r has the COMMON sign (= sign of the OOS mean)
Survivor -> Phase 2 path-true event trades (separate pre-registration:
  next-bar-close entry, 0.095% RT per event trade, K1-K7 kills).

MULTIPLICITY NOTE (stated up front): 28 candidates at these thresholds
can produce false survivors by chance; Phase 2's independent costed kill
table is the required second filter - nothing is adoptable from Phase 1.

RESEARCH_POLICY: all 28 candidates x both eras reported, no best-of, no
auto-adopt; Phase 1 is descriptive (no costs).

Output: backtest/tests/_event_descriptive_results.json
Run: python -u backtest/tests/exp_event_descriptive.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "data" / "scheduled_events" / "official_us_events_2021_2026.json"
OUT = ROOT / "backtest" / "tests" / "_event_descriptive_results.json"

CANDIDATES = ["cpi", "ppi", "employment", "jolts", "fomc_statement",
              "gdp", "pce"]
WINDOWS = {"pre24": (-24, 0), "post1": (0, 1), "post4": (0, 4),
           "post24": (0, 24)}
ERAS = {"oos": ("2021-07-01", "2023-01-01"), "is": ("2023-07-01", "2026-09-10")}
MIN_N = 10
MIN_CONSIST = 0.60
IST = timezone(timedelta(hours=5, minutes=30))


def load_events() -> list[dict]:
    blob = json.loads(EVENTS.read_text(encoding="utf-8"))
    evs = [e for e in blob["events"] if e.get("timestamp_utc")]
    assert all(e["known_in_advance"] for e in evs), "not all known_in_advance"
    assert all(e["evidence"].startswith("scheduled_exact_utc") for e in evs)
    out = []
    for e in evs:
        t = datetime.fromisoformat(e["timestamp_utc"].replace("Z", "+00:00"))
        out.append({"t": t, "type": e["event_type"], "name": e["name"]})
    out.sort(key=lambda e: e["t"])
    return out


def load_price_anchors() -> tuple[list[pd.Timestamp], pd.Series]:
    px = pd.read_csv(ROOT / "data" / "btc-fut" / "BTCUSDT_15m.csv",
                     usecols=["timestamp", "close"],
                     parse_dates=["timestamp"])
    ends = px["timestamp"] + pd.Timedelta(minutes=15)   # IST wall clock
    return list(ends), px["close"]


def anchor_price(anchor_utc: datetime, ends, closes) -> float:
    a_ist = anchor_utc.astimezone(IST).replace(tzinfo=None)
    a_ts = pd.Timestamp(a_ist)
    import bisect
    i = bisect.bisect_left(ends, a_ts)
    if i >= len(ends):
        return float("nan")
    return float(closes.iloc[i])


def main() -> int:
    evs = load_events()
    ends, closes = load_price_anchors()
    print("[data] exact events=%d  price bars=%d %s..%s"
          % (len(evs), len(closes), ends[0], ends[-1]), flush=True)

    res = {"meta": {"hypothesis": "scheduled macro releases leave a "
                    "repeatable pre/post drift tradeable on BTC",
                    "kind": "descriptive (no costs, next-bar-close anchors)",
                    "candidates": CANDIDATES, "windows": list(WINDOWS),
                    "eras": {k: list(v) for k, v in ERAS.items()},
                    "survivor_rule": "S1 n>=10 both eras + S2 same mean "
                                     "sign both eras + S3 consistency>=0.60 "
                                     "both eras",
                    "excluded": "date_only families (political 4, fed "
                                "speeches 62) - no exact timestamp",
                    "events_total": len(evs)},
           "cells": {}, "verdicts": {}}

    dropped = 0
    for et in CANDIDATES:
        cells = {}
        et_evs = [e for e in evs if e["type"] == et]
        for wname, (wh0, wh1) in WINDOWS.items():
            per_era = {}
            for era, (a0, b0) in ERAS.items():
                vals = []
                for e in et_evs:
                    ed = e["t"].date().isoformat()
                    if not (a0 <= ed < b0):
                        continue
                    a_ = e["t"] + timedelta(hours=wh0)
                    b_ = e["t"] + timedelta(hours=wh1)
                    p0 = anchor_price(a_, ends, closes)
                    p1 = anchor_price(b_, ends, closes)
                    if pd.isna(p0) or pd.isna(p1) or p0 <= 0:
                        dropped += 1
                        continue
                    vals.append(p1 / p0 - 1.0)
                per_era[era] = vals
            o, i_ = per_era["oos"], per_era["is"]
            mean_o = (sum(o) / len(o)) if o else float("nan")
            mean_i = (sum(i_) / len(i_)) if i_ else float("nan")
            s = 1.0 if (mean_o == mean_o and mean_o > 0) else (
                -1.0 if (mean_o == mean_o and mean_o < 0) else 0.0)
            def consist(vals):
                if not vals:
                    return float("nan")
                hit = sum(1 for v in vals if (v > 0) == (s > 0) and v != 0)
                return hit / len(vals)
            cell = {"n_oos": len(o), "n_is": len(i_),
                    "mean_oos": None if mean_o != mean_o else round(mean_o, 6),
                    "mean_is": None if mean_i != mean_i else round(mean_i, 6),
                    "median_oos": None if not o else round(
                        sorted(o)[len(o) // 2], 6),
                    "median_is": None if not i_ else round(
                        sorted(i_)[len(i_) // 2], 6),
                    "consist_oos": None if not o else round(consist(o), 4),
                    "consist_is": None if not i_ else round(consist(i_), 4)}
            cells[f"{et}|{wname}"] = cell
        res["cells"][et] = cells

    for et in CANDIDATES:
        cells = res["cells"][et]
        verds = {}
        for wname in WINDOWS:
            c = cells[f"{et}|{wname}"]
            n_ok = c["n_oos"] >= MIN_N and c["n_is"] >= MIN_N
            mo, mi = c["mean_oos"], c["mean_is"]
            sign_ok = (mo is not None and mi is not None
                       and mo != 0 and mi != 0
                       and ((mo > 0) == (mi > 0)))
            consist_ok = (c["consist_oos"] is not None
                          and c["consist_is"] is not None
                          and c["consist_oos"] >= MIN_CONSIST
                          and c["consist_is"] >= MIN_CONSIST)
            verds[wname] = {"S1_n_ok": n_ok, "S2_same_sign": sign_ok,
                            "S3_consist_ok": consist_ok,
                            "survives": bool(n_ok and sign_ok and consist_ok),
                            "direction": (1 if (mo or 0) > 0 else -1)
                            if sign_ok else None}
        res["verdicts"][et] = verds

    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")

    print(f"{'event|window':22s} {'nO':>3s} {'nI':>3s} {'meanO%':>8s} "
          f"{'meanI%':>8s} {'cO':>5s} {'cI':>5s}  verdict")
    surv = []
    for et in CANDIDATES:
        for wname in WINDOWS:
            c = res["cells"][et][f"{et}|{wname}"]
            v = res["verdicts"][et][wname]
            mo = "%.2f" % (100 * c["mean_oos"]) if c["mean_oos"] is not None else "n/a"
            mi = "%.2f" % (100 * c["mean_is"]) if c["mean_is"] is not None else "n/a"
            co = "%.2f" % c["consist_oos"] if c["consist_oos"] is not None else "n/a"
            ci = "%.2f" % c["consist_is"] if c["consist_is"] is not None else "n/a"
            tag = "SURVIVE" if v["survives"] else "fail"
            if v["survives"]:
                surv.append(f"{et}|{wname}")
            print(f"{et+'|'+wname:22s} {c['n_oos']:3d} {c['n_is']:3d} "
                  f"{mo:>8s} {mi:>8s} {co:>5s} {ci:>5s}  {tag}")
    print("SURVIVORS:", surv if surv else "none")
    print("anchor-window NaN drops:", dropped)
    print("JSON:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
