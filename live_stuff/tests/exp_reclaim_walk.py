"""Phase 1 — dip-then-reclaim entry predicate (descriptive, read-only, identity-gated).

User idea (2026-09-25): do NOT enter at signal close; wait for price to dip
DEEP into the pullback first, then enter only when price re-breaches the entry
level from the other side (dip -> reclaim -> enter at reclaim). SL unchanged.

Pre-registered arms (frozen before run):
  depths  : 0.10R / 0.25R / 0.50R dip required BEFORE reclaim counts
  wait    : 240 min from signal close (same window as Phase B)
  configs : champion_multi_sw10 + age10_dirmatch_swingpause_single_sw10
  scopes  : IS + OOS

Walk logic per trade (conservative OHLC ordering — ambiguity => miss):
  1. setup killed permanently if SL level touched while waiting (baseline
     would already be stopped; reclaim never becomes valid)
  2. armed on first 1m bar with adverse >= depth (bar that also touches SL
     => killed, SL checked first)
  3. reclaim fires only in a bar AFTER arming: long hi >= entry (fill at
     max(entry, open) if open gapped above entry, else entry) / mirror short
  4. no reclaim within window => timeout (miss)
  5. never dipped depth => no_dip (miss — direct runners, shallow pullbacks)
Filled-trade outcome is reported as the ORIGINAL signal's r as a PROXY only
(selectivity read); path-true P&L is Phase 2's job.

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_reclaim_walk.py
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_4_new_concepts import load_fine_1m, load_unseen
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = ROOT / "live_stuff/tests/_reclaim_walk_results.json"
CONFIGS = (
    "champion_multi_sw10",
    "age10_dirmatch_swingpause_single_sw10",
)
DEPTHS = (0.10, 0.25, 0.50)
WAIT_MIN = 240
MONSTER_R = 10.0


def load_scope(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        sw15 = _compute_swings(f15, "continuous", min_bars=SWING["min_bars_15m"])
        sw10 = _compute_swings(f1h, "continuous", min_bars=10)
        return {
            "c15": c15, "sw15": sw15, "c1h": c1h, "sw10": sw10,
            "fine": load_fine_1m(c15[0]["ts"], c15[-1]["ts"]),
        }
    data = get_data()
    identity_gate(data, build_module())
    return data


def walk_reclaim(trade, fine, fine_ts, depth):
    """One trade, one depth: bucket = no_dip | killed | timeout | filled."""
    entry = float(trade["entry_price"])
    sl = float(trade["sl"])
    direction = 1 if trade["dir"] == "long" else -1
    risk = abs(entry - sl)
    if risk <= 0:
        return None
    start = bisect.bisect_left(fine_ts, int(trade["entry_ts"]) + 900)
    deadline = int(trade["entry_ts"]) + WAIT_MIN * 60
    end = bisect.bisect_right(fine_ts, min(deadline, int(fine_ts[-1])))
    if start >= end:
        return {"bucket": "no_dip", "fill_off": None, "arm_off": None}

    armed = False
    arm_off = None
    for k in range(start, end):
        c = fine[k]
        hi, lo = float(c["high"]), float(c["low"])
        op = float(c["open"])
        if direction > 0:
            adv = (entry - lo) / risk
            sl_hit = lo <= sl
            reclaim = hi >= entry
            gap_fill = max(entry, op)
        else:
            adv = (hi - entry) / risk
            sl_hit = hi >= sl
            reclaim = lo <= entry
            gap_fill = min(entry, op)
        off = k - start
        if armed:
            if sl_hit:
                return {"bucket": "killed", "fill_off": None, "arm_off": arm_off}
            if reclaim:
                return {"bucket": "filled", "fill_off": off, "arm_off": arm_off,
                        "fill_px": gap_fill if op != entry else entry}
        else:
            if sl_hit:
                return {"bucket": "killed", "fill_off": None, "arm_off": None}
            if adv >= depth:
                armed = True
                arm_off = off
    return {"bucket": "timeout" if armed else "no_dip",
            "fill_off": None, "arm_off": arm_off}


def med(xs):
    s = sorted(x for x in xs if x is not None)
    return s[len(s) // 2] if s else None


def analyze_scope(scope, sim, data):
    fine = data["fine"]
    fine_ts = [int(c["ts"]) for c in fine]
    result = {"scope": scope, "configs": {}}
    print(f"\n=== dip->reclaim descriptive walk [{scope.upper()}] ===", flush=True)
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=fine, **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        base_monsters ={(t.get("swing_no"), t.get("dir")) for t in trades
                         if float(t.get("r_multiple") or 0) >= MONSTER_R}
        base_net = sum(float(t.get("r_multiple") or 0) for t in trades)
        base_wr = (100.0 * sum(1 for t in trades
                               if float(t.get("r_multiple") or 0) > 0)
                   / len(trades)) if trades else 0.0
        print(f"\n  {key}: n={len(trades)} gross={base_net:+.1f} "
              f"WR={base_wr:.1f}% monsters={len(base_monsters)}", flush=True)
        print(
            f"    {'depth':>6} {'filled':>6} {'fill%':>6} {'fNet*':>8} {'fWR%':>6} "
            f"{'noDip':>5} {'ndNet':>8} {'killed':>6} {'kNet':>8} {'t/o':>5} "
            f"{'toNet':>8} {'mCap':>4} {'mMiss':>5} {'armMed':>6} {'fillMed':>7}",
            flush=True,
        )
        rows = {}
        for depth in DEPTHS:
            buckets = {b: [] for b in ("no_dip", "killed", "timeout", "filled")}
            fills = []
            for t in trades:
                w = walk_reclaim(t, fine, fine_ts, depth)
                if w is None:
                    continue
                r = float(t.get("r_multiple") or 0.0)
                buckets[w["bucket"]].append((t, r, w))
            f = buckets["filled"]
            nd, kd, to = buckets["no_dip"], buckets["killed"], buckets["timeout"]
            f_net = sum(r for _, r, _ in f)
            f_wr = 100.0 * sum(1 for _, r, _ in f if r > 0) / len(f) if f else 0.0
            f_keys = {(t.get("swing_no"), t.get("dir")) for t, _, _ in f}
            m_cap = len(base_monsters & f_keys)
            m_miss = len(base_monsters - f_keys)
            arm_med = med([w["arm_off"] for _, _, w in f])
            fill_med = med([w["fill_off"] for _, _, w in f])
            print(
                f"    {depth:>6.2f} {len(f):>6} "
                f"{100.0 * len(f) / len(trades) if trades else 0:>5.1f}% "
                f"{f_net:>+8.1f} {f_wr:>6.1f} "
                f"{len(nd):>5} {sum(r for _, r, _ in nd):>+8.1f} "
                f"{len(kd):>6} {sum(r for _, r, _ in kd):>+8.1f} "
                f"{len(to):>5} {sum(r for _, r, _ in to):>+8.1f} "
                f"{m_cap:>4} {m_miss:>5} "
                f"{(arm_med if arm_med is not None else -1):>6} "
                f"{(fill_med if fill_med is not None else -1):>7}",
                flush=True,
            )
            rows[str(depth)] = {
                "filled_n": len(f), "filled_r_proxy": round(f_net, 4),
                "filled_wr": round(f_wr, 2),
                "no_dip_n": len(nd), "no_dip_r": round(sum(r for _, r, _ in nd), 4),
                "killed_n": len(kd), "killed_r": round(sum(r for _, r, _ in kd), 4),
                "timeout_n": len(to), "timeout_r": round(sum(r for _, r, _ in to), 4),
                "monsters_captured": m_cap, "monsters_missed": m_miss,
                "arm_wait_med_1m": arm_med, "fill_wait_med_1m": fill_med,
                "filled_winners": sum(1 for _, r, _ in f if r > 0),
                "filled_losses": sum(1 for _, r, _ in f if r <= 0),
                "skipped_monster_ids": sorted(
                    [list(k) for k in (base_monsters - f_keys)],
                    key=lambda z: str(z)),
            }
        result["configs"][key] = rows
    return result


def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  PHASE 1 — DIP->RECLAIM ENTRY PREDICATE (descriptive) — IS + OOS", flush=True)
    print("  depths 0.10/0.25/0.50R, wait 240min, conservative OHLC order, "
          "filled r = ORIGINAL signal r (proxy only)", flush=True)
    print("=" * 104, flush=True)

    sim = build_module()
    data_is = load_scope("is")
    data_oos = load_scope("oos")

    res_is = analyze_scope("is", sim, data_is)
    res_oos = analyze_scope("oos", sim, data_oos)

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "study": "dip->reclaim entry predicate (descriptive; r of filled = proxy)",
        "depths": list(DEPTHS), "wait_min": WAIT_MIN,
        "configs": list(CONFIGS),
        "caveats": [
            "filled r_proxy = original baseline r of that signal; path after a "
            "reclaim fill differs (later entry, trail path changes) — Phase 2 "
            "measures path-true P&L",
            "SL touch while waiting = setup killed permanently (conservative)",
            "same-bar arm+reclaim impossible: reclaim only counted in a later bar",
        ],
        "is": res_is, "oos": res_oos,
        "elapsed_sec": round(time.time() - t0, 2),
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
