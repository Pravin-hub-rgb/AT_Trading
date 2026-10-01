"""P21 - GRAY-WITH-SLOT-HELD vs TRUE PURGE. The one thing never run.

THE CORRECTION, AND IT MATTERS
==============================
I told the user my P14-P20 filters were "purge" and that
"gray-with-slot-held" had never been run. **That was wrong, and being
wrong in this direction is the useful kind.** Look at what a post-hoc
filter actually does:

    engine runs -> trade booked -> busy_until = exit   (slot HELD)
    I then drop the trade from the list afterwards

The engine already set `busy_until` before I ever saw the trade. So the
next signal inside that window was **already blocked** and never appears
in the list for me to keep. **Every post-hoc filter I have ever run was
gray-with-slot-held.** The thing that has never been run is TRUE PURGE:
reject the signal BEFORE the slot is taken, so the engine stays free and
the next signal is allowed in.

So the honest statement is: P14-P20 measured held-slot, not purge. This
measures the difference between the two, same rule, predicate held
identical between arms.

WHY IT COULD MATTER
===================
A filtered trade that was going to lose still cost the OPPORTUNITY to
take the signal behind it. Purging gives that signal back. If the trades
my filter removes are worse than the trades they were blocking, purge
beats held-slot.

ARMS
====
  A  control              n = all trades
  B  GRAY  (busy)         trade NOT booked, slot HELD, r = 0,
                          **n stays 500** - the position is never taken,
                          so no cost is paid on it
  C  SKIP  (remove)       trade removed from the book, slot HELD by
                          the engine, n falls to 307

B and C carry the same P&L. They differ in whether the rejected trade
occupies a slot in the reported book and pays cost. The user is right that
B must keep n = 500; my earlier table conflated the two.
"""
from __future__ import annotations

import bisect as bs
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))

from experiment_registry import BP, EXPERIMENTS  # noqa: E402
from run_experiment import get_data, identity_gate, net_r  # noqa: E402
import test_experiments_craze as tc  # noqa: E402
from test_4_new_concepts import load_unseen, load_fine_1m  # noqa: E402
from test_experiments_craze import _compute_swings  # noqa: E402
from engine.v18_params import SWING  # noqa: E402

NEST, AGE = 0.25, 0.5   # the leading candidate rule from P19

LANES = (
    ("champion_multi_sw10", {"is": (500, 325.8), "oos": (279, 70.1)}),
    ("age25_dirmatch_multi_sw10", {"is": (249, 386.7), "oos": (166, 156.4)}),
    ("age10_swingpause_single_sw10", {"is": (130, 435.7), "oos": (76, 43.2)}),
)


def _patched():
    """build_module()'s patched source + a pre-slot purge gate (default off)."""
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
                  "    _exp_purge_nest=0.0,\n"
                  "    _exp_purge_age=0.0,\n"
                  "    _exp_purge_log=None,\n")

    # Inject AFTER the busy check. `continue` here means the slot is never
    # taken: busy_until is left untouched and the next signal is free.
    a = ("        if (not exp_mltf) and busy_until and "
         "bar_time <= busy_until:\n"
         "            if exp_shadow_book: _sr[\"reason\"]=\"busy\"\n")
    assert s.count(a) == 1, "busy anchor"
    s = s.replace(a, a)
    s = s.replace(a, a + (
        "        _nst, _agd = 0.5, 0.0\n"
        "        _ints = intervals_flip if use==\"flip\" else "
        "(intervals_b2 if use==\"b2\" else intervals_decisive)\n"
        "        _sts = starts_flip if use==\"flip\" else "
        "(starts_b2 if use==\"b2\" else starts_decisive)\n"
        "        if _ints and _sts:\n"
        "            _et = int(candles_ltf[i][\"ts\"])\n"
        "            _ii = bs.bisect_right(_sts, _et) - 1\n"
        "            if _ii >= 0:\n"
        "                _a2 = int(_ints[_ii][0]); _b2v = int(_ints[_ii][1])\n"
        "                if _b2v > _a2:\n"
        "                    _nst = (_et - _a2) / float(_b2v - _a2)\n"
        "                    _agd = (_et - _a2) / 86400.0\n"
        "        if _exp_purge_log is not None:\n"
        "            _exp_purge_log.append((int(candles_ltf[i][\"ts\"]), "
        "use, _nst, _agd))\n"
        "        if (_exp_purge_nest > 0 or _exp_purge_age > 0) and \\\n"
        "                (_nst <= _exp_purge_nest or _agd <= _exp_purge_age):\n"
        "            continue\n"
    ))
    return s


