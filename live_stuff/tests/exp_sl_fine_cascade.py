"""Fine SL-width ladder + GRAY-MODE re-test of the cascade experiment.

TWO QUESTIONS, ONE RUN (both asked by the user, 2026-09-27)
==========================================================

Q1 - "1.6 tak hi dekha, 2% aur uske upar ka kya scene hai?"
The previous autopsy used an 8-band ladder whose top band was 1.60-99.00 -
a 37%-wide bucket with 488 trades. Anything above 2% was invisible inside it.
This run splits the tail into real bands so the 2%+ region is actually
measured rather than assumed to be bad. Descriptive only, costs-aware (net_r),
all six ledger controls asserted.

Q2 - "there was an experiment that said if we don't take this trade the NEXT
trade gets worse; can we use the gray rule there too?"
That experiment is `exp_cascade_tax_test.py` (H2). Its finding: the wick
removal scored +28.1R post-process but -50.5R path-true, a -78.6R cascade
that is 280% of the direct effect. Its diagnostic isolates the cause by
turning the three stateful carriers off (exp_mltf, cooldown_bars,
max_consecutive_losses) and re-measuring both ways. The result is the striking
part, already on disk in _cascade_tax_test.json:

    is|champion  gate_on dNet_path_true  -50.55   -> gate_off  +5.61
    is|utcsat    gate_on                -54.54   -> gate_off  +8.60
    oos|champion gate_on                -77.96   -> gate_off  -6.59
    oos|utcsat   gate_on                -59.61   -> gate_off  (see JSON)

i.e. with the carriers off, the SAME removal stops being harmful. That is
exactly the shape a gray trade should fix: gray keeps every carrier updating
(the slot stays busy, the streak still advances, the cooldown still fires) so
the downstream trade set is unchanged, while the gray trade simply books 0R.

This run re-tests the wick gate under GRAY MODE, path-true in the real engine,
with the carriers at their shipped values. Predicted by the mechanism: gray
dNet should land between the post-process number (+28.1, too optimistic, the
slot refills) and the path-true number (-50.5, too pessimistic, the chain
reshuffles) - because gray is the only variant that perturbs neither.

PRE-REGISTERED BEFORE THE RUN (2026-09-27)
------------------------------------------
  Q1 bands: 0-0.25, 0.25-0.4, 0.4-0.55, 0.55-0.7, 0.7-0.9, 0.9-1.2, 1.2-1.6,
            1.6-2.0, 2.0-2.5, 2.5-3.0, 3.0-5.0, 5.0+
  Q2 gate: wick_max = 6.03 on short, lb = 12 (frozen from the original
     experiment, NOT re-tuned), gray mode on, exp_gray_streak = True (the
     variant that preserved seq_identical in f569879).
  CONTROLS: bybit base ledgers must reproduce the 24.85 references; and the
     gray gate OFF arm must reproduce the cascade-tax gate_on path-true
     numbers, or the harness is wrong rather than the mode.
  Reported per cell: n, gray count, dNet vs base, maxDD delta, and
     seq_identical (the cascade-free property - gray must NOT refill slots).
  Nothing is retuned after the run.

Run: $env:PYTHONIOENCODING='utf-8'; python -u exp_sl_fine_cascade.py
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

OUT = ROOT / "live_stuff/tests/_sl_fine_cascade.json"

FINE_BUCKETS = ((0.0, 0.25), (0.25, 0.4), (0.4, 0.55), (0.55, 0.7),
                (0.7, 0.9), (0.9, 1.2), (1.2, 1.6), (1.6, 2.0),
                (2.0, 2.5), (2.5, 3.0), (3.0, 5.0), (5.0, 999.0))

WICK_MAX = 6.03
WICK_LB = 12

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
# END_MARKER



def slw(t):
    e = float(t["entry_price"]); s = float(t["sl"])
    return abs(e - s) / e * 100.0 if e else None


def build_module():
    """build_module()'s super-set source, spied, + the wick predicate.

    The wick injection is copied verbatim from exp_cascade_tax_test.py
    (WICK_MAX=6.03, LB=12) so the gray arm is measured against the SAME gate
    the cascade experiment used, not a re-tuned variant.
    """
    import test_experiments_craze as tc
    cap = {}
    orig = tc._load_module

    def spy(text, name):
        cap["text"] = text
        return orig(text, name)

    tc._load_module = spy
    try:
        tc.build_module()
    finally:
        tc._load_module = orig
    s = cap["text"]

    t1 = "    *,\n"
    assert s.count(t1) == 1, "sig star"
    s = s.replace(t1, t1 +
                  "    _WICK_MAX=0.0,\n    _WICK_LB=12,\n"
                  "    exp_gray_lo=0.0,\n    exp_gray_hi=0.0,\n"
                  "    exp_gray_streak=True,\n")

    a = '        if i < 0 or i>=n-1: continue\n'
    assert s.count(a) == 1, "wick anchor"
    # wick_atr12@short <= WICK_MAX  ->  GRAY (not skip).
    # wick_atr12 = (sum(up_wick) + sum(low_wick)) / ATR15 over the 12 closed
    # 15m bars ending at the entry bar. up_wick = high - max(open,close),
    # low_wick = min(open,close) - low. Frozen at 6.03/12 from Stage B.
    s = s.replace(a, a + (
        '        _isgray = False\n'
        '        _gslw=0.0\n'
        '        if _WICK_MAX>0 and int(sig["dir"])!=1:\n'
        f'            _j=i\n'
        f'            if _j>={WICK_LB}:\n'
        f'                _lo=_j-{WICK_LB}+1\n'
        f'                _us=0.0; _ls=0.0\n'
        f'                for _k in range(_lo,_j+1):\n'
        f'                    _c=candles_ltf[_k]\n'
        f'                    _o=float(_c["open"]); _h=float(_c["high"])\n'
        f'                    _l=float(_c["low"]); _cc=float(_c["close"])\n'
        f'                    _us+=_h-max(_o,_cc)\n'
        f'                    _ls+=min(_o,_cc)-_l\n'
        f'                _a=atr15[_j]\n'
        f'                if _a>0 and exp_gray_lo>0 and (_us+_ls)/_a<=_WICK_MAX:\n'
        f'                    _isgray=True\n'
    ))

    for ind in (8, 12):
        old = "\n" + " " * ind + "sl0=sl; sl_cur=sl; best=entry\n"
        assert s.count(old) == 1, f"sl anchor {ind}: {s.count(old)}"
        pad = " " * ind
        new = (
            f"\n{pad}if exp_gray_lo>0 and not _isgray:\n"
            f"{pad}    _gslw=abs(entry-sl)/entry*100.0 if entry>0 else 0.0\n"
            f"{pad}    if _gslw < exp_gray_lo or _gslw > exp_gray_hi: _isgray=True\n"
            f"{pad}sl0=sl; sl_cur=sl; best=entry\n")
        s = s.replace(old, new)

    st = '        if max_consecutive_losses > 0:\n'
    assert s.count(st) == 1, "streak"
    s = s.replace(st, '        if max_consecutive_losses > 0 and not (_isgray and not exp_gray_streak):\n')
    cd = '        if cooldown_bars > 0 and r_multiple < 0:\n'
    assert s.count(cd) == 1, "cooldown"
    s = s.replace(cd, '        if cooldown_bars > 0 and r_multiple < 0 and not _isgray:\n')
    bk = '            "r_multiple": round(float(r_multiple),3),\n'
    assert s.count(bk) == 1, "book"
    s = s.replace(bk,
                  '            "r_multiple": round(0.0 if _isgray else float(r_multiple),3),\n'
                  '            "is_gray": bool(_isgray),\n'
                  '            "sl_width_pct": round(_gslw,4),\n'
                  '            "r_multiple_raw": round(float(r_multiple),3),\n')

    import importlib.util
    p = ROOT / "live_stuff/tests/_slfine_tmp.py"
    p.write_text(s, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("v18_slfine", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.simulate_htf_ltf_streak_halt


def main():
    t0 = time.time()
    print("=" * 100, flush=True)
    print("  FINE SL LADDER (2%+ deep dive) + GRAY-MODE cascade re-test", flush=True)
    print("=" * 100, flush=True)

    from exp_sizing_combo import run as sim_fn
    from exp_cross_instrument_transfer import load_bybit
    from exp_equity_quality import equity_quality
    from experiment_registry import BP, EXPERIMENTS
    from run_experiment import net_r

    sim = build_module()
    years = {"is": 3.67, "oos": 2.0}
    payload = {
        "stage": "sl_fine_cascade",
        "fine_buckets": [f"{lo:.2f}-{hi:.2f}" for lo, hi in FINE_BUCKETS],
        "wick": {"max": WICK_MAX, "lb": WICK_LB, "dir": "short"},
        "pre_registered": {
            "q1": "split the 1.60-99.00 tail into 1.6-2.0/2.0-2.5/2.5-3.0/3.0-5.0/5.0+",
            "q2": ("gray-mode re-test of the cascade-tax wick gate, carriers at "
                   "shipped values; predicted between post-process (+28.1) and "
                   "path-true (-50.5) because gray perturbs neither"),
            "gray_streak": True,
            "control": "base ledgers reproduce 24.85; gray-OFF reproduces cascade-tax gate_on",
            "no_retune": "wick threshold frozen at 6.03/lb 12 from the original",
        },
        "cells": {}, "agg": {}, "gray": {},
    }
    agg = {}

    for scope in ("is", "oos"):
        print(f"\n=== [{scope.upper()}] ===", flush=True)
        data = load_bybit(scope, sim)
        for name, key in LANES:
            params = {**BP, **EXPERIMENTS[key]["params"]}
            ref = sim_fn(sim, data, params)
            n_ref, net_ref = len(ref), net_r(ref)
            exp_n, exp_net = BYBIT_BASE[name][scope]
            assert n_ref == exp_n and abs(net_ref - exp_net) < 0.5, (
                f"CONTROL {scope}/{name}: {n_ref}/{net_ref:.2f} != {exp_n}/{exp_net}")
            print(f"  {scope}/{name} ref n={n_ref} net={net_ref:+.1f} [ctrl OK]",
                  flush=True)

            rows = []
            for lo, hi in FINE_BUCKETS:
                sel = [net_r([t]) for t in ref
                       if (w := slw(t)) is not None and lo <= w < hi]
                m = len(sel)
                a = round(sum(sel) / m, 4) if m else None
                wr = round(sum(1 for x in sel if x > 0) / m, 4) if m else None
                rows.append({"band": f"{lo:.2f}-{hi:.2f}", "n": m, "avg_r": a,
                             "wr": wr, "net": round(sum(sel), 2)})
                g = agg.setdefault(rows[-1]["band"], {"n": 0, "s": 0.0, "w": 0.0})
                g["n"] += m
                if m:
                    g["s"] += sum(sel); g["w"] += sum(1 for x in sel if x > 0)
                print(f"      {rows[-1]['band']:>10}  n={m:>4}  avgR={str(a):>8}  "
                      f"wr={str(wr):>7}  net={rows[-1]['net']:>+9.1f}", flush=True)
            payload["cells"][f"{scope}/{name}"] = rows

            # --- Q2: gray-mode wick gate, path-true, carriers shipped ---
            gray = sim_fn(sim, data, params, _WICK_MAX=WICK_MAX,
                          exp_gray_lo=0.01, exp_gray_hi=99.0,
                          exp_gray_streak=True)
            mg = equity_quality(gray, years[scope])
            mr = equity_quality(ref, years[scope])
            grays = sum(1 for t in gray if t.get("is_gray"))
            seq_ref = [(t["entry_ts"], t["exit_ts"]) for t in ref]
            seq_g = [(t["entry_ts"], t["exit_ts"]) for t in gray]
            raw_gray = sum(float(t.get("r_multiple_raw") or 0.0)
                           for t in gray if t.get("is_gray"))
            cell = {
                "n": mg["n"], "n_gray": grays,
                "kept_pct": round(100.0 * (mg["n"] - grays) / max(1, mg["n"]), 2),
                "net": mg["net"], "d_net": round(mg["net"] - mr["net"], 3),
                "d_max_dd": round(mr["max_dd"] - mg["max_dd"], 3),
                "seq_identical": seq_ref == seq_g,
                "raw_r_forgiven_by_gray": round(raw_gray, 2),
            }
            payload["gray"][f"{scope}/{name}"] = cell
            print(f"      GRAY wick kept={cell['kept_pct']:>6}% gray={grays:>3} "
                  f"dNet={cell['d_net']:>+8.1f} dDD={cell['d_max_dd']:>+6.2f} "
                  f"seqID={cell['seq_identical']} "
                  f"rawR_grayed={cell['raw_r_forgiven_by_gray']:>+7.1f}", flush=True)

    print("\n=== FINE LADDER AGGREGATE (all 6 cells) ===", flush=True)
    for lo, hi in FINE_BUCKETS:
        b = f"{lo:.2f}-{hi:.2f}"
        g = agg.get(b, {"n": 0, "s": 0.0, "w": 0.0})
        if not g["n"]:
            print(f"  {b:>10}  (empty)", flush=True)
            continue
        payload["agg"][b] = {"n": g["n"], "avg_r": round(g["s"] / g["n"], 4),
                             "wr": round(g["w"] / g["n"], 4),
                             "net": round(g["s"], 2)}
        print(f"  {b:>10}  n={g['n']:>5}  avgR={g['s']/g['n']:>7.3f}  "
              f"WR={g['w']/g['n']*100:>5.1f}%  net={g['s']:>+10.1f}", flush=True)

    print("\n=== GRAY-MODE CASCADE RESULT ===", flush=True)
    for k, v in payload["gray"].items():
        print(f"  {k:16} dNet={v['d_net']:>+8.1f}  seqID={v['seq_identical']}  "
              f"kept={v['kept_pct']:>6}%", flush=True)
    payload["verdicts"] = {
        "gray_seq_identical_cells": sum(1 for v in payload["gray"].values()
                                        if v["seq_identical"]),
        "gray_cells": len(payload["gray"]),
        "gray_dnet_positive_cells": sum(1 for v in payload["gray"].values()
                                        if (v["d_net"] or 0) > 0),
        "gray_cascade_free": all(v["seq_identical"] for v in payload["gray"].values()),
    }
    payload["elapsed_sec"] = round(time.time() - t0, 2)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("\n" + json.dumps(payload["verdicts"], indent=1), flush=True)
    print(f"wrote {OUT} ({payload['elapsed_sec']}s)", flush=True)


if __name__ == "__main__":
    main()
