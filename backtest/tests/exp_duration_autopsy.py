"""Stage R — Duration & negative-zone forensic (descriptive, IS+OOS, no gate).

Answers (user questions, pre-registered):
  R1 hold-time anatomy: losers vs winners vs monsters — mean/median hours per
     duration bucket + net per bucket ("loss ki avg duration kya hai")
  R2 winner time-to-first-positive: hours to first touch 0R / +0.5R / +1R
     ("winners 0R+ kab nikal jaate hai")
  R3 negative-zone residency: hours in [-1,0), longest continuous stretch in
     zone [-0.9,-0.2], level snapshots r at 12h/24h/48h
  R4 stuck-cohort recovery table: trades whose zone stretch reached H hours
     (H=12/24/48) -> final class/net vs cut-at-H net (decision table for the
     negative-zone time-stop idea)
  R5 Stage-H cut-bucket decomposition by LEVEL at cut (<= -0.5 vs (-0.5,+0.5)):
     was the OOS "+33R cut bucket" in the band the user's narrow gate spares?
  R6 ceilings: eventual full-SL trades with >=24h below -0.5 (save side) vs
     winners stuck at -0.5 for >=24h (cost side)

Fine 1m replay causal; descriptive only — no engine change, no gate.
Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_duration_autopsy.py
"""
from __future__ import annotations

import json
import sys
import time
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING

OUT = ROOT / "backtest/tests/_duration_autopsy_results.json"
HS = (12, 24, 48)
BUCKETS = ((0, 6), (6, 12), (12, 24), (24, 48), (48, 96), (96, 1e9))

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


def analyze(trades, fine):
    """Per-trade fine-path metrics. Returns list of dicts."""
    if not fine:
        return []
    fts = [int(f["ts"]) for f in fine]
    rows = []
    for t in trades:
        e_ts, x_ts = int(t["entry_ts"]), int(t["exit_ts"])
        i0, i1 = bisect_right(fts, e_ts), bisect_right(fts, x_ts)
        if i1 - i0 < 2:
            continue
        e = float(t["entry_price"])
        sl = float(t["sl"])
        rk = abs(e - sl)
        if rk <= 0 or e <= 0:
            continue
        sgn = 1.0 if t.get("dir") == "long" else -1.0
        rs = [sgn * (float(fine[i]["close"]) - e) / rk for i in range(i0, i1)]
        ts = [int(fine[i]["ts"]) for i in range(i0, i1)]
        r_f = float(t["r_multiple"])
        dur_h = (x_ts - e_ts) / 3600.0
        cls = "monster" if r_f >= 4.0 else ("win" if r_f > 0 else "loss")

        def first_touch(level):
            for j, r in enumerate(rs):
                if r >= level:
                    return round((ts[j] - e_ts) / 3600.0, 2)
            return None

        # zone residency: [-1,0) total, [-0.9,-0.2] stretches
        hrs_neg = 0.0
        cur_start = None
        zone_longest = 0.0
        zone_hit = {}  # H -> (r_at_hit, index)
        for j, r in enumerate(rs):
            if -1.0 <= r < 0:
                hrs_neg += 1.0 / 60.0  # 1m bars
            if -0.9 <= r <= -0.2:
                if cur_start is None:
                    cur_start = j
                stretch_h = (ts[j] - ts[cur_start]) / 3600.0 + 1.0 / 60.0
                if stretch_h > zone_longest:
                    zone_longest = stretch_h
                for H in HS:
                    if H not in zone_hit and stretch_h >= H:
                        zone_hit[H] = r
            else:
                cur_start = None

        # snapshots at H (first bar at/after H; open check)
        snap = {}
        for H in HS:
            k = bisect_right(ts, e_ts + H * 3600)
            if k < len(ts):
                mfe_h = max(rs[:k]) if k else rs[0]
                snap[H] = {"open": True, "r": round(rs[k], 3),
                           "mfe": round(mfe_h, 3)}
            else:
                snap[H] = {"open": False}

        hrs_below05 = sum(1.0 / 60.0 for r in rs if r <= -0.5)
        rows.append({
            "dur_h": round(dur_h, 2), "cls": cls, "r_f": r_f,
            "t0": first_touch(0.0), "t05": first_touch(0.5), "t1": first_touch(1.0),
            "hrs_neg": round(hrs_neg, 2), "zone_longest": round(zone_longest, 2),
            "hrs_below05": round(hrs_below05, 2),
            "snap": snap,
            "zone_hit": {H: round(v, 3) for H, v in zone_hit.items()},
        })
    return rows


