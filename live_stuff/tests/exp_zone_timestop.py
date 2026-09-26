"""Stage S — negative-zone time-stop arms (fine replay, IS+OOS, pre-registered).

Stage R verdict: the "long sideways bleed" cohort is tiny (zone>=24h = 5/466),
full-SL ceiling ~+1-1.5R, BUT the H12 OOS massacre (+33.2R cut bucket) was
100% band B (-0.5..+0.5) - the user's narrow negative-level gate would have
cut ZERO trades there. Pre-registered arms (no post-hoc additions):

  S1  H=24h  snapshot, exit if r <= -0.5
  S2  H=24h  snapshot, exit if r <= -0.8
  S3  H=48h  snapshot, exit if r <= -0.5
  S4  H=48h  snapshot, exit if r <= -0.8
  S5  H=2h   snapshot, exit if r <= -0.6   (fast-fail on instant deaths)
  S6  H=48h  snapshot, exit if |r| <= 0.25  (stale-zero)
  S7  residency: exit at first moment zone [-0.9,-0.2] stretch reaches 24h

Snapshot semantics = evaluate ONCE at first fine bar >= H (Stage-H precedent).
Causal, descriptive replay - engine untouched. Monster-safe audit on cut set:
n cut / n winners / n 4R+ monsters / orig net of cut set vs realized net.
Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_zone_timestop.py
"""
from __future__ import annotations

import json
import sys
import time
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

from exp_equity_quality import equity_quality, arm_scores, curve_better

OUT = ROOT / "live_stuff/tests/_zone_timestop_results.json"
YEARS = {"is": 3.67, "oos": 2.0}

# arms: (name, kind, hours, level) kind: "snap" (r<=L at H) / "abs" (|r|<=L)
# / "zone" (residency stretch >= hours -> exit)
ARMS = (
    ("S1_24h_-0.5", "snap", 24.0, -0.5),
    ("S2_24h_-0.8", "snap", 24.0, -0.8),
    ("S3_48h_-0.5", "snap", 48.0, -0.5),
    ("S4_48h_-0.8", "snap", 48.0, -0.8),
    ("S5_2h_-0.6", "snap", 2.0, -0.6),
    ("S6_48h_stale0", "abs", 48.0, 0.25),
    ("S7_zone24h", "zone", 24.0, None),
)

HALF = dict(exp_trail_half=1, exp_trail_delay_r=1.0)
SKIPD = dict(exp_skip_decisive=1)
RETEST = dict(exp_retest_fill=0.25, exp_retest_wait=240)

