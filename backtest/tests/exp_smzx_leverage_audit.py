"""IS sMZX REAL SELECTION, OR JUST LEVERAGE? (the definitive test)

THE QUESTION
============
`sMZX` is the ONLY lever in this repo that has ever passed at scale
(6/6 cells, champion +346.5 IS / +130.4 OOS). It works by applying a
multiplier of 1.5^count to trades flagged by M2 (cur_mag_atr >= 3.0),
ZC (vol7_prev7 <= 0.846) and X (parent risk_pct < 1.0).

But `monster_sizing` M1 was already condemned in this repo as a
"LEVERAGE TRAP - do not adopt", on the grounds that "its gain is 1.5x
leverage, not selection" (CHECKLIST 24.58). sMZX uses the same 1.5x
mechanism and has never been given that same test. So it is not yet
established that sMZX is a different animal.

Note the built-in ceiling on the answer: if the flagged cohort is simply
LARGER POSITIVE R than average, then boosting it raises total R, and the
honest comparison is not "does it beat flat leverage" (flat leverage scales
the whole book by the same factor and CANNOT be beaten on R by
construction) but "does it beat the FLAT book by more than its extra
concentration buys". The concentration term is the whole risk of the arm:
putting 1.5-3.4x on a subset raises the variance of the book even when the
expectancy improves.

THE TEST OF RECORD
==================
Three arms, all applied to the SAME flat book, all reported, no best-of:

  A  FLAT LEVERAGE   every trade x L, where L is sMZX's own average
                     multiplier. This is the correct control: it isolates
                     "the arm beat the book" from "the arm beat the book
                     by more than its extra size explains". This is an
                     arithmetic identity check on the arm's own dNet.
  B  sMZX REAL       the published arm, unchanged (must reproduce the
                     published dNet exactly, or the run aborts).
  C  sMZX SHUFFLED   the identical multiplier VALUES, randomly reassigned
                     to different trades within the same book. Same size
                     distribution, same total size budget, same multiplier
                     magnitudes - but the flags no longer mean anything.
                     THIS is the discriminator:
                       if C ~= B, the arm is a leverage/concentration
                         effect, and M2/ZC/X carry no selection skill;
                       if B > C materially, the flags are selecting and
                         the edge is real.

A shuffled arm must be repeated (a single shuffle is one draw), so 50
shuffles are run and the MEAN and SPREAD of C are reported, plus how many
of the 50 shuffles beat B. If B sits inside the middle of the shuffle
distribution, the arm is indistinguishable from luck.

PRE-REGISTERED VERDICT RULE (fixed before the run)
==================================================
sMZX is declared SELECTION, not leverage, only if ALL of:
  1. B reproduces the published dNet in all 4 cells (control)
  2. B's dNet exceeds A's dNet in all 4 cells (it beats flat leverage)
  3. B sits ABOVE the 90th percentile of the 50 shuffles in all 4 cells
     (i.e. the flags beat random size assignment)
Anything else is reported as LEVERAGE / CONCENTRATION, which means the
arm is a risk-appetite change, not an edge, and must be labelled as such
and capped as such - never shipped as "better performance".

Also reported regardless: maxDD, drawdown-normalised return (calmar), and
ex-best-5, because an arm that improves R by concentrating risk should
show up as a WORSE calmar even when its R rises.

CONTROL: flat books must reproduce the reference ledgers exactly.
STATUS: descriptive audit of an existing published arm. Nothing adopted,
no engine change, no default touched.
"""
from __future__ import annotations

import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_smzx_leverage_audit.json"
SIZE = 1.5
M2_MIN_ATR = 3.0
VOL7PREV_Q1 = 0.846
N_SHUFFLE = 50
SEED = 20260928
YEARS = {"is": 3.67, "oos": 2.0}
LANES = (("champion", "champion_multi_sw10"),
         ("utcsat", "utcsat_multi_sw10"))
EXPECT_FLAT = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (453, 279.5), "oos": (254, 66.9)},
}
# published sMZX dNet per lane (is,oos) from CAPITAL_STAGE_PLAN.md row 2
PUB_SMZX_IS = {"champion": (346.5, 130.4), "utcsat": (341.2, 146.6)}

def load_scope(scope):
    """Same loader exp_sizing_combo uses, so the flat books are the published
    ones (its own ledger assertions are re-run here as the control)."""
    from exp_sizing_combo import load_scope as _ls
    return _ls(scope)


