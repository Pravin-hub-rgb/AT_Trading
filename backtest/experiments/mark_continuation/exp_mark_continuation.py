"""
MARK CONTINUATION - is a mark followed by continuation distinguishable, and is
it knowable at the entry bar?

THE THESIS UNDER TEST

exp_edge_decay.py found the signal is not decaying: reward/ATR accrues at roughly
+0.04 per bar for ~24 bars after a mark, and the FS entry sits around +16 bars
worth of it. The swing is a TREND, not a resolution, and we enter into its
middle.

That gives one testable claim:

    a mark followed by ~16 bars of continuation should be a DIFFERENT trade from
    a mark followed by immediate failure.

The reason this is worth testing - and the reason it is not another knob fit - is
that we enter 37 bars after the mark on median. By then, whether the swing
trended or failed is PAST INFORMATION, visible at the entry bar without
lookahead. Every other hypothesis in this sweep conditioned on something the
engine already filtered on. This one conditions on the one thing the FS gate
throws away.

THE CAUSAL STORY (pipeline 4c)

For each swing, take the LAST mark before FS. Walk forward from that mark's bar
for `W` bars, all at or before the entry bar, and measure how far price travelled
in the leg's direction, in ATR units. That is the continuation score.

    score = (close[i0+W] - close[i0]) / ATR(i0+W)     signed by leg direction

    i0 = the last mark's bar
    W  = 16 bars  (measured as the accrual window in exp_edge_decay)

Causality: the window ends at i0+W, and we only ever act at the FS bar which is
strictly after that. Nothing after the entry bar is read. i0, W, the ATR and the
leg direction are all known at or before the entry bar. Stated here to be checked
rather than trusted.

THE INVERSE TEST IS AVAILABLE FOR FREE

Split swings on the MEDIAN continuation score. If the two halves behave the same,
there is nothing here. If high-continuation trades the same as low-continuation
trades, the signal is not conditioning anything and this joins the shape and
volatile results as a negative.

MEASURED ON

  - the full IS chain, as a distribution first, before any book
  - then the four 15m books' actual trades, bucketed by their swing's score
  - both eras

WHAT IS NOT DONE

No book, no knob, no registry change. If this separates, the filter is the next
experiment and it gets its own IS-then-OOS pass like everything else.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_mark_continuation.py
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
from exp_mcl_matrix import metrics, load_era, LADDER_BOOKS  # noqa: E402

W = 16          # continuation window, from exp_edge_decay's accrual slope
ATRW = 14


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS
    from engine.v18_params import SWING
    from src.btc.btc_swing import compute_btc_swings

    sim = build_family_module()
    out = {"stage": "mark_continuation", "window": W, "atr_window": ATRW,
           "eras": {}}

    for era in ("is", "oos"):
        print()
        print("=" * 112)
        print("MARK CONTINUATION - last mark before FS, %d bars of follow-through    %s"
              % (W, era.upper()))
        print("=" * 112)
        d = load_era(era)
        c15, f15 = d["c15"], d["f15"]
        sw = compute_btc_swings(f15, opts={"minBars": SWING["min_bars_15m"],
                                           "b2GapBars": 1},
                                max_swings=max(1, len(f15) // 2))
        close = [float(c["close"]) for c in c15]
        n = len(close)

        def atr_at(i):
            if i < ATRW or i >= n:
                return None
            tr = []
            for j in range(i - ATRW + 1, i + 1):
                h, l, pc = c15[j]["high"], c15[j]["low"], c15[j - 1]["close"]
                tr.append(max(h - l, abs(h - pc), abs(l - pc)))
            return sum(tr) / ATRW

        # ---- score every swing, causally ----------------------------------
        score = {}
        n_skip = 0
        for s in sw:
            fs = s.get("fs_at_idx")
            if fs is None or not s["breaks"]:
                continue
            i0 = max(b["idx"] for b in s["breaks"])
            j = i0 + W
            if j >= fs or j >= n:          # window must close BEFORE the entry
                n_skip += 1
                continue
            a = atr_at(j)
            if not a:
                continue
            m = close[j] - close[i0]
            if s["dir"] != "up":
                m = -m
            score[s["swing_index"]] = {"ra": m / a, "kind": s["breaks"][-1]["kind"],
                                       "lag": fs - i0}

        vals = sorted(v["ra"] for v in score.values())
        med = vals[len(vals) // 2]
        print("  swings scored: %d   (skipped %d: continuation window would close"
              " at or after the entry bar)" % (len(score), n_skip))
        print("  continuation score, med reward/ATR over %d bars:" % W)
        print("     p10 %+.3f  p25 %+.3f  MEDIAN %+.3f  p75 %+.3f  p90 %+.3f"
              % (vals[len(vals) // 10], vals[len(vals) // 4], med,
                 vals[3 * len(vals) // 4], vals[9 * len(vals) // 10]))
        print()

        era_out = {"median_ra": round(med, 4), "n_scored": len(score),
                   "n_skipped": n_skip, "books": {}}

        # ---- distribution: does the score separate at all? ------------------
        hi = [v for v in score.values() if v["ra"] > med]
        lo = [v for v in score.values() if v["ra"] <= med]
        print("  DISTRIBUTION CHECK - do the two halves differ even before a book?")
        print("    %-18s %6s %11s %9s" % ("half", "n", "mean RA", ">0"))
        for lab, g in (("above median", hi), ("below median", lo)):
            if not g:
                continue
            ra = [x["ra"] for x in g]
            print("    %-18s %6d %+11.3f %8.1f%%"
                  % (lab, len(g), sum(ra) / len(g),
                     100.0 * sum(1 for x in ra if x > 0) / len(ra)))
        print()

        # ---- the real test: bucket each book's actual trades ---------------
        print("  BOOK TEST - trades bucketed by their swing's continuation score")
        print("  %-26s %-14s %6s %9s %8s %7s %7s"
              % ("book", "bucket", "n", "GROSS", "DD", "MaxCL", "PF"))
        print("  " + "-" * 84)
        book_out = {}
        for b in LADDER_BOOKS:
            cfg = EXPERIMENTS[b]
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            ch_sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
            r = sim(d["c1h"], ch_sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            tr = [t for t in (r["ltf_trades"] if isinstance(r, dict) else r)
                  if str(t.get("outcome", "")).lower() != "open"]
            buckets = {}
            for t in tr:
                sc = score.get(t.get("swing_no"))
                if not sc:
                    continue
                k = "HIGH cont." if sc["ra"] > med else "LOW cont."
                buckets.setdefault(k, []).append((sc["ra"], float(t["r_multiple"])))
            bo = {}
            for k in ("HIGH cont.", "LOW cont."):
                g = buckets.get(k, [])
                if not g:
                    continue
                rs = [x[1] for x in g]
                n_ = len(rs)
                wins = [x for x in rs if x > 0]
                losses = sum(x for x in rs if x <= 0)
                pf = (sum(wins) / abs(losses)) if losses else 0.0
                eq = peak = dd = 0.0
                mc = cur = 0
                for x in rs:
                    eq += x; peak = max(peak, eq); dd = max(dd, peak - eq)
                    cur = cur + 1 if x <= 0 else 0
                    mc = max(mc, cur)
                print("  %-26s %-14s %6d %+9.2f %8.2f %7d %7.2f"
                      % (b if k == "HIGH cont." else "", k, n_, sum(rs), dd, mc, pf))
                bo[k] = {"n": n_, "gross": round(sum(rs), 2), "dd": round(dd, 2),
                         "mc": mc, "pf": round(pf, 2),
                         "mean_ra": round(sum(x[0] for x in g) / n_, 4)}
            if "HIGH cont." in bo and "LOW cont." in bo:
                dh = bo["HIGH cont."]; dl = bo["LOW cont."]
                print("  %-26s %-14s HIGH net-per-trade %+.3f vs LOW %+.3f"
                      % ("", "difference",
                         dh["gross"] / dh["n"] - dl["gross"] / dl["n"], 0.0))
            print()
            book_out[b] = bo
        era_out["books"] = book_out
        out["eras"][era] = era_out

    (HERE / "mark_continuation_results.json").write_text(json.dumps(out, indent=2),
                                                         encoding="utf-8")
    print("  wrote %s" % (HERE / "mark_continuation_results.json"))
    print()
    print("  NO BOOK, NO KNOB, NO REGISTRY CHANGE. If HIGH and LOW separate in both")
    print("  eras on trade quality, the filter is the next experiment and it gets")
    print("  its own IS-then-OOS pass. If they match, this joins the shape and")
    print("  volatile results as a negative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())