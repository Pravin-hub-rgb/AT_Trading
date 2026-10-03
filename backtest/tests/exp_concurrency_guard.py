"""P96 - IS THE CHAMPION 3-6 DEEP BY ACCIDENT? Fixing a broken concurrency
guard and measuring what it costs.

THE BUG, VERIFIED IN SOURCE BEFORE THIS RUN
    v18_streak_halt.py:743   busy_until = candles_ltf[exit_idx]["date"]
    v18_streak_halt.py:577   if busy_until and bar_time <= busy_until: continue

    Line 743 writes a DATE string ("2026-09-30"). Line 577 compares it
    against bar_time, a DATETIME string ("2026-09-30 14:00:00"). Python
    compares them as strings, and a longer string is greater than its own
    prefix, so "2026-09-30 14:00:00" <= "2026-09-30" is ALWAYS False.

    **The concurrency guard therefore never blocks a same-day re-entry.**
    RISK_CONCURRENCY.md measured the consequence and recorded it in one
    line without acting: max concurrent open positions 6 / 5 / 6 / 3, against
    a design that intends one position. "Recorded, not fixed."

    So a material part of the pinned +325.8R may consist of 3-6 simultaneous
    positions admitted by a type mismatch rather than by a position policy.

WHAT THIS RUN DOES
    Four arms, all reported, none selected (R3):
      (a) shipped                       - control, must hit the pin exactly
      (b) guard compares datetimes      - the minimal fix
      (c) (b) plus exp_max_concurrent=1 - strictly serial, the design intent
      (d) PLACEBO: guard "fixed" but compared against a synthetic date that
          REPRODUCES today's broken behaviour

    Arm (d) is not decoration. Without it, arm (b)'s delta cannot be
    attributed to the fix rather than to re-timing, which is exactly the
    failure mode P88 and P90 had.

WHY IT MATTERS WHATEVER IT PRINTS
    This is a BUG FIX, not a parameter. It is not adoptable as an
    improvement - a correct guard is simply correct. **The result is a
    DEPLOYMENT BOUND**: how much of the shipped expectancy a live bot with
    working code can actually capture. That number has never been measured
    and it is the one an owner shipping capital needs.

    And the answer is genuinely two-sided. Removing concurrent entries also
    removes overlap that may be double-counted in R. **If (b) is close to
    the pin, the book is far more deployable than anyone assumed. If (b) is
    deeply negative, a material part of the headline was not available to a
    bot at all.**

WHAT IS NOT CLAIMED
    No statement about whether the concurrency is profitable. Only about
    whether the shipped number depends on the guard failing.
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backtest/sweeps", "backend"):
    sys.path.insert(0, str(ROOT / p))
sys.path.append(str(ROOT / "backend" / "src"))

from experiment_registry import BP, EXPERIMENTS
from run_experiment import get_data, identity_gate, net_r
import test_experiments_craze as tc
from test_4_new_concepts import load_unseen
from test_4_new_concepts import load_fine_1m as load_fine_oos

M_NULL = 193.4
ENGINE = ROOT / "backend" / "src" / "btc" / "engines" / "htf_ltf" \
    / "v18_streak_halt.py"
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((453, 279.5), (254, 66.9))}


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def build(fix_mode, cap1=False):
    """Build the champion engine with `busy_until` overridden at the SOURCE
    level, by taking the module tc.build_module() already built and
    re-exec'ing its source.

    THE TWO FAILED ATTEMPTS, both worth recording:
      1. Reading backend/.../v18_streak_halt.py raw and patching :743 gave a
         NARROWER signature - the repo's super-set kwargs (exp_partial_r,
         exp_persist, exp_mltf, ...) live in tc.build_module's own patch, not
         in the file - so every call died on TypeError.
      2. Patching tc.SRC instead: that IS the raw file, so the same failure.

    What works is patching the source of the ALREADY-PATCHED module - i.e.
    the text tc.build_module() is about to exec - which is the only copy
    carrying both the champion's kwargs and a unique :743 site.
    """
    if fix_mode is None:
        return tc.build_module()
    import inspect as _ins
    inner = tc.build_module()
    # recover the source the repo execs, by re-deriving it the same way
    src = tc.SRC
    star = "    *,\n"
    if src.count(star) == 1:
        # apply the SAME super-set patch build_module applies
        patched = tc.build_module.__doc__ or ""
        import re as _re
        # build_module injects kwargs right after the bare-star line; grab
        # them from the built function's signature instead of guessing
        sig = _ins.signature(inner)
        extra = [p for n, p in sig.parameters.items()
                 if n.startswith("exp_") and p.default is not p.empty]
        block = "".join('    %s=%r,\n' % (p.name, p.default) for p in extra)
        src = src.replace(star, star + block, 1)
    old = ('        busy_until=candles_ltf[exit_idx]["date"] '
           'if exit_idx is not None and exit_idx < n else ""')
    if src.count(old) != 1:
        raise SystemExit("busy_until site not unique (%d) after kwargs"
                         % src.count(old))
    if fix_mode == "dt":
        new = ('        busy_until=((candles_ltf[exit_idx]["date"]'
               ' + " 23:59:59") if exit_idx is not None '
               'and exit_idx < n else "")')
    else:
        new = ('        busy_until="0000-00-00" '
               'if exit_idx is not None and exit_idx < n else ""')
    m = types.ModuleType("v18_%s%s" % (fix_mode, cap1))
    m.__file__ = str(tc.ENGINE)
    exec(compile(src.replace(old, new), str(tc.ENGINE), "exec"), m.__dict__)
    return m.simulate_htf_ltf_streak_halt


def concurrency(tr):
    """Max simultaneously open positions, from the realised exit times."""
    ev = []
    for t in tr:
        ev.append((int(t["entry_ts"]), 1))
        ev.append((int(t["exit_ts"]), -1))
    ev.sort()
    cur = mx = 0
    for _, d in ev:
        cur += d
        mx = max(mx, cur)
    return mx


def main():
    print("=" * 100)
    print("  P96  IS THE CHAMPION 3-6 DEEP BY ACCIDENT?")
    print("=" * 100)
    print("  VERIFIED IN SOURCE: v18:743 writes a DATE, v18:577 compares it")
    print("  against a DATETIME, and '2026-09-30 14:00:00' <= '2026-09-30' is")
    print("  always False. The guard has never blocked a same-day re-entry.")
    print("  RISK_CONCURRENCY.md: max concurrent 6/5/6/3, 'recorded, not")
    print("  fixed'. M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h,
                   tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15,
                   tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    ARMS = [("(a) shipped", None, False),
            ("(d) placebo guard", "placebo", False),
            ("(b) guard FIXED (datetime)", "dt", False),
            ("(c) fixed + max_concurrent=1", "dt", True)]

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        print("  " + "=" * 100)
        print("  LANE: %s" % name)
        for i, scope in enumerate(("is", "oos")):
            args = src[scope]
            print("  --- [%s]" % scope.upper())
            ctl = [t for t in tc.build_module()(*args, **params)["ltf_trades"]
                   if t.get("outcome") != "open"]
            if (abs(len(ctl) - PIN[name][i][0]) > 2
                    or abs(net_r(ctl) - PIN[name][i][1]) > 1.5):
                print("      CONTROL FAILED %dt %+.1fR - STOP"
                      % (len(ctl), net_r(ctl)))
                return
            print("      %-28s %6s %9s %8s %6s %8s %11s"
                  % ("arm", "n", "net", "R/t", "PF", "maxconc", "dNet"))
            for lbl, mode, cap1 in ARMS:
                sim = build(mode, cap1)
                p = dict(params)
                if cap1:
                    p["exp_max_concurrent"] = 1
                tr = [t for t in sim(*args, **p)["ltf_trades"]
                      if t.get("outcome") != "open"]
                rs = [float(t["r_multiple"]) for t in tr]
                net = net_r(tr)
                dv = net - net_r(ctl)
                print("      %-28s %6d %+9.1fR %+8.3f %6.2f %8d %+9.1fR%s"
                      % (lbl, len(rs), net, net / len(rs), pf(rs),
                         concurrency(tr), dv,
                         "  <-- EXCEEDS M" if abs(dv) > M_NULL else ""))
            print()
    print("  Read: (b) vs (a) is the DEPLOYMENT BOUND - how much of the")
    print("  shipped expectancy survives a working guard. (d) vs (a) is the")
    print("  placebo and must be near zero, or (b)'s delta is re-timing and")
    print("  not the fix. (c) is the design intent.")
    print("  Nothing adopted; a correct guard is not a parameter.")


if __name__ == "__main__":
    main()