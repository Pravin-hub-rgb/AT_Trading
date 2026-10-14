"""
B1 - sweep `b2_gap_bars`. A real knob that has never been swept.

WHY THIS ONE

`b2_gap_bars` is the length of the 1-candle gap a pivot must clear before a
break of it can be marked. It is a genuine engine parameter
(`firstswing.py:77`, overridable via `b2GapBars`), it gates 2487 of the 20460
armed suppressed breaks in `exp_swing_invariants.py` plus a share of the
pre-arm population, and **no harness has ever varied it**. It has been pinned at
1 since the beginning.

The reason this matters for the sweep rather than in general: the owner's ruling
on this rule was *"even a 0.5 point break is a break"* - an argument about the
MAGNITUDE of a break, not about the LENGTH of the required gap. The length was
never a ruling. It was a default.

WHAT CHANGES, AND IT IS NOT A SMALL THING

This is not an entry filter. It changes the CHAIN: a different gap length
produces a different mark set, so the fingerprints change and every book's entry
population changes with it. Each arm rebuilds sw15/sw10/sw20/htf15 from the flow
and reports the chain alongside the book numbers, so a reader can see how much
of the chain moved. Arms that produce a chain fingerprint equal to the baseline
are reported as such - if gap=1 does not reproduce `83a3af3f6ebf0ffa` then
something is wrong with the harness and the run stops.

DISCIPLINE

IS ONLY. OOS stays sealed until an arm has won on IS. The baseline for every
comparison is the A1 freeze, `_baseline_2026_10_14.json`. Per the sweep rules no
arm is promoted on IS alone - a winner must be re-derived on OOS exactly once
and dies if it fails there.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_b2_gap_sweep.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

HERE = Path(__file__).resolve().parent
BASE_FP = "83a3af3f6ebf0ffa"
BOOKS = ["fsent_champ_long", "fsent_champ_short", "fsent_champ_long_htf15",
         "fsent_champ_long_htffs", "fsent_champ_long_mcloff"]
GAPS = [0, 1, 2, 3]


def chain(candles: list[dict], flow, min_bars: int, gap: int) -> tuple[list[dict], dict]:
    """Rebuild one chain with an explicit b2_gap_bars."""
    from src.btc.btc_swing import compute_btc_swings
    opts = {"minBars": max(2, int(min_bars)), "b2GapBars": int(gap)}
    sw = compute_btc_swings(flow, opts=opts, max_swings=max(1, len(flow) // 2))
    ts = [c["date"][:16] for c in candles]
    rows = []
    for s in sw:
        for b in s["breaks"]:
            rows.append("%s|%s|%s|%d|%d" % (ts[b["idx"]], b["kind"], b["dir"],
                                            round(float(b["px"]), 1), s["swing_index"]))
        if s.get("fs_at_idx") is not None:
            rows.append("FS|%s|%s" % (ts[s["fs_at_idx"]], s["dir"]))
    rows.sort()
    h = hashlib.sha256(chr(10).join(rows).encode()).hexdigest()[:16]
    return sw, {"fingerprint": h, "swings": len(sw),
                "marks": sum(len(s["breaks"]) for s in sw)}


def stats(trades: list[dict]) -> dict:
    closed = [t for t in trades if str(t.get("outcome", "")).lower() != "open"]
    v = [float(t["r_multiple"]) for t in closed if t.get("r_multiple") is not None]
    n = len(v)
    net = sum(v)
    wins = [x for x in v if x > 0]
    losses = [x for x in v if x <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    eq = peak = dd = 0.0
    for x in v:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {"n": n, "net": round(net, 2), "dd": round(dd, 2),
            "pf": round(pf, 2) if pf is not None else None}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, get_data
    from engine.v18_params import SWING
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    d = get_data()

    print("=" * 92)
    print("B1 - b2_gap_bars sweep, IS ONLY (OOS sealed)")
    print("=" * 92)
    print("  baseline chain fingerprint (A1 freeze): %s" % BASE_FP)
    print()

    out = {"stage": "b2_gap_sweep", "era": "is", "baseline_fingerprint": BASE_FP,
           "arms": {}}
    chains = {}
    for gap in GAPS:
        sw15, c15 = chain(d["c15"], d["f15"], SWING["min_bars_15m"], gap)
        sw10, c10 = chain(d["c1h"], d["f1h"], 10, gap)
        sw20, c20 = chain(d["c1h"], d["f1h"], SWING["min_bars_1h"], gap)
        htf15, c_h = chain(d["c1h"], d["f1h"], 15, gap)
        chains[gap] = (sw15, sw10, sw20, htf15)
        same = "  == BASELINE" if c15["fingerprint"] == BASE_FP else ""
        print("  gap=%d  15m %s swings=%d marks=%d%s"
              % (gap, c15["fingerprint"], c15["swings"], c15["marks"], same))
    print()

    # the gap=1 arm must reproduce the freeze, or the harness is wrong
    if chains[1][0] and out["arms"] is None:
        pass
    sw15_1, _, _, _ = chains[1]
    fp1 = chain(d["c15"], d["f15"], SWING["min_bars_15m"], 1)[1]["fingerprint"]
    if fp1 != BASE_FP:
        print("  ABORT: gap=1 does not reproduce the A1 baseline (%s != %s)."
              % (fp1, BASE_FP))
        print("  The harness is wrong; nothing below is trustworthy.")
        return 2
    print("  gap=1 reproduces the baseline exactly - harness verified.")
    print()

    for gap in GAPS:
        sw15, sw10, sw20, htf15 = chains[gap]
        series = {"c15": d["c15"], "f15": d["f15"], "c1h": d["c1h"], "f1h": d["f1h"],
                  "sw15": sw15, "sw10": sw10, "sw20": sw20, "htf15": htf15,
                  "fine": d["fine"]}
        print("  ================= gap=%d =================" % gap)
        out["arms"][str(gap)] = {}
        for b in BOOKS:
            cfg = EXPERIMENTS.get(b)
            if not isinstance(cfg, dict):
                continue
            p = {**BP, **cfg["params"]}
            p.setdefault("exp_partial_r", 0.0)
            key = cfg.get("swing") or "sw10"
            sw = {"sw10": sw10, "sw20": sw20, "htf15": htf15}.get(key, sw10)
            res = sim(series["c1h"], sw, series["c15"], sw15,
                      fine_ltf=series["fine"], **p)
            tr = res["ltf_trades"] if isinstance(res, dict) else res
            s = stats(tr)
            out["arms"][str(gap)][b] = s
            print("    %-28s n=%-4d net=%+9.2fR  PF=%-5s DD=%6.2f"
                  % (b, s["n"], s["net"], s["pf"] if s["pf"] is not None else "-", s["dd"]))
        print()

    print("  ---- IS summary: net by gap ----")
    hdr = "    %-28s" % "book" + "".join("  gap=%d" % g for g in GAPS)
    print(hdr)
    for b in BOOKS:
        if str(b) not in out["arms"]["0"]:
            continue
        line = "    %-28s" % b
        for g in GAPS:
            line += "  %+7.1f" % out["arms"][str(g)][b]["net"]
        print(line)
    tot = {g: sum(out["arms"][str(g)][b]["net"] for b in BOOKS if b in out["arms"][str(g)])
           for g in GAPS}
    print("    %-28s" % "TOTAL IS" + "".join("  %+7.1f" % tot[g] for g in GAPS))
    print()
    print("  gap=1 is the pinned value. OOS is NOT opened here by design.")

    (HERE / "b2_gap_sweep_results.json").write_text(json.dumps(out, indent=2),
                                                    encoding="utf-8")
    print("\nwrote %s" % (HERE / "b2_gap_sweep_results.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())