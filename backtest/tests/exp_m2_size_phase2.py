"""Stage O — M2 bigleg sizing Phase 2: full equity-lens on sized books.

Phase 1 (Stage M / 24.58) showed M2 (cur_mag_atr >= 3.0 at entry) is a
genuine quality flag: avgR flagged > unflagged BOTH eras ALL 3 lanes,
monster-enriched, ~3x leverage-matched expectation.

Phase 2 (this): apply x1.5 sizing to flagged trades on the FULL trade list
(post-process - sizing does not feed back into entry decisions), and score
the ENTIRE book with equity_quality (DD, ulcer, sortino, calmar, streak, PF)
vs the flat book. Identity check: trade key sequence (entry_ts/exit_ts/slug)
byte-identical before/after; ONLY r_multiple differs on flagged rows.

Pre-registered: flag = cur_mag_atr >= 3.0; size = 1.5; no other maps
(M1/M3/M4 rejected in Phase 1 for leverage-trap / era-flip).
Lanes: champion/utcsat/age10 cand arms. Scopes: IS + OOS.
RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_m2_size_phase2.py
"""
from __future__ import annotations

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
from test_experiments_craze import build_module
from test_4_new_concepts import load_fine_1m, load_unseen
from src.btc.btc_routes import _compute_swings
from engine.v18_params import SWING
from exp_thesis_swing_geometry_deep import trade_rows

from exp_equity_quality import equity_quality, arm_scores, curve_better

OUT = ROOT / "backtest/tests/_m2_size_phase2_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 1.5
M2_MIN_ATR = 3.0

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


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print(f"  STAGE O — M2 BIGLEG SIZING PHASE 2 (x{SIZE} on cur_mag_atr>={M2_MIN_ATR}, equity-lens)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "m2_size_phase2",
        "lens": "post-process sizing; identity = same trade keys; no automatic gate",
        "flag": f"cur_mag_atr >= {M2_MIN_ATR}", "size": SIZE,
        "years": YEARS, "scopes": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        sc = {}
        for name, key, flags in LANES:
            cfg = EXPERIMENTS[key]
            params = {**BP, **cfg["params"]}
            params.setdefault("exp_partial_r", 0.0)
            trades = run(sim, data, params, **flags)
            rows = trade_rows(trades, data)
            row_keys = {(int(r["entry_ts"]), int(r["exit_ts"])) for r in rows}
            flagged_keys = {(int(r["entry_ts"]), int(r["exit_ts"])) for r in rows
                            if (r.get("cur_mag_atr") or 0) >= M2_MIN_ATR}

            sized = []
            for t in trades:
                t2 = dict(t)
                if (int(t["entry_ts"]), int(t["exit_ts"])) in flagged_keys:
                    t2["r_multiple"] = round(float(t["r_multiple"]) * SIZE, 6)
                sized.append(t2)
            # identity: same keys, only r_multiple differs on flagged rows
            assert [(t["entry_ts"], t["exit_ts"]) for t in sized] == \
                   [(t["entry_ts"], t["exit_ts"]) for t in trades], "key sequence changed"
            n_flag_full = sum(1 for t in trades
                              if (int(t["entry_ts"]), int(t["exit_ts"])) in flagged_keys)

            m_flat = equity_quality(trades, yrs)
            m_size = equity_quality(sized, yrs)
            d = arm_scores(m_size, m_flat)
            sc[name] = {
                "n": m_flat["n"], "n_flagged": n_flag_full,
                "pct_flagged": round(100.0 * n_flag_full / len(trades), 1),
                "flat": m_flat, "sized": m_size, "delta": d,
                "identity_ok": True,
                "rows_covered": f"{len(row_keys)}/{len(trades)}",
            }
            print(f"\n  {name} (flagged {n_flag_full}/{len(trades)} = "
                  f"{sc[name]['pct_flagged']}%, rows {sc[name]['rows_covered']})", flush=True)
            print(f"    {'book':<8} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
                  f"{'sort':>7} {'calmar':>7} {'streak':>6} {'PF':>6}", flush=True)
            for lbl, m in (("flat", m_flat), ("sized", m_size)):
                print(f"    {lbl:<8} {m['n']:>4} {m.get('net', 0):>+8.1f} "
                      f"{m.get('max_dd', 0):>6.1f} {m.get('ulcer', 0):>7.2f} "
                      f"{m.get('sortino', 0):>7.2f} {m.get('calmar', 0):>7.3f} "
                      f"{m.get('max_streak', 0):>6} {m.get('pf', 0):>6.2f}", flush=True)
            print(f"    delta: dNet {d.get('d_net'):+.1f} dDD {d.get('d_max_dd'):+.1f} "
                  f"dUlcer {d.get('d_ulcer'):+.2f} curve_better={curve_better(d)}", flush=True)
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA VERDICT (sized vs flat) ===", flush=True)
    verdicts = {}
    for name, _, _ in LANES:
        d_is = payload["scopes"]["is"][name]["delta"]
        d_oos = payload["scopes"]["oos"][name]["delta"]
        v = {
            "d_net_is": d_is.get("d_net"), "d_net_oos": d_oos.get("d_net"),
            "d_dd_is": d_is.get("d_max_dd"), "d_dd_oos": d_oos.get("d_max_dd"),
            "curve_better_is": curve_better(d_is),
            "curve_better_oos": curve_better(d_oos),
        }
        v["net_positive_both"] = (v["d_net_is"] or 0) > 0 and (v["d_net_oos"] or 0) > 0
        v["curve_pass_both"] = v["curve_better_is"] and v["curve_better_oos"]
        verdicts[name] = v
        print(f"  {name:<10} dNet {v['d_net_is']:+8.1f}/{v['d_net_oos']:+7.1f} "
              f"dDD {v['d_dd_is']:+6.1f}/{v['d_dd_oos']:+6.1f} "
              f"curve {v['curve_pass_both']} net+ {v['net_positive_both']}", flush=True)
    payload["verdicts"] = verdicts
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