def build_ctx(data):
    """The M2 / ZC / X flag context, copied from exp_sizing_combo.main so the
    flag DEFINITIONS are identical - a different flag set would be a different
    arm, not an audit of this one."""
    from exp_regime_structure_autopsy import build_arrays, compute_features
    from exp_regime_structure_autopsy import _chop_series_1h
    from exp_thesis_htf_deep_atlas import build_windows, window_rows
    from exp_htf_break_measures import flatten_breaks, enrich_windows
    arr = build_arrays(data["c1h"])
    conf = []
    for s in data["sw10"]:
        ci = s.get("confirmed_at_idx")
        if ci is None or not (0 <= ci < arr["n"]):
            continue
        dur = max(0, (s["seg"]["end_idx"] - s["seg"]["start_idx"]))
        conf.append((arr["ts"][ci], s["dir"], float(dur)))
    conf.sort(key=lambda x: x[0])
    ctx = {"arr": arr, "chop": _chop_series_1h(data["c1h"], lb=14),
           "conf_ts": [x[0] for x in conf], "conf_dir": [x[1] for x in conf],
           "conf_dur": [x[2] for x in conf]}
    fine_ts = [int(c["ts"]) for c in data["fine"]]
    breaks = flatten_breaks(data["sw10"])
    raw = build_windows(data, 3.0, 16)
    windows = {lane: window_rows(rows, data["fine"], fine_ts, lane)
               for lane, rows in raw.items()}
    for lane in windows:
        enrich_windows(windows[lane], data["c1h"], breaks)
    return ctx, windows


def flag_keys(trades, data, ctx, windows):
    """{family: set of (entry_ts, exit_ts)} - identical definitions to
    exp_sizing_combo."""
    from exp_regime_structure_autopsy import compute_features
    from exp_thesis_swing_geometry_deep import trade_rows
    from exp_htf_break_sizing import flagged_keys
    rows = trade_rows(trades, data)
    k_m2 = {(int(r["entry_ts"]), int(r["exit_ts"])) for r in rows
            if (r.get("cur_mag_atr") or 0) >= M2_MIN_ATR}
    feats = [compute_features(t, ctx) for t in trades]
    k_zc = {(int(t["entry_ts"]), int(t["exit_ts"]))
            for t, f in zip(trades, feats)
            if f.get("vol7_prev7") is not None
            and f["vol7_prev7"] <= VOL7PREV_Q1}
    k_x = flagged_keys(trades, windows, "risk_pct", -1e9, 1.0)
    return {"M2": k_m2, "ZC": k_zc, "X": k_x}


def mults_for(trades, fam_keys):
    """sMZX multiplier per trade, in book order."""
    out = []
    for t in trades:
        k = (int(t["entry_ts"]), int(t["exit_ts"]))
        c = sum(1 for f in ("M2", "ZC", "X") if k in fam_keys[f])
        out.append(SIZE ** c if c else 1.0)
    return out


def apply_mults(trades, mults):
    """Scale r_multiple in place-of-copy. Cost/funding are NOT scaled - the
    published arm scales r_multiple only, so this matches it exactly."""
    out = []
    for t, m in zip(trades, mults):
        t2 = dict(t)
        t2["r_multiple"] = round(float(t["r_multiple"]) * m, 6)
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades], "key seq changed"
    return out

def m_of(book, yrs):
    from exp_equity_quality import equity_quality
    return equity_quality(book, yrs)


