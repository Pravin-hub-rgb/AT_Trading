"""CROSS-ASSET - tier 4's third axis, on an asset that was never used to build the book.

WHY THIS IS A NEW STUDY AND NOT A RE-RUN
----------------------------------------
Everything in this repo called "cross-instrument" is a cross-VENUE study.
exp_cross_instrument_transfer.py compares Bybit perp against Binance perp on the
SAME asset. Venue transfer is not asset transfer, and the framework's question is
the other one: "Does the underlying phenomenon survive across instruments?"

THE FRAMEWORK'S OWN ASK
-----------------------
docs/learn/finding optimal book.md, tier 4 / bucket 11: same conceptual strategy
across BTC, ETH, ALT 1..N, and then

    Cross-Asset Success Rate

e.g. "7/10 assets profitable". It does NOT demand equal performance. It asks
where the phenomenon works and where it does not.

WHAT EXISTS AND WHAT DOES NOT
-----------------------------
ETHUSDT perp, 2025-01-01 to 2025-12-26, 34,498 x 15m bars, verified zero missing
slots and zero duplicate timestamps. The 1h file is RESAMPLED from the 15m by
plain OHLC aggregation - stated as a derived file wherever the result is used.

This is ONE asset over ONE year. The framework asks for seven to ten. So this
cannot produce a success RATE; it can produce a first data point and it can
answer the weaker question the framework also asks - is there ANY identifiable
market behaviour, or is the edge an artefact of BTC's own history.

THE COMPARISON IS LIKE FOR LIKE
-------------------------------
The same book params, the same risk model, the same costs (55bp fee/side, 2x,
5bp entry / 10bp exit), run twice: once on BTC Bybit over the SAME calendar
window, and once on ETH. Window-matching matters - a year of ETH against three
years of BTC would compare a regime to a regime and nothing else.

THE 1h LAYER IS THE CAVEAT
--------------------------
The books are HTF/LTF: sw10 opens the window from 1h swings. On ETH that 1h is
resampled. So the ETH result tests a resampled HTF plane, not a native one. This
is disclosed in the output and in the doc rather than buried.

Writes _cross_asset_eth.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

import exp_repin_stale as repin                               # noqa: E402
from run_experiment import net_r                              # noqa: E402
from exp_full_metrics import compute                          # noqa: E402
import run_experiment as re_                                  # noqa: E402

# Base params MUST come from run_experiment.BP, exactly as exp_repin_stale.measure
# does: sim(..., **{**dict(re_.BP), **cfg["params"]}). The registry's params dict
# alone is NOT enough - it carries exp_mltf (not an engine kwarg) and does NOT
# carry max_positions, chop_thresh, htf_rr, window_end, atr_low_thresh or
# atr_high_thresh. Passing params alone therefore produced ZERO trades on both
# assets and a silent all-null table.
BASE_PARAMS = dict(re_.BP)

# The books worth carrying to a second asset. Chosen for a reason, not by rank:
# the shipping book, the two the optimal-book study flags as strongest, the one
# it retires, and the two serial signal books because they are the smallest and
# so the easiest to kill.
BOOKS = [
    "fsent_champ_long",
    "fsent_champ_long_mcloff",
    "fsent_champ_long_htf15",
    "fsent_champ_long_htffs",
    "fsent_sig_multi",
    "fsent_sig_full",
]


def summarise(tr):
    tr = [t for t in tr if t.get("outcome") != "open"]
    if not tr:
        return None
    repin._trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    rs = [net_r([t]) for t in tr]
    dates = [t.get("exit_date") or t.get("date") or "" for t in tr]
    m = compute(rs, dates)
    tot = sum(rs)
    return {"n": len(tr), "net": round(tot, 2),
            "avgR": round(tot / len(tr), 3), "pf": m.get("pf"),
            "wr": m.get("wr"), "max_dd": m.get("max_dd"),
            "ulcer": m.get("ulcer")}


def load_asset(symbol: str, want_lo: str, want_hi: str):
    """Load one asset through the same loaders the books use, then trim both
    the candles and the swing chains to a common calendar window so the two
    assets are compared over identical dates."""
    from src.btc.btc_routes import _load_window, _compute_swings
    # _load_window returns ((candles, flow), err) - take the payload and ignore
    # the error slot, but fail loudly rather than silently trading on nothing.
    res15, err15 = _load_window("15m", None, symbol)
    res1h, err1h = _load_window("1h", None, symbol)
    if not res15 or not res1h:
        print("  !! %s failed to load: %s / %s" % (symbol, err15, err1h))
        return None
    c15, f15 = res15
    c1h, f1h = res1h
    lo = min(c15[0]["ts"], c1h[0]["ts"])
    hi = max(c15[-1]["ts"], c1h[-1]["ts"])
    if want_lo:
        lo = max(lo, want_lo)
    if want_hi:
        hi = min(hi, want_hi)

    def trim(candles, flow):
        # FlowCandle is a dataclass whose time field is `date` and it is a
        # STRING "YYYY-MM-DD HH:MM:SS", while a candle's `ts` is an int epoch.
        # Comparing them - `f.date in idx` where idx holds ints - matches
        # NOTHING, so the flow silently came back untrimmed while the candles
        # were trimmed, and the two no longer lined up: sw10 came back with 0
        # swings on BTC over a window that plainly contains 8,624 1h bars.
        # Trim the flow by its own parsed timestamp instead.
        from datetime import datetime as _dt
        keep = [c for c in candles if lo <= c["ts"] <= hi]
        keep_flow = []
        for f in flow:
            try:
                t = int(_dt.fromisoformat(f.date).timestamp())
            except Exception:
                continue
            if lo <= t <= hi:
                keep_flow.append(f)
        return keep, keep_flow

    c15, f15 = trim(c15, f15)
    c1h, f1h = trim(c1h, f1h)
    sw15 = _compute_swings(f15, "continuous", min_bars=15)
    sw10 = _compute_swings(f1h, "continuous", min_bars=10)
    sw20 = _compute_swings(f1h, "continuous", min_bars=20)
    # measure() looks the swing up by key in a dict that must carry all four;
    # only the one the book names is used, but a missing key raises KeyError
    # rather than returning nothing, which is the right failure.
    #
    # fine_ltf is the 1m series and the FINE BASIS IS REQUIRED - the books are
    # measured on it and every registry pin depends on it. basis="coarse" with
    # fine_ltf=[] returns ZERO trades, which is how a run once reported six
    # "agreements" that were six empty cells.
    fine = []
    try:
        from src.btc.btc_routes import _load_fine_1m
        fine = _load_fine_1m(c15[0]["ts"], c15[-1]["ts"], symbol) or []
    except Exception as e:
        print("     (no 1m fine series for %s: %s -- will use coarse)" % (symbol, e))
    return {"c15": c15, "f15": f15, "c1h": c1h, "f1h": f1h,
            "sw15": sw15, "sw10": sw10, "sw20": sw20, "htf15": sw15,
            "fine": fine,
            "window": (lo, hi), "candles_15m": len(c15),
            "fine_bars": len(fine)}


def main() -> int:
    import test_experiments_craze as craze
    from src.btc.engines.htf_ltf.unified import simulate_htf_ltf_streak_halt
    from experiment_registry import EXPERIMENTS

    import test_experiments_craze as craze
    from experiment_registry import EXPERIMENTS
    sim = craze.build_module()

    t0 = time.time()
    print("loading ETH ...", flush=True)
    eth = load_asset("ETHUSDT_PERP", None, None)
    print("  ETH window %s -> %s   %d x 15m bars"
          % (eth["window"][0], eth["window"][1], eth["candles_15m"]), flush=True)
    print("  ETH 1m fine bars: %d" % eth["fine_bars"], flush=True)

    print("loading BTC ...", flush=True)
    btc = load_asset("BTCUSDT_BYBIT", eth["window"][0], eth["window"][1])
    print("  BTC trimmed to the SAME window: %d x 15m bars"
          % btc["candles_15m"], flush=True)

    # IDENTITY GATE, BEFORE ANY CROSS-ASSET NUMBER IS QUOTED. Run the control
    # through the SAME path this harness uses and require it to reproduce the
    # registry pin. Without this the run reports "sign agreement 6 of 6" on
    # six all-zero cells - basis="coarse" with fine_ltf=[] yields ZERO trades on
    # BTC too, so both assets looked like they agreed when nothing had run.
    cfg0 = dict(EXPERIMENTS["fsent_champ_long"])
    cfg0["swing"] = "sw10"
    g = repin.measure(sim, btc, cfg0)
    print("  identity gate: fsent_champ_long on the trimmed BTC window -> n=%d net=%.2f"
          % (g["n"], g["net"]), flush=True)
    if g["n"] == 0:
        print("  !! GATE FAILED - zero trades on the control. This harness")
        print("     cannot measure anything yet; refusing to report.")
        return 1
    print("  (note: 497 / +466.92 is the full-history registry pin. A one-year")
    print("   window trades less by construction - the gate is n>0, not equality)",
          flush=True)

    out = {"window": eth["window"], "eth_15m_bars": eth["candles_15m"],
           "btc_15m_bars": btc["candles_15m"],
           "eth_1m_fine_bars": eth["fine_bars"],
           "btc_1m_fine_bars": btc["fine_bars"],
           "eth_1h_is_resampled": True, "books": {}}

    for key in BOOKS:
        cfg = EXPERIMENTS.get(key)
        if not isinstance(cfg, dict):
            print("  %-28s not in registry" % key)
            continue
        # Call the SAME wrapper the registry books are measured through, not
        # the engine directly. sim = test_experiments_craze.build_module() takes
        # (c1h, swings_htf, c15, sw15) and the swing KEY comes from the cfg -
        # calling unified.simulate_htf_ltf_streak_halt directly returned ZERO
        # trades on BOTH assets while repin.measure on the same data returns 497
        # for this book. Two all-null cells looked like a real cross-asset
        # finding and were a harness error.
        cfg = dict(cfg)
        row = {}
        for label, asset in (("btc", btc), ("eth", eth)):
            cfg = dict(cfg)
            cfg["swing"] = "sw10"
            # The books and their registry pins are measured on the FINE basis,
            # and BTC is here too. ETH has no 1m file in this dataset, so ETH
            # runs coarse, and that difference is stated in the output and in
            # the doc rather than hidden - it is a real caveat, not a footnote.
            if not asset["fine"]:
                cfg["basis"] = "coarse"
            try:
                meas = repin.measure(sim, asset, cfg)
            except Exception as e:
                print("  %-28s %-4s FAILED %s: %s"
                      % (key, label, type(e).__name__, e), flush=True)
                continue
            row[label] = meas
            print("  %-28s %-4s n=%-5d net=%9.2f dd=%-7s win=%s"
                  % (key, label, meas["n"], meas["net"],
                     meas.get("dd_net"), meas.get("win")), flush=True)
        out["books"][key] = row

    Path(__file__).with_name("_cross_asset_eth.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8")

    print()
    print("=" * 92)
    print("CROSS-ASSET - same window, same knobs, same costs, BTC Bybit vs ETH perp")
    print("=" * 92)
    print("  window %s -> %s" % eth["window"])
    print()
    print("%-28s %18s %18s %s" % ("book", "BTC n / net", "ETH n / net", "verdict"))
    print("-" * 92)
    agree = 0
    for key, row in out["books"].items():
        b, e = row.get("btc"), row.get("eth")
        if not b or not e:
            continue
        both = (b["net"] > 0) == (e["net"] > 0)
        agree += 1 if both else 0
        print("%-28s %8d /%9.2f %8d /%9.2f %s"
              % (key, b["n"], b["net"], e["n"], e["net"],
                 "AGREE" if both else "SIGN FLIP"))
    print()
    print("  sign agreement: %d of %d books" % (agree, len(out["books"])))
    print("  NOTE: this is ONE asset. The framework asks for 7-10, so no")
    print("  cross-asset SUCCESS RATE can be claimed from this run.")
    print()
    print("wrote _cross_asset_eth.json  (%.0fs)" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())