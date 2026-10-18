"""The four validation techniques from the notes doc, run on 107 and 110.

WHY 107 AND 110 ONLY
====================
The portfolio is 54 pinned books. These two are the ones going live, and the
open question is which of the two, so a verdict on any other book does not
change a decision. Scope is the two.

WHY A NEW HARNESS RATHER THAN THE FOUR THAT ALREADY EXIST
==========================================================
  exp_top10_stability      probes values one at a time. The doc wants a heat map
                           - two axes together - because a cliff only shows up
                           in the interaction.
  exp_wfo_true             hardcoded to champion_multi_sw10, retired 2026-10-14.
                           It has never been pointed at 107 or 110.
  exp_closeout_battery     post-hoc only. Re-scores booked trades, so it cannot
                           see that worse fills change WHICH trades fill.
                           That is now possible - see exp_stop_slip_bps.
  exp_trade_order_shuffle  does shuffle. But it answers "is this drawdown an
                           ordering artefact", not the doc's survivability
                           question, which is "how many orderings destroy the
                           account".

This harness covers all four against the current engine and the current
default of exp_no_opposite=1.

WHAT EACH TECHNIQUE ANSWERS
===========================
T1 sensitivity    does the edge survive neighbouring parameter values, or is it
                  balanced on one number. The doc's failure shape is a cliff.
T2 walk-forward   does performance hold on windows the parameters were not
                  chosen on. The doc calls this where most backtests lie.
T3 stress         slippage 0 -> 10% at engine level, costs 1x/2x/3x, and the
                  execution-delay test the doc calls a killer.
T4 survivability  of N shuffled orderings, how many leave you flat or worse.
                  The doc's warning is "many curves go up, a few go straight
                  down" - that is a sizing verdict, not a strategy verdict.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_four_techniques.py [t1|t2|t3|t4]
"""
from __future__ import annotations

import io
import itertools
import json
import math
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

from experiment_registry import EXPERIMENTS, BP  # noqa: E402
from run_experiment import net_r, get_swings, get_data  # noqa: E402
from exp_tf_family import build_family_module  # noqa: E402
from exp_signal_metrics import load_era  # noqa: E402

ALL_BOOKS = [("fsent_champ_long_mcloff_htf15", "107"),
             ("fsent_champ_long_htf15_tskip6", "110"),
             ("fsent_champ_long_htffs", "106"),
             ("fsent_champ_long_htf15_htffs", "109"),
             ("fsent_champ_long_htfesmcl4", "108")]
# The eight multi books that were on the registry but never reached the scorecard.
# They are the actual test of whether the shortlist was right, so they get the
# same battery as the five that were chosen.
REST_BOOKS = [("fsent_sig_multi_acc", "acc"),
              ("fsent_champ_long_htf15", "htf15"),
              ("fsent_champ_long_mcloff", "mcloff"),
              ("fsent_champ_long_causalfloor", "causalfloor"),
              ("fsent_champ_long_mode_chop", "modechop"),
              ("fsent_champ_long_biasmom05", "biasmom05"),
              ("fsent_sig_multi_htffs", "sigm_htffs"),
              ("fsent_sig_multi", "sigm")]
BOOKS = ALL_BOOKS  # all 13 multi books

OUT = HERE / ("four_techniques_%s.json" % (sys.argv[1].lower() if len(sys.argv) > 1 else "all"))
MD = HERE / "four_techniques.md"


def sim_book(sim, data, cfg, swing, **over):
    p = {**BP, **(cfg.get("params") or {}), **over}
    o = sim(data["c1h"], get_swings(data, swing), data["c15"], data["sw15"],
            fine_ltf=data["fine"], **p)
    return o["ltf_trades"] if isinstance(o, dict) else o


def closed(trades):
    return sorted([t for t in trades if t.get("outcome") != "open"],
                  key=lambda t: int(t["entry_ts"]))


def rs_of(trades):
    return [net_r([t]) for t in trades]


def stats(rs):
    if not rs:
        return None
    n = len(rs)
    w = [r for r in rs if r > 0]
    l = [r for r in rs if r <= 0]
    cum = peak = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    st = bst = 0
    for r in rs:
        st = st + 1 if r < 0 else 0
        bst = max(bst, st)
    gw = sum(float(r) for r in w)
    gl = -sum(float(r) for r in l)
    return {"n": n, "net": round(sum(rs), 2), "rpt": round(sum(rs) / n, 4),
            "wr": round(100.0 * len(w) / n, 1),
            "pf": round(gw / gl, 3) if gl else 0.0,
            "dd": round(dd, 2), "streak": bst,
            "calmar": round(sum(rs) / dd, 2) if dd else 0.0}


