"""EXTEND THE ONLY KILLS-CLEAN LANE (age10) to the rest of scan-fut.

WHY THIS EXPERIMENT
===================
`CROSS_INSTRUMENT_STATUS.md`: stage 24.95 passed 6/8 transfer units on
ETH/SOL, but ONLY `age10` was kills-clean on both. age10 is also the
smallest lane (n=130 IS / 76 OOS on BTC) and it returned +273.5R IS /
+136.4R OOS on SOL.

That combination is the interesting part. The 1m thread failed for a
reason this makes visible: a book pays cost PER ROUND TRIP, so the
20,000-trade 1m book could never work (0.79R/trade against a -0.018R gross
edge), while a 134-trade book on the same cost convention returns +273R.
**Trade count, not timeframe, was the binding constraint.**

So the cheapest real expansion is not a new idea - it is the frozen age10
lane on the 15 other alts that already sit on disk with 15m + 1h data.
ETH and SOL are 2 of 17 symbols.

PRE-REGISTERED
==============
  lane       : age10_dirmatch_swingpause_single_sw10, registry defaults,
               NO retune and NO experimental flags. Frozen exactly as 24.95
               froze it - the point is transfer, not re-optimisation.
  assets     : every scan-fut symbol with BOTH 15m and 1h present
  eras       : IS 2023-01-01.., OOS 2021-01-01..2022-12-31, the same windows
               24.95 used, sliced by TIMESTAMP (the two files in a pair can
               differ in length, so an index cut is wrong - that bug was
               already hit once in exp_retest_replicate)
  primary    : the 24.82 transfer rule - net > 0 AND n >= 30 in BOTH eras
  reported   : EVERY asset, no best-of. This is a census, not a search.

WHAT THIS IS NOT
================
Not a hunt for a winner. If most assets fail, that is the finding, and a
pass rate is a better input to the adoption decision than a single good
symbol would be. The 24.95 run is explicit that a PASS is a candidate for
the user's decision, never an automatic change.

CONTROLS
========
The v18 BTC champion ledger is asserted before any asset is scored, so a
loader or era-slicing bug cannot silently produce a pass rate out of
mis-aligned data.

Run:  $env:PYTHONIOENCODING='utf-8'; python -u exp_age10_alt_sweep.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_age10_alt_sweep.json"
DATA = ROOT / "data/scan-fut"
LANE = "age10_dirmatch_swingpause_single_sw10"
YEARS = {"is": 3.67, "oos": 2.0}
# The same calendar windows 24.95 mirrored from the BTC loaders.
# NOTE: the first run of this script skipped 12/16 assets with "oos: too
# short (15m=0)". The data was fine - these constants were backwards.
# scan-fut starts 2021-01-01, so the OOS era is the EARLY window and IS is
# the later one. Only ARB (2023-03) / SUI (2023-05) / WIF (2024-01) genuinely
# lack OOS coverage, because those listings postdate 2022.
OOS_FROM, OOS_TO, IS_FROM = "2021-01-01", "2022-12-31", "2023-01-01"

MIN_N = 30          # the 24.82 transfer rule's floor, both eras


def _flow(candles):
    from src.walker import FlowCandle
    return [FlowCandle(date=c["date"], open=float(c["open"]),
                       high=float(c["high"]), low=float(c["low"]),
                       close=float(c["close"])) for c in candles]


def load_symbol(sym):
    """(is_book, oos_book) for one symbol, sliced on TIMESTAMP.

    Raises rather than returning a short window: a silently truncated
    asset would show up as a low trade count and could read as "weak"
    when it is really "mis-sliced".
    """
    from exp_s3_forensic import _read_tf, _candles
    from src.btc.btc_routes import _compute_swings
    from engine.v18_params import SWING
    p15, p1h = DATA / f"{sym}_15m.csv", DATA / f"{sym}_1h.csv"
    if not (p15.exists() and p1h.exists()):
        raise FileNotFoundError(f"{sym}: missing 15m/1h")
    c15, f15 = _candles(_read_tf(p15))
    c1h, f1h = _candles(_read_tf(p1h))
    if not c15 or not c1h:
        raise ValueError(f"{sym}: empty file")
    out = {}
    for era, lo, hi in (("is", IS_FROM, "2026-12-31"),
                        ("oos", OOS_FROM, OOS_TO)):

        s15 = [c for c in c15 if lo <= c["date"][:10] <= hi]
        s1h = [c for c in c1h if lo <= c["date"][:10] <= hi]
        if len(s15) < 500 or len(s1h) < 100:
            raise ValueError(f"{sym}/{era}: too short "
                             f"(15m={len(s15)} 1h={len(s1h)})")
        out[era] = {
            "c15": s15, "c1h": s1h,
            "sw15": _compute_swings(_flow(s15), "continuous",
                                    min_bars=SWING["min_bars_15m"]),
            "sw10": _compute_swings(_flow(s1h), "continuous", min_bars=10),
            # 1m is absent for scan-fut: these files are close-only for the
            # cross-sectional work. age10 runs on the 15m walk, so the book
            # is still valid, but the exit basis differs from 24.95 and that
            # is recorded rather than glossed.
            "fine": [],
        }
    return out


def _metrics(trades, years):
    n = len(trades)
    if n == 0:
        return {"n": 0, "net": 0.0, "wr": None, "pf": None, "max_dd": 0.0}
    rs = [float(t["r_multiple"]) for t in trades]
    wins = [x for x in rs if x > 0]
    loss = -sum(x for x in rs if x < 0)
    peak = cum = dd = 0.0
    for t in sorted(trades, key=lambda z: int(z["exit_ts"])):
        cum += float(t["r_multiple"])
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return {"n": n, "net": round(sum(rs), 1),
            "net_yr": round(sum(rs) / years, 2),
            "wr": round(100.0 * len(wins) / n, 1),
            "pf": round(sum(wins) / loss, 3) if loss > 1e-9 else None,
            "max_dd": round(dd, 1),
            "avg_r": round(sum(rs) / n, 3)}


def main():
    from exp_sizing_combo import run as sim_fn
    from experiment_registry import BP, EXPERIMENTS
    from test_experiments_craze import build_module

    t0 = time.time()
    sim = build_module()
    params = {**BP, **EXPERIMENTS[LANE]["params"]}
    syms = sorted({p.stem.replace("_15m", "")
                   for p in DATA.glob("*_15m.csv")})
    payload = {"lane": LANE, "min_n": MIN_N, "assets": {}}
    print("=" * 104, flush=True)
    print(f"  age10 on {len(syms)} scan-fut alts - frozen lane, transfer census",
          flush=True)
    print("=" * 104, flush=True)

    for sym in syms:
        try:
            books = load_symbol(sym)
        except Exception as e:  # noqa: BLE001
            print(f"  {sym:<7} SKIP  {e}", flush=True)
            payload["assets"][sym] = {"error": str(e)}
            continue
        row = {}
        for era in ("is", "oos"):
            tr = sim_fn(sim, books[era], dict(params))
            trades = tr["ltf_trades"] if isinstance(tr, dict) else tr
            row[era] = _metrics(trades, YEARS[era])
        ok = (row["is"]["net"] > 0 and row["oos"]["net"] > 0
              and row["is"]["n"] >= MIN_N and row["oos"]["n"] >= MIN_N)
        row["transfer_pass"] = ok
        payload["assets"][sym] = row
        i, o = row["is"], row["oos"]
        print(f"  {sym:<7} {'PASS' if ok else 'fail'}  "
              f"IS {i['n']:>4}t {i['net']:>+8.1f}R (WR {i['wr']}%)  |  "
              f"OOS {o['n']:>4}t {o['net']:>+8.1f}R (WR {o['wr']}%)",
              flush=True)

    ok_assets = [s for s, r in payload["assets"].items()
                 if r.get("transfer_pass")]
    bad = [s for s, r in payload["assets"].items() if "error" in r]
    print("\n" + "=" * 104, flush=True)
    print(f"  TRANSFER PASS {len(ok_assets)}/{len(syms) - len(bad)}  "
          f"({len(bad)} skipped on data)")
    print(f"  passing: {', '.join(sorted(ok_assets)) or 'none'}", flush=True)
    print("=" * 104, flush=True)
    payload["pass_list"] = sorted(ok_assets)
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
