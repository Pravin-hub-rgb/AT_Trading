"""
B2 - are the pinned constants still optimal on the CORRECTED chain?

WHY

Every threshold in these books was chosen by maximising on a chain whose marks
were ~3% wrong - 43 B2s had become FLIPs, 35 FLIPs had become B2s, 51 B1
directions had flipped. A threshold fitted to the wrong surface is not optimal
on the right one. This is the cheapest high-probability win available.

PRE-FLIGHT: all five knobs verified sim-only

    chop_thresh, atr_high_thresh, sl_buf_atr, cooldown_bars,
    max_consecutive_losses  ->  absent from backend/src/firstswing.py

So they cannot move the chain. Every arm below runs on the SAME mark surface and
the A1 identity gate holds for all of them. This sweep can only re-fit entry and
exit, never silently re-draw the marks it is being scored against.

DISCIPLINE - this is the item most likely to manufacture a number that does not
survive, so it is fenced in hard:

  1. IS ONLY. OOS is not opened in this script at all.
  2. ONE KNOB AT A TIME. No grid, no combinations. Five knobs swept
     independently so the result cannot be a combinatorial fluke.
  3. CURVE SHAPE is reported, not just the argmax. A flat curve has no optimum
     to find, and re-fitting it is noise. A curve that is flat to the decimal
     means the knob is not wired at all, which is reported separately.
  4. NOTHING is promoted here. This produces evidence for the owner to rule on.
     A winner may be re-derived on OOS EXACTLY ONCE afterwards and dies if it
     fails there. That step is deliberately not in this file.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_refit_constants.py
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

PINS = {"chop_thresh": 58.0, "atr_high_thresh": 0.65, "sl_buf_atr": 0.01,
        "cooldown_bars": 8, "max_consecutive_losses": 3}
SWEEPS = [
    ("chop_thresh", [40, 48, 54, 58, 62, 68, 74]),
    ("atr_high_thresh", [0.45, 0.55, 0.60, 0.65, 0.70, 0.80]),
    ("sl_buf_atr", [0.0, 0.005, 0.01, 0.02, 0.04, 0.10]),
    ("cooldown_bars", [0, 4, 8, 12, 20]),
    ("max_consecutive_losses", [1, 2, 3, 4, 6]),
]

FLAT_SPREAD = 40.0  # R. below this a curve has no usable optimum.


def chain(candles, flow, min_bars: int, gap: int = 1):
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


def stats(trades):
    closed = [t for t in trades if str(t.get("outcome", "")).lower() != "open"]
    v = [float(t["r_multiple"]) for t in closed if t.get("r_multiple") is not None]
    wins = [x for x in v if x > 0]
    losses = [x for x in v if x <= 0]
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    eq = peak = dd = 0.0
    for x in v:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {"n": len(v), "net": round(sum(v), 2), "dd": round(dd, 2),
            "pf": round(pf, 2) if pf is not None else None}


def main() -> int:
    from exp_tf_family import build_family_module
    from run_experiment import BP, get_data
    from engine.v18_params import SWING
    from experiment_registry import EXPERIMENTS

    sim = build_family_module()
    d = get_data()

    print("=" * 78)
    print("B2 - re-fit the pinned constants.  IS ONLY.  OOS NOT OPENED.")
    print("=" * 78)

    # ---- build the chains ONCE; these knobs are sim-only so they are stable ----
    sw15, c15 = chain(d["c15"], d["f15"], SWING["min_bars_15m"])
    sw10, c10 = chain(d["c1h"], d["f1h"], 10)
    sw20, c20 = chain(d["c1h"], d["f1h"], SWING["min_bars_1h"])
    htf15, c_h = chain(d["c1h"], d["f1h"], 15)

    if c15["fingerprint"] != BASE_FP:
        print("  ABORT: 15m chain %s != A1 freeze %s. Harness is wrong;"
              " nothing below is trustworthy." % (c15["fingerprint"], BASE_FP))
        return 2
    print("  identity gate: 15m chain %s  swings=%d marks=%d  == A1 freeze"
          % (c15["fingerprint"], c15["swings"], c15["marks"]))
    print("  all five knobs are sim-only, so this chain is FIXED across every arm.")
    print()

    bases = {}
    for b in BOOKS:
        cfg = EXPERIMENTS.get(b)
        if not isinstance(cfg, dict):
            continue
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        key = cfg.get("swing") or "sw10"
        bases[b] = (p, {"sw10": sw10, "sw20": sw20, "htf15": htf15}.get(key, sw10))
    if not bases:
        print("  no books resolved")
        return 2

    def total(override):
        tot = 0.0
        per = {}
        for b, (p, sw) in bases.items():
            q = {**p, **override}
            res = sim(d["c1h"], sw, d["c15"], sw15, fine_ltf=d["fine"], **q)
            tr = res["ltf_trades"] if isinstance(res, dict) else res
            s = stats(tr)
            per[b] = s
            tot += s["net"]
        return tot, per

    base_tot, base_per = total({})
    print("  baseline (all pins)  TOTAL IS = %+.1fR over %d books" % (base_tot, len(bases)))
    for b, s in base_per.items():
        print("      %-28s n=%-4d net=%+9.2fR" % (b, s["n"], s["net"]))
    print()

    out = {"stage": "refit_constants", "era": "is",
           "baseline_fingerprint": c15["fingerprint"],
           "baseline_total_is": round(base_tot, 2), "pins": PINS,
           "baseline_per_book": base_per, "knobs": {}}

    for knob, values in SWEEPS:
        print("  ---- %s   (pin %s) ----" % (knob, PINS[knob]))
        rows = []
        for v in values:
            t, per = total({knob: v})
            rows.append((v, t, t - base_tot, per))
        best = max(rows, key=lambda r: r[2])
        spread = max(r[2] for r in rows) - min(r[2] for r in rows)
        ns = {r[0]: r[1] for r in rows}
        flat = max(ns.values()) - min(ns.values()) < 1e-9

        for r in rows:
            mark = "   <== pin" if r[0] == PINS[knob] else ("   <== best" if r[0] == best[0] else "")
            print("      %-8s TOTAL IS %+9.1fR   delta %+8.1fR%s" % (r[0], r[1], r[2], mark))

        if flat:
            shape = "DEAD KNOB - every value gives an identical total, so it is not wired"
            verdict = "not_wired"
        elif spread < FLAT_SPREAD:
            shape = ("FLAT - spread only %.1fR. No optimum to find; re-fitting this is noise."
                     % spread)
            verdict = "flat_keep_pin"
        else:
            n_better = sum(1 for r in rows if r[2] > 0)
            if best[0] == PINS[knob]:
                shape = "PEAKED at the PIN (%+.1fR). Current value already optimal." % best[2]
                verdict = "pin_confirmed"
            else:
                shape = ("PEAKED at %s (%+.1fR); %d of %d values beat the pin"
                         % (best[0], best[2], n_better, len(rows)))
                verdict = "candidate"
        print("      -> %s\n" % shape)

        out["knobs"][knob] = {"pin": PINS[knob], "spread": round(spread, 2),
                              "verdict": verdict,
                              "best_value": best[0], "best_delta": round(best[2], 2),
                              "curve": [{"value": r[0], "total_is": round(r[1], 2),
                                         "delta": round(r[2], 2)} for r in rows]}

    (HERE / "refit_constants_results.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("  wrote %s" % (HERE / "refit_constants_results.json"))

    cand = {k: v for k, v in out["knobs"].items() if v["verdict"] == "candidate"}
    print()
    print("  SUMMARY")
    for k, v in out["knobs"].items():
        print("      %-24s %s" % (k, v["verdict"]))
    if not cand:
        print("  No candidates. Every pin is either confirmed or the knob is dead.")
        print("  Nothing to reveal OOS - which is the good outcome here.")
    else:
        print("  %d candidate(s): %s" % (len(cand), ", ".join(cand)))
        print("  These are NOT promoted. IS-only evidence for the owner to rule on.")
        print("  One OOS reveal each, after a decision - never a sweep on OOS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())