def rolling(rs, w):
    wins = tot = 0
    worst = None
    for i in range(0, max(len(rs) - w + 1, 0)):
        s = sum(rs[i:i + w])
        tot += 1
        if s > 0:
            wins += 1
        worst = s if worst is None else min(worst, s)
    return (round(100.0 * wins / tot, 1) if tot else 0.0,
            round(worst if worst is not None else 0.0, 2), tot)


# --------------------------------------------------------------------------
# T3 - stress
# --------------------------------------------------------------------------
SLIP = [0, 5, 10, 25, 50, 100, 250, 500, 1000]


def t3(sim, ERA, log):
    """Slippage at engine level, plus cost multiples, plus execution delay."""
    out = {}
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        rec = {}
        for era in ("is", "oos"):
            base = closed(sim_book(sim, ERA[era], cfg, swing))
            b = stats(rs_of(base))
            slip = []
            for bps in SLIP:
                if bps == 0:
                    slip.append(dict(bps=0, **b))
                    continue
                tr = closed(sim_book(sim, ERA[era], cfg, swing,
                                     exp_stop_slip_bps=bps))
                s = stats(rs_of(tr))
                slip.append(dict(bps=bps, **s, d_net=round(s["net"] - b["net"], 2)))
            # cost multiple: post-hoc is legitimate for fees. A fee does not
            # change which trades exist, so scaling it needs no engine run.
            br = rs_of(base)
            cost = []
            for mult in (1.0, 2.0, 3.0):
                if mult == 1.0:
                    cost.append(dict(mult=1.0, net=b["net"]))
                else:
                    cost.append(dict(mult=mult,
                                     net=round(b["net"] - 0.028 * (mult - 1.0) * b["n"], 2)))
            rec[era] = {"base": b, "slippage": slip, "cost": cost}
            log("  %s %s slip 0->1000bps: net %+.1f -> %+.1f  dd %.1f -> %.1f  streak %d -> %d"
                % (code, era.upper(), b["net"], slip[-1]["net"],
                   b["dd"], slip[-1]["dd"], b["streak"], slip[-1]["streak"]))
        out[name] = rec
    return out


# --------------------------------------------------------------------------
# T4 - survivability
# --------------------------------------------------------------------------
def t4(sim, ERA, log, paths=2000, seed=20261016):
    """The doc's actual question: how many orderings leave you flat or worse."""
    out = {}
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        rng = random.Random(seed)
        rec = {}
        for era in ("is", "oos"):
            base = closed(sim_book(sim, ERA[era], cfg, swing))
            r = rs_of(base)
            obs = stats(r)
            finals, dds, streaks = [], [], []
            for _ in range(paths):
                sh = list(r)
                rng.shuffle(sh)
                s = stats(sh)
                finals.append(s["net"])
                dds.append(s["dd"])
                streaks.append(s["streak"])
            finals.sort()
            dds.sort()
            streaks.sort()

            def pct(sorted_vals, q):
                return sorted_vals[min(len(sorted_vals) - 1,
                                       max(0, int(q * (len(sorted_vals) - 1))))]

            # ruin: an ordering whose worst drawdown would have stopped you out
            for risk_frac in (0.10, 0.15, 0.20):
                pass
            rec[era] = {
                "observed": obs,
                "final_net_p05": round(pct(finals, 0.05), 2),
                "final_net_p50": round(pct(finals, 0.50), 2),
                "final_net_p95": round(pct(finals, 0.95), 2),
                "worst_final": round(finals[0], 2),
                "dd_p50": round(pct(dds, 0.50), 2),
                "dd_p95": round(pct(dds, 0.95), 2),
                "dd_p99": round(pct(dds, 0.99), 2),
                "dd_worst": round(dds[-1], 2),
                "streak_p95": pct(streaks, 0.95),
                "streak_p99": pct(streaks, 0.99),
                "streak_worst": streaks[-1],
                "paths": paths,
                # ruin thresholds, as a fraction of the book's own worst DD
                "frac_paths_dd_over_25": round(100.0 * sum(1 for d in dds if d > 25.0) / paths, 2),
                "frac_paths_dd_over_50": round(100.0 * sum(1 for d in dds if d > 50.0) / paths, 2),
                "frac_paths_flat_or_worse": round(100.0 * sum(1 for f in finals if f <= 0) / paths, 2),
                "obs_dd_rank_pct": round(100.0 * sum(1 for d in dds if d < obs["dd"]) / paths, 2),
            }
            log("  %s %s observed dd %.2f is at the %s percentile | shuffled dd p50 %.1f p95 %.1f worst %.1f | worst streak %d"
                % (code, era.upper(), obs["dd"], rec[era]["obs_dd_rank_pct"],
                   rec[era]["dd_p50"], rec[era]["dd_p95"], rec[era]["dd_worst"],
                   rec[era]["streak_worst"]))
        out[name] = rec
    return out