def load(scope, swtag):
    if scope == "oos":
        mb1h = 10 if "sw10" in swtag else 20
        (c15, f15), (c1h, f1h) = load_unseen("15m"), load_unseen("1h")
        return (c1h, _compute_swings(f1h, "continuous", min_bars=mb1h),
                c15, _compute_swings(f15, "continuous",
                                     min_bars=SWING["min_bars_15m"]),
                load_fine_1m(c15[0]["ts"], c15[-1]["ts"]))
    d = get_data()
    identity_gate(d, tc.build_module())
    return (d["c1h"], d[swtag], d["c15"], d["sw15"], d["fine"])


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def streak(rs):
    cur = mx = 0
    for x in rs:
        cur = cur + 1 if x < 0 else 0
        mx = max(mx, cur)
    return mx


def main():
    print("=" * 96)
    print("  P21  GRAY/SLOT-HELD  vs  TRUE PURGE   (the never-run arm)")
    print("=" * 96)
    print("  A control   engine, no filter")
    print("  B HELD      post-hoc drop  <-- what P14-P20 actually measured")
    print("  C PURGE     engine `continue` before the slot is taken")
    print("  B and C use the same rule and the same parent-window lookup.\n")

    eng = tc._load_module(_patched(), "p21_purge")
    eng = (eng[0] if isinstance(eng, tuple) else eng)
    sim = eng.simulate_htf_ltf_streak_halt

    for key, pins in LANES:
        cfg = EXPERIMENTS[key]
        params = {**BP, **cfg["params"]}
        swtag = "sw10" if "sw10" in key else "sw20"
        print(f"  --- {key} " + "-" * max(1, 84 - len(key)))
        for scope in ("is", "oos"):
            args = load(scope, swtag)
            want_n, want_net = pins[scope]

            logA = []
            ra = sim(*args, _exp_purge_log=logA, **params)["ltf_trades"]
            ra = [t for t in ra if t.get("outcome") != "open"]
            na, ga = net_r(ra), len(ra)
            ok = ("PIN ok" if abs(na - want_n) <= 2 and abs(ga - want_net) <= 1.5
                  else f"PIN MISS (want {want_n}/{want_net})")

            feat = {e[0]: (e[2], e[3]) for e in logA}

            def keep(t, _f=feat):
                v = _f.get(int(t["entry_ts"]))
                return True if v is None else (v[0] > NEST and v[1] > AGE)

            rb = [t for t in ra if keep(t)]
            nb = net_r(rb)
            # GRAY: the rejected trades still occupy their slot and stay
            # in the book at r=0. No position was taken, so no cost is
            # paid on them - which is the whole point of a real gray.
            per = (sum(float(t["r_multiple"]) for t in ra) - na) / len(ra)
            grayed = [t for t in ra if not keep(t)]
            gray_net = (sum(float(t["r_multiple"]) for t in rb)
                        - per * len(rb))

            rc = sim(*args, _exp_purge_nest=NEST, _exp_purge_age=AGE,
                     **params)["ltf_trades"]
            rc = [t for t in rc if t.get("outcome") != "open"]
            nc = net_r(rc)

            sa = [float(t["r_multiple"]) for t in ra]
            sb = [float(t["r_multiple"]) for t in rb]
            sc = [float(t["r_multiple"]) for t in rc]
            print(f"    [{scope}] control {ga:>4}t net {na:+8.1f}R  ({ok})")
            print(f"      GRAY (busy)      n={len(ra):>4} net={gray_net:>+8.1f}R "
                  f"dNet={gray_net-na:>+7.1f}R   {len(grayed)} at r=0, no cost")
            print(f"      SKIP (remove)    n={len(rb):>4} net={nb:>+8.1f}R "
                  f"dNet={nb-na:>+7.1f}R  R/tr={sum(sb)/max(1,len(sb)):+5.2f} "
                  f"PF={pf(sb):4.2f} strk={streak(sb):2d}")
            print(f"      PURGE (slot free) n={len(rc):>4} net={nc:>+8.1f}R "
                  f"dNet={nc-na:>+7.1f}R  R/tr={sum(sc)/max(1,len(sc)):+5.2f} "
                  f"PF={pf(sc):4.2f} strk={streak(sc):2d}")
            print(f"      PURGE - SKIP (cost of freeing slot) {nc-nb:>+7.1f}R   "
                  f"n {len(rc)-len(rb):+d}")
    print()


if __name__ == "__main__":
    main()