LANES = (
    ("champion", "champion_multi_sw10", dict(HALF, **SKIPD)),
    ("utcsat", "utcsat_multi_sw10", dict(HALF, **SKIPD)),
    ("age10", "age10_dirmatch_swingpause_single_sw10", dict(RETEST)),
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


def run(sim, data, params, **flags):
    out = sim(
        data["c1h"], data["sw10"], data["c15"], data["sw15"],
        fine_ltf=data["fine"], **{**params, **flags},
    )
    return out["ltf_trades"] if isinstance(out, dict) else out


def replay(trades, fine, kind, hours, level):
    """Returns (new_trades, affected) where affected has audit fields."""
    if not fine:
        return list(trades), []
    fts = [int(f["ts"]) for f in fine]
    out, affected = [], []
    for t in trades:
        e_ts, x_ts = int(t["entry_ts"]), int(t["exit_ts"])
        i0, i1 = bisect_right(fts, e_ts), bisect_right(fts, x_ts)
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
        rs = [sgn * (float(fine[i]["close"]) - e) / rk for i in range(i0, i1)]
        ts = [int(fine[i]["ts"]) for i in range(i0, i1)]
        exit_i = None
        if kind in ("snap", "abs"):
            k = bisect_right(ts, e_ts + hours * 3600)
            if k < len(ts) and ts[k] <= x_ts:
                r = rs[k]
                hit = (r <= level) if kind == "snap" else (abs(r) <= level)
                if hit:
                    exit_i = k
        else:  # zone residency
            cur_start = None
            for j, r in enumerate(rs):
                if -0.9 <= r <= -0.2:
                    if cur_start is None:
                        cur_start = j
                    if (ts[j] - ts[cur_start]) >= hours * 3600:
                        exit_i = j
                        break
                else:
                    cur_start = None
        if exit_i is None or ts[exit_i] >= x_ts:
            out.append(t)
            continue
        r_new = rs[exit_i]
        t2 = dict(t)
        t2["r_multiple"] = round(r_new, 3)
        t2["exit_ts"] = ts[exit_i]
        t2["exit_date"] = fine[exit_i].get("date", t.get("exit_date"))
        t2["bars_held"] = max(1, (ts[exit_i] - e_ts) // (15 * 60))
        out.append(t2)
        affected.append({
            "entry_date": t.get("entry_date"),
            "orig_r": float(t["r_multiple"]),
            "new_r": round(r_new, 3),
            "orig_win": float(t["r_multiple"]) > 0,
            "orig_monster": float(t["r_multiple"]) >= 4.0,
        })
    return out, affected


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE S — NEGATIVE-ZONE TIME-STOP (fine replay, 7 pre-registered arms)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "stage": "zone_timestop",
        "lens": "descriptive fine replay; snapshot semantics at H",
        "arms": [{"name": n, "kind": k, "hours": h, "level": l}
                 for n, k, h, l in ARMS],
        "years": YEARS, "scopes": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        fine = data["fine"]
        yrs = YEARS[scope]
        sc = {}
        for name, key, flags in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            base = run(sim, data, params, **flags)
            bm = equity_quality(base, yrs)
            sc[name] = {"baseline": {"n": bm["n"], "net": bm.get("net"),
                                     "max_dd": bm.get("max_dd")}}
            print(f"\n  {name}: base n={bm['n']} net={bm.get('net'):+.1f} "
                  f"DD={bm.get('max_dd'):.1f}", flush=True)
            for arm, kind, hours, level in ARMS:
                new, aff = replay(base, fine, kind, hours, level)
                m = equity_quality(new, yrs)
                d = arm_scores(m, bm)
                n_win = sum(1 for a in aff if a["orig_win"])
                n_mon = sum(1 for a in aff if a["orig_monster"])
                aff_orig = round(sum(a["orig_r"] for a in aff), 1)
                aff_new = round(sum(a["new_r"] for a in aff), 1)
                sc[name][arm] = {
                    **{k: m.get(k) for k in ("n", "net", "max_dd", "ulcer",
                                             "sortino", "calmar", "pf")},
                    "d_net": round(d.get("d_net", 0), 1),
                    "d_dd": round(d.get("d_max_dd", 0), 1),
                    "curve_better": curve_better(d),
                    "n_cut": len(aff), "n_cut_winners": n_win,
                    "n_cut_monsters": n_mon,
                    "cut_orig_net": aff_orig, "cut_new_net": aff_new,
                }
                print(f"    {arm:<14} cut={len(aff):>2} (win {n_win}, mon {n_mon}) "
                      f"cutNet {aff_orig:+6.1f}->{aff_new:+6.1f} | "
                      f"net {bm.get('net'):+7.1f}->{m.get('net'):+7.1f} "
                      f"({d.get('d_net', 0):+6.1f}) DD {d.get('d_max_dd', 0):+5.1f} "
                      f"curve={curve_better(d)}", flush=True)
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA VERDICT ===", flush=True)
    verdicts = {}
    for name, _, _ in LANES:
        verdicts[name] = {}
        for arm, _, _, _ in ARMS:
            a_is = payload["scopes"]["is"][name][arm]
            a_oos = payload["scopes"]["oos"][name][arm]
            v = {
                "d_net_is": a_is["d_net"], "d_net_oos": a_oos["d_net"],
                "cut_is": a_is["n_cut"], "cut_oos": a_oos["n_cut"],
                "monsters_cut_is": a_is["n_cut_monsters"],
                "monsters_cut_oos": a_oos["n_cut_monsters"],
                "both_positive": a_is["d_net"] > 0 and a_oos["d_net"] > 0,
                "curve_pass_both": a_is["curve_better"] and a_oos["curve_better"],
            }
            verdicts[name][arm] = v
            print(f"  {name:<10} {arm:<14} dNet {v['d_net_is']:+7.1f}/{v['d_net_oos']:+6.1f} "
                  f"cut {v['cut_is']:>2}/{v['cut_oos']:<2} "
                  f"mon {v['monsters_cut_is']}/{v['monsters_cut_oos']} "
                  f"both+ {v['both_positive']} curve {v['curve_pass_both']}", flush=True)
    payload["verdicts"] = verdicts
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
