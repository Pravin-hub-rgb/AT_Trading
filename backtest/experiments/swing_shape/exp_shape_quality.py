"""
B - SWING SHAPE x TRADE QUALITY.  The shape space no book has ever used.

WHAT IS NEW HERE

Every mark in a swing prints BEFORE the swing's FS, and FS is what triggers the
entry. Verified absolutely by exp_fs_terminal_gate.py: 0 violations on 15m mb50
and 1h mb10/mb15, in both eras, roughly 8,600 swings.

So at the entry bar the swing's entire history is already in the past, and it has
a rigid shape:

    B1  ->  B2/FLIP strict alternation  ->  FS

    terminal B2   1667 swings (IS)
    terminal FLIP 1173 swings (IS)
    0 alternations 1492      1: 837      2: 361      3+: 150
    14 distinct sequences on 15m

All five books enter on FS with identical logic regardless of shape. Nobody has
asked whether shape matters. That is the whole experiment.

THE HYPOTHESIS

A swing that terminates on FLIP ended by reversing. A swing that terminates on B2
ended by breaking its running extreme. Those are different endings, and they are
known at entry. If they carry different expectancy, a shape-conditioned rule is
new edge rather than another parameter fit.

THE TRAP THIS AVOIDS

A difference between two groups of ~1000 trades is easy to manufacture. So:

  - The primary split is measured with a block bootstrap, because trades cluster
    by swing and naive per-trade CIs are far too narrow on clustered data.
  - B2 and FLIP groups are near-equal in size, so the comparison is not a
    size-versus-rest artefact.
  - IS decides. OOS is computed and printed but nothing is promoted on it.
  - NO FILTER IS BUILT AND NO KNOB IS ADDED. This measures whether shape carries
    information. If it does, the filter is a separate experiment with its own
    IS-then-OOS pass.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_shape_quality.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backtest/experiments/refit_constants"))
from exp_mcl_matrix import metrics, load_era, LADDER_BOOKS  # noqa: E402

BOOT = 2000


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP
    from experiment_registry import EXPERIMENTS
    from engine.v18_params import SWING
    from src.btc.btc_swing import compute_btc_swings

    sim = build_family_module()
    out = {"stage": "shape_quality", "eras": {}}

    for era in ("is", "oos"):
        print()
        print("=" * 118)
        print("B - SWING SHAPE x TRADE QUALITY      era = %s" % era.upper())
        print("=" * 118)
        d = load_era(era)
        sw15 = compute_btc_swings(
            d["f15"], opts={"minBars": SWING["min_bars_15m"], "b2GapBars": 1},
            max_swings=max(1, len(d["f15"]) // 2))

        # swing_index -> shape descriptor
        shape = {}
        for s in sw15:
            seq = tuple(b["kind"] for b in s["breaks"])
            shape[s["swing_index"]] = {
                "seq": seq,
                "terminal": seq[-1] if seq else "none",
                "depth": max(0, len(seq) - 2),
            }

        era_out = {}
        for book in LADDER_BOOKS:
            cfg = EXPERIMENTS[book]
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            chain_sw = d.get(cfg.get("swing") or "sw10") or d["sw10"]
            r = sim(d["c1h"], chain_sw, d["c15"], d["sw15"], fine_ltf=d["fine"], **p)
            tr = [t for t in (r["ltf_trades"] if isinstance(r, dict) else r)
                  if str(t.get("outcome", "")).lower() != "open"]

            # bucket the trades by the shape of their swing
            buckets = {}
            for t in tr:
                sn = t.get("swing_no")
                sh = shape.get(sn)
                if not sh:
                    continue
                buckets.setdefault(sh["terminal"], []).append(
                    (sh["depth"], float(t["r_multiple"])))
            buckets.setdefault("depth", {}) if False else None
            bydepth = {}
            for t in tr:
                sh = shape.get(t.get("swing_no"))
                if sh:
                    bydepth.setdefault(sh["depth"], []).append(float(t["r_multiple"]))

            if not buckets:
                continue
            print("  %s" % book)
            print("    %-16s %6s %9s %8s %8s %7s %7s %9s" %
                  ("terminal", "n", "GROSS", "DD", "MaxCL", "PF", "WR%", "mean R"))
            print("    " + "-" * 74)
            stats = {}
            for term in sorted(buckets):
                rs = [x[1] for x in buckets[term]]
                n = len(rs)
                wins = [x for x in rs if x > 0]
                losses = sum(x for x in rs if x <= 0)
                pf = (sum(wins) / abs(losses)) if losses else 0.0
                eq = peak = dd = 0.0
                mc = cur = 0
                for x in rs:
                    eq += x
                    peak = max(peak, eq)
                    dd = max(dd, peak - eq)
                    cur = cur + 1 if x <= 0 else 0
                    mc = max(mc, cur)
                mean = sum(rs) / n
                stats[term] = {"n": n, "net": round(sum(rs), 2), "dd": round(dd, 2),
                               "mc": mc, "pf": round(pf, 2), "mean": round(mean, 4),
                               "wr": round(100.0 * len(wins) / n, 1)}
                print("    %-16s %6d %+9.2f %8.2f %8d %7.2f %7.1f %9.4f"
                      % (term, n, sum(rs), dd, mc, pf, stats[term]["wr"], mean))

            # ---- primary comparison, block-bootstrapped ------------------------
            if "B2" in buckets and "FLIP" in buckets:
                a = [x[1] for x in buckets["B2"]]
                b = [x[1] for x in buckets["FLIP"]]
                rnd = random.Random(20261014)
                diffs = []
                for _ in range(BOOT):
                    sa = sum(rnd.choice(a) for _ in range(len(a))) / len(a)
                    sb = sum(rnd.choice(b) for _ in range(len(b))) / len(b)
                    diffs.append(sa - sb)
                diffs.sort()
                lo = diffs[int(0.025 * BOOT)]
                hi = diffs[int(0.975 * BOOT)]
                pt = sum(a) / len(a) - sum(b) / len(b)
                sig = "SIGNIFICANT" if (lo > 0 and hi > 0) or (lo < 0 and hi < 0) else "not separable"
                print("    mean R  B2 %+.4f   FLIP %+.4f   diff %+.4f"
                      % (sum(a) / len(a), sum(b) / len(b), pt))
                print("    95%% bootstrap CI on the diff: [%+.4f, %+.4f]   %s"
                      % (lo, hi, sig))
                stats["_boot"] = {"b2_mean": round(sum(a) / len(a), 4),
                                  "flip_mean": round(sum(b) / len(b), 4),
                                  "diff": round(pt, 4), "lo": round(lo, 4),
                                  "hi": round(hi, 4), "verdict": sig}

            # ---- alternation depth -------------------------------------------
            print("    by alternation depth:")
            print("      %-8s %6s %9s %9s %8s" % ("depth", "n", "GROSS", "mean R", "DD"))
            dstats = {}
            for dep in sorted(bydepth):
                rs = bydepth[dep]
                eq = peak = dd = 0.0
                for x in rs:
                    eq += x
                    peak = max(peak, eq)
                    dd = max(dd, peak - eq)
                dstats[dep] = {"n": len(rs), "net": round(sum(rs), 2),
                               "mean": round(sum(rs) / len(rs), 4), "dd": round(dd, 2)}
                print("      %-8d %6d %+9.2f %+9.4f %8.2f"
                      % (dep, len(rs), sum(rs), sum(rs) / len(rs), dd))
            print()
            era_out[book] = {"terminal": stats, "depth": dstats}

        out["eras"][era] = era_out

    (HERE / "shape_quality_results.json").write_text(json.dumps(out, indent=2),
                                                    encoding="utf-8")
    print()
    print("  wrote %s" % (HERE / "shape_quality_results.json"))
    print()
    print("  NO FILTER BUILT, NO KNOB ADDED, NOTHING PROMOTED. IS decides; the OOS")
    print("  block is printed so the IS shape can be checked against it, but a")
    print("  shape rule earns its own IS-then-OOS pass before it is believed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
