"""Winner early-path autopsy (2026-09-25) — descriptive, no gates.

Gap closed: LOSS_AUTOPSY death-path taxonomy covered LOSSES only; winner
tPeak / retest / first-0.5R were computed in exp_deathpath_autopsy but stripped
from pack(). This study reports WINNER early-path shape:

  1. direct vs pullback-first: did price go adverse >=0.10R before +0.5R?
  2. time-to-first +0.5R / +1R (1m bars), peak-at-hold% (tPeak)
  3. MAE before proving (before +0.5R) and before peak
  4. retest-after-half: after +0.5R, came back within 0.15R of entry
  5. retest-zone miss proxy (Phase B): never returned to/below entry after
     start => a wait-for-pullback entry would have MISSED this trade

Read-only. Identity-gated. Configs: champion multi + age10 single, IS + OOS.
Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_winner_path_autopsy.py
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
from run_experiment import get_data, identity_gate, net_r
from test_4_new_concepts import load_fine_1m, load_unseen
from test_experiments_craze import build_module
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = ROOT / "backtest/tests/_winner_path_autopsy_results.json"
CONFIGS = (
    "champion_multi_sw10",
    "age10_dirmatch_swingpause_single_sw10",
)
COHORTS = (
    ("loss", lambda x: x["r"] <= 0),
    ("win_0_4", lambda x: 0 < x["r"] < 4),
    ("win_4_10", lambda x: 4 <= x["r"] < 10),
    ("monster_10+", lambda x: x["r"] >= 10),
    ("winners_all", lambda x: x["r"] > 0),
    ("all", lambda x: True),
)


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


def walk_path(trade, fine, fine_ts):
    """Fine (1m) walk: early-path shape for one trade."""
    entry = float(trade["entry_price"])
    sl = float(trade["sl"])
    direction = 1 if trade["dir"] == "long" else -1
    risk = abs(entry - sl)
    start = bisect.bisect_left(fine_ts, int(trade["entry_ts"]) + 900)
    end = bisect.bisect_right(fine_ts, int(trade.get("exit_ts") or fine_ts[-1]))
    if risk <= 0 or start >= end:
        return None

    mfe = mae = 0.0
    peak_k = 0
    first_05 = None
    first_10 = None
    mae_before_05 = 0.0
    saw_half = False
    saw_one = False
    retested_after_half = False
    adv_before_05 = 0.0
    touched_entry_before_05 = False   # any bar with adverse >= 0 (lo<=entry) before +0.5R
    touch_05_k = None                 # bars from entry to first such touch
    deep_before_05 = False            # adverse >= 0.5R before +0.5R
    touched_entry_ever = False

    for k in range(start, end):
        c = fine[k]
        hi, lo = float(c["high"]), float(c["low"])
        if direction > 0:
            fav = (hi - entry) / risk
            adv = (entry - lo) / risk
        else:
            fav = (entry - lo) / risk
            adv = (hi - entry) / risk
        off = k - start
        if adv >= 0:
            touched_entry_ever = True
            if not saw_half:
                touched_entry_before_05 = True
                if touch_05_k is None:
                    touch_05_k = off
        if not saw_half:
            if adv > mae_before_05:
                mae_before_05 = adv
            if adv >= 0.5:
                deep_before_05 = True
            adv_before_05 = max(adv_before_05, adv)
        if fav > mfe:
            mfe = fav
            peak_k = off
        if adv > mae:
            mae = adv
        if not saw_half and fav >= 0.5:
            saw_half = True
            first_05 = off
        if not saw_one and fav >= 1.0:
            saw_one = True
            first_10 = off
        if saw_half and not retested_after_half:
            if adv >= 0:
                retested_after_half = True

    hold = end - start
    tfrac = peak_k / max(hold, 1)

    # path class (the core question: direct vs pullback-first)
    if first_05 is None:
        pclass = "never_proved"     # never reached +0.5R
    elif adv_before_05 >= 0.10:
        pclass = "pullback_first"   # adverse >=0.10R before proving
    else:
        pclass = "direct"           # essentially straight to +0.5R

    return {
        "mfe": mfe, "mae": mae, "hold": hold,
        "peak_k": peak_k, "tfrac": tfrac,
        "first_05": first_05, "first_10": first_10,
        "mae_before_05": mae_before_05,
        "adv_before_05": adv_before_05,
        "retest_after_half": retested_after_half,
        "pclass": pclass,
        "touched_before_05": touched_entry_before_05,
        "touch_05_k": touch_05_k,
        "deep_before_05": deep_before_05,
        "touched_ever": touched_entry_ever,
        "exit_r": float(trade.get("r_multiple") or 0.0),
    }


def med(xs):
    s = sorted(x for x in xs if x is not None)
    return s[len(s) // 2] if s else None


def pct(n, d):
    return 100.0 * n / d if d else 0.0


def cohort_table(rows):
    print(f"  {'cohort':<14} {'n':>4} {'NET':>8} {'direct%':>8} {'pbFirst%':>8} "
          f"{'neverP%':>7} {'f05med':>7} {'f10med':>7} {'maeB4med':>8} "
          f"{'tPk%':>5} {'retest%':>7} {'dipB4%':>6} {'deep<.5%':>8}", flush=True)
    for name, pred in COHORTS:
        sub = [x for x in rows if pred(x)]
        if not sub:
            print(f"  {name:<14} n=0", flush=True)
            continue
        n = len(sub)
        c_d = sum(1 for x in sub if x["pclass"] == "direct")
        c_p = sum(1 for x in sub if x["pclass"] == "pullback_first")
        c_n = sum(1 for x in sub if x["pclass"] == "never_proved")
        f05 = med([x["first_05"] for x in sub])
        f10 = med([x["first_10"] for x in sub])
        mb4 = med([x["mae_before_05"] for x in sub])
        tpk = med([x["tfrac"] for x in sub])
        rt = sum(1 for x in sub if x["retest_after_half"])
        dip0 = sum(1 for x in sub if x["touched_before_05"])
        dip5 = sum(1 for x in sub if x["deep_before_05"])
        net = sum(x["r"] for x in sub)
        print(f"  {name:<14} {n:4d} {net:+8.1f} {pct(c_d, n):7.1f}% {pct(c_p, n):7.1f}% "
              f"{pct(c_n, n):6.1f}% {(f05 if f05 is not None else -1):7.0f} "
              f"{(f10 if f10 is not None else -1):7.0f} "
              f"{(mb4 if mb4 is not None else -1):8.2f} "
              f"{(100 * tpk if tpk is not None else -1):4.0f}% "
              f"{pct(rt, n):6.1f}% {pct(dip0, n):5.1f}% {pct(dip5, n):7.1f}%", flush=True)


def analyze_scope(scope, sim, data):
    fine = data["fine"]
    fine_ts = [int(c["ts"]) for c in fine]
    result = {"scope": scope, "configs": {}}
    print(f"\n=== winner early-path autopsy [{scope.upper()}] ===", flush=True)
    for key in CONFIGS:
        params = {**BP, **EXPERIMENTS[key]["params"]}
        params.setdefault("exp_partial_r", 0.0)
        out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                  fine_ltf=fine, **params)
        trades = out["ltf_trades"] if isinstance(out, dict) else out
        rows = []
        for t in trades:
            p = walk_path(t, fine, fine_ts)
            if p is None:
                continue
            rows.append({
                "r": p["exit_r"],
                "pclass": p["pclass"],
                "mfe": p["mfe"], "mae": p["mae"], "hold": p["hold"],
                "tfrac": p["tfrac"],
                "first_05": p["first_05"], "first_10": p["first_10"],
                "mae_before_05": p["mae_before_05"],
                "adv_before_05": p["adv_before_05"],
                "retest_after_half": p["retest_after_half"],
                "touched_before_05": p["touched_before_05"],
                "touch_05_k": p["touch_05_k"],
                "deep_before_05": p["deep_before_05"],
                "touched_ever": p["touched_ever"],
                "date": str(t.get("exit_date") or "")[:10],
            })
        net = sum(net_r([t]) for t in trades)
        gross = sum(float(t.get("r_multiple") or 0.0) for t in trades)
        print(f"\n  {key}: n={len(rows)} gross={gross:+.1f} net={net:+.1f}", flush=True)
        cohort_table(rows)

        # Phase-B miss-cost rollup on winners + monsters
        wins = [x for x in rows if x["r"] > 0]
        mons = [x for x in rows if x["r"] >= 10]
        w_dip = sum(1 for x in wins if x["touched_before_05"])
        m_dip = sum(1 for x in mons if x["touched_before_05"])
        w_miss = [x for x in wins if not x["touched_before_05"]]
        touch_med = med([x["touch_05_k"] for x in wins])
        print(f"    retest-entry capture (touched entry BEFORE +0.5R): "
              f"winners {w_dip}/{len(wins)} ({pct(w_dip, len(wins)):.1f}%)  "
              f"monsters {m_dip}/{len(mons)} ({pct(m_dip, len(mons)):.1f}%)  "
              f"missed_win_R={sum(x['r'] for x in w_miss):+.1f} "
              f"(n={len(w_miss)})  winner_wait_med={(touch_med if touch_med is not None else -1)} 1m-bars",
              flush=True)
        result["configs"][key] = rows
    return result


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  WINNER EARLY-PATH AUTOPSY — direct vs pullback-first, tPeak, retest, zone-miss", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    data_is = load_scope("is")
    data_oos = load_scope("oos")

    res_is = analyze_scope("is", sim, data_is)
    res_oos = analyze_scope("oos", sim, data_oos)

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "study": "winner early-path autopsy (descriptive; no gates)",
        "configs": list(CONFIGS),
        "is": res_is,
        "oos": res_oos,
        "elapsed_sec": round(time.time() - t0, 2),
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