def med(v):
    if not v:
        return None
    s = sorted(v)
    n = len(s)
    return round(s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2, 2)


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  STAGE R — DURATION & NEGATIVE-ZONE FORENSIC (descriptive, IS+OOS)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {"stage": "duration_autopsy", "lens": "descriptive fine replay",
               "years": {"is": 3.67, "oos": 2.0}, "scopes": {}}

    for scope in ("is", "oos"):
        print(f"\n{'=' * 30} [{scope.upper()}] {'=' * 30}", flush=True)
        data = load_scope(scope)
        sc = {}
        for name, key, flags in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            trades = run(sim, data, params, **flags)
            rows = analyze(trades, data["fine"])
            print(f"\n  --- {name} (n={len(rows)}) ---", flush=True)

            # R1 duration anatomy
            r1 = {}
            print(f"    R1 bucket | loss n/net | win n/net | monster n/net | net | dur med(h)",
                  flush=True)
            for lo, hi in BUCKETS:
                sel = [r for r in rows if lo <= r["dur_h"] < hi]
                g = lambda c: [r for r in sel if r["cls"] == c]
                parts = {}
                for c in ("loss", "win", "monster"):
                    gg = g(c)
                    parts[c] = {"n": len(gg), "net": round(sum(x["r_f"] for x in gg), 1)}
                tot = round(sum(x["r_f"] for x in sel), 1)
                lbl = f"{lo}-{int(hi) if hi < 1e9 else 'inf'}h"
                r1[lbl] = {**parts, "net": tot,
                           "dur_med": med([x["dur_h"] for x in sel])}
                if sel:
                    print(f"    {lbl:>10} | {parts['loss']['n']:>3}/{parts['loss']['net']:+7.1f} | "
                          f"{parts['win']['n']:>3}/{parts['win']['net']:+7.1f} | "
                          f"{parts['monster']['n']:>3}/{parts['monster']['net']:+7.1f} | "
                          f"{tot:+7.1f} | {r1[lbl]['dur_med']}", flush=True)
            d_l = med([r["dur_h"] for r in rows if r["cls"] == "loss"])
            d_w = med([r["dur_h"] for r in rows if r["cls"] == "win"])
            d_m = med([r["dur_h"] for r in rows if r["cls"] == "monster"])
            print(f"    MEDIAN dur: loss {d_l}h | win {d_w}h | monster {d_m}h", flush=True)

            # R2 winner time-to-positive
            wins = [r for r in rows if r["cls"] != "loss"]
            r2 = {}
            for lbl, k in (("0R", "t0"), ("+0.5R", "t05"), ("+1R", "t1")):
                v = [r[k] for r in wins if r[k] is not None]
                r2[lbl] = {"n_known": len(v), "n_never": len(wins) - len(v),
                           "med": med(v), "mean": round(sum(v) / len(v), 2) if v else None}
            print(f"    R2 first-touch (winners n={len(wins)}): "
                  + " | ".join(f"{k}: med {r2[k]['med']}h mean {r2[k]['mean']}h "
                               f"never {r2[k]['n_never']}" for k in r2), flush=True)

            # R3 residency by class
            r3 = {}
            for c in ("loss", "win", "monster"):
                gg = [r for r in rows if r["cls"] == c]
                r3[c] = {
                    "n": len(gg),
                    "hrs_neg_med": med([x["hrs_neg"] for x in gg]),
                    "zone_longest_med": med([x["zone_longest"] for x in gg]),
                    "hrs_below05_med": med([x["hrs_below05"] for x in gg]),
                }
                print(f"    R3 {c:<8} n={len(gg):>3} hrsIn[-1,0) med={r3[c]['hrs_neg_med']}h "
                      f"zoneStretch med={r3[c]['zone_longest_med']}h "
                      f"hrsBelow-0.5 med={r3[c]['hrs_below05_med']}h", flush=True)

            # R4 stuck-cohort (zone stretch reached H) recovery table
            r4 = {}
            for H in HS:
                coh = [r for r in rows if H in r["zone_hit"]]
                if not coh:
                    r4[H] = {"n": 0}
                    print(f"    R4 zone>={H}h: n=0", flush=True)
                    continue
                cls_ct = {c: sum(1 for x in coh if x["cls"] == c)
                          for c in ("loss", "win", "monster")}
                final_net = round(sum(x["r_f"] for x in coh), 1)
                cut_net = round(sum(x["zone_hit"][H] for x in coh), 1)
                r4[H] = {"n": len(coh), "classes": cls_ct,
                         "final_net": final_net, "cut_net_at_H": cut_net,
                         "delta_cut_minus_final": round(cut_net - final_net, 1),
                         "n_sl": sum(1 for x in coh if x["r_f"] <= -0.95)}
                print(f"    R4 zone>={H}h: n={len(coh):>3} sl={cls_ct['loss']}"
                      f"(full {r4[H]['n_sl']}) win={cls_ct['win']} monster={cls_ct['monster']} | "
                      f"final {final_net:+.1f} vs cutAtH {cut_net:+.1f} "
                      f"= {cut_net - final_net:+.1f}", flush=True)

            # R5 Stage-H bucket decomposition by level at cut
            r5 = {}
            for H in HS:
                cands = [r for r in rows if r["snap"].get(H, {}).get("open")
                         and r["snap"][H]["r"] < 0.5
                         and r["snap"][H]["mfe"] < 0.5]
                bands = {}
                for bname, lo, hi in (("A_r<=-0.5", -9.0, -0.5),
                                      ("B_-0.5<r<+0.5", -0.5, 0.5)):
                    bb = [c for c in cands if lo <= c["snap"][H]["r"] < hi]
                    if not bb:
                        bands[bname] = {"n": 0}
                        continue
                    cut_net = sum(c["snap"][H]["r"] for c in bb)
                    fin_net = sum(c["r_f"] for c in bb)
                    bands[bname] = {
                        "n": len(bb),
                        "cut_net": round(cut_net, 1),
                        "final_net": round(fin_net, 1),
                        "delta_cut_minus_final": round(cut_net - fin_net, 1),
                        "n_win": sum(1 for c in bb if c["r_f"] > 0),
                        "n_mon": sum(1 for c in bb if c["r_f"] >= 4.0),
                    }
                r5[H] = bands
                a, b = bands["A_r<=-0.5"], bands["B_-0.5<r<+0.5"]
                print(f"    R5 H={H:>2}: bandA(n={a.get('n',0)}, "
                      f"cut {a.get('cut_net',0):+.1f} vs final {a.get('final_net',0):+.1f} "
                      f"= {a.get('delta_cut_minus_final', 0):+.1f}) | "
                      f"bandB(n={b.get('n',0)}, cut {b.get('cut_net',0):+.1f} "
                      f"vs final {b.get('final_net',0):+.1f} "
                      f"= {b.get('delta_cut_minus_final', 0):+.1f})", flush=True)

            # R6 ceilings
            save_side = [r for r in rows if r["r_f"] <= -0.95 and r["hrs_below05"] >= 24]
            cost_side = [r for r in rows if r["r_f"] > 0 and r["hrs_below05"] >= 24]
            r6 = {
                "full_sl_with_24h_below_-0.5": {
                    "n": len(save_side),
                    "save_if_cut_at_-0.5": round(0.5 * len(save_side), 1),
                },
                "winners_with_24h_below_-0.5": {
                    "n": len(cost_side),
                    "final_net": round(sum(x["r_f"] for x in cost_side), 1),
                },
            }
            print(f"    R6 ceilings: full-SL stuck>=24h below -0.5: n={len(save_side)} "
                  f"-> max save {0.5 * len(save_side):+.1f}R | "
                  f"winners stuck>=24h below -0.5: n={len(cost_side)} "
                  f"(their final {r6['winners_with_24h_below_-0.5']['final_net']:+.1f}R "
                  f"= cost side)", flush=True)

            sc[name] = {"n_rows": len(rows), "r1": r1, "r2": r2, "r3": r3,
                        "r4": r4, "r5": r5, "r6": r6,
                        "median_dur": {"loss": d_l, "win": d_w, "monster": d_m}}
        payload["scopes"][scope] = sc

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
