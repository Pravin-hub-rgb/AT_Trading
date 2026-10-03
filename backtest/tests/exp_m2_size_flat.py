"""Flat-book M2 bigleg sizing: the confirming run (2026-09-26).

Stage O (24.60) measured M2 (cur_mag_atr >= 3.0, x1.5) on the Stage-B stack
books (half+delay1 [+skip_decisive] for champion/utcsat, retest for age10).
The end-of-session side-by-side (24.77) flagged that a FLAT-book M2 number
does not exist, so flat adoption needs one confirming run. This is that run.

Identical to exp_m2_size_phase2.py EXCEPT the lanes carry no arm flags:
every book is the raw config (flat), i.e. champion 500t/+325.8 IS, 279t/+70.2
OOS; utcsat 454t/+358.9 IS, 253t/+60.2 OOS (asserted below - abort if the
book is not the known flat reference).

PRE-REGISTERED BEFORE THE RUN (2026-09-26):
  flag = cur_mag_atr >= 3.0; size = 1.5; no other maps.
  Lanes: champion / utcsat / age10 cand configs, NO arm flags. Scopes: IS+OOS.
  PASS = dNet > 0 AND curve_better TRUE in ALL 6 cells (3 lanes x 2 eras)
  - the same strictness Stage O passed on the stack books.
  Identity: trade key sequence (entry_ts, exit_ts) byte-identical before/after;
  ONLY r_multiple differs on flagged rows (sizing exemption: sizing never
  changes which trades fire, so post-process = path-true by construction).
RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_m2_size_flat.py
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

OUT = ROOT / "backtest/tests/_m2_size_flat_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 1.5
M2_MIN_ATR = 3.0

# Flat reference ledgers (asserted): the books must be the raw configs.
EXPECT_FLAT = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (453, 279.5), "oos": (254, 66.9)},
}

LANES = (
    ("champion", "champion_multi_sw10", {}),
    ("utcsat", "utcsat_multi_sw10", {}),
    ("age10", "age10_dirmatch_swingpause_single_sw10", {}),
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
    print(f"  FLAT-BOOK M2 BIGLEG (x{SIZE} on cur_mag_atr>={M2_MIN_ATR}, no arm flags)", flush=True)
    print("=" * 100, flush=True)

    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "m2_size_flat",
        "lens": "post-process sizing on FLAT books; identity = same trade keys; no automatic gate",
        "flag": f"cur_mag_atr >= {M2_MIN_ATR}", "size": SIZE,
        "years": YEARS, "scopes": {},
        "pre_registered": "PASS = dNet>0 AND curve_better TRUE in all 6 cells (3 lanes x 2 eras)",
        "baseline_reference": "champion 500/+325.8 IS, 279/+70.2 OOS; utcsat 453/+279.5 IS, 253/+60.2 OOS (asserted)",
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

            m_flat = equity_quality(trades, yrs)
            if name in EXPECT_FLAT:
                exp_n, exp_net = EXPECT_FLAT[name][scope]
                assert m_flat["n"] == exp_n, (
                    f"flat ledger n mismatch {name}/{scope}: "
                    f"{m_flat['n']} != {exp_n} - not the flat reference book")
                assert abs(m_flat["net"] - exp_net) < 0.5, (
                    f"flat ledger net mismatch {name}/{scope}: "
                    f"{m_flat['net']} != {exp_net} - not the flat reference book")
                print(f"  [ledger-ok] {name}/{scope}: n={m_flat['n']} "
                      f"net={m_flat['net']:+.1f} matches reference", flush=True)

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

    cells = [verdicts[n][k] for n, _, _ in LANES
             for k in ("curve_better_is", "curve_better_oos")]
    nets = [verdicts[n][k] for n, _, _ in LANES
            for k in ("net_positive_both",)]
    payload["pass_all_6"] = all(cells) and all(nets)
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nPRE-REGISTERED RULE: {'PASS 6/6' if payload['pass_all_6'] else 'FAIL'}", flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
