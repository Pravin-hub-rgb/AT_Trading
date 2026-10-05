"""PHASE 1 PRE-FLIGHT - can 1m swings be dropped into the engine as-is?

WHY THIS FILE EXISTS
====================
`method/HANDOVER_SESSION.md` section 7 calls Phase 1 "wiring, not a new concept":
add a kwarg substituting `swings_ltf` with 1m swings, reuse the existing
`_collect_signals` call. Phase 0 removed the compute blocker, so this is
next - but reading the engine says the substitution is NOT self-contained,
and this script proves that before anyone patches the engine.

THE INDEX COUPLING
==================
In v18_streak_halt.simulate_htf_ltf_streak_halt:

    ltf_sigs = _collect_signals(swings_ltf, "decisive", ..., candles=candles_ltf)
    for sig in ltf_sigs:
        bar = ltf_store.pos(sig["bar"])   # ltf_store = CandleStore(candles_ltf)
        if bar < 0 or bar >= len(candles_ltf): continue     <-- silent drop

`bar` is a POSITION IN candles_ltf, then used to index chop_per_ltf,
atr_pct and candle_ts_ltf (and downstream atr15). A signal survives only if
its timestamp resolves inside candles_ltf.

So passing 1m swings with 15m candles_ltf makes every 1m timestamp fail to
resolve -> every signal is dropped by that `continue`. No crash, no obvious
symptom: just a quietly near-empty book.

THE DEEPER CONFOUND
===================
Passing 1m candles as candles_ltf too is the real fix, and that is NOT a
neutral swap - candles_ltf drives the per-bar feature layer AND the
bar-counted risk params, so every one of these changes meaning by ~15x:
  * `_atr_pct_15m(candles_ltf)` - 1m ATR is a fraction of 15m ATR
  * `chop_thresh=58.0` under mode="atr_high" - a 15m-calibrated threshold
    evaluated on 1m is a DIFFERENT gate, not the same one
  * `atr15[i]` behind `sl_buf_atr=0.01` - 1m ATR tightens the buffer a lot
  * `cooldown_bars=8`, `max_consecutive_losses=3`, `sustainBars`, `minBars`
    - these count BARS: 8 bars is 2h on 15m and 8min on 1m
  * `ts+900` in the chop/garch lookbacks is the 15m bar duration, hardcoded

A 1m layer is a re-parameterisation, not a flag flip. This script quantifies
each confound so Phase 1 is designed from numbers.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u phase1_preflight.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

CSV_1M = ROOT / "data/bybit/BTCUSDT_1m.csv"
CSV_15M = ROOT / "data/bybit/BTCUSDT_15m.csv"
OUT = ROOT / "backtest/tests/_phase1_preflight.json"


def _read(path):
    import pandas as pd
    df = pd.read_csv(path, usecols=["timestamp", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return (df.sort_values("timestamp")
              .drop_duplicates(subset="timestamp", keep="last")
              .reset_index(drop=True))


def _candles(df):
    return [{"date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
             "ts": int(r.timestamp.timestamp()) - 5 * 3600 - 30 * 60,
             "open": float(r.open), "high": float(r.high),
             "low": float(r.low), "close": float(r.close)}
            for r in df.itertuples(index=False)]


def _flow(candles):
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=c["open"], high=c["high"],
                       low=c["low"], close=c["close"]) for c in candles]


def _swings(flow, min_bars):
    from src.btc.btc_swing import compute_btc_swings
    return compute_btc_swings(flow, opts={"minBars": max(2, int(min_bars))},
                              max_swings=max(1, len(flow) // 2))


def _atr_pct(candles, lb=14):
    """ATR as % of close, the same shape as the engine's _atr_pct_15m."""
    n = len(candles)
    tr = [0.0] * n
    for i in range(n):
        hi, lo = float(candles[i]["high"]), float(candles[i]["low"])
        pc = float(candles[i - 1]["close"]) if i else hi
        tr[i] = max(hi - lo, abs(hi - pc), abs(lo - pc))
    out = [0.0] * n
    for i in range(n):
        lo_i = max(0, i - lb + 1)
        a = sum(tr[lo_i:i + 1]) / (i - lo_i + 1)
        out[i] = a / (float(candles[i]["close"]) or 1.0) * 100.0
    return out


