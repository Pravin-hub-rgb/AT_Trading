"""SL-WIDTH sizing - tests the user's ORIGINAL causal sizing idea, directly.

THE IDEA BEING TESTED
---------------------
"when the SL is bigger, we can take 1.5x R on those trades only, because
those trades tend to have a higher success rate."

This has been tested three times in the repo, none of which is this exact arm:
  - ANCHOR_BASIS_AUDIT 3e (risk-width, 2026-09-20): remove wide-SL trades.
    FAILED - removal reshuffles the path-dependent cascade.
  - Stage M / M1 (monster, 2026-09-25): flag broadly, size 1.5x. FAILED as a
    "leverage trap" - flagged avgR WORSE than unflagged (dNet = pure leverage).
  - Stage X / A (HTF break, 2026-09-25): x1.5 on parent risk_pct < 1.0 (TIGHT
    sl). PASS 4/4 but on n=7/9 OOS - and that is the OPPOSITE direction to the
    user's claim (tight, not wide). So it is not a test of this idea either.
  - M2 (cur_mag_atr >= 3): PROXIMATE to "wide" but it reads seg.end_px, which
    is forward-looking. Non-deployable as measured.

So the wide-SL SIZING arm has genuinely never been run. This harness runs it
and - more importantly - tests the underlying CLAIM (wide SL => higher success
rate) separately from the sizing result, because a sizing arm can pass its
dNet gate for pure-leverage reasons even when the underlying claim is false.

CAUSALITY (why this is cleaner than M2)
---------------------------------------
Every trade record carries `entry_price` and `sl` (v18_streak_halt.py:732-733),
both fixed AT ENTRY. So

    sl_width_pct = |entry_price - sl| / entry_price * 100

is known at the moment of entry and involves no end-of-segment price. This is
the causal substitute for M2's cur_mag_atr. It is a post-process SIZING read
(sizing exemption: multipliers never change which trades fire, so the trade-key
sequence is identical and this is a real measurement, not an upper bound).

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
-------------------------------------------
  Lanes: champion / utcsat / age10. Scopes: IS (2023+) / OOS (2021-22).
  Control: base ledgers must reproduce the 24.85 references or abort.
  Arm: size x1.5 on trades in the TOP HALF of sl_width_pct within the book
       (median split, per-cell - a threshold-free, per-book split, NOT a
       hand-picked absolute number, to avoid overfitting the gate).
  PASS (per arm) requires ALL of:
    1. CLAIM holds: mean r_multiple of wide-SL trades > narrow-SL trades, in
       EVERY cell (6/6). This is the user's actual hypothesis, tested first.
    2. dNet > 0 in every cell.
    3. curve_better in every cell.
    4. Not a leverage trap: flagged mean_r strictly greater than the per-cell
       book mean (the Stage-M M1 failure mode).
    5. Beats a matched-count random null at the 90th percentile.
  NULL: x1.5 on a random subset of the SAME flagged count, 200 seeds/cell.
  Nothing is retuned after the run. If the CLAIM (1) fails in any cell, the
  arm is dead regardless of its dNet - that is the whole point of running this.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_sl_width_sizing.py
"""
from __future__ import annotations

import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "live_stuff/tests/_sl_width_sizing.json"
SIZE = 1.5
SEEDS = 200
RNG = 0x517  # fixed for reproducibility

BYBIT_BASE = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)


def sl_width_pct(t):
    """Stop distance as % of entry. Known at entry - no lookahead."""
    e = float(t["entry_price"])
    s = float(t["sl"])
    return abs(e - s) / e * 100.0 if e else None


def wide_keys(trades):
    """Top-half sl_width trades (median split per book). Returns (keys, n_wide)."""
    ws = [(sl_width_pct(t), (int(t["entry_ts"]), int(t["exit_ts"]))) for t in trades]
    ws = [(w, k) for w, k in ws if w is not None]
    if not ws:
        return set(), 0
    ws.sort()
    med = ws[len(ws) // 2][0]
    return {k for w, k in ws if w >= med}, len(ws)


def apply_size(trades, keys, mult=SIZE):
    out = []
    for t in trades:
        t2 = dict(t)
        if (int(t["entry_ts"]), int(t["exit_ts"])) in keys:
            t2["r_multiple"] = round(float(t["r_multiple"]) * mult, 6)
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades], "key sequence changed"
    return out


