"""Stage Z2 - path-true sizing/gate test on Z1 regime-structure survivors.

Z1 (exp_regime_structure_autopsy) survivors - pre-registered rule
(same-sign 4/4 + monotone >=3/4 cells + n>=15):

  er50            50-bar 1h Kaufman ER, LOW better   (IS edges Q1 <= 0.0767)
  wick_gt3x_pct12 % of last 12 1h bars with wick > 3x body, HIGH better
                  (IS edge Q3 > 33.30)
  vol7_prev7      7d / prior-7d rolling volume, DECLINING better
                  (IS edge Q1 <= 0.846)

Arms (post-process, identity = same trade-key sequence; engine untouched):
  A x1.5 sizing where er50 <= 0.0767
  B x1.5 sizing where wick_gt3x_pct12 > 33.30
  C x1.5 sizing where vol7_prev7 <= 0.846
  D EXPLORATORY gate: skip trades where vol7_prev7 > 1.064 (bad bucket is
     net-negative in OOS but POSITIVE in IS -> predicted FAIL / era-flip)

Pre-registered PASS (each sizing arm): dNet > 0 AND curve_better in all 4
cells (champion/utcsat x IS/OOS). Flag counts reported; n<20 -> SMALL-N caveat.
RESEARCH_POLICY: no automatic gate; report raw P&L + equity + caveats.
Run: $env:PYTHONIOENCODING='utf-8'; python -u live_stuff/tests/exp_regime_structure_sizing.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "live_stuff/tests"))
sys.path.insert(0, str(ROOT / "live_stuff"))
sys.path.insert(0, str(ROOT / "backend"))

from experiment_registry import BP, EXPERIMENTS
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope
from exp_equity_quality import equity_quality, arm_scores, curve_better
from exp_regime_structure_autopsy import build_arrays, compute_features
from exp_htf_break_sizing import size_book, skip_book

OUT = ROOT / "live_stuff/tests/_regime_structure_sizing_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 1.5
LANES = (("champion", "champion_multi_sw10"), ("utcsat", "utcsat_multi_sw10"))
ER50_Q1 = 0.0767
WICK3X_Q3 = 33.30
VOL7PREV_Q1 = 0.846
VOL7PREV_Q2 = 1.064

ARMS = (
    ("A", "size", lambda f: f.get("er50") is not None and f["er50"] <= ER50_Q1,
     f"x{SIZE} where er50 <= {ER50_Q1}"),
    ("B", "size", lambda f: f.get("wick_gt3x_pct12") is not None
     and f["wick_gt3x_pct12"] > WICK3X_Q3,
     f"x{SIZE} where wick_gt3x_pct12 > {WICK3X_Q3}"),
    ("C", "size", lambda f: f.get("vol7_prev7") is not None
     and f["vol7_prev7"] <= VOL7PREV_Q1,
     f"x{SIZE} where vol7_prev7 <= {VOL7PREV_Q1}"),
    ("D", "skip", lambda f: f.get("vol7_prev7") is not None
     and f["vol7_prev7"] > VOL7PREV_Q2,
     f"skip where vol7_prev7 > {VOL7PREV_Q2} (predicted FAIL)"),
)


def main():
    t0 = time.time()
    print("=" * 112, flush=True)
    print("  STAGE Z2 - REGIME-STRUCTURE SIZING (A/B/C x1.5 survivors; D predicted fail)",
          flush=True)
    print("=" * 112, flush=True)
    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT", "stage": "z2_regime_sizing",
        "lens": "post-process; identity = same trade keys; no automatic gate",
        "arms": {a: desc for a, _, _, desc in ARMS},
        "years": YEARS, "scopes": {},
    }
    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        arr = build_arrays(data["c1h"])
        # confirmed swing series (same as Z1)
        conf = []
        for s in data["sw10"]:
            ci = s.get("confirmed_at_idx")
            if ci is None or not (0 <= ci < arr["n"]):
                continue
            dur = max(0, (s["seg"]["end_idx"] - s["seg"]["start_idx"]))
            conf.append((arr["ts"][ci], s["dir"], float(dur)))
        conf.sort(key=lambda x: x[0])
        # chop needed by compute_features
        from exp_regime_structure_autopsy import _chop_series_1h
        chop = _chop_series_1h(data["c1h"], lb=14)
        ctx0 = {"arr": arr, "chop": chop,
                "conf_ts": [x[0] for x in conf],
                "conf_dir": [x[1] for x in conf],
                "conf_dur": [x[2] for x in conf]}
        sc = {}
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            feats = [compute_features(t, ctx0) for t in trades]
            m_flat = equity_quality(trades, yrs)
            lanes = {"flat": m_flat}
            sc[name] = {"n": m_flat["n"]}
            print(f"\n  {name} (n={m_flat['n']})", flush=True)
            for arm, mode, cond, _desc in ARMS:
                keys = {(int(t["entry_ts"]), int(t["exit_ts"]))
                        for t, f in zip(trades, feats) if cond(f)}
                book = size_book(trades, keys) if mode == "size" else skip_book(trades, keys)
                m = equity_quality(book, yrs)
                d = arm_scores(m, m_flat)
                lanes[arm] = (m, len(keys))
            print(f"    {'arm':<5} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
                  f"{'sort':>7} {'calmar':>7} {'streak':>6} {'PF':>6} {'dNet':>8} curve",
                  flush=True)
            print(f"    {'flat':<5} {m_flat['n']:>4} {m_flat.get('net', 0):>+8.1f} "
                  f"{m_flat.get('max_dd', 0):>6.1f} {m_flat.get('ulcer', 0):>7.2f} "
                  f"{m_flat.get('sortino', 0):>7.2f} {m_flat.get('calmar', 0):>7.3f} "
                  f"{m_flat.get('max_streak', 0):>6} {m_flat.get('pf', 0):>6.2f}",
                  flush=True)
            for arm, _m2, _c2, _d2 in ARMS:
                m, nk = lanes[arm]
                d = arm_scores(m, m_flat)
                small = " SMALL-N" if nk < 20 else ""
                print(f"    {arm:<5} {m['n']:>4} {m.get('net', 0):>+8.1f} "
                      f"{m.get('max_dd', 0):>6.1f} {m.get('ulcer', 0):>7.2f} "
                      f"{m.get('sortino', 0):>7.2f} {m.get('calmar', 0):>7.3f} "
                      f"{m.get('max_streak', 0):>6} {m.get('pf', 0):>6.2f} "
                      f"{d.get('d_net', 0):>+8.1f} {curve_better(d)}{small}", flush=True)
                sc[name][arm] = {"n_affected": nk, "metric": m, "delta": d,
                                 "curve_better": curve_better(d)}
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA VERDICT (per arm, per lane) ===", flush=True)
    verdicts = {}
    for name, _ in LANES:
        for arm, _m2, _c2, desc in ARMS:
            a_is = payload["scopes"]["is"][name][arm]
            a_oos = payload["scopes"]["oos"][name][arm]
            d_is, d_oos = a_is["delta"], a_oos["delta"]
            ni, no = a_is["n_affected"], a_oos["n_affected"]
            v = {"desc": desc, "n_is": ni, "n_oos": no,
                 "d_net_is": d_is.get("d_net"), "d_net_oos": d_oos.get("d_net"),
                 "d_dd_is": d_is.get("d_max_dd"), "d_dd_oos": d_oos.get("d_max_dd"),
                 "curve_better_is": curve_better(d_is),
                 "curve_better_oos": curve_better(d_oos),
                 "small_n": ni < 20 or no < 20}
            v["pass"] = (v["d_net_is"] or 0) > 0 and (v["d_net_oos"] or 0) > 0 and \
                        v["curve_better_is"] and v["curve_better_oos"]
            verdicts[f"{name}_{arm}"] = v
            print(f"  {name:<10} {arm}  n {ni}/{no}  dNet {v['d_net_is']:+8.1f}/"
                  f"{v['d_net_oos']:+7.1f}  dDD {v['d_dd_is']:+6.1f}/{v['d_dd_oos']:+6.1f}  "
                  f"curve {v['curve_better_is']}/{v['curve_better_oos']}  "
                  f"PASS={v['pass']} smallN={v['small_n']}", flush=True)
    payload["verdicts"] = verdicts
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
