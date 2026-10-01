"""Phase 1 — revenge re-entry at ORIGINAL ENTRY LEVEL (descriptive, identity-gated).

User idea (2026-09-25): after a loss, re-enter SAME direction when price comes
back to the ORIGINAL entry price — "the level that stopped us out gets
revisited; re-enter there with the ORIGINAL SL." Distinct from SL-candle
reclaim (24.38: level = exit-candle high/low, re-SL = recomputed) and from
dip->reclaim (24.34: level = entry, but SL first must dip 0.10-0.50R deep).
Here: no depth requirement, level = original entry, SL = original SL.

Pre-registered (frozen before run):
  eligibility : every baseline loss (r < 0)
  level       : original entry price
  trigger A   : TOUCH — first 1m bar after exit fill crossing original entry
                in original direction; fill = max(level, open) long /
                min(level, open) short (gap-aware stop)
  trigger B   : CLOSE — first 15m close beyond original entry after exit
                candle; fill = that close
  wait        : exit_ts + 240 min, else timeout
  re-SL       : ORIGINAL SL (unchanged); risk = fill - originalSL with engine
                guards (risk > 0, risk >= 0.0005*fill) else invalid
  same-bar    : fill bar also touching re-SL => SL first (conservative)
  proxy exit  : 1m first-passage SL vs +1R/+2R/+3R (no trail, 16-day cap)
  binary net  : +1R-before-SL win = +1R, else -1R; cost 0.125% notional in R
                (funding NOT in proxy — caveat)
  gate        : Phase 2 only if binary net > 0 on BOTH eras in >=1 config x
                >=1 trigger; else DEAD at Phase 1.
Configs: champion_multi_sw10 + age10_dirmatch_swingpause_single_sw10, IS+OOS.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_revenge_walk.py
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_4_new_concepts import load_fine_1m, load_unseen
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = ROOT / "backtest/tests/_revenge_walk_results.json"
CONFIGS = (
    "champion_multi_sw10",
    "age10_dirmatch_swingpause_single_sw10",
)
WAIT_MIN = 240
HORIZON_15M = 96 * 16
COST_PCT = 0.00055 * 2 + 0.00005 + 0.00010


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


def find_fill(trade, c15, cts15, fine, fine_ts, mode):
    """Revenge fill at ORIGINAL entry level. Returns dict or None."""
    direction = 1 if trade["dir"] == "long" else -1
    exit_ts = int(trade["exit_ts"])
    level = float(trade["entry_price"])
    resl = float(trade["sl"])
    deadline = exit_ts + WAIT_MIN * 60

    if mode == "touch":
        k = bisect.bisect_right(fine_ts, exit_ts)
        end = bisect.bisect_right(fine_ts, deadline)
        fill_ts = fill_px = None
        c = None
        while k < end and k < len(fine):
            c = fine[k]
            hi, lo = float(c["high"]), float(c["low"])
            if direction > 0 and hi >= level:
                fill_px, fill_ts = max(level, float(c["open"])), int(c["ts"])
                break
            if direction < 0 and lo <= level:
                fill_px, fill_ts = min(level, float(c["open"])), int(c["ts"])
                break
            k += 1
        if fill_ts is None:
            return {"bucket": "timeout"}
        lo1, hi1 = float(c["low"]), float(c["high"])
        samebar = lo1 <= resl if direction > 0 else hi1 >= resl
    else:
        ei = bisect.bisect_right(cts15, exit_ts) - 1
        if ei < 0 or ei >= len(c15):
            return None
        j = ei + 1
        end_j = min(ei + 1 + HORIZON_15M, len(c15))
        fill_ts = fill_px = None
        while j < end_j and cts15[j] <= deadline:
            cl = float(c15[j]["close"])
            if direction > 0 and cl >= level:
                fill_px, fill_ts = cl, int(cts15[j])
                break
            if direction < 0 and cl <= level:
                fill_px, fill_ts = cl, int(cts15[j])
                break
            j += 1
        if fill_ts is None:
            return {"bucket": "timeout"}
        samebar = False

    if direction > 0:
        risk = fill_px - resl
    else:
        risk = resl - fill_px
    if risk <= 0 or risk < 0.0005 * fill_px:
        return {"bucket": "invalid"}
    return {"bucket": "filled", "fill_ts": fill_ts, "fill_px": fill_px,
            "resl": resl, "risk": risk, "samebar_sl": samebar, "mode": mode}


def first_passage(fill, direction, fine, fine_ts):
    fill_px, resl, risk = fill["fill_px"], fill["resl"], fill["risk"]
    if fill.get("samebar_sl"):
        return {"outcome": "sl", "maxr": 0.0, "bars": 0}
    if fill["mode"] == "touch":
        k = bisect.bisect_right(fine_ts, fill["fill_ts"])
    else:
        k = bisect.bisect_left(fine_ts, fill["fill_ts"] + 900)
    end_ts = fill["fill_ts"] + HORIZON_15M * 900
    reached = 0.0
    end = bisect.bisect_right(fine_ts, min(end_ts, fine_ts[-1]))
    for j in range(k, end):
        c = fine[j]
        hi, lo = float(c["high"]), float(c["low"])
        if direction > 0:
            sl_hit, fav = lo <= resl, (hi - fill_px) / risk
        else:
            sl_hit, fav = hi >= resl, (fill_px - lo) / risk
        if sl_hit:
            return {"outcome": "sl", "maxr": reached, "bars": j - k}
        reached = max(reached, fav)
        if reached >= 3.0:
            return {"outcome": "r3", "maxr": reached, "bars": j - k}
    return {"outcome": "unresolved" if reached < 1.0 else "r%s" % reached,
            "maxr": reached, "bars": end - k}


def med(xs):
    s = sorted(x for x in xs if x is not None)
    return s[len(s) // 2] if s else None


def analyze_scope(scope, sim, data):
    fine = data["fine"]
    fine_ts = [int(c["ts"]) for c in fine]
    c15 = data["c15"]
    cts15 = [int(c["ts"]) for c in c15]
    result = {"scope": scope, "configs": {}}
    print(f"\n=== revenge re-entry descriptive [{scope.upper()}] ===", flush=True)
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=fine, **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        losses = [t for t in trades if float(t.get("r_multiple") or 0.0) < 0]
        print(f"\n  {key}: trades={len(trades)} losses={len(losses)}", flush=True)
        print(f"    {'mode':>6} {'fill':>5} {'to':>4} {'inv':>4} {'r1win':>5} "
              f"{'sl1':>5} {'r2+':>4} {'r3':>4} {'gross*':>8} {'net*':>8} "
              f"{'waitMed':>7}", flush=True)
        rows = {}
        for mode in ("touch", "close"):
            buckets = {"timeout": 0, "invalid": 0}
            fills = []
            for t in losses:
                f = find_fill(t, c15, cts15, fine, fine_ts, mode)
                if f is None:
                    continue
                if f["bucket"] != "filled":
                    buckets[f["bucket"]] += 1
                    continue
                direction = 1 if t["dir"] == "long" else -1
                f["fp"] = first_passage(f, direction, fine, fine_ts)
                f["trade"] = t
                fills.append(f)
            wins = [f for f in fills if f["fp"]["maxr"] >= 1.0]
            n_sl = sum(1 for f in fills
                       if f["fp"]["outcome"] == "sl" and f["fp"]["maxr"] < 1.0)
            n_r3 = sum(1 for f in fills if f["fp"]["outcome"] == "r3")
            gross = len(wins) * 1.0 - n_sl * 1.0
            cost = sum(COST_PCT / (f["risk"] / f["fill_px"]) for f in fills
                       if f["risk"] > 0)
            net = gross - cost
            wait_med = med([(f["fill_ts"] - int(f["trade"]["exit_ts"])) / 60
                            for f in fills])
            print(f"    {mode:>6} {len(fills):>5} {buckets['timeout']:>4} "
                  f"{buckets['invalid']:>4} {len(wins):>5} {n_sl:>5} "
                  f"{sum(1 for f in fills if f['fp']['maxr'] >= 2.0 and f['fp']['outcome'] != 'r3'):>4} "
                  f"{n_r3:>4} {gross:>+8.1f} {net:>+8.1f} "
                  f"{(wait_med if wait_med is not None else -1):>7}", flush=True)
            rows[mode] = {
                "losses": len(losses), "filled": len(fills),
                "timeout": buckets["timeout"], "invalid": buckets["invalid"],
                "binary_wins": len(wins), "binary_losses_sl": n_sl,
                "r3": n_r3,
                "gross_proxy": round(gross, 4),
                "net_proxy": round(net, 4),
                "wait_med_min": wait_med,
                "per_fill_net": [round(
                    (1.0 if f["fp"]["maxr"] >= 1.0 else -1.0)
                    - COST_PCT / (f["risk"] / f["fill_px"]), 4)
                    for f in fills],
            }
        result["configs"][key] = rows
    return result


def main():
    t0 = time.time()
    print("=" * 104, flush=True)
    print("  PHASE 1 — REVENGE RE-ENTRY @ ORIGINAL ENTRY (descriptive) — IS + OOS", flush=True)
    print("  original entry level; original SL; touch/close; 240min; binary 1R proxy", flush=True)
    print("=" * 104, flush=True)

    sim = build_module()
    data_is = load_scope("is")
    data_oos = load_scope("oos")
    res_is = analyze_scope("is", sim, data_is)
    res_oos = analyze_scope("oos", sim, data_oos)

    print("\n=== GATE (pre-registered: binary net > 0 on BOTH eras "
          "in >=1 config x >=1 mode => Phase 2) ===", flush=True)
    gate = {}
    for key in CONFIGS:
        for mode in ("touch", "close"):
            nis = res_is["configs"][key][mode]["net_proxy"]
            noos = res_oos["configs"][key][mode]["net_proxy"]
            ok = nis > 0 and noos > 0
            gate[f"{key}|{mode}"] = {"net_is": nis, "net_oos": noos,
                                     "phase2": ok}
            print(f"  {key:38} {mode:>6}  IS {nis:+8.1f}  OOS {noos:+8.1f}"
                  f"  -> {'PHASE 2' if ok else 'no'}", flush=True)
    phase2 = any(v["phase2"] for v in gate.values())
    print(f"  => Phase 2 warranted: {phase2}", flush=True)

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "study": "revenge re-entry at original entry (descriptive, binary 1R proxy)",
        "wait_min": WAIT_MIN, "cost_pct": COST_PCT, "configs": list(CONFIGS),
        "gate": gate, "phase2_warranted": phase2,
        "caveats": [
            "proxy: fixed 1R target first-passage, NO trail, funding not in cost",
            "eligibility = all baseline losses (r<0)",
            "level = original entry price; re-SL = original SL (unchanged)",
            "conservative same-bar: fill bar also touching SL => SL first",
            "5th reclaim-adjacent family; distinct from dip->reclaim (depth req) "
            "and SL-candle reclaim (exit-candle level)",
        ],
        "is": res_is, "oos": res_oos,
        "elapsed_sec": round(time.time() - t0, 2),
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