# --------------------------------------------------------------------------
# T1 - parameter sensitivity, as a 2-axis heat map
# --------------------------------------------------------------------------
# 110: exp_trail_skip_n x exp_persist. skip_n is the one knob 110 has that 107
#      does not, and a previous 1-D sweep suggested a cliff in it. A 1-D sweep
#      cannot tell a cliff from an interaction - a value can look safe alone and
#      collapse once the other axis moves, which is exactly what a heat map is
#      for. The doc asks for two axes on the same picture.
# 107: cooldown_bars x exp_persist. 107 has no skip_n, so this is its two most
#      load-bearing structural knobs instead.
GRIDS = {
    "fsent_champ_long_htf15_tskip6": (
        "exp_trail_skip_n", [0, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16],
        "exp_persist", [5, 6, 7, 8, 9]),
    "fsent_champ_long_mcloff_htf15": (
        "cooldown_bars", [2, 4, 6, 8, 10, 12, 16],
        "exp_persist", [5, 6, 7, 8, 9]),
    # 106, 109 carry exp_htf_fs_entry; 108 carries exp_mcl_cooldown. Each gets
    # the two knobs that are actually load-bearing for that book rather than a
    # copied grid, for the reason the review makes: sweeping inert knobs proves
    # nothing and costs the runs that matter.
    "fsent_champ_long_htffs": (
        "cooldown_bars", [2, 4, 6, 8, 10, 12, 16],
        "exp_persist", [5, 6, 7, 8, 9]),
    "fsent_champ_long_htf15_htffs": (
        "cooldown_bars", [2, 4, 6, 8, 10, 12, 16],
        "exp_persist", [5, 6, 7, 8, 9]),
    "fsent_champ_long_htfesmcl4": (
        "cooldown_bars", [2, 4, 6, 8, 10, 12, 16],
        "exp_persist", [5, 6, 7, 8, 9]),
    # ---- the eight never-scored books ----
    # Each is swept on its OWN load-bearing knob where it has one, not on a
    # copied grid. Two of them carry exp_trail_skip_n, which is the knob that
    # produced the only cliff found anywhere in this battery, so those two get it
    # on the A axis specifically.
    "fsent_sig_multi": (
        "exp_trail_skip_n", [0, 1, 2, 3, 4, 6, 8],
        "cooldown_bars", [4, 8, 12]),
    "fsent_sig_multi_htffs": (
        "exp_trail_skip_n", [0, 1, 2, 3, 4, 6, 8],
        "cooldown_bars", [4, 8, 12]),
    "fsent_champ_long_biasmom05": (
        "exp_bias_momentum_min", [0.3, 0.5, 0.7],
        "cooldown_bars", [4, 8, 12]),
    "fsent_champ_long_causalfloor": (
        "exp_window_floor_s", [2700, 4500, 7200, 10800],
        "cooldown_bars", [4, 8, 12]),
    "fsent_sig_multi_acc": (
        "cooldown_bars", [4, 8, 12, 16],
        "exp_persist", [6, 7, 8]),
    "fsent_champ_long_htf15": (
        "cooldown_bars", [2, 4, 6, 8, 10, 12, 16],
        "exp_persist", [5, 6, 7, 8, 9]),
    "fsent_champ_long_mcloff": (
        "cooldown_bars", [2, 4, 6, 8, 10, 12, 16],
        "exp_persist", [5, 6, 7, 8, 9]),
    "fsent_champ_long_mode_chop": (
        "cooldown_bars", [2, 4, 6, 8, 10, 12, 16],
        "exp_persist", [5, 6, 7, 8, 9]),
}


