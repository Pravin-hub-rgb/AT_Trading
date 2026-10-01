"""Death-path + parent-state loss autopsy (2026-09-24).

NEW dimensions not covered by prior autopsies (wage, volume, fast-death, era,
forensics-MFE, parent-final-outcome):

  1. DEATH-PATH taxonomy of losses (path shape, peak timing, recovery):
     - instant / fade / trail-giveback / deep-then-trail
     - time-to-peak vs time-to-death
     - did price retest entry after first touch of +0.5R?

  2. PARENT UNREALIZED R at LTF entry (CAUSAL — knowable live):
     parent's current unrealized R when we enter the LTF, using only
     parent entry/sl + price at LTF entry. exp43 used parent FINAL outcome
     (lookahead); this is the causal handle.

  3. PARENT DISTANCE-TO-SL at LTF entry (CAUSAL):
     how close is the covering HTF window to its own stop when we enter?

  4. IN-WINDOW PRIOR LTF LOSSES (CAUSAL — our own prior exits):
     count of prior LTF losses inside the SAME parent window before this entry.

  5. ENTRY MICROSTRUCTURE (causal at entry bar close):
     body % of range, upper/lower wick ratio, gap vs prior close.

Read-only. Identity-gated. Champion multi + lb30 w0 (both lanes).
Run: python backtest/tests/exp_deathpath_autopsy.py
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from run_experiment import get_data, BP, net_r, identity_gate
import test_experiments_craze as craze
from experiment_registry import EXPERIMENTS
from src.btc.engines.htf_ltf import v18_streak_halt as shipped_mod
from test_experiments_craze import BASE as CRAZE_BASE, stats

OUT = ROOT / "backtest/tests/_deathpath_autopsy_results.json"


def bucket_table(name, rows, key_fn, bins):
    print(f"\n  -- {name} --", flush=True)
    hdr = (f"  {'bin':<18} {'n':>4} {'W':>4} {'L':>4} {'NET':>8} {'WR%':>6} "
           f"{'avgR':>7} {'fast%':>6} {'mfeMed':>7} {'mfeAvg':>7}")
    print(hdr, flush=True)
    for b in bins:
        sub = [r for r in rows if key_fn(r) == b]
        if not sub:
            print(f"  {b:<18} n=0", flush=True)
            continue
        w = sum(1 for r in sub if r["win"])
        l = len(sub) - w
        net = sum(r["r"] for r in sub)
        wr = 100.0 * w / len(sub)
        avg = net / len(sub)
        fastp = 100.0 * sum(1 for r in sub if r["fast"]) / len(sub)
        mfes = sorted(r["mfe"] for r in sub)
        mfe_med = mfes[len(mfes) // 2]
        mfe_avg = sum(mfes) / len(mfes)
        print(f"  {b:<18} {len(sub):4d} {w:4d} {l:4d} {net:+8.1f} {wr:5.1f}% "
              f"{avg:+7.3f} {fastp:5.1f}% {mfe_med:+7.2f} {mfe_avg:+7.2f}",
              flush=True)


def enrich_path(trade, fine, fine_ts):
    entry = float(trade["entry_price"])
    sl = float(trade["sl"])
    direction = 1 if trade["dir"] == "long" else -1
    risk = abs(entry - sl)
    start = bisect.bisect_left(fine_ts, int(trade["entry_ts"]) + 900)
    end = bisect.bisect_right(fine_ts, int(trade.get("exit_ts") or fine_ts[-1]))
    if risk <= 0 or start >= end:
        return None
    # walk fine bars: MFE/MAE + peak bar index + first +0.5R bar + retest
    mfe = mae = 0.0
    peak_k = 0  # offset from start
    first_05 = None
    saw_half = False
    retested_after_half = False
    exit_r = float(trade.get("r_multiple") or 0.0)
    for k in range(start, end):
        c = fine[k]
        hi, lo = float(c["high"]), float(c["low"])
        if direction > 0:
            fav = (hi - entry) / risk
            adv = (entry - lo) / risk
        else:
            fav = (entry - lo) / risk
            adv = (hi - entry) / risk
        if fav > mfe:
            mfe = fav
            peak_k = k - start
        if adv > mae:
            mae = adv
        if not saw_half and fav >= 0.5:
            saw_half = True
            first_05 = k - start
        elif saw_half and not retested_after_half:
            # after reaching +0.5R, did we come back near entry (fav low)?
            if direction > 0 and (entry - lo) / risk <= 0.15:
                retested_after_half = True
            elif direction < 0 and (hi - entry) / risk <= 0.15:
                retested_after_half = True
    hold = end - start
    time_to_peak = peak_k
    time_frac_peak = peak_k / max(hold, 1)
    # death path class (losses only classified; wins get "win")
    if exit_r > 0:
        path = "win"
    elif mfe < 0.25:
        path = "instant"        # never really worked
    elif mfe < 0.75:
        path = "fade"           # small bounce then death
    elif time_frac_peak < 0.4 and mfe >= 1.0:
        path = "early-peak"     # peaked early, trailed back
    else:
        path = "trail-giveback" # meaningful MFE, gave it back
    return {
        "mfe": mfe, "mae": mae, "hold": hold,
        "peak_k": peak_k, "time_frac_peak": time_frac_peak,
        "first_05": first_05, "retest_after_half": retested_after_half,
        "path": path, "exit_r": exit_r,
    }


def make_ivs(htf_list):
    iv = []
    for t in htf_list:
        if t.get("outcome") == "open":
            continue
        iv.append((
            int(t["entry_ts"]),
            int(t["exit_ts"]),
            1 if t["dir"] == "long" else -1,
            float(t["entry_price"]),
            float(t["sl"]),
            float(t.get("r_multiple") or 0.0),
        ))
    iv.sort()
    return iv, [w[0] for w in iv]


def find_parent(iv, starts, ts, td):
    j = bisect.bisect_right(starts, ts) - 1
    if j >= 0 and iv[j][0] < ts <= iv[j][1] and iv[j][2] == td:
        return iv[j]
    return None


def parent_state(parent, entry_px):
    """Causal parent state at LTF entry: unrealized R + distance-to-sl in R."""
    if parent is None:
        return None, None
    p_entry, _pend, pdir, p_px, p_sl, _pr = parent
    hrisk = abs(p_px - p_sl)
    if hrisk <= 0:
        return None, None
    unreal = (entry_px - p_px) * pdir / hrisk
    # distance to parent SL in R units (positive = still away from stop)
    if pdir > 0:
        dist_sl = (entry_px - p_sl) / hrisk
    else:
        dist_sl = (p_sl - entry_px) / hrisk
    return unreal, dist_sl


def microstructure(c15, idx):
    if idx < 1 or idx >= len(c15):
        return None
    c, prev = c15[idx], c15[idx - 1]
    o, h, l, cl = float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"])
    rng = h - l
    if rng <= 0:
        return None
    body = abs(cl - o) / rng
    mid = (h + l) / 2.0
    upper = (h - max(o, cl)) / rng
    lower = (min(o, cl) - l) / rng
    gap = (o - float(prev["close"])) / float(prev["close"]) * 100.0 if float(prev["close"]) else 0.0
    return {"body": body, "upper": upper, "lower": lower, "gap_pct": gap}


def analyze_lane(label, out, data, fine, fine_ts, c15, ts15, sw_list):
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    htf_f = out.get("htf_trades") if isinstance(out, dict) else []
    htf_b = out.get("htf_trades_b2") if isinstance(out, dict) else []
    ivf, sf = make_ivs(htf_f)
    ivb, sb = make_ivs(htf_b)

    # sort trades by entry for in-window prior counting
    trades_sorted = sorted(trades, key=lambda t: int(t["entry_ts"]))

    rows = []
    # track per-parent-window prior loss counts (causal: own prior exits)
    prior_losses_by_window = defaultdict(int)  # key = parent interval start ts
    prior_count_by_window = defaultdict(int)

    for t in trades_sorted:
        ets = int(t["entry_ts"])
        td = 1 if t["dir"] == "long" else -1
        entry_px = float(t["entry_price"])
        r = float(t.get("r_multiple") or 0.0)
        win = r > 0
        bars = int(t.get("bars_held") or 0)
        fast = bars < 12
        regime = t.get("htf_regime") or ""

        # find parent
        if regime in ("flip", "b2"):
            parent = find_parent(*((ivf, sf) if regime == "flip" else (ivb, sb)), ets, td)
        else:
            parent = find_parent(ivf, sf, ets, td) or find_parent(ivb, sb, ets, td)

        unreal, dist_sl = parent_state(parent, entry_px)
        parent_key = parent[0] if parent else None
        # prior losses in this window BEFORE this trade (causal)
        n_prior = prior_count_by_window[parent_key] if parent_key is not None else 0
        n_prior_loss = prior_losses_by_window[parent_key] if parent_key is not None else 0
        if parent_key is not None:
            prior_count_by_window[parent_key] += 1
            if not win:
                prior_losses_by_window[parent_key] += 1

        # entry bar index
        e_idx = bisect.bisect_left(ts15, ets)
        micro = microstructure(c15, e_idx) if 0 <= e_idx < len(c15) else None

        p = enrich_path(t, fine, fine_ts)
        if p is None:
            continue

        wage_h = (ets - parent[0]) / 3600.0 if parent else None
        ext_r = None
        if parent and abs(parent[4] - parent[3]) > 0:
            ext_r = (entry_px - parent[3]) * parent[2] / abs(parent[4] - parent[3])

        rows.append({
            "r": r, "win": win, "fast": fast, "bars": bars,
            "path": p["path"], "mfe": p["mfe"], "mae": p["mae"],
            "hold": p["hold"], "peak_k": p["peak_k"],
            "tfrac": p["time_frac_peak"],
            "retest": p["retest_after_half"],
            "first_05": p["first_05"],
            "unreal": unreal, "dist_sl": dist_sl,
            "n_prior": n_prior, "n_prior_loss": n_prior_loss,
            "wage_h": wage_h, "ext_r": ext_r,
            "kind": t.get("break_kind") or "?",
            "regime": regime,
            "hour": (ets % 86400) // 3600,
            "body": micro["body"] if micro else None,
            "upper": micro["upper"] if micro else None,
            "lower": micro["lower"] if micro else None,
            "gap": micro["gap_pct"] if micro else None,
        })

    losses = [x for x in rows if not x["win"]]
    wins = [x for x in rows if x["win"]]
    print(f"\n  === LANE {label}: n={len(rows)} loss={len(losses)} win={len(wins)} "
          f"NET={sum(x['r'] for x in rows):+.1f} ===", flush=True)
    if not rows:
        return rows

    # ---- 1. Death-path taxonomy ----
    print("\n  [1] DEATH-PATH taxonomy (all trades)", flush=True)
    paths = sorted(set(x["path"] for x in rows))
    bucket_table("path class", rows, lambda x: x["path"], paths)
    print("\n  loss path detail (MFE/MAE/hold/peak-timing):", flush=True)
    print(f"  {'path':<16} {'n':>4} {'NET':>8} {'mfeAvg':>7} {'maeAvg':>7} "
          f"{'holdMed':>7} {'tPeak%':>6} {'retest%':>7} {'f05bar':>6}", flush=True)
    for pth in paths:
        sub = [x for x in rows if x["path"] == pth]
        if not sub:
            continue
        holds = sorted(x["hold"] for x in sub)
        f05s = sorted(x["first_05"] for x in sub if x["first_05"] is not None)
        retestp = 100.0 * sum(1 for x in sub if x["retest"]) / len(sub)
        print(f"  {pth:<16} {len(sub):4d} {sum(x['r'] for x in sub):+8.1f} "
              f"{sum(x['mfe'] for x in sub)/len(sub):+7.2f} "
              f"{sum(x['mae'] for x in sub)/len(sub):+7.2f} "
              f"{holds[len(holds)//2]:7.0f} "
              f"{100.0*sum(x['tfrac'] for x in sub)/len(sub):5.0f}% "
              f"{retestp:6.0f}% "
              f"{(f05s[len(f05s)//2] if f05s else -1):6.0f}", flush=True)

    # ---- 2. Parent unrealized R at entry (CAUSAL) ----
    print("\n  [2] PARENT UNREALIZED R at LTF entry (CAUSAL)", flush=True)
    ubins = ["a:<-0.5", "b:-0.5-0", "c:0-0.5", "d:0.5-1.5", "e:1.5+", "z:none"]

    def ukey(x):
        u = x["unreal"]
        if u is None:
            return "z:none"
        if u < -0.5:
            return "a:<-0.5"
        if u < 0:
            return "b:-0.5-0"
        if u < 0.5:
            return "c:0-0.5"
        if u < 1.5:
            return "d:0.5-1.5"
        return "e:1.5+"

    bucket_table("parent unrealized R", rows, ukey, ubins)

    # also: skip-if-parent-underwater candidate
    print("\n  candidate: skip if parent unrealized < 0 (causal):", flush=True)
    keep = [x for x in rows if x["unreal"] is None or x["unreal"] >= 0]
    cut = [x for x in rows if x["unreal"] is not None and x["unreal"] < 0]
    print(f"    keep n={len(keep)} NET={sum(x['r'] for x in keep):+.1f} "
          f"cut n={len(cut)} NET={sum(x['r'] for x in cut):+.1f} "
          f"delta={sum(x['r'] for x in keep)-sum(x['r'] for x in rows):+.1f}",
          flush=True)
    for thr in (-0.5, -0.3, 0.0, 0.25):
        cut = [x for x in rows if x["unreal"] is not None and x["unreal"] < thr]
        keep = [x for x in rows if x["unreal"] is None or x["unreal"] >= thr]
        dnet = sum(x["r"] for x in keep) - sum(x["r"] for x in rows)
        cut_run = sum(1 for x in cut if x["r"] >= 4)
        print(f"    parent_u < {thr:+.2f}: cut {len(cut)}t "
              f"(NET {sum(x['r'] for x in cut):+.1f}, {cut_run} runners>=4R) "
              f"-> dNET {dnet:+.1f}", flush=True)

    # ---- 3. Parent distance-to-SL (CAUSAL) ----
    print("\n  [3] PARENT DISTANCE-TO-SL at LTF entry (CAUSAL)", flush=True)
    dbins = ["a:<0.3", "b:0.3-0.7", "c:0.7-1.2", "d:1.2-2.0", "e:2.0+", "z:none"]

    def dkey(x):
        d = x["dist_sl"]
        if d is None:
            return "z:none"
        if d < 0.3:
            return "a:<0.3"
        if d < 0.7:
            return "b:0.3-0.7"
        if d < 1.2:
            return "c:0.7-1.2"
        if d < 2.0:
            return "d:1.2-2.0"
        return "e:2.0+"

    bucket_table("parent dist-to-SL (R)", rows, dkey, dbins)
    for thr in (0.3, 0.5, 0.7):
        cut = [x for x in rows if x["dist_sl"] is not None and x["dist_sl"] < thr]
        keep = [x for x in rows if x["dist_sl"] is None or x["dist_sl"] >= thr]
        dnet = sum(x["r"] for x in keep) - sum(x["r"] for x in rows)
        cut_run = sum(1 for x in cut if x["r"] >= 4)
        print(f"    parent_dist < {thr}R: cut {len(cut)}t "
              f"(NET {sum(x['r'] for x in cut):+.1f}, {cut_run} runners>=4R) "
              f"-> dNET {dnet:+.1f}", flush=True)

    # ---- 4. In-window prior losses (CAUSAL) ----
    print("\n  [4] IN-WINDOW PRIOR LTF LOSSES (CAUSAL — own prior exits)", flush=True)
    pbins = ["a:0", "b:1", "c:2+", "z:none"]

    def pkey(x):
        if x["n_prior"] is None:
            return "z:none"
        if x["n_prior_loss"] == 0:
            return "a:0"
        if x["n_prior_loss"] == 1:
            return "b:1"
        return "c:2+"

    bucket_table("prior losses in same parent window", rows, pkey, pbins)

    # also raw prior count (any outcome)
    def rawkey(x):
        n = x["n_prior"]
        if n is None:
            return "z:none"
        if n == 0:
            return "a:0"
        if n == 1:
            return "b:1"
        if n <= 3:
            return "c:2-3"
        return "d:4+"

    bucket_table("prior trades in same window", rows, rawkey,
                 ["a:0", "b:1", "c:2-3", "d:4+", "z:none"])

    # candidate: skip if >=1 prior loss in window
    cut = [x for x in rows if x["n_prior_loss"] is not None and x["n_prior_loss"] >= 1]
    keep = [x for x in rows if x["n_prior_loss"] is None or x["n_prior_loss"] == 0]
    dnet = sum(x["r"] for x in keep) - sum(x["r"] for x in rows)
    cut_run = sum(1 for x in cut if x["r"] >= 4)
    print(f"    skip if prior_loss>=1: cut {len(cut)}t "
          f"(NET {sum(x['r'] for x in cut):+.1f}, {cut_run} runners>=4R) "
          f"-> dNET {dnet:+.1f}", flush=True)

    # ---- 5. Entry microstructure ----
    print("\n  [5] ENTRY MICROSTRUCTURE (causal at entry bar close)", flush=True)
    bucket_table("body % of range",
                 rows,
                 lambda x: "z:none" if x["body"] is None else
                           ("a:<0.25" if x["body"] < 0.25 else
                            "b:0.25-0.5" if x["body"] < 0.5 else
                            "c:0.5-0.75" if x["body"] < 0.75 else "d:0.75+"),
                 ["a:<0.25", "b:0.25-0.5", "c:0.5-0.75", "d:0.75+", "z:none"])
    bucket_table("upper wick (longs entered on high)",
                 rows,
                 lambda x: "z:none" if x["upper"] is None else
                           ("a:<0.2" if x["upper"] < 0.2 else
                            "b:0.2-0.4" if x["upper"] < 0.4 else
                            "c:0.4-0.6" if x["upper"] < 0.6 else "d:0.6+"),
                 ["a:<0.2", "b:0.2-0.4", "c:0.4-0.6", "d:0.6+", "z:none"])
    bucket_table("lower wick (shorts / wick-under)",
                 rows,
                 lambda x: "z:none" if x["lower"] is None else
                           ("a:<0.2" if x["lower"] < 0.2 else
                            "b:0.2-0.4" if x["lower"] < 0.4 else
                            "c:0.4-0.6" if x["lower"] < 0.6 else "d:0.6+"),
                 ["a:<0.2", "b:0.2-0.4", "c:0.4-0.6", "d:0.6+", "z:none"])
    bucket_table("gap vs prior close %",
                 rows,
                 lambda x: "z:none" if x["gap"] is None else
                           ("a:<-0.2" if x["gap"] < -0.2 else
                            "b:-0.2-0" if x["gap"] < 0 else
                            "c:0-0.2" if x["gap"] < 0.2 else "d:0.2+"),
                 ["a:<-0.2", "b:-0.2-0", "c:0-0.2", "d:0.2+", "z:none"])

    # ---- 6. MFE-timing interaction with causal gates ----
    print("\n  [6] LOSS MFE × parent-state (does parent health predict giveback?)", flush=True)
    for label2, pred in [
        ("parent_u<0", lambda x: x["unreal"] is not None and x["unreal"] < 0),
        ("parent_u>=0", lambda x: x["unreal"] is not None and x["unreal"] >= 0),
        ("parent_dist<0.5", lambda x: x["dist_sl"] is not None and x["dist_sl"] < 0.5),
        ("parent_dist>=1", lambda x: x["dist_sl"] is not None and x["dist_sl"] >= 1),
        ("prior_loss>=1", lambda x: (x["n_prior_loss"] or 0) >= 1),
        ("prior_loss=0", lambda x: (x["n_prior_loss"] or 0) == 0),
    ]:
        sub = [x for x in losses if pred(x)]
        if not sub:
            print(f"  {label2:<20} n=0", flush=True)
            continue
        mfes = sorted(x["mfe"] for x in sub)
        print(f"  {label2:<20} n={len(sub):3d} "
              f"NET={sum(x['r'] for x in sub):+7.1f} "
              f"mfeMed={mfes[len(mfes)//2]:+.2f} "
              f"mfeAvg={sum(mfes)/len(mfes):+.2f} "
              f"mfe>=1R={100.0*sum(1 for m in mfes if m>=1)/len(mfes):.0f}% "
              f"instant={100.0*sum(1 for x in sub if x['path']=='instant')/len(sub):.0f}%",
              flush=True)

    # ---- 7. Time-of-day of DEATH (not entry) ----
    print("\n  [7] When do losses actually die? (bars_held quartiles of losses)", flush=True)
    if losses:
        bl = sorted(x["bars"] for x in losses)
        q1, q2, q3 = bl[len(bl)//4], bl[len(bl)//2], bl[3*len(bl)//4]
        print(f"  bars_held quartiles: Q1={q1} Q2={q2} Q3={q3} max={bl[-1]}", flush=True)

    return rows


def main():
    t0 = time.time()
    print("=" * 100)
    print("  DEATH-PATH + PARENT-STATE LOSS AUTOPSY (causal dimensions)")
    print("=" * 100)

    data = get_data()
    identity_gate()
    sim = craze.build_module()
    c15, sw15, c1h, sw10 = data["c15"], data["sw15"], data["c1h"], data["sw10"]
    fine = data["fine"]
    fine_ts = [int(c["ts"]) for c in fine]
    ts15 = [int(c["ts"]) for c in c15]

    # Lane 1: champion multi (production king multi)
    p1 = {**BP, **EXPERIMENTS["champion_multi_sw10"]["params"]}
    p1.setdefault("exp_partial_r", 0.0)
    out1 = sim(c1h, sw10, c15, sw15, fine_ltf=fine, **p1)
    print(f"champion_multi_sw10: {len(out1['ltf_trades'])} trades", flush=True)

    # Lane 2: lb30 w0 (leading single-position candidate)
    p2 = {**BP, "exp31_lb": 30, "ext_stop_r": 1.5}
    out2 = sim(c1h, data["sw20"], c15, sw15, fine_ltf=fine, **p2)
    print(f"lb30_w0: {len(out2['ltf_trades'])} trades", flush=True)

    results = {}
    rows1 = analyze_lane("champion_multi_sw10", out1, data, fine, fine_ts, c15, ts15, sw10)
    rows2 = analyze_lane("lb30_w0", out2, data, fine, fine_ts, c15, ts15, data["sw20"])
    results["champion"] = rows1
    results["lb30"] = rows2

    # cross-lane: any causal feature that looks promising on BOTH?
    print("\n" + "=" * 100)
    print("  CROSS-LANE SUMMARY — causal candidates (dNET if cut)")
    print("=" * 100)
    for name, rows in (("champion", rows1), ("lb30", rows2)):
        if not rows:
            continue
        base = sum(x["r"] for x in rows)
        cands = []
        # parent under water
        for thr in (-0.5, 0.0):
            cut = [x for x in rows if x["unreal"] is not None and x["unreal"] < thr]
            keep_net = sum(x["r"] for x in rows if x["unreal"] is None or x["unreal"] >= thr)
            cands.append((f"parent_u<{thr:+.1f}", keep_net - base, len(cut),
                          sum(1 for x in cut if x["r"] >= 4)))
        for thr in (0.3, 0.5):
            cut = [x for x in rows if x["dist_sl"] is not None and x["dist_sl"] < thr]
            keep_net = sum(x["r"] for x in rows if x["dist_sl"] is None or x["dist_sl"] >= thr)
            cands.append((f"parent_dist<{thr}", keep_net - base, len(cut),
                          sum(1 for x in cut if x["r"] >= 4)))
        cut = [x for x in rows if (x["n_prior_loss"] or 0) >= 1]
        keep_net = sum(x["r"] for x in rows if (x["n_prior_loss"] or 0) == 0)
        cands.append(("prior_loss>=1", keep_net - base, len(cut),
                      sum(1 for x in cut if x["r"] >= 4)))
        cut = [x for x in rows if (x["n_prior_loss"] or 0) >= 2]
        keep_net = sum(x["r"] for x in rows if (x["n_prior_loss"] or 0) < 2)
        cands.append(("prior_loss>=2", keep_net - base, len(cut),
                      sum(1 for x in cut if x["r"] >= 4)))
        # body-heavy entry
        cut = [x for x in rows if x["body"] is not None and x["body"] >= 0.75]
        keep_net = sum(x["r"] for x in rows if x["body"] is None or x["body"] < 0.75)
        cands.append(("body>=0.75", keep_net - base, len(cut),
                      sum(1 for x in cut if x["r"] >= 4)))

        print(f"\n  {name}: base NET {base:+.1f}", flush=True)
        for lab, dnet, ncut, nrun in sorted(cands, key=lambda z: -z[1]):
            flag = " **" if dnet > 5 and nrun <= 3 else ""
            print(f"    {lab:<22} dNET={dnet:+7.1f}  cut={ncut:3d}t "
                  f"runners_lost={nrun}{flag}", flush=True)

    # save compact summary (not full rows — too big)
    def pack(rows):
        out = []
        for x in rows:
            out.append({k: x[k] for k in
                        ("r", "win", "fast", "path", "mfe", "mae", "hold",
                         "unreal", "dist_sl", "n_prior", "n_prior_loss",
                         "body", "upper", "lower", "gap", "wage_h", "ext_r",
                         "kind", "regime")})
        return out
    OUT.write_text(json.dumps(
        {"champion": pack(rows1), "lb30": pack(rows2)}, indent=1), encoding="utf-8")
    print(f"\n  wrote {OUT}", flush=True)
    print(f"(done in {time.time()-t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