def claim_holds(trades, keys):
    """The user's actual hypothesis: wide-SL trades average more R."""
    fw = [float(t["r_multiple"]) for t in trades
          if (int(t["entry_ts"]), int(t["exit_ts"])) in keys]
    fn = [float(t["r_multiple"]) for t in trades
          if (int(t["entry_ts"]), int(t["exit_ts"])) not in keys]
    if not fw or not fn:
        return None
    return {
        "wide_mean_r": round(sum(fw) / len(fw), 4),
        "narrow_mean_r": round(sum(fn) / len(fn), 4),
        "n_wide": len(fw), "n_narrow": len(fn),
        "wide_wr": round(sum(1 for x in fw if x > 0) / len(fw), 4),
        "narrow_wr": round(sum(1 for x in fn if x > 0) / len(fn), 4),
        "wide_beats_narrow": (sum(fw) / len(fw)) > (sum(fn) / len(fn)),
    }


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  SL-WIDTH SIZING - the user's causal 'wide SL => size up' idea", flush=True)
    print("=" * 100, flush=True)

    from test_experiments_craze import build_module
    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import load_bybit
    from exp_equity_quality import equity_quality, arm_scores, curve_better
    from experiment_registry import BP, EXPERIMENTS

    sim = build_module()
    years = {"is": 3.67, "oos": 2.0}
    payload = {
        "stage": "sl_width_sizing",
        "lens": ("post-process sizing on flat books; trade keys identical; "
                 "sl_width_pct = |entry-sl|/entry, known at entry (no end_px)"),
        "arm": f"x{SIZE} on top-half sl_width_pct (median split per book)",
        "pre_registered": {
            "pass": ("CLAIM(wide mean_r > narrow, 6/6) AND dNet>0 6/6 AND "
                     "curve_better 6/6 AND not-leverage-trap 6/6 AND "
                     "beats matched null at 90th pct 6/6"),
            "claim_first": "the hypothesis is tested BEFORE the sizing result",
            "null": "x1.5 on random subset of same flagged count, 200 seeds",
            "control": "base ledgers reproduce the 24.85 references",
            "no_retune": "nothing retuned after the run",
        },
        "scopes": {}, "verdicts": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_bybit(scope, sim)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            trades = sim_fn(sim, data, params)
            m_base = equity_quality(trades, years[scope])
            exp_n, exp_net = BYBIT_BASE[name][scope]
            assert trades and m_base["n"] == exp_n, (
                f"CONTROL FAIL {scope}/{name} n: {m_base['n']} != {exp_n}")
            assert abs(m_base["net"] - exp_net) < 0.5, (
                f"CONTROL FAIL {scope}/{name} net: {m_base['net']} != {exp_net}")

            keys, n_wide = wide_keys(trades)
            cl = claim_holds(trades, keys)
            m_arm = equity_quality(apply_size(trades, keys), years[scope])
            d = arm_scores(m_arm, m_base)
            d_net, cb = d.get("d_net"), curve_better(d)
            book_mean = m_base["net"] / m_base["n"]
            leverage_trap = cl["wide_mean_r"] <= book_mean

            all_keys = [(int(t["entry_ts"]), int(t["exit_ts"])) for t in trades]
            rng = random.Random(RNG)
            null_nets, null_cbs = [], 0
            for _ in range(SEEDS):
                rk = set(rng.sample(all_keys, n_wide))
                dn = arm_scores(equity_quality(apply_size(trades, rk),
                                               years[scope]), m_base)
                null_nets.append(dn.get("d_net") or 0.0)
                if curve_better(dn):
                    null_cbs += 1
            null_nets.sort()
            pct = round(100.0 * sum(1 for x in null_nets if x < d_net)
                        / len(null_nets), 1)

            cell = {
                "n": m_base["n"], "net": m_base["net"], "n_wide": n_wide,
                "claim": cl, "d_net": d_net, "curve_better": cb,
                "book_mean_r": round(book_mean, 4), "leverage_trap": leverage_trap,
                "real_percentile_vs_null": pct,
                "null_curve_pass_rate": round(100.0 * null_cbs / SEEDS, 1),
                "beats_null_90": pct >= 90.0,
                "claim_holds": cl["wide_beats_narrow"],
                "arm_pass": bool(cl["wide_beats_narrow"] and (d_net or 0) > 0
                                 and cb and not leverage_trap and pct >= 90.0),
            }
            payload["scopes"][f"{scope}/{name}"] = cell
            print(f"  {scope}/{name:<9} claim={cl['wide_beats_narrow']} "
                  f"wideR={cl['wide_mean_r']:+.3f} narrowR={cl['narrow_mean_r']:+.3f} "
                  f"| dNet={d_net:+.1f} curve={cb} trap={leverage_trap} "
                  f"pct={pct} pass={cell['arm_pass']}", flush=True)

    n_pass = sum(1 for c in payload["scopes"].values() if c["arm_pass"])
    n_claim = sum(1 for c in payload["scopes"].values() if c["claim_holds"])
    nc = len(payload["scopes"])
    payload["verdicts"] = {
        "cells": nc, "claim_holds_cells": n_claim, "arm_pass_cells": n_pass,
        "arm_is_real": n_pass == nc,
        "conclusion": ("wide-SL claim SUPPORTED in every cell and the sizing arm "
                       "is real" if n_pass == nc else
                       "wide-SL claim FAILS in at least one cell - the sizing "
                       "idea is not supported, regardless of dNet"),
    }
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print("\n" + "=" * 100, flush=True)
    v = payload["verdicts"]
    print(f"  CLAIM HOLDS: {v['claim_holds_cells']}/{v['cells']} cells", flush=True)
    print(f"  ARM PASS   : {v['arm_pass_cells']}/{v['cells']} cells", flush=True)
    print(f"  CONCLUSION : {v['conclusion']}", flush=True)
    print("=" * 100, flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
