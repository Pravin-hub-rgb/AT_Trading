"""
E - THE VOLATILE CANDLE POPULATION.

WHY THIS POPULATION AND NOT ANOTHER

Volatile candles are where the youngest logic in the engine lives, and none of it
has been tested as a POPULATION.

  - The close-colour rule for volatile B1/B2/FLIP was added 2026-10-13 (5d6cab2).
    Before it, volatile candles took their direction from something else.
  - firstswing.py:509-534 is the other half: a volatile candle that SUSTAINS a
    direction which has already flipped since B1 produces NO MARK AT ALL. The
    owner's ruling: "we cannot mark it anything here ... so we have to wait."
  - 197 volatile B1s and 51 B1 direction flips were recorded when the colour rule
    landed. 197 swings is a real population, not a rounding error, and it did not
    EXIST as a category before the fix.

So this asks whether a volatile candle anywhere in the swing carries information
about the trade that follows - and specifically whether the silent-suppression
path (volatile sustains a flipped leg, no mark) sits in front of better or worse
trades than the ones that do print.

THE THREE GROUPS

    clean          no volatile candle in the swing at all
    volatile-early a volatile candle before the swing's first FLIP
    volatile-late  a volatile candle after the first FLIP - this is the window
                   where the engine can go SILENT, so it is the interesting one

Volatility is detected the same way the engine detects it: a candle whose high
exceeds the running high AND whose low breaches the running low, both measured
against the candles before it inside the same leg. Not a proxy, not a
range-percentile guess.

DISCIPLINE

  IS decides; OOS is printed for check. Groups are reported with counts so a
  group built from nine trades cannot be mistaken for a finding.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_volatile_b1.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backtest/experiments/refit_constants"))
from exp_mcl_matrix import load_era, LADDER_BOOKS  # noqa: E402


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS
    from engine.v18_params import SWING
    from src.btc.btc_swing import compute_btc_swings

    sim = build_family_module()
    out = {"stage": "volatile_population", "eras": {}}

    for era in ("is", "oos"):
        print()
        print("=" * 112)
        print("E - VOLATILE CANDLE POPULATION      era = %s" % era.upper())
        print("=" * 112)
        d = load_era(era)
        c15 = d["c15"]
        sw15 = compute_btc_swings(
            d["f15"], opts={"minBars": SWING["min_bars_15m"], "b2GapBars": 1},
            max_swings=max(1, len(d["f15"]) // 2))

        # classify each swing by where its volatile candles sit
        klass = {}
        n_vol_total = 0
        for s in sw15:
            bs = s["breaks"]
            lo_i = s["leg_start_idx"]
            hi_i = s["confirmed_at_idx"]
            if hi_i is None:
                hi_i = max([b["idx"] for b in bs], default=lo_i)
            flip_at = next((b["idx"] for b in bs if b["kind"] == "FLIP"), None)
            early = late = 0
            hi = lo = None
            for i in range(lo_i, min(hi_i + 1, len(c15) - 1)):
                h = float(c15[i]["high"]); l = float(c15[i]["low"])
                if hi is not None and lo is not None and h > hi and l < lo:
                    n_vol_total += 1
                    if flip_at is None or i < flip_at:
                        early += 1
                    else:
                        late += 1
                hi = h if hi is None else max(hi, h)
                lo = l if lo is None else min(lo, l)
            klass[s["swing_index"]] = (
                "clean" if (early + late) == 0 else
                "volatile-late" if late and not early else
                "volatile-early" if early else "clean")
        print("  volatile candles inside swings: %d" % n_vol_total)

        era_out = {}
        for book in LADDER_BOOKS:
            cfg = EXPERIMENTS[book]
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            ch_sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
            r = sim(d["c1h"], ch_sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            tr = [t for t in (r["ltf_trades"] if isinstance(r, dict) else r)
                  if str(t.get("outcome", "")).lower() != "open"]
            g = {}
            for t in tr:
                g.setdefault(klass.get(t.get("swing_no"), "clean"), []).append(
                    float(t["r_multiple"]))
            if not g:
                continue
            print("  %s" % book)
            print("    %-16s %6s %9s %9s %7s %7s %7s" %
                  ("group", "n", "GROSS", "mean R", "PF", "DD", "MaxCL"))
            print("    " + "-" * 66)
            gs = {}
            for k in ("clean", "volatile-early", "volatile-late"):
                v = g.get(k, [])
                if not v:
                    continue
                n = len(v)
                wins = [x for x in v if x > 0]
                losses = sum(x for x in v if x <= 0)
                pf = (sum(wins) / abs(losses)) if losses else 0.0
                eq = peak = dd = 0.0
                mc = cur = 0
                for x in v:
                    eq += x; peak = max(peak, eq); dd = max(dd, peak - eq)
                    cur = cur + 1 if x <= 0 else 0
                    mc = max(mc, cur)
                gs[k] = {"n": n, "gross": round(sum(v), 2), "mean": round(sum(v) / n, 4),
                         "pf": round(pf, 2), "dd": round(dd, 2), "mc": mc}
                print("    %-16s %6d %+9.2f %+9.4f %7.2f %7.2f %7d"
                      % (k, n, sum(v), sum(v) / n, pf, dd, mc))
            thin = [k for k, s in gs.items() if s["n"] < 30]
            if thin:
                print("    (n<30, treat as anecdote not signal: %s)" % ", ".join(thin))
            print()
            era_out[book] = gs
        out["eras"][era] = era_out

    (HERE / "volatile_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("  wrote %s" % (HERE / "volatile_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())