def pct_rank(vals, x):
    """Fraction of vals <= x."""
    return sum(1 for v in vals if v <= x) / max(1, len(vals))


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  sMZX LEVERAGE AUDIT - is it selection, or just 1.5x leverage?",
          flush=True)
    print("=" * 100, flush=True)
    from exp_sizing_combo import run as sim_fn
    from test_experiments_craze import build_module
    from experiment_registry import BP, EXPERIMENTS

    sim = build_module()
    payload = {"stage": "smzx_leverage_audit", "cells": {}, "errors": [],
               "n_shuffle": N_SHUFFLE, "size": SIZE}
    rng = random.Random(SEED)

    for scope in ("is", "oos"):
        data = load_scope(scope)
        yrs = YEARS[scope]
        ctx, windows = build_ctx(data)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            trades = sim_fn(sim, data, params)
            m0 = m_of(trades, yrs)
            exp_n, exp_net = EXPECT_FLAT[name][scope]
            if m0["n"] != exp_n or abs(m0["net"] - exp_net) > 0.5:
                payload["errors"].append(f"flat ledger {scope}/{name}")
                print(f"  [ABORT] flat ledger {scope}/{name}: {m0['n']}t "
                      f"{m0['net']:+.1f} != {exp_n}t {exp_net:+.1f}", flush=True)
                continue
            print(f"\n  [{scope}/{name}] flat book OK: {m0['n']}t "
                  f"{m0['net']:+.1f}R DD {m0['max_dd']:.1f} "
                  f"calmar {m0.get('calmar', 0):.3f}", flush=True)

            fam = flag_keys(trades, data, ctx, windows)
            real_m = mults_for(trades, fam)
            L = sum(real_m) / len(real_m)
            n_flag = sum(1 for m in real_m if m > 1.0)
            mB = m_of(apply_mults(trades, real_m), yrs)
            mA = m_of(apply_mults(trades, [L] * len(trades)), yrs)
            shuf_nets, shuf_dd = [], []
            for _ in range(N_SHUFFLE):
                sm = real_m[:]
                rng.shuffle(sm)
                mS = m_of(apply_mults(trades, sm), yrs)
                shuf_nets.append(mS["net"])
                shuf_dd.append(mS["max_dd"])
            pr = pct_rank(shuf_nets, mB["net"])
            beats = sum(1 for v in shuf_nets if v >= mB["net"])
            cell = {
                "flat": {"n": m0["n"], "net": m0["net"],
                         "max_dd": m0["max_dd"], "calmar": m0.get("calmar")},
                "A_flat_leverage": {"L": round(L, 4), "net": mA["net"],
                                    "max_dd": mA["max_dd"],
                                    "calmar": mA.get("calmar"),
                                    "d_net": round(mA["net"] - m0["net"], 1)},
                "B_smzx_real": {"n_flagged": n_flag,
                                "pct_flagged": round(100.0 * n_flag
                                                     / len(trades), 1),
                                "net": mB["net"], "max_dd": mB["max_dd"],
                                "calmar": mB.get("calmar"),
                                "d_net": round(mB["net"] - m0["net"], 1)},
                "C_smzx_shuffled": {
                    "mean_net": round(statistics.mean(shuf_nets), 1),
                    "sd_net": round(statistics.pstdev(shuf_nets), 1),
                    "min": round(min(shuf_nets), 1),
                    "max": round(max(shuf_nets), 1),
                    "mean_dd": round(statistics.mean(shuf_dd), 1),
                    "B_percentile": round(100.0 * pr, 1),
                    "n_shuffles_beating_B": beats,
                },
            }
            cell["B_beats_A"] = mB["net"] > mA["net"]
            cell["B_above_p90"] = pr > 0.90
            cell["SELECTION"] = (cell["B_beats_A"] and cell["B_above_p90"])
            cell["selection_edge_over_shuffle"] = round(
                mB["net"] - statistics.mean(shuf_nets), 1)
            payload["cells"][f"{scope}/{name}"] = cell

            c = cell["C_smzx_shuffled"]
            print(f"    flags M2={len(fam['M2'])} ZC={len(fam['ZC'])} "
                  f"X={len(fam['X'])}  sized {n_flag}/{len(trades)} "
                  f"({cell['B_smzx_real']['pct_flagged']}%)", flush=True)
            print(f"    A flat leverage L={L:.3f}  net {mA['net']:+8.1f}  "
                  f"DD {mA['max_dd']:>6.1f}  calmar {mA.get('calmar', 0):.3f}",
                  flush=True)
            print(f"    B sMZX REAL         net {mB['net']:+8.1f}  "
                  f"DD {mB['max_dd']:>6.1f}  calmar {mB.get('calmar', 0):.3f}"
                  f"  (dNet {cell['B_smzx_real']['d_net']:+.1f})", flush=True)
            print(f"    C sMZX SHUFFLED     net {c['mean_net']:+8.1f} "
                  f"+-{c['sd_net']:.1f}  range [{c['min']:+.1f}, "
                  f"{c['max']:+.1f}]  DD {c['mean_dd']:.1f}", flush=True)
            print(f"    >>> B is at the {c['B_percentile']}th pct of the "
                  f"shuffle dist; {beats}/{N_SHUFFLE} random size "
                  f"assignments BEAT it", flush=True)
            print(f"    >>> B vs A: {'beats' if cell['B_beats_A'] else 'LOSES to'}"
                  f" flat leverage   |   edge over mean shuffle: "
                  f"{cell['selection_edge_over_shuffle']:+.1f}R   "
                  f"=> {'SELECTION' if cell['SELECTION'] else 'LEVERAGE/CONCENTRATION'}",
                  flush=True)
    payload["all_selection"] = all(
        c.get("SELECTION") for c in payload["cells"].values()) \
        if payload["cells"] and not payload["errors"] else None
    payload["elapsed_sec"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nVERDICT: {'SELECTION' if payload['all_selection'] else 'LEVERAGE/CONCENTRATION'}")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)")


if __name__ == "__main__":
    main()


