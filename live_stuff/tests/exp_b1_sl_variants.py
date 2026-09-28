"""B1-vs-B2 ENTRY and SL VARIANTS (the user's request, both parts).

PART 1 - B1 entry, descriptive
===============================
The engine enters on B2/flip. B1 is an EARLIER mark, so entering there buys
more of the move at a worse price. There is no engine kwarg for "enter at
B1" (`exp_b1_b2_mode` is a blocking filter on the B2 trigger, not a different
trigger), so this part is measured against the real signal path rather than
by patching the engine: for every trade we locate the actual B1 mark of the
same swing and price the move from the B1 fill to the real exit, under
several stops.

This is a fair comparison because the EXIT is held fixed across variants -
only the entry and the stop change - so the differences are attributable.

PART 2 - SL variants, PATH-TRUE
================================
These are real engine runs, not arithmetic on an existing book: a different
stop changes which trades survive, when they exit, and therefore the whole
path. Variants are the engine's own knobs so nothing is invented:
  baseline            (sl_buf_atr 0.01, the champion setting)
  wider buffer        sl_buf_atr 0.10 / 0.25
  causal SL           exp_causal_sl=1
  pivot trail         exp_pivot_trail=1
Reported per cell: n, net, WR, PF, maxDD, avg/trade, and the same-sign check
across eras. All on the champion and utcsat flat books.

The M2 bucket split from the previous study is NOT repeated here: it was
shown to be a risk-normalisation artefact, and this run is about the book.
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_b1_sl_variants.json"
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
YEARS = {"is": 3.67, "oos": 2.0}
SL_ARMS = (
    ("baseline buf0.01", {}),
    ("buf 0.10", {"sl_buf_atr": 0.10}),
    ("buf 0.25", {"sl_buf_atr": 0.25}),
    ("causal SL", {"exp_causal_sl": 1}),
    ("pivot trail", {"exp_pivot_trail": 1}),
)

def b1_part(scope, name, key, data, c15, ts15, by_i, trades):
    """Price the trade as if it had been entered at the B1 mark instead.

    Exit is held at the real one, so the only things that change are the
    entry price and the stop. Stops tried: the swing low (what the engine
    uses), a fixed 1.0 and 1.5 ATR15 buffer above it, and a fixed 1.0 ATR
    stop measured from the B1 fill.
    """
    from exp_thesis_swing_geometry_deep import first_mark
    import bisect as _b

    def atr_at(i, lb=15):
        if i < lb:
            return None
        trs = []
        for k in range(i - lb + 1, i + 1):
            c, pc = c15[k], c15[k - 1]["close"]
            trs.append(max(float(c["high"]) - float(c["low"]),
                           abs(float(c["high"]) - pc),
                           abs(float(c["low"]) - pc)))
        return sum(trs) / lb

    out = []
    for t in trades:
        s = by_i.get(int(t.get("swing_no", -1)))
        if not s:
            continue
        e_idx = _b.bisect_right(ts15, int(t["entry_ts"])) - 1
        m = first_mark(s, "B1", e_idx)
        if not m:
            continue
        mi = int(m.get("idx", -1))
        if not (0 <= mi < len(c15)):
            continue
        atr = atr_at(mi)
        if not atr or atr <= 0:
            continue
        b1_px = float(c15[mi]["close"])
        d = 1 if t["dir"] == "long" else -1
        move = d * (float(t["exit_price"]) - b1_px)
        swing_low = min(float(s["seg"]["start_px"]), float(s["seg"]["end_px"]))
        risk_low = abs(b1_px - swing_low)
        # DEGENERATE-RISK GUARD. Entering at B1 often puts the fill within a
        # hair of the swing extreme, so |b1_px - swing_low| collapses toward
        # zero and R explodes (an unguarded first pass reported a nonsensical
        # avg +19.4R and net +9700R). Any stop closer than a quarter of ATR is
        # inside the noise and cannot be traded, so those trades are EXCLUDED
        # and counted, never silently averaged in. This is the same
        # near-zero-denominator trap that produced the nonsense R-half column
        # in exp_fs_entry_risk.py.
        if risk_low < 0.25 * atr:
            continue
        rec = {
            "move": move,
            "r_swinglow": move / risk_low,
            "r_atr1": move / atr,
            "r_atr15": move / (1.5 * atr),
        }
        out.append(rec)
    return out


def stat(rs):
    if not rs:
        return None
    return {"n": len(rs), "avg": round(statistics.mean(rs), 3),
            "median": round(statistics.median(rs), 3),
            "net": round(sum(rs), 1),
            "wr": round(100.0 * sum(1 for x in rs if x > 0) / len(rs), 1)}


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  B1-vs-B2 ENTRY (descriptive) + SL VARIANTS (path-true)",
          flush=True)
    print("=" * 100, flush=True)
    from exp_sizing_combo import run as sim_fn
    from exp_5m_confirm import load_book
    from test_experiments_craze import build_module
    from experiment_registry import BP, EXPERIMENTS
    from exp_equity_quality import equity_quality

    sim = build_module()
    payload = {"stage": "b1_sl_variants", "b1": {}, "sl": {}}
    books = {}
    for scope in ("is", "oos"):
        data, _ = load_book(scope)
        c15 = data["c15"]
        ts15 = [int(c["ts"]) for c in c15]
        by_i = {int(s["swing_index"]): s for s in data["sw15"]}
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            base = sim_fn(sim, data, params)
            books[(scope, name)] = (data, params)
            m0 = equity_quality(base, YEARS[scope])
            print(f"\n  [{scope}/{name}] BASE {m0['n']}t {m0['net']:+.1f}R "
                  f"WR {m0['wr']}% PF {m0['pf']} DD {m0['max_dd']} "
                  f"calmar {m0['calmar']}", flush=True)
            # PART 1 - B1
            b1 = b1_part(scope, name, key, data, c15, ts15, by_i, base)
            if b1:
                rec = {"n": len(b1)}
                for f, lbl in (("r_swinglow", "B1 + swing-low SL"),
                               ("r_atr1", "B1 + 1.0 ATR stop"),
                               ("r_atr15", "B1 + 1.5 ATR stop")):
                    v = [r[f] for r in b1 if r[f] is not None]
                    rec[lbl] = stat(v)
                payload["b1"][f"{scope}/{name}"] = rec
                print(f"    B1 entry found for {len(b1)}/{len(base)} trades",
                      flush=True)
                for lbl in ("B1 + swing-low SL", "B1 + 1.0 ATR stop",
                            "B1 + 1.5 ATR stop"):
                    s = rec[lbl]
                    if s:
                        print(f"      {lbl:<20} n{s['n']:>3} "
                              f"avg{s['avg']:>+7.3f} med{s['median']:>+7.3f} "
                              f"net{s['net']:>+8.1f} WR{s['wr']:>5.1f}%",
                              flush=True)
                print(f"      (excluded {len(base)-len(b1)} trades whose B1 "
                      f"fill sat within 0.25xATR of the swing extreme - "
                      f"degenerate stop)", flush=True)
                print(f"      (BASE for reference: "
                      f"avg {m0['net']/m0['n']:+.3f} over {m0['n']}t)",
                      flush=True)
            # PART 2 - SL variants, path-true
            print(f"    -- SL variants (path-true) --", flush=True)
            for arm, override in SL_ARMS:
                arm_tr = sim_fn(sim, data, {**params, **override})
                m = equity_quality(arm_tr, YEARS[scope])
                d = round(m["net"] - m0["net"], 1)
                payload["sl"][f"{scope}/{name}/{arm}"] = {
                    "n": m["n"], "net": m["net"], "wr": m["wr"],
                    "pf": m["pf"], "max_dd": m["max_dd"],
                    "calmar": m["calmar"], "d_net": d,
                    "d_dd": round(m0["max_dd"] - m["max_dd"], 1)}
                print(f"      {arm:<18} {m['n']:>4}t {m['net']:>+8.1f}R "
                      f"({d:+7.1f})  WR {m['wr']:>5}%  PF {m['pf']:>6}  "
                      f"DD {m['max_dd']:>5.1f} ({m0['max_dd']-m['max_dd']:+.1f})"
                      f"  cal {m['calmar']:>6.3f}", flush=True)
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
