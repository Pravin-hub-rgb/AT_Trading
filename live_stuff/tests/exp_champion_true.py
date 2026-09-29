"""P4 - THE CORRECT RUN. Reproduce champion_multi_sw10 first, then the floor.

WHY THIS FILE EXISTS - the mistake it is fixing
==============================================
P3-A..P3-D ran against the SHIPPED engine with `mode` values I guessed.
Those numbers are valid measurements of *a* book, but NOT of the champion.

  - P3-D's "champion" used mode=b2_vs_flip_chop, chop=61.8, cooldown=20,
    sl_buf=0.25, ext=1.5, mcl=5 -> IS 356t / +277.1R.
  - The real champion (experiment_registry.py:191-202) is
    mode=atr_high, atr_high_thresh=0.65, atr_low_thresh=0.35,
    sl_buf_atr=0.01, chop_thresh=58.0, cooldown_bars=8,
    max_consecutive_losses=3, ext_stop_r=3.0, exp_partial_r=0.0,
    exp_mltf=True, exp_persist=7, window_end=exit; swing=sw10;
    engine="patched".

Two of those are fatal to what I ran before:
  1. engine="patched" — `exp_mltf` and `exp_persist` DO NOT EXIST on the
     shipped engine. The champion is only reachable through
     test_experiments_craze.build_module().
  2. `net_r` is NOT sum(r_multiple) — it subtracts fees AND funding
     (run_experiment.py:121-124). The published pins are NET:
     IS 500 trades / +325.8R NET, from +445.2R GROSS. Comparing a gross
     number to a net pin is a category error, and that is the second
     reason 277.1 never became 325.8.

ORDER OF OPERATIONS - non-negotiable
====================================
  STEP 1  reproduce the pin exactly (IS 500/+325.8N, OOS 279/+70.2N).
          Hard fail otherwise, and print nothing else.
  STEP 2  identity gate the floored patch at floor=None.
  STEP 3  the floor grid + head-to-head.
"""
from __future__ import annotations

