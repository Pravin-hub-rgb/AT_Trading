"""Stage GateSize - PATH-TRUE gate + size combination (vol7_prev7<=1.20 x M2) (2026-09-26).

Closes REGIME_STRUCTURE_AUTOPSY.md L143: "Sizing flag and gate can combine, but
the combined effect is UNTESTED." Also closes the Stage-B rule gap for the Z3
gate itself: Z3 (thr 1.20) was measured as a POST-PROCESS removal, and under
exp_mltf a post-process skip is an UPPER BOUND never adoptable (LOG 80/81) -
so the gate must be re-run PATH-TRUE before any combined claim.

ARMS (per lane x scope):
  flat       shipped engine, no flags (asserts the flat reference books)
  flat_M2    flat book + post-process M2 sizing (x1.5 on cur_mag_atr>=3.0)
             CONTROL - must reproduce 24.78 dNet (champion +152.7/+29.1,
             utcsat +147.5/+31.3, age10 +113.0/+21.3; tolerance 1.0R)
  gate_off   PATCHED engine with _VOL_GATE=0 -> identity gate: entry_ts
             sequence + net MUST equal `flat` in all 6 cells (else void)
  gate_on    PATCHED engine, predicate injected after `if i<0 or i>=n-1:
             continue` BEFORE busy_until/cooldown/streak/book mutation:
             skip entry iff round(vol7_prev7, 3) > 1.20, where vol7_prev7 =
             (7d volume) / (prior 7d volume) over CLOSED UTC days at cutoff
             = entry bar ts + 900 (the autopsy obs_ts convention; day-level
             feature, identical formula to compute_features V6, rounded the
             same way; None-features kept, exactly like Z3)
  gate_M2    gate_on survivors + post-process M2 sizing (sizing exemption:
             multipliers never change which survivors fire)

PRE-REGISTERED BEFORE THE RUN (2026-09-26):
  1. Identity gate (gate_off == flat, all 6 cells) REQUIRED, else void.
  2. Formula-parity gate: for every flat trade, the in-engine replication
     (prefix-sum day volumes at cutoff entry_ts+900, rounded 3dp) must equal
     compute_features()'s vol7_prev7 exactly, else void.
  3. G-RULE for gate_on (ported from Z3, now 6 cells, ALL must pass):
     kept 70-90% AND avgNet/trade >= flat AND maxDD(R) <= flat.
  4. COMBINED headline vs FLAT: dNet>0 AND curve_better TRUE in all 6 cells.
  5. COMBINED marginal vs gate_on: dNet>0 AND curve_better TRUE in all 6 cells.
     (Both pre-registered and both reported - no best-of hiding.)
  6. CASCADE comparison vs Z3 post-process (reference, not a gate):
     Z3 kept 80/79/77/78% (n 398/360/216/196 champ/uts IS + champ/uts OOS),
     avgNet up 4/4, maxDD down 4/4, dNet -61.1/-60.5 IS, +3.6/+15.0 OOS.
RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.

Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_gate_size_pathtrue.py
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
from run_experiment import net_r
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope, obs_ts
from exp_equity_quality import equity_quality, arm_scores, curve_better
from exp_regime_structure_autopsy import build_arrays, compute_features, _chop_series_1h
from exp_thesis_swing_geometry_deep import trade_rows

OUT = ROOT / "backtest/tests/_gate_size_pathtrue.json"
YEARS = {"is": 3.67, "oos": 2.0}
GATE = 1.20
M2_MIN_ATR = 3.0
M2_SIZE = 1.5

LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("age10", "age10_dirmatch_swingpause_single_sw10"),
)

EXPECT_FLAT = {
    "champion": {"is": (500, 325.8), "oos": (279, 70.2)},
    "utcsat": {"is": (454, 358.9), "oos": (253, 60.2)},
    "age10": {"is": (130, 435.7), "oos": (76, 43.2)},
}
EXPECT_M2 = {
    "champion": {"is": 152.7, "oos": 29.1},
    "utcsat": {"is": 147.5, "oos": 31.3},
    "age10": {"is": 113.0, "oos": 21.3},
}
Z3_POSTPROCESS = {
    "champion|is": {"n": 398, "kept": 0.80, "dNet": -61.1},
    "utcsat|is": {"n": 360, "kept": 0.79, "dNet": -60.5},
    "champion|oos": {"n": 216, "kept": 0.77, "dNet": 3.6},
    "utcsat|oos": {"n": 196, "kept": 0.78, "dNet": 15.0},
}

ANCHOR = "        if i < 0 or i>=n-1: continue\n"
INJECT = ANCHOR + (
    "        if _VOL_GATE > 0:\n"
    "            _cut = int(candles_ltf[i][\"ts\"]) + 900\n"
    "            _dmax = bisect.bisect_right(_DAYS, _cut // 86400 - 1) - 1\n"
    "            if _dmax >= 13:\n"
    "                _v7 = _DPREF[_dmax + 1] - _DPREF[_dmax - 6]\n"
    "                _p7 = _DPREF[_dmax - 6] - _DPREF[_dmax - 13]\n"
    "                if _p7 > 0 and round(_v7 / _p7, 3) > _VOL_GATE:\n"
    "                    continue\n"
)


def build_patched():
    """Craze super-set + one asserted, default-off gate patch (wick pattern)."""
    import test_experiments_craze as T

    orig_load = T._load_module
    captured = {}

    def spy(text, name):
        captured["text"] = text
        raise SystemExit(0)

    T._load_module = spy
    try:
        T.build_module()
    except SystemExit:
        pass
    finally:
        T._load_module = orig_load
    assert "text" in captured, "failed to capture craze super-set source"
    s = captured["text"]

    assert s.count(ANCHOR) == 1, f"LTF entry anchor count={s.count(ANCHOR)}"
    s = s.replace(ANCHOR, INJECT)

    fut = "from __future__ import annotations\n"
    if fut in s:
        assert s.count(fut) == 1, "future import anchor"
        s = s.replace(fut, fut + "\n_VOL_GATE = 0.0\n_DAYS = []\n_DPREF = []\n")
    else:
        s = "_VOL_GATE = 0.0\n_DAYS = []\n_DPREF = []\n" + s

    import importlib.util
    p = ROOT / "backtest/tests/_gate_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("gate_patched", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(fn, data, params):
    out = fn(data["c1h"], data["sw10"], data["c15"], data["sw15"],
             fine_ltf=data["fine"], **params)
    trades = out["ltf_trades"] if isinstance(out, dict) else out
    return sorted(trades, key=lambda t: int(t["entry_ts"]))


def m2_book(trades, data):
    rows = trade_rows(trades, data)
    assert len(rows) == len(trades), "trade_rows coverage"
    mag = {(int(r["entry_ts"]), int(r["exit_ts"])): (r.get("cur_mag_atr") or 0)
           for r in rows}
    out = []
    for t in trades:
        t2 = dict(t)
        if mag[(int(t["entry_ts"]), int(t["exit_ts"]))] >= M2_MIN_ATR:
            t2["r_multiple"] = round(float(t["r_multiple"]) * M2_SIZE, 6)
        out.append(t2)
    assert [(t["entry_ts"], t["exit_ts"]) for t in out] == \
           [(t["entry_ts"], t["exit_ts"]) for t in trades]
    return out


def parity_check(trades, data):
    """In-engine vol7_prev7 replication == compute_features, trade by trade."""
    arr = build_arrays(data["c1h"])
    days, pref = arr["days"], arr["dpref"]
    conf = []
    for s in data["sw10"]:
        ci = s.get("confirmed_at_idx")
        if ci is None or not (0 <= ci < arr["n"]):
            continue
        dur = max(0, (s["seg"]["end_idx"] - s["seg"]["start_idx"]))
        conf.append((arr["ts"][ci], s["dir"], float(dur)))
    conf.sort(key=lambda x: x[0])
    chop = _chop_series_1h(data["c1h"], lb=14)
    ctx = {"arr": arr, "chop": chop,
           "conf_ts": [x[0] for x in conf],
           "conf_dir": [x[1] for x in conf],
           "conf_dur": [x[2] for x in conf]}
    mism = 0
    c15_ts = {int(c["ts"]) for c in data["c15"]}
    not_bar = 0
    for t in trades:
        cut = obs_ts(t)
        dmax = bisect.bisect_right(days, cut // 86400 - 1) - 1
        mine = None
        if dmax >= 13:
            v7 = pref[dmax + 1] - pref[dmax - 6]
            p7 = pref[dmax - 6] - pref[dmax - 13]
            if p7 > 0:
                mine = round(v7 / p7, 3)
        theirs = compute_features(t, ctx).get("vol7_prev7")
        if mine != theirs:
            mism += 1
        if int(t["entry_ts"]) not in c15_ts:
            not_bar += 1
    return mism, not_bar, len(trades)


def qline(tag, base, other, yrs):
    qb, qo = equity_quality(base, yrs), equity_quality(other, yrs)
    d = arm_scores(qo, qb)
    cf = curve_better(d)
    return (f"  {tag:26s} n {len(base):4d}->{len(other):4d} "
            f"({100.0 * len(other) / len(base):5.1f}%)  "
            f"net {qb['net']:+8.1f}->{qo['net']:+8.1f} (d{qo['net'] - qb['net']:+7.1f})  "
            f"avg {net_r(base) / len(base):+.3f}->{net_r(other) / len(other):+.3f}  "
            f"DD {qb['max_dd']:5.1f}->{qo['max_dd']:5.1f}  "
            f"ulcer {qb['ulcer']:7.2f}->{qo['ulcer']:7.2f}  "
            f"calmar {qb['calmar']:.3f}->{qo['calmar']:.3f}  curve {cf}")


def main():
    t0 = time.time()
    print("=" * 116, flush=True)
    print(f"  STAGE GATESIZE - PATH-TRUE vol7_prev7<={GATE} GATE x M2 SIZING (combined, flat books)",
          flush=True)
    print("=" * 116, flush=True)

    ship = build_module()
    pmod = build_patched()
    patched = pmod.simulate_htf_ltf_streak_halt
    identity_ok = True
    parity_ok = True
    control_ok = True

    payload = {
        "instrument": "BTCUSDT_BYBIT",
        "stage": "gate_size_pathtrue",
        "gate": f"vol7_prev7 <= {GATE} (path-true, injected pre-state-mutation)",
        "m2": f"x{M2_SIZE} on cur_mag_atr >= {M2_MIN_ATR} (post-process on survivors)",
        "years": YEARS,
        "pre_registered": {
            "identity": "gate_off == flat all 6 cells (entry_ts seq + net)",
            "formula_parity": "injected vol7_prev7 == compute_features on every flat trade",
            "g_rule_gate_on": "kept 70-90% AND avgNet/trade>=flat AND maxDD<=flat, ALL 6 cells",
            "combined_vs_flat": "dNet>0 AND curve_better all 6 cells",
            "combined_vs_gated": "dNet>0 AND curve_better all 6 cells",
            "control_flat_M2": "dNet within 1.0R of 24.78 (champion +152.7/+29.1, utcsat +147.5/+31.3, age10 +113.0/+21.3)",
        },
        "z3_postprocess_reference": Z3_POSTPROCESS,
        "cells": {},
    }

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        arr = build_arrays(data["c1h"])
        pmod._DAYS = arr["days"]
        pmod._DPREF = arr["dpref"]
        pmod._VOL_GATE = 0.0

        for lane, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            flat = run(ship, data, params)

            exp_n, exp_net = EXPECT_FLAT[lane][scope]
            assert len(flat) == exp_n and abs(net_r(flat) - exp_net) < 0.5, (
                f"flat ledger mismatch {lane}/{scope}: {len(flat)}t/{net_r(flat):+.1f} "
                f"!= {exp_n}t/{exp_net:+.1f}")

            mism, not_bar, n_tr = parity_check(flat, data)
            if mism or not_bar:
                parity_ok = False
            print(f"  [{scope}|{lane}] flat {len(flat)}t net {net_r(flat):+.1f} "
                  f"(asserted)  parity mismatches {mism}/{n_tr}  "
                  f"entry_ts not a 15m bar open: {not_bar}", flush=True)

            off = run(patched, data, params)   # _VOL_GATE already 0
            same = (len(off) == len(flat)
                    and round(net_r(off), 6) == round(net_r(flat), 6)
                    and [t["entry_ts"] for t in off] == [t["entry_ts"] for t in flat])
            identity_ok &= same
            print(f"  [{scope}|{lane}] identity gate: {len(off)}t vs shipped "
                  f"{len(flat)}t -> {'IDENTICAL' if same else 'MISMATCH'}", flush=True)
            if not same:
                continue

            pmod._VOL_GATE = GATE
            gated = run(patched, data, params)
            pmod._VOL_GATE = 0.0

            flat_m2 = m2_book(flat, data)
            gate_m2 = m2_book(gated, data)

            d_m2 = arm_scores(equity_quality(flat_m2, yrs), equity_quality(flat, yrs))
            m2_ctrl = abs((d_m2.get("d_net") or 0) - EXPECT_M2[lane][scope]) <= 1.0
            control_ok &= m2_ctrl

            print("  " + qline(f"{scope}|{lane} gate_on vs flat", flat, gated, yrs))
            print("  " + qline(f"{scope}|{lane} gate+M2 vs flat", flat, gate_m2, yrs))
            print("  " + qline(f"{scope}|{lane} gate+M2 vs gated", gated, gate_m2, yrs))
            print("  " + qline(f"{scope}|{lane} flat_M2 ctrl (24.78)", flat, flat_m2, yrs)
                  + ("  ctrl-ok" if m2_ctrl else "  CTRL-MISMATCH"), flush=True)

            qf = equity_quality(flat, yrs)
            qg = equity_quality(gated, yrs)
            qgm = equity_quality(gate_m2, yrs)
            kept = len(gated) / len(flat)
            avg_flat = net_r(flat) / len(flat)
            avg_gate = net_r(gated) / len(gated)
            g_cell = (0.70 <= kept <= 0.90 and avg_gate >= avg_flat
                      and qg["max_dd"] <= qf["max_dd"])

            d_cf = arm_scores(qgm, qf)
            cf_flat = curve_better(d_cf)
            pass_cf = (d_cf.get("d_net") or 0) > 0 and cf_flat
            d_cg = arm_scores(qgm, qg)
            cf_gated = curve_better(d_cg)
            pass_cg = (d_cg.get("d_net") or 0) > 0 and cf_gated
            n_aff = sum(1 for a, b in zip(gated, gate_m2)
                        if a["r_multiple"] != b["r_multiple"])

            payload["cells"][f"{scope}|{lane}"] = {
                "flat_n": len(flat), "flat_net": round(net_r(flat), 2),
                "gate_n": len(gated), "gate_net": round(net_r(gated), 2),
                "kept": round(kept, 4),
                "z3_postprocess_n": Z3_POSTPROCESS.get(f"{lane}|{scope}", {}).get("n"),
                "z3_postprocess_dNet": Z3_POSTPROCESS.get(f"{lane}|{scope}", {}).get("dNet"),
                "gate_dNet_vs_flat": round(net_r(gated) - net_r(flat), 2),
                "g_rule_cell": g_cell,
                "avg_flat": round(avg_flat, 4), "avg_gate": round(avg_gate, 4),
                "dd_flat": qf["max_dd"], "dd_gate": qg["max_dd"],
                "parity_mismatches": mism, "identity": same,
                "flat_M2_dNet": round(d_m2.get("d_net") or 0, 2),
                "flat_M2_control_ok": m2_ctrl,
                "combined_vs_flat": {"d_net": d_cf.get("d_net"), "curve": cf_flat,
                                     "pass": pass_cf},
                "combined_vs_gated": {"d_net": d_cg.get("d_net"), "curve": cf_gated,
                                      "pass": pass_cg},
                "gate_M2_n_aff": n_aff,
                "gate_M2_eq": {"n": qgm["n"], "net": round(qgm["net"], 1),
                               "max_dd": qgm["max_dd"], "calmar": round(qgm["calmar"], 3)},
            }
            print(f"  [{scope}|{lane}] G-RULE cell: kept {kept:.1%} "
                  f"avg {avg_flat:+.3f}->{avg_gate:+.3f} "
                  f"DD {qf['max_dd']}->{qg['max_dd']} -> "
                  f"{'PASS' if g_cell else 'FAIL'} | combined vs flat "
                  f"{d_cf.get('d_net'):+.1f}/curve {cf_flat} -> "
                  f"{'PASS' if pass_cf else 'FAIL'} | vs gated "
                  f"{d_cg.get('d_net'):+.1f}/curve {cf_gated} -> "
                  f"{'PASS' if pass_cg else 'FAIL'} | M2-nAff {n_aff}"
                  + ("" if n_aff >= 20 else " SMALL-N"), flush=True)

    cells = payload["cells"]
    print("\n=== PRE-REGISTERED VERDICTS ===", flush=True)
    payload["identity_ok"] = identity_ok
    payload["parity_ok"] = parity_ok
    payload["flat_M2_control_ok"] = control_ok
    all6 = len(cells) == 6
    g_all = all6 and all(c["g_rule_cell"] for c in cells.values())
    cf_all = all6 and all(c["combined_vs_flat"]["pass"] for c in cells.values())
    cg_all = all6 and all(c["combined_vs_gated"]["pass"] for c in cells.values())
    payload["g_rule_pass_all_6"] = g_all
    payload["combined_vs_flat_pass_all_6"] = cf_all
    payload["combined_vs_gated_pass_all_6"] = cg_all
    print(f"  identity gate (required)      : {identity_ok}", flush=True)
    print(f"  formula-parity gate (required): {parity_ok}", flush=True)
    print(f"  flat_M2 control vs 24.78      : {control_ok}", flush=True)
    print(f"  G-RULE gate_on all 6 cells    : {g_all}", flush=True)
    print(f"  COMBINED vs FLAT all 6 cells  : {cf_all}", flush=True)
    print(f"  COMBINED vs GATED all 6 cells : {cg_all}", flush=True)
    if all6:
        print("\n  cascade vs Z3 post-process (champion/utcsat):", flush=True)
        for lane in ("champion", "utcsat"):
            for sc in ("is", "oos"):
                c = cells[f"{sc}|{lane}"]
                z = Z3_POSTPROCESS[f"{lane}|{sc}"]
                print(f"    {lane:<10} {sc:<3} n {z['n']}->{c['gate_n']}  "
                      f"dNet pp {z['dNet']:+7.1f} -> path-true "
                      f"{c['gate_dNet_vs_flat']:+7.1f}", flush=True)

    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
