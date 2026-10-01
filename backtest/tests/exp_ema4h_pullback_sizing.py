"""Stage Y — 4h EMA-extension path-true promotions (closes Stage 12's open item).

Stage 12 (CHECKLIST 24.12) recorded: "4h `pullback_toward_ema` is positive in
both eras for all three [references], but is not adopted without a
pre-registered path-true test." This harness runs exactly that.

Feature (entry-causal, reused verbatim from exp_boundary_state_autopsy):
  cutoff = entry_ts + 900 (entry bar close); hours completed before cutoff
  -> aggregate 4h; ema4h20 + atr4h; signed4 = dir * (price - ema20)/atr4h.
  buckets: <=-0.5 opposite_ema | (-0.5,0] pullback_toward_ema |
  (0,1) aligned_near_ema | [1,2) aligned_extended | >=2 aligned_far_extended.

Pre-registered arms (post-process; identity = same trade-key sequence):
  A PRIMARY: x1.5 size where bucket == pullback_toward_ema.
     Pass = dNet>0 AND curve_better in all 4 cells (champion/utcsat x IS/OOS).
     fullstack single reported as reference only (6th cell, not in pass rule).
  B EXPLORATORY: skip aligned_far_extended (Stage 12: IS+ / OOS- -> predicted
     FAIL era-flip).
  C EXPLORATORY: skip opposite_ema (mixed across refs/eras -> predicted FAIL).
  D COMBO: A sizing + B skip together (reported regardless; interpretable only
     if B itself passes).

Not run (closed families, do NOT re-test): 4h direction-confirm
(exp_htf4_confirm DEAD, LOG 2026-09-23), 1h-swing direction confirm (exp_mtf_mode
DEAD), weekly-boundary path-true (Stage 13), boundary-state gates.

Sanity pre-flight: descriptive pullback bucket must reproduce Stage 12 sums
(champion IS n=71 gross +117.3; OOS n=42 +37.8; utcsat IS n=60 +120.2;
OOS n=37 +41.9; fullstack IS n=29 +104.0, OOS n=21 +27.6).

RESEARCH_POLICY: report raw P&L + equity + caveats; no automatic gate.
Run: $env:PYTHONIOENCODING='utf-8'; python -u backtest/tests/exp_ema4h_pullback_sizing.py
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
from test_experiments_craze import build_module
from exp_boundary_state_autopsy import load_scope, obs_ts, ema_state, classify_extension
from exp_equity_quality import equity_quality, arm_scores, curve_better

OUT = ROOT / "backtest/tests/_ema4h_pullback_sizing_results.json"
YEARS = {"is": 3.67, "oos": 2.0}
SIZE = 1.5
PULLBACK = "pullback_toward_ema"
LANES = (
    ("champion", "champion_multi_sw10"),
    ("utcsat", "utcsat_multi_sw10"),
    ("fullstack", "fullstack_wage10_cd0_single_sw10"),
)
# Stage-12 sanity targets: (lane, era) -> (n, gross_sum)
SANITY = {
    ("champion", "is"): (71, 117.3), ("champion", "oos"): (42, 37.8),
    ("utcsat", "is"): (60, 120.2), ("utcsat", "oos"): (37, 41.9),
    ("fullstack", "is"): (29, 104.0), ("fullstack", "oos"): (21, 27.6),
}


def annotate(trades, c1h):
    out = []
    for t in trades:
        st = ema_state(c1h, obs_ts(t), float(t["entry_price"]))
        b = classify_extension(t, st, st)
        out.append((t, b))
    return out


def key(t):
    return (int(t["entry_ts"]), int(t["exit_ts"]))


def main():
    t0 = time.time()
    print("=" * 110, flush=True)
    print(f"  STAGE Y — 4h EMA-EXTENSION PATH-TRUE (A: x{SIZE} on pullback_toward_ema; "
          f"B skip far_extended; C skip opposite_ema; D combo)", flush=True)
    print("=" * 110, flush=True)
    sim = build_module()
    payload = {
        "instrument": "BTCUSDT_BYBIT", "stage": "ema4h_pullback_sizing",
        "lens": "post-process; identity = same trade keys; no automatic gate",
        "arms": {"A": f"x{SIZE} where ema4h_bucket == {PULLBACK}",
                 "B": "skip aligned_far_extended",
                 "C": "skip opposite_ema",
                 "D": "A + B combined"},
        "years": YEARS, "scopes": {},
    }
    sanity_ok = True
    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] years={YEARS[scope]} ===", flush=True)
        data = load_scope(scope)
        yrs = YEARS[scope]
        sc = {}
        for name, keyname in LANES:
            params = {**BP, **EXPERIMENTS[keyname]["params"]}
            params.setdefault("exp_partial_r", 0.0)
            out = sim(data["c1h"], data["sw10"], data["c15"], data["sw15"],
                      fine_ltf=data["fine"], **params)
            trades = out["ltf_trades"] if isinstance(out, dict) else out
            ann = annotate(trades, data["c1h"])

            # sanity: reproduce Stage-12 pullback descriptives
            pb = [(t, b) for t, b in ann if b == PULLBACK]
            sn, ss = SANITY[(name, scope)]
            got_n = len(pb)
            got_sum = sum(float(t["r_multiple"]) for t, _ in pb)
            ok = (got_n == sn) and abs(got_sum - ss) < 0.6
            sanity_ok = sanity_ok and ok
            print(f"\n  {name} (n={len(trades)})  pullback n={got_n} "
                  f"gross={got_sum:+.1f} [Stage12: n={sn} {ss:+.1f}] "
                  f"{'OK' if ok else '*** MISMATCH ***'}", flush=True)

            pb_keys = {key(t) for t, _ in pb}
            fe_keys = {key(t) for t, b in ann if b == "aligned_far_extended"}
            oe_keys = {key(t) for t, b in ann if b == "opposite_ema"}
            m_flat = equity_quality(trades, yrs)

            books = {"flat": (m_flat, 0)}
            sized = []
            for t in trades:
                t2 = dict(t)
                if key(t) in pb_keys:
                    t2["r_multiple"] = round(float(t["r_multiple"]) * SIZE, 6)
                sized.append(t2)
            assert [key(t) for t in sized] == [key(t) for t in trades], "key seq changed"
            books["A"] = (equity_quality(sized, yrs), len(pb_keys))
            books["B"] = (equity_quality([t for t in trades if key(t) not in fe_keys],
                                         yrs), len(fe_keys))
            books["C"] = (equity_quality([t for t in trades if key(t) not in oe_keys],
                                         yrs), len(oe_keys))
            combo = [t for t in sized if key(t) not in fe_keys]
            books["D"] = (equity_quality(combo, yrs), len(pb_keys))

            sc[name] = {"n": m_flat["n"], "buckets": {}}
            # descriptive bucket net table (context)
            from collections import defaultdict
            grp = defaultdict(list)
            for t, b in ann:
                grp[b].append(t)
            for b, ts in sorted(grp.items()):
                sc[name]["buckets"][b] = {"n": len(ts),
                                          "gross": round(sum(float(x["r_multiple"]) for x in ts), 2)}
            print(f"    {'arm':<5} {'n':>4} {'net':>8} {'DD':>6} {'ulcer':>7} "
                  f"{'sort':>7} {'calmar':>7} {'streak':>6} {'PF':>6} {'dNet':>8} curve", flush=True)
            print(f"    {'flat':<5} {m_flat['n']:>4} {m_flat.get('net', 0):>+8.1f} "
                  f"{m_flat.get('max_dd', 0):>6.1f} {m_flat.get('ulcer', 0):>7.2f} "
                  f"{m_flat.get('sortino', 0):>7.2f} {m_flat.get('calmar', 0):>7.3f} "
                  f"{m_flat.get('max_streak', 0):>6} {m_flat.get('pf', 0):>6.2f}", flush=True)
            for arm in ("A", "B", "C", "D"):
                m, nk = books[arm]
                d = arm_scores(m, m_flat)
                small = " SMALL-N" if 0 < nk < 20 else ""
                print(f"    {arm:<5} {m['n']:>4} {m.get('net', 0):>+8.1f} "
                      f"{m.get('max_dd', 0):>6.1f} {m.get('ulcer', 0):>7.2f} "
                      f"{m.get('sortino', 0):>7.2f} {m.get('calmar', 0):>7.3f} "
                      f"{m.get('max_streak', 0):>6} {m.get('pf', 0):>6.2f} "
                      f"{d.get('d_net', 0):>+8.1f} {curve_better(d)}{small}", flush=True)
                sc[name][arm] = {"n_affected": nk, "metric": m, "delta": d,
                                 "curve_better": curve_better(d)}
        payload["scopes"][scope] = sc

    print("\n=== CROSS-ERA VERDICT (champion/utcsat = pass cells; fullstack = reference) ===", flush=True)
    verdicts = {}
    for name, _ in LANES:
        for arm in ("A", "B", "C", "D"):
            d_is = payload["scopes"]["is"][name][arm]["delta"]
            d_oos = payload["scopes"]["oos"][name][arm]["delta"]
            ni = payload["scopes"]["is"][name][arm]["n_affected"]
            no = payload["scopes"]["oos"][name][arm]["n_affected"]
            v = {"n_is": ni, "n_oos": no,
                 "d_net_is": d_is.get("d_net"), "d_net_oos": d_oos.get("d_net"),
                 "d_dd_is": d_is.get("d_max_dd"), "d_dd_oos": d_oos.get("d_max_dd"),
                 "curve_better_is": curve_better(d_is),
                 "curve_better_oos": curve_better(d_oos)}
            v["pass"] = (v["d_net_is"] or 0) > 0 and (v["d_net_oos"] or 0) > 0 and \
                        v["curve_better_is"] and v["curve_better_oos"]
            verdicts[f"{name}_{arm}"] = v
            print(f"  {name:<10} {arm}  n {ni}/{no}  dNet {v['d_net_is']:+8.1f}/"
                  f"{v['d_net_oos']:+7.1f}  dDD {v['d_dd_is']:+6.1f}/{v['d_dd_oos']:+6.1f}  "
                  f"curve {v['curve_better_is']}/{v['curve_better_oos']}  PASS={v['pass']}",
                  flush=True)
    multi_pass = {a: verdicts[f"champion_{a}"]["pass"] and verdicts[f"utcsat_{a}"]["pass"]
                  for a in ("A", "B", "C", "D")}
    payload["verdicts"] = verdicts
    payload["multi_lane_pass"] = multi_pass
    payload["sanity_ok"] = sanity_ok
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nmulti-lane pass (champion AND utcsat): {multi_pass}")
    print(f"sanity (Stage-12 reproduction): {'OK' if sanity_ok else 'FAILED'}")
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
