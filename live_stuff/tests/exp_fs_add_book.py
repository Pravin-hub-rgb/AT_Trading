"""BASE vs ARMED - what the FS add actually does to the book, with costs.

THE QUESTION, STATED AS THE USER STATED IT
==========================================
  1x everywhere, no exits. At FS, if the swing bucket is GOOD, add 0.5
  position. What is the base book R, what is the armed book R, and what is
  the delta?

The earlier runs reported "earns +X R" for a selected subset. That is NOT the
book. This run reports the book: base net vs armed net, in R, with the cost
of the extra position charged against it.

COSTS (the earlier runs omitted these, which flattered the add)
==============================================================
`run_experiment._trade_costs` expresses fee + slippage + funding in R,
normalised by the trade's own risk. Because the R scale is risk-normalised,
a 0.5x add costs exactly 0.5 x the base cost - not zero. So the honest
contribution of one add is:

    0.5 * remaining_R  -  0.5 * cost_r

and the add is only worth doing if the first term wins by more than the
second. Ignoring the second term is how a scale-in looks good and then isn't.

ARMS (all reported, no best-of)
==============================
  base       1x, no exits, no adds - the shipped book
  add_M2     add 0.5 when swing magnitude at FS is in the top third
             (this is M2's own rule, applied at the legal moment)
  add_slow   add 0.5 when the swing took unusually long to confirm
             (the `bars_fs` feature that paid in IS)
  add_wide   add 0.5 when swing magnitude is in the top HALF - a looser cut
             in case the tercile is too thin to matter

Reported per cell: n, base net, armed net, DELTA, extra adds placed, cost of
those adds, gross the adds earned, PF, maxDD, and the delta in maxDD. The
delta is the number that matters; everything else is context for it.
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

OUT = ROOT / "live_stuff/tests/_fs_add_book.json"
ADD = 0.5
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
YEARS = {"is": 3.67, "oos": 2.0}


def build(scope, name, key):
    from exp_5m_confirm import load_book
    from exp_tf_family import build_family_module
    from experiment_registry import BP, EXPERIMENTS
    from exp_fs_time_geometry import atr_at_15m
    from run_experiment import net_r
    data, _ = load_book(scope)
    c15 = data["c15"]
    ts15 = [int(c["ts"]) for c in c15]
    by_i = {int(s["swing_index"]): s for s in data["sw15"]}
    sim = build_family_module()
    trades = sim(data["c1h"], data["sw10"], c15, data["sw15"],
                 fine_ltf=data["fine"],
                 **{**BP, **EXPERIMENTS[key]["params"]})["ltf_trades"]
    net_r(trades)                      # populates per-trade cost_r
    rows = []
    for t in trades:
        s = by_i.get(int(t.get("swing_no", -1)))
        base = {"cost_r": float(t.get("cost_r") or 0.0)}
        if not s or s.get("fs_at_idx") is None:
            rows.append(base)
            continue
        fi = int(s["fs_at_idx"])
        if not (0 <= fi < len(c15)):
            rows.append(base)
            continue
        fs_ts = ts15[fi]
        e_ts, x_ts = int(t["entry_ts"]), int(t["exit_ts"])
        if not (e_ts < fs_ts < x_ts):
            rows.append(base)
            continue
        seg = s.get("seg", {})
        if not seg or "end_px" not in seg:
            rows.append(base)
            continue
        atr = atr_at_15m(c15, fi)
        entry, sl = float(t["entry_price"]), float(t["sl"])
        risk = abs(entry - sl)
        if not atr or risk <= 0:
            rows.append(base)
            continue
        d = 1 if t["dir"] == "long" else -1
        r_fs = d * (float(c15[fi]["close"]) - entry) / risk
        base["mag"] = abs(float(seg["end_px"]) - float(seg["start_px"])) / atr
        base["bars_fs"] = (fs_ts - e_ts) // 900
        base["remaining"] = float(t["r_multiple"]) - r_fs
        rows.append(base)
    return trades, rows

def base_metrics(trades, yrs):
    from exp_equity_quality import equity_quality
    return equity_quality(trades, yrs)


def armed_metrics(trades, add_r_list, yrs):
    """The book with an extra 0.5x position folded into selected trades.

    Each add is modelled as extra R on the same trade: +ADD*remaining
    (gross) and -ADD*cost_r (its own fee/slip/funding). Folding the add into
    the trade's own r_multiple keeps the equity curve, PF and drawdown
    correct, because the add rides the same exit.
    """
    out = []
    for t, extra in zip(trades, add_r_list):
        t2 = dict(t)
        if extra:
            t2["r_multiple"] = round(float(t["r_multiple"]) + extra, 6)
        out.append(t2)
    from exp_equity_quality import equity_quality
    return equity_quality(out, yrs), out


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  FS ADD vs BASE - the actual book, with the add's costs charged",
          flush=True)
    print("=" * 100, flush=True)
    payload = {"stage": "fs_add_book", "add": ADD, "cells": {}}
    for scope in ("is", "oos"):
        for name, key in LANES:
            trades, rows = build(scope, name, key)
            yrs = YEARS[scope]
            mb = base_metrics(trades, yrs)
            ok = [r for r in rows if "mag" in r]
            mags = sorted(r["mag"] for r in ok)
            bars = sorted(r["bars_fs"] for r in ok)
            if not ok:
                print(f"  [{scope}/{name}] no actionable trades", flush=True)
                continue
            t1, t2 = mags[len(mags) // 3], mags[2 * len(mags) // 3]
            bh = bars[2 * len(bars) // 3]
            # CONTROL ARM. Every arm above adds to a bucket the feature
            # likes. But the FS-open population has POSITIVE average
            # remaining R regardless of bucket, so adding size anywhere
            # should earn money. If adding to the WORST bucket is also
            # positive, then the feature contributes nothing and the whole
            # delta is just drift - adding size into a move that was going to
            # keep going. That is not selection, and it is not free.
            arms = {
                "CTRL add_BAD (bottom mag)":
                    lambda r: "mag" in r and r["mag"] <= mags[len(mags) // 3],
                "CTRL add_any (all open)":
                    lambda r: "mag" in r,
                "add_M2 (top third mag)":
                    lambda r: "mag" in r and r["mag"] >= t1,
                "add_wide (top half mag)":
                    lambda r: "mag" in r and r["mag"] >= mags[len(mags) // 2],
                "add_slow (bars_fs top third)":
                    lambda r: "bars_fs" in r and r["bars_fs"] >= bh,
            }
            print(f"\n  [{scope}/{name}] BASE {mb['n']}t {mb['net']:+.1f}R "
                  f"WR {mb['wr']}% PF {mb['pf']} DD {mb['max_dd']} "
                  f"| {len(ok)} trades open at FS", flush=True)
            cell = {"base": {k: mb.get(k) for k in
                             ("n", "net", "wr", "pf", "max_dd",
                              "calmar", "net_per_yr", "max_streak")},
                    "n_actionable": len(ok), "arms": {}}
            for arm, pick in arms.items():
                sel = [r for r in rows if pick(r)]
                gross = ADD * sum(r["remaining"] for r in sel)
                cost = ADD * sum(r["cost_r"] for r in sel)
                extra = [0.0] * len(rows)
                for i, r in enumerate(rows):
                    if pick(r):
                        extra[i] = ADD * r["remaining"] - ADD * r["cost_r"]
                ma, _ = armed_metrics(trades, extra, yrs)
                d = round(ma["net"] - mb["net"], 1)
                rec = {"n_adds": len(sel), "gross_R": round(gross, 1),
                       "cost_R": round(cost, 1), "net_of_cost": round(gross - cost, 1),
                       "armed_net": ma["net"], "DELTA": d,
                       "armed_pf": ma["pf"], "armed_dd": ma["max_dd"],
                       "d_dd": round(mb["max_dd"] - ma["max_dd"], 1),
                       "armed_calmar": ma["calmar"]}
                cell["arms"][arm] = rec
                print(f"    {arm:<28} adds {len(sel):>3}  "
                       f"gross {gross:+7.1f}  cost {cost:+6.1f}  "
                       f"net {gross - cost:+7.1f}  book {mb['net']:+.1f} "
                       f"-> {ma['net']:+.1f}  DELTA {d:+7.1f}  "
                       f"DD {mb['max_dd']:.1f}->{ma['max_dd']:.1f} "
                       f"PF {mb['pf']}->{ma['pf']}", flush=True)
            payload["cells"][f"{scope}/{name}"] = cell
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2, default=str) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()
