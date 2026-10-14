"""
B2 v2 - re-fit the pinned constants, PER BOOK. IS ONLY. OOS NOT OPENED.

WHY v2

v1 swept one value across all five books at once while the baseline arm let each
book sit at its OWN pin. That is not a comparison. It is visibly wrong here:

    fsent_champ_long_mcloff   has its own max_consecutive_losses = 0

So in v1's baseline arm mcloff ran at 0, and in every sweep arm it ran at the
swept value. The reported delta for that knob mixed 'the knob changed' with 'mcloff
left its own pin'. The mcl column of v1 is therefore not interpretable and is
discarded, not caveated.

v2 sweeps each book INDEPENDENTLY around that book's own pin, holding the other
four exactly where they are. The question changes shape as a result: not "what
single value is best across the portfolio" but "is each book's own pin still the
right value for THAT BOOK". That is the question the owner actually asked when the
pins were set, and the only version whose per-book answer transfers.

WHAT THIS DOES NOT DO

  - No grid, no combinations. One knob, one book at a time.
  - OOS is never opened here.
  - Nothing is promoted. This is evidence for the owner to rule on.

THE DEAD-KNOB FINDING, WHICH v2 REPORTS PER BOOK

All five books run mode="atr_high", not mode="b2_vs_flip_chop". In atr_high mode
chop_thresh is never read - v18_params.py line 65 says of atr_high_thresh:
"(unused in b2_vs_flip_chop, kept for sweep parity)", and chop_thresh is likewise
inert for this mode. Four of the five book configs still carry a chop_thresh value
they never use. v2 prints each book's OWN pin and flags the inert ones rather than
letting a shared pin-list imply the books are chop-filtered when they are not.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\..\\backend\\venv\\Scripts\\python.exe -u exp_refit_per_book.py
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

# candidate grid per knob; mcl extended past v1's top because v1's best sat on
# the boundary of the grid, which means the search stopped before the turnover.
GRID = {
    "chop_thresh": [40, 48, 54, 58, 62, 68, 74],
    "atr_high_thresh": [0.45, 0.55, 0.60, 0.65, 0.70, 0.80],
    "sl_buf_atr": [0.0, 0.005, 0.01, 0.02, 0.04, 0.10],
    "cooldown_bars": [0, 4, 8, 12, 20],
    # 8 and 12 added: v1 rose monotonically to its top value, so the optimum was
    # never bracketed. An unbracketed "best" is a search artefact, not a finding.
    "max_consecutive_losses": [0, 1, 2, 3, 4, 6, 8, 12],
}
INERT_IN_ATR_HIGH = {"chop_thresh"}  # mode="atr_high" never reads these
FLAT_SPREAD = 40.0


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

    print("=" * 92)
    print("B2 v2 - re-fit per book.  IS ONLY.  OOS NOT OPENED.")
    print("=" * 92)

    sw15, c15 = chain(d["c15"], d["f15"], SWING["min_bars_15m"])
    sw10, c10 = chain(d["c1h"], d["f1h"], 10)
    sw20, c20 = chain(d["c1h"], d["f1h"], SWING["min_bars_1h"])
    htf15, c_h = chain(d["c1h"], d["f1h"], 15)
    if c15["fingerprint"] != BASE_FP:
        print("  ABORT: 15m chain %s != A1 freeze %s." % (c15["fingerprint"], BASE_FP))
        return 2
    print("  identity gate: 15m chain %s  swings=%d marks=%d  == A1 freeze"
          % (c15["fingerprint"], c15["swings"], c15["marks"]))
    print()

    books = {}
    for b in BOOKS:
        cfg = EXPERIMENTS.get(b)
        if not isinstance(cfg, dict):
            continue
        p = {**BP, **cfg["params"]}
        p.setdefault("exp_partial_r", 0.0)
        key = cfg.get("swing") or "sw10"
        books[b] = {"params": p,
                    "sw": {"sw10": sw10, "sw20": sw20, "htf15": htf15}.get(key, sw10)}
    if not books:
        print("  no books resolved")
        return 2

    def run(b: str, override: dict):
        e = books[b]
        q = {**e["params"], **override}
        res = sim(d["c1h"], e["sw"], d["c15"], sw15, fine_ltf=d["fine"], **q)
        tr = res["ltf_trades"] if isinstance(res, dict) else res
        return stats(tr)

    base = {b: run(b, {}) for b in books}
    base_tot = sum(s["net"] for s in base.values())
    print("  each book at its OWN pin.  TOTAL IS = %+.1fR" % base_tot)
    print()
    print("  %-28s %-9s %-8s %-6s %-4s %-4s %-7s" %
          ("book", "mode", "swing", "chop", "atrhi", "cd", "mcl/sl_buf"))
    for b, e in books.items():
        p = e["params"]
        print("  %-28s %-9s %-8s %-6s %-4s %-4s mcl=%-3s sl=%s" %
              (b, p.get("mode"), EXPERIMENTS.get(b, {}).get("swing"),
               p.get("chop_thresh"), p.get("atr_high_thresh"),
               p.get("cooldown_bars"), p.get("max_consecutive_losses"),
               p.get("sl_buf_atr")))
    print()
    print("  NOTE every book is mode=atr_high. In that mode chop_thresh is never")
    print("  read, so a chop value sitting in the config has no effect at all.")
    print()

    out = {"stage": "refit_per_book", "era": "is",
           "baseline_fingerprint": c15["fingerprint"],
           "baseline_total_is": round(base_tot, 2),
           "baseline_per_book": base, "inert_in_atr_high": sorted(INERT_IN_ATR_HIGH),
           "books": {}}

    summary = {k: {"pin_confirmed": 0, "candidate": 0, "inert": 0, "flat": 0}
               for k in GRID}

    for knob, values in GRID.items():
        print("  ================ %s ================" % knob)
        for b, e in books.items():
            pin = e["params"].get(knob)
            rows = []
            for v in values:
                s = run(b, {knob: v})
                rows.append((v, s["net"], s["net"] - base[b]["net"], s))
            ns = {r[0]: r[1] for r in rows}
            flat = max(ns.values()) - min(ns.values()) < 1e-9
            spread = max(r[2] for r in rows) - min(r[2] for r in rows)
            best = max(rows, key=lambda r: r[2])

            if knob in INERT_IN_ATR_HIGH and flat:
                verdict, tag = "inert", "INERT in atr_high mode - value never read"
                summary[knob]["inert"] += 1
            elif flat:
                verdict, tag = "inert", "value never changes any trade"
                summary[knob]["inert"] += 1
            elif spread < FLAT_SPREAD:
                verdict, tag = "flat", "flat (%.1fR spread) - pin is fine, no optimum" % spread
                summary[knob]["flat"] += 1
            elif best[0] == pin:
                verdict, tag = "pin_confirmed", "PIN CONFIRMED (own pin is the argmax)"
                summary[knob]["pin_confirmed"] += 1
            else:
                verdict, tag = "candidate", "candidate %s (%+.1fR vs own pin)" % (best[0], best[2])
                summary[knob]["candidate"] += 1

            print("    %-28s own pin %-6s  base %+9.1fR" % (b, pin, base[b]["net"]))
            for r in rows:
                mk = "  <== own pin" if r[0] == pin else ("  <== best" if r[0] == best[0] else "")
                print("        %-8s %+9.1fR   delta %+8.1fR%s" % (r[0], r[1], r[2], mk))
            print("        -> %s" % tag)
            out["books"].setdefault(knob, {})[b] = {
                "own_pin": pin, "verdict": verdict, "spread": round(spread, 2),
                "best_value": best[0], "best_delta": round(best[2], 2),
                "curve": [{"value": r[0], "net": round(r[1], 2),
                           "delta": round(r[2], 2)} for r in rows]}
            print()

    out["summary"] = summary
    (HERE / "refit_per_book_results.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    print("  ==================== SUMMARY (per book) ====================")
    print("  %-24s %-14s %-11s %-7s %-6s" % ("knob", "pin confirmed", "candidate", "inert", "flat"))
    for k, s in summary.items():
        print("  %-24s %-14d %-11d %-7d %-6d" % (k, s["pin_confirmed"], s["candidate"],
                                                 s["inert"], s["flat"]))
    print()
    print("  wrote %s" % (HERE / "refit_per_book_results.json"))
    print("  OOS NOT OPENED. Any candidate earns one OOS reveal, after the owner")
    print("  rules on it - never a sweep on OOS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())