import bisect as bs
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("live_stuff/tests", "live_stuff", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
from test_experiments_craze import build_module, _compute_swings  # noqa: E402
from test_4_new_concepts import load_unseen  # noqa: E402
from test_4_new_concepts import load_fine_1m  # noqa: E402
from engine.v18_params import SWING  # noqa: E402

CFG = EXPERIMENTS["champion_multi_sw10"]
PARAMS = {**BP, **CFG["params"]}
PINS = {"is": (500, 325.8), "oos": (279, 70.2)}

_ORIG = ('            wend = _r_touch_end(t, fine_ltf, fine_ts, ext_stop_r) '
         'if window_end=="r_touch" else int(t["exit_ts"])\n'
         '            iv.append([int(t["entry_ts"]), wend, '
         '1 if t["dir"]=="long" else -1, float(t["entry_price"]), '
         'float(t["sl"])])')

_PATCHED = '''            wend = _r_touch_end(t, fine_ltf, fine_ts, ext_stop_r) if window_end=="r_touch" else int(t["exit_ts"])
            _a=int(t["entry_ts"]); _d=1 if t["dir"]=="long" else -1
            _p=float(t["entry_price"]); _s=float(t["sl"])
            _risk=abs(_p-_s)
            if live_r_floor is None or _risk<=0 or _a>=wend:
                iv.append([_a, wend, _d, _p, _s])
            else:
                _pxs=[float(c["close"]) for c in fine_ltf] if fine_ltf else []
                _run=None
                for _k in range(_a, wend+1, 60):
                    _j=bs.bisect_right(fine_ts,_k)-1
                    if _j<0 or _j>=len(_pxs): continue
                    _ok=(_d*(_pxs[_j]-_p))/_risk >= live_r_floor
                    if _ok and _run is None: _run=_k
                    if (not _ok) and _run is not None:
                        iv.append([_run,_k-1,_d,_p,_s]); _run=None
                if _run is not None: iv.append([_run,wend,_d,_p,_s])'''


def build_floored():
    """Champion's PATCHED engine, plus our kwarg and the interval split.

    `test_experiments_craze.SRC` is the engine's SOURCE TEXT (line 23),
    and build_module() rewrites that text, writes `_craze_tmp.py` and
    imports it. So we hand it our modified text instead - that keeps every
    champion kwarg (exp_mltf, exp_persist, ...) intact, which is the whole
    point of P4, and adds only the floor.
    """
    import test_experiments_craze as T
    original = T.SRC
    if _ORIG not in original:
        raise SystemExit("PATCH TARGET MISSING in the engine source text")
    out = original.replace(_ORIG, _PATCHED)
    t1 = "    *,\n"
    assert out.count(t1) == 1, "signature star anchor moved"
    out = out.replace(t1, t1 + "    live_r_floor=None,\n")
    saved, T.SRC = T.SRC, out
    try:
        return build_module()
    finally:
        T.SRC = saved


def tm(x):
    if not x:
        return 0.0
    x = sorted(x)
    k = max(1, len(x) // 20)
    return sum(x) / len(x) if len(x) <= k else sum(x[:-k]) / (len(x) - k)


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def maxdd(rs):
    eq = peak = dd = 0.0
    for x in rs:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def stats(tr):
    rs = [float(t["r_multiple"]) for t in tr if t.get("outcome") != "open"]
    n = len(rs)
    if not n:
        return "n=0", 0.0, 0
    return (f"n={n:<4} netNET={net_r(tr):+8.1f}  "
            f"WR={100.0*sum(1 for x in rs if x>0)/n:>5.1f}%  PF={pf(rs):>5.2f}"
            f"  tm={tm(rs):+.3f}  DD={maxdd(rs):>6.1f}"), sum(rs), n


def load(scope):
    if scope == "oos":
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=10),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, build_module())
    return (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"])


def main():
    print("=" * 94)
    print("  P4  THE REAL CHAMPION  (champion_multi_sw10)")
    print("=" * 94)
    print("  config:", {k: v for k, v in PARAMS.items()})
    print("  engine: PATCHED (exp_mltf/exp_persist do not exist on shipped)")
    print("  metric: NET (gross - fees - funding), matching the published pins\n")

    base = build_module()
    floored = build_floored()

    print("-" * 94)
    print("  STEP 1 — REPRODUCE THE PIN (hard gate)")
    print("-" * 94)
    ok_all = True
    for scope in ("is", "oos"):
        a = load(scope)
        tr = base(*a, **PARAMS)["ltf_trades"]
        s, gross, n = stats(tr)
        want_n, want_net = PINS[scope]
        good = abs(n - want_n) <= 2 and abs(net_r(tr) - want_net) <= 1.0
        ok_all &= good
        print(f"  [{scope}]  got n={n} netNET={net_r(tr):+.1f} gross={gross:+.1f}"
              f"   want n={want_n} netNET={want_net}")
        print(f"           {s}")
        print(f"           -> {'PIN OK' if good else '*** PIN MISMATCH ***'}")
    if not ok_all:
        print("\n  PIN NOT REPRODUCED. Refusing to report any arm - the config, "
              "the swing set or the cost model is not what the docs describe.")
        return
    print("\n  PIN REPRODUCED. Everything below is now about the champion.\n")

    print("-" * 94)
    print("  STEP 2 — IDENTITY GATE on the floored patch (floor=None)")
    print("-" * 94)
    for scope in ("is", "oos"):
        a = load(scope)
        t1 = base(*a, **PARAMS)["ltf_trades"]
        t2 = floored(*a, live_r_floor=None, **PARAMS)["ltf_trades"]
        same = (len(t1) == len(t2) and
                all(abs(float(x["r_multiple"]) - float(y["r_multiple"])) < 1e-9
                    for x, y in zip(t1, t2)))
        print(f"  [{scope}] {len(t1)} vs {len(t2)} -> "
              f"{'IDENTICAL' if same else '*** DIVERGED ***'}")
        if not same:
            return
    print()

    print("-" * 94)
    print("  STEP 3 — THE FLOOR, ON THE REAL CHAMPION")
    print("-" * 94)
    print(f"  {'floor':>7}  {'IS':<48} {'OOS':<48} both?")
    base_net = {}
    for scope in ("is", "oos"):
        a = load(scope)
        base_net[scope] = net_r(base(*a, **PARAMS)["ltf_trades"])
    for f in (None, -0.25, -0.10, 0.0, 0.10, 0.25, 0.50):
        cells, nets = [], {}
        for scope in ("is", "oos"):
            a = load(scope)
            tr = floored(*a, live_r_floor=f, **PARAMS)["ltf_trades"]
            s, _, _ = stats(tr)
            nets[scope] = net_r(tr)
            cells.append(s)
        di = nets["is"] - base_net["is"]
        do = nets["oos"] - base_net["oos"]
        ok = "YES" if di > 0 and do > 0 else ("no" if di < 0 and do < 0
                                              else "MIXED")
        lab = "None" if f is None else f"{f:+.2f}"
        print(f"  {lab:>7}  {cells[0]:<48} {cells[1]:<48} {ok}")
    print()

    print("=" * 94)
    print(f"  BASE: IS {base_net['is']:+.1f}R NET   OOS {base_net['oos']:+.1f}R NET")
    for f in (0.0, 0.50):
        a = load("is")
        tr = floored(*a, live_r_floor=f, **PARAMS)["ltf_trades"]
        s, _, _ = stats(tr)
        print(f"  floor={f:+.2f} IS: {s}")
        print(f"          dNetNET {net_r(tr)-base_net['is']:+.1f}R")


if __name__ == "__main__":
    main()