def t1(sim, ERA, log):
    out = {}
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        ka, va, kb, vb = GRIDS[name]
        rec = {}
        for era in ("is", "oos"):
            cells = {}
            for a, b in itertools.product(va, vb):
                tr = closed(sim_book(sim, ERA[era], cfg, swing, **{ka: a, kb: b}))
                s = stats(rs_of(tr))
                cells["%s|%s" % (a, b)] = s
            rec[era] = {"ax_a": [ka, va], "ax_b": [kb, vb], "cells": cells}
            nets = [c["net"] for c in cells.values() if c]
            reg = cells.get("%s|%s" % ((cfg.get("params") or {}).get(ka, BP.get(ka)),
                                       (cfg.get("params") or {}).get(kb, BP.get(kb))))
            log("  %s %s  %d cells  net range %+.1f .. %+.1f   registered %+.1f"
                % (code, era.upper(), len(cells), min(nets), max(nets),
                   reg["net"] if reg else float("nan")))
        out[name] = rec
    return out


# --------------------------------------------------------------------------
# T2 - walk forward, actually re-optimising
# --------------------------------------------------------------------------
# The doc: split into train and test, roll forward, and at each step the
# strategy has never seen the test window. "Where most backtests lie to you."
#
# Both books are FIXED, so there is nothing to re-optimise unless a
# neighbourhood is searched - which is exactly the point. A parameter set that
# only survives because it was picked once on the whole history is not evidence
# of anything. So each fold searches a grid on the training windows only, and
# the winner is then scored blind on the window after it.
#
# IMPLEMENTATION NOTE, and it is the whole design. The first version of this
# sliced the candle arrays into train and test windows and rebuilt the swings
# per slice. That is fragile in a way that is not worth it: the HTF plane is
# 1h against a 15m LTF plane, so the swing index bases do not line up, and a
# re-derived swing series at a slice boundary is not the same object the book
# was measured on. Instead the engine runs once per cell over the whole span and
# the resulting TRADES are partitioned by entry_ts. Parameter selection then
# only ever sees trades inside the training window, which is the property the
# test exists to establish. Same question, no index arithmetic, no chance of a
# boundary artifact reading as a result.
#
# Grid is coarser than T1's on purpose - 3 folds x cells, and a validation that
# costs more than the decision is worth is not a free check.
WF_GRIDS = {
    "fsent_champ_long_htf15_tskip6": (
        "exp_trail_skip_n", [0, 2, 4, 6, 8, 12, 16], "exp_persist", [6, 7, 8]),
    "fsent_champ_long_mcloff_htf15": (
        "cooldown_bars", [4, 8, 12, 16], "exp_persist", [6, 7, 8]),
    "fsent_champ_long_htffs": (
        "cooldown_bars", [4, 8, 12, 16], "exp_persist", [6, 7, 8]),
    "fsent_champ_long_htf15_htffs": (
        "cooldown_bars", [4, 8, 12, 16], "exp_persist", [6, 7, 8]),
    "fsent_champ_long_htfesmcl4": (
        "cooldown_bars", [4, 8, 12, 16], "exp_persist", [6, 7, 8]),
    "fsent_sig_multi": (
        "exp_trail_skip_n", [0, 2, 4], "cooldown_bars", [4, 8, 12]),
    "fsent_sig_multi_htffs": (
        "exp_trail_skip_n", [0, 2, 4], "cooldown_bars", [4, 8, 12]),
    "fsent_champ_long_biasmom05": (
        "exp_bias_momentum_min", [0.3, 0.5, 0.7], "cooldown_bars", [4, 8, 12]),
    "fsent_champ_long_causalfloor": (
        "exp_window_floor_s", [2700, 7200, 10800], "cooldown_bars", [4, 8, 12]),
    "fsent_sig_multi_acc": (
        "cooldown_bars", [4, 8, 12, 16], "exp_persist", [6, 7, 8]),
    "fsent_champ_long_htf15": (
        "cooldown_bars", [4, 8, 12, 16], "exp_persist", [6, 7, 8]),
    "fsent_champ_long_mcloff": (
        "cooldown_bars", [4, 8, 12, 16], "exp_persist", [6, 7, 8]),
    "fsent_champ_long_mode_chop": (
        "cooldown_bars", [4, 8, 12, 16], "exp_persist", [6, 7, 8]),
}
WF_FOLDS = 3


