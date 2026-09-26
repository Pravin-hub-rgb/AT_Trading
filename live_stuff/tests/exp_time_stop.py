"""Stage 2 — Time-stop family (descriptive Phase 1, fine-path replay, IS + OOS).

Question: does cutting UNPROVED trades at H hours improve the book without
killing winners?

Pre-registered gate (monster-safe, from LOSS_AUTOPSY #1 + LA1):
  cut at H only if BOTH:
    (a) unrealized R at H < +0.5   (not proved yet)
    (b) MFE in [entry, H] < +0.5   (never proved before H either)
  -> a trade that ever showed +0.5R is NEVER touched (winners/monsters safe).
  Zero winners exit <48 bars (12h) in audit => H12/H24/H48 arms cover it.

Arms (frozen, no post-hoc extras): H12, H24, H48 (hours after entry).
Lanes: candidate champion, utcsat, age10 (Stage B winners).
Replay is causal: uses fine 1m path ONLY up to H; if engine already exited
(trail/SL/window) before H the trade is untouched.

Reported: n_cut, delta net (gross + net_r), lost winners/monsters (cut trades
whose ORIGINAL outcome was positive/4R+), cut-R distribution, equity quality
before/after.

Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_time_stop.py
"""
from __future__ import annotations

import json
import sys
import time
from bisect import bisect_left, bisect_right
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

from exp_equity_quality import equity_quality

OUT = ROOT / "live_stuff/tests/_time_stop_results.json"
YEARS = {"is": 3.67, "oos": 2.0}

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)

LANES = (
    ("champion", "champion_multi_sw10", dict(HALF, **SKIPD)),
    ("utcsat", "utcsat_multi_sw10", dict(HALF, **SKIPD)),
    ("age10", "age10_dirmatch_swingpause_single_sw10", dict(RETEST)),
)

HOURS = (12, 24, 48)
PROOF = 0.5


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


def run(sim, data, params, **flags):
    out = sim(
        data["c1h"], data["sw10"], data["c15"], data["sw15"],
        fine_ltf=data["fine"], **{**params, **flags},
    )
    return out["ltf_trades"] if isinstance(out, dict) else out


def replay(trades, fine, hours):
    """Cut unproved trades at `hours` using fine path. Returns (new_trades, cuts)."""
    if not fine:
        return list(trades), []
    fts = [int(f["ts"]) for f in fine]
    out = []
    cuts = []
    h_s = hours * 3600
    for t in trades:
        e_ts = int(t["entry_ts"])
        x_ts = int(t["exit_ts"])
        cut_ts = e_ts + h_s
        if x_ts <= cut_ts:
            out.append(t)
            continue
        i0 = bisect_right(fts, e_ts)
        i1 = bisect_right(fts, cut_ts)
        if i1 - i0 < 2:
            out.append(t)
            continue
        e = float(t["entry_price"])
        sl = float(t["sl"])
        rk = abs(e - sl)
        if rk <= 0 or e <= 0:
            out.append(t)
            continue
        sgn = 1.0 if t.get("dir") == "long" else -1.0
        mfe = None
        r_cut = None
        for i in range(i0, i1):
            c = float(fine[i]["close"])
            r = sgn * (c - e) / rk
            mfe = r if mfe is None else max(mfe, r)
        r_last = sgn * (float(fine[i1 - 1]["close"]) - e) / rk
        r_cut = r_last
        if mfe is not None and mfe < PROOF and r_cut < PROOF:
            t2 = dict(t)
            t2["r_multiple"] = round(r_cut, 3)
            t2["exit_ts"] = int(fine[i1 - 1]["ts"])
            t2["exit_date"] = fine[i1 - 1]["date"]
            t2["bars_held"] = max(1, (t2["exit_ts"] - e_ts) // (15 * 60))
            out.append(t2)
            cuts.append({
                "entry_date": t.get("entry_date"),
                "orig_r": float(t["r_multiple"]),
                "cut_r": round(r_cut, 3),
                "mfe": round(mfe, 3),
                "orig_win": float(t["r_multiple"]) > 0,
                "orig_monster": float(t["r_multiple"]) >= 4.0,
            })
        else:
            out.append(t)
    return out, cuts


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE 2 — TIME-STOP FAMILY (descriptive fine-path replay, IS + OOS)", flush=True)
    print("  gate: cut at H only if unrealized R < +0.5 AND MFE before H < +0.5", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "time_stop",
        "lens": "descriptive fine-path replay; no engine change",
        "years": YEARS,
        "arms": [{"hours": h, "proof_r": PROOF} for h in HOURS],
        "lanes": [{"name": n, "cfg": c, "flags": f} for n, c, f in LANES],
        "scopes": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        fine = data["fine"]
        sc = {}
        for name, key, flags in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            base = run(sim, data, params, **flags)
            bm = equity_quality(base, yrs)
            sc[name] = {"baseline": bm}
            print(f"\n  {name}: base n={bm['n']} net={bm['net']:+.1f} "
                  f"DD={bm['max_dd']:.1f} calmar={bm['calmar']:.3f}", flush=True)
            for h in HOURS:
                new, cuts = replay(base, fine, h)
                m = equity_quality(new, yrs)
                lost_w = sum(1 for c in cuts if c["orig_win"])
                lost_m = sum(1 for c in cuts if c["orig_monster"])
                cut_orig_net = sum(c["orig_r"] for c in cuts)
                cut_new_net = sum(c["cut_r"] for c in cuts)
                sc[name][f"H{h}"] = {
                    **m,
                    "n_cut": len(cuts),
                    "lost_winners": lost_w,
                    "lost_monsters": lost_m,
                    "cut_orig_net_r": round(cut_orig_net, 1),
                    "cut_new_net_r": round(cut_new_net, 1),
                    "d_net_vs_base": round(m["net"] - bm["net"], 1),
                    "d_dd_vs_base": round(m["max_dd"] - bm["max_dd"], 1),
                }
                print(f"    H{h:<3} cut={len(cuts):>3} lostW={lost_w:>2} "
                      f"lostM={lost_m:>2} cutR {cut_orig_net:+.1f}->{cut_new_net:+.1f} | "
                      f"net {bm['net']:+.1f}->{m['net']:+.1f} "
                      f"({m['net'] - bm['net']:+.1f}) DD {bm['max_dd']:.1f}->{m['max_dd']:.1f} "
                      f"calmar {bm['calmar']:.3f}->{m['calmar']:.3f}", flush=True)
        payload["scopes"][scope] = sc

    # cross-era verdict
    print("\n=== CROSS-ERA DELTA NET (vs own lane baseline) ===", flush=True)
    verdicts = {}
    for name, _, _ in LANES:
        verdicts[name] = {}
        for h in HOURS:
            d_is = payload["scopes"]["is"][name][f"H{h}"]["d_net_vs_base"]
            d_oos = payload["scopes"]["oos"][name][f"H{h}"]["d_net_vs_base"]
            verdicts[name][f"H{h}"] = {
                "d_is": d_is, "d_oos": d_oos,
                "both_positive": d_is > 0 and d_oos > 0,
            }
            print(f"  {name:<10} H{h:<3} dNet {d_is:+7.1f}/{d_oos:+6.1f} "
                  f"both+ {d_is > 0 and d_oos > 0}", flush=True)
    payload["verdicts"] = verdicts
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