def main() -> None:
    from src.btc.btc_engine import CandleStore, _collect_signals
    report: dict = {}

    c15 = _candles(_read(CSV_15M))
    c1 = _candles(_read(CSV_1M))
    print(f"15m bars: {len(c15):,}   1m bars: {len(c1):,}")

    # A 90-day window keeps this quick; the failure mode is structural and
    # does not depend on sample size.
    c15w, c1w = c15[-90 * 96:], c1[-90 * 1440:]
    sw15, sw1 = _swings(_flow(c15w), 10), _swings(_flow(c1w), 10)
    print(f"window swings: 15m={len(sw15):,}  1m={len(sw1):,}")

    # --- 1. the drop test: 1m signals against a 15m store -------------------
    store15 = CandleStore(c15w)
    sig1 = _collect_signals(sw1, "decisive", skip_first=True,
                            selection="stream", candles=c1w)
    kept = sum(1 for s in sig1 if store15.pos(s["bar"]) >= 0)
    print(f"\n1m signals: {len(sig1):,}   resolvable in the 15m store: "
          f"{kept:,}  ({100.0*kept/max(1,len(sig1)):.2f}%)")
    report["drop_test"] = {
        "one_min_signals": len(sig1), "resolvable_in_15m_store": kept,
        "pct_kept": round(100.0 * kept / max(1, len(sig1)), 4),
        "note": "the engine's `if bar < 0: continue` drops the rest silently",
    }

    # Control: 15m signals against the 15m store must all resolve.
    sig15 = _collect_signals(sw15, "decisive", skip_first=True,
                             selection="stream", candles=c15w)
    k15 = sum(1 for s in sig15 if store15.pos(s["bar"]) >= 0)
    print(f"control 15m signals: {len(sig15):,}  resolvable: {k15:,} "
          f"({100.0*k15/max(1,len(sig15)):.2f}%)")
    report["control_15m"] = {
        "signals": len(sig15), "resolvable": k15,
        "pct_kept": round(100.0 * k15 / max(1, len(sig15)), 4),
    }

    # --- 2. the scale confounds --------------------------------------------
    a15, a1 = _atr_pct(c15w), _atr_pct(c1w)
    m15, m1 = sum(a15) / len(a15), sum(a1) / len(a1)
    print(f"\nmean ATR%: 15m={m15:.4f}   1m={m1:.4f}   "
          f"ratio={m15/max(m1,1e-12):.1f}x")
    report["atr_scale"] = {
        "mean_atr_pct_15m": round(m15, 5), "mean_atr_pct_1m": round(m1, 5),
        "ratio_15m_over_1m": round(m15 / max(m1, 1e-12), 2),
    }

    print("\nbar-counted params, what one value means in wall time:")
    rows = []
    for name, val in (("cooldown_bars", 8), ("max_consecutive_losses", 3),
                      ("sustainBars", 7), ("minBars(sw10)", 10)):
        r = {"param": name, "value": val,
             "minutes_on_15m": val * 15, "minutes_on_1m": val}
        rows.append(r)
        print(f"  {name:<22} {val:>3}  ->  {r['minutes_on_15m']:>5} min on 15m, "
              f"{r['minutes_on_1m']:>4} min on 1m  "
              f"({r['minutes_on_15m']/r['minutes_on_1m']:.0f}x)")
    report["bar_params"] = rows
    report["hardcoded_900_in_source"] = "ts+900 lookbacks assume the 15m bar"

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nreport -> {OUT}")


if __name__ == "__main__":
    main()