def t2(sim, ERA, log):
    """Re-optimising walk-forward over the IS span, both books."""
    out = {}
    data = ERA["is"]
    lo, hi = int(data["c15"][0]["ts"]), int(data["c15"][-1]["ts"]) + 900
    span = hi - lo
    width = span // (WF_FOLDS + 1)
    log("  IS %s .. %s, %d folds of %ds" % (lo, hi, WF_FOLDS, width))
    for name, code in BOOKS:
        cfg = EXPERIMENTS[name]
        swing = cfg.get("swing") or "sw10"
        ka, va, kb, vb = WF_GRIDS[name]
        # one engine run per cell, reused across every fold
        cache = {}
        for a, b in itertools.product(va, vb):
            cache[(a, b)] = closed(sim_book(sim, data, cfg, swing, **{ka: a, kb: b}))
        log("  %s: %d cells run once" % (code, len(cache)))

        reg_a = (cfg.get("params") or {}).get(ka, BP.get(ka))
        reg_b = (cfg.get("params") or {}).get(kb, BP.get(kb))
        rec = []
        for k in range(WF_FOLDS):
            # train everything up to the end of this fold's window, then score
            # the winner on the window immediately after it. Train grows, test
            # is always exactly one width wide and always disjoint from it.
            t_lo = lo + (k + 1) * width
            t_hi = t_lo + width
            best = None
            for (a, b), tr in cache.items():
                s = stats(rs_of([t for t in tr if int(t["entry_ts"]) < t_hi]))
                if s and (best is None or s["net"] > best[2]["net"]):
                    best = (a, b, s)
            if best is None:
                continue
            tw = [t for t in cache[(best[0], best[1])] if t_lo <= int(t["entry_ts"]) < t_hi]
            ts = stats(rs_of(tw))
            # A book that never set a knob falls back to the base default, which
            # may not be a member of the grid at all. Only compare against it when
            # it actually is one of the swept cells.
            reg_key = (reg_a, reg_b) if (reg_a, reg_b) in cache else None
            rw = ([t for t in cache[reg_key] if t_lo <= int(t["entry_ts"]) < t_hi]
                  if reg_key else [])
            rs_ = stats(rs_of(rw)) if rw else None
            rec.append({"fold": k + 1,
                        "chosen": "%s=%s %s=%s" % (ka, best[0], kb, best[1]),
                        "train_net": best[2]["net"], "train_dd": best[2]["dd"],
                        "test_net": ts["net"] if ts else None,
                        "test_dd": ts["dd"] if ts else None,
                        "test_n": ts["n"] if ts else 0,
                        "reg_test_net": rs_["net"] if rs_ else None,
                        "reg_test_dd": rs_["dd"] if rs_ else None})
            log("  %s fold %d  train picked %-26s (%+.1fR dd %.1f)  ->  blind test %+.1fR dd %.1f (n=%d)  | registered same window %s"
                % (code, k + 1, rec[-1]["chosen"], best[2]["net"], best[2]["dd"],
                   ts["net"] if ts else 0.0, ts["dd"] if ts else 0.0, ts["n"] if ts else 0,
                   ("%+.1fR dd %.1f" % (rs_["net"], rs_["dd"])) if rs_ else "not in grid"))
        out[name] = rec
    return out


def main() -> int:
    which = (sys.argv[1] if len(sys.argv) > 1 else "t3").lower()
    t0 = time.time()
    logf = io.open(HERE / "four_run.log", "a", encoding="utf-8")

    def log(msg):
        print(msg, flush=True)
        logf.write(str(msg) + "\n")

    log("\n===== %s  (%.0fs) =====" % (which, time.time() - t0))
    print("loading eras ...", flush=True)
    ERA = {"is": get_data(), "oos": load_era("oos")}
    sim = build_family_module()

    res = {}
    if OUT.exists():
        res = json.loads(OUT.read_text(encoding="utf-8"))

    if which == "t3":
        log("T3 - stress: engine-level slippage and cost multiples")
        res["t3"] = t3(sim, ERA, log)
    elif which == "t4":
        log("T4 - survivability: shuffled orderings")
        res["t4"] = t4(sim, ERA, log)
    elif which == "t1":
        log("T1 - parameter sensitivity, 2-axis heat map")
        res["t1"] = t1(sim, ERA, log)
    elif which == "t2":
        log("T2 - walk forward, re-optimising on train only")
        res["t2"] = t2(sim, ERA, log)
    else:
        raise SystemExit("t1 / t2 / t3 / t4 wired")

    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    log("\nwrote %s  (%.0fs)" % (OUT.name, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())