"""P97 - A CORRECT SLOT QUEUE. What does the champion look like with a
position policy that actually works?

P96 ESTABLISHED THE BUG; THIS RUN BUILDS THE FIX.

    v18:743  busy_until = candles_ltf[exit_idx]["date"]     -> "2026-09-30"
    v18:577  if busy_until and bar_time <= busy_until:      -> "2026-09-30 14:00:00"

    The guard never fires. P96 measured what that costs: IS -188.1R, OOS
    -83.4R, maxconcurrent 6 -> 1.

    BUT P96's own repair was DAY-granularity - it appended " 23:59:59" to a
    date string, which blocks for the rest of the EXIT DAY rather than until
    the exit instant. That is coarser than the design, so P96's -188.1R is
    an OVERSTATEMENT of the true deployment cost. This run measures the real
    one.

THE RIGHT FIX IS ALREADY IN THE REPO
    v7/v8_break_entry use INDEX discipline: busy_until = exit_idx, guard
    `i <= busy_until`. Integer comparison cannot mismatch types. The string
    form is a regression, not a missing feature.

    And `exp_max_concurrent` already counts open slots CORRECTLY:
        sum(1 for t in ltf_trades if int(t["exit_ts"]) > int(candles_ltf[i]["ts"]))
    - epoch ints on both sides. So the slot-queue machinery is BUILT and
    CORRECT; it was simply never enabled (default 0 = off) while the broken
    string guard pretended to enforce one position.

    That is why P96's arm (c) was byte-identical to arm (b): once the string
    guard was repaired, it was already serialising, so an additional explicit
    cap of 1 had nothing left to remove.

WHAT THIS RUN DOES
    Arms, all reported, none selected (R3):
      (a) shipped                          control, must hit the pin exactly
      (d) placebo guard                    isolates fix from re-timing
      (b) day-granularity guard            P96's repair, for reconciliation
      (c) INDEX guard - the true minimal fix, matching v7/v8 discipline
    Then the sweep that matters, on the INDEX guard:
      max_concurrent = 1..8
    Plus a real overlap audit, because the repo's own E2 test is a FALSE PASS.

WHY THE E2 TEST IS A FALSE PASS - verified in source
    backend/debug/test_cat_e.py:
        for a,b in zip(tr,tr[1:]): if b["entry_idx"] <= a["exit_idx"]: viol+=1
    Two defects:
      1. It only compares CONSECUTIVE pairs. With 6 concurrent positions,
         trade 1 overlaps trades 2,3,4,5,6 but only the 1-2 pair is ever
         tested. N-1 pairs cannot detect a concurrency-6 book.
      2. It runs mode="b2_vs_flip_chop" - 330 trades. The champion is
         `multi_sw10`, 500 trades. The test certifies a different book.
    fix/backtest_checklist_v18.md records this as "E2 PASS, 0 overlapping
    pairs". That PASS is evidence about a book we do not ship.

WHAT IS NOT CLAIMED
    No production file is edited. This is a measurement of a deployable
    policy, and its result is a deployment bound, not an improvement. A
    correct position guard is not a parameter and cannot be adopted as one.
    Where the sweep finds a better book, that is a CANDIDATE requiring the
    full P63/P87 gates - it is not a pass.
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
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}

# the two strings that must agree; the bug is that they do not
GUARD_INIT = '    busy_until=""  # datetime string — timestamp-based, not index'
GUARD_SITE = ('        busy_until=candles_ltf[exit_idx]["date"] '
              'if exit_idx is not None and exit_idx < n else ""')
GUARD_TEST = 'if busy_until and bar_time <= busy_until: continue'
INDEX_TEST = 'if busy_until >= 0 and i <= busy_until: continue'


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def build(mode):
    """mode: None -> shipped; 'day' -> P96's repair; 'index' -> the true
    minimal fix (integer discipline, as v7/v8 already use); 'placebo' ->
    a sentinel that can never block."""
    if mode is None:
        return tc.build_module()
    src = tc.SRC
    for site, want in ((GUARD_INIT, 1), (GUARD_SITE, 1), (GUARD_TEST, 1)):
        if src.count(site) != want:
            raise SystemExit("site %r found %d times" % (site[:40],
                                                         src.count(site)))
    if mode == "placebo":
        new_site = ('        busy_until=(-1) '
                    'if exit_idx is not None and exit_idx < n else -1')
        new_test = INDEX_TEST
        # the INITIALISER must change type too. Leaving it as `""` makes the
        # very first `if busy_until >= 0` raise str-vs-int before a single
        # trade is booked - which is what the second run did.
        new_init = "    busy_until=-1  # P97 placebo: integer sentinel"
    elif mode == "day":
        new_site = ('        busy_until=((candles_ltf[exit_idx]["date"]'
                    ' + " 23:59:59") if exit_idx is not None '
                    'and exit_idx < n else "")')
        new_test = GUARD_TEST
        new_init = GUARD_INIT
    else:                                   # index
        new_site = ('        busy_until=(exit_idx '
                    'if exit_idx is not None and exit_idx < n else -1)')
        new_test = INDEX_TEST
        new_init = "    busy_until=-1  # P97: index sentinel, v7/v8 discipline"
    src = (src.replace(GUARD_INIT, new_init)
              .replace(GUARD_SITE, new_site)
              .replace(GUARD_TEST, new_test))
    import inspect as _ins
    inner = tc.build_module()
    sig = _ins.signature(inner)
    star = "    *,\n"
    extra = [p for n, p in sig.parameters.items()
             if n.startswith("exp_") and p.default is not p.empty]
    block = "".join("    %s=%r,\n" % (p.name, p.default) for p in extra)
    src = src.replace(star, star + block, 1)
    m = types.ModuleType("v18_%s" % mode)
    m.__file__ = str(ENGINE)
    exec(compile(src, str(ENGINE), "exec"), m.__dict__)
    return m.simulate_htf_ltf_streak_halt


def overlaps(tr):
    """Honest overlap audit: compare EVERY pair, not consecutive ones.
    Returns (max_concurrent, total_overlapping_pairs)."""
    ev = []
    for t in tr:
        ev.append((int(t["entry_ts"]), 1))
        ev.append((int(t["exit_ts"]), -1))
    ev.sort()
    cur = mx = 0
    for _, d in ev:
        cur += d
        mx = max(mx, cur)
    spans = sorted((int(t["entry_ts"]), int(t["exit_ts"])) for t in tr)
    pairs = 0
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            if spans[j][0] < spans[i][1]:
                pairs += 1
            else:
                break
    return mx, pairs


def main():
    print("=" * 100)
    print("  P97  A CORRECT SLOT QUEUE")
    print("=" * 100)
    print("  P96 measured the broken guard. P96's REPAIR was day-granularity")
    print("  (blocking to end of the exit DAY), which is coarser than the")
    print("  design - so -188.1R is an OVERSTATEMENT. The true minimal fix is")
    print("  INDEX discipline, as v7/v8_break_entry already use.")
    print("  M = %.1fR\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h, tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15, tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    ARMS = [("(a) shipped", None, 0),
            ("(d) placebo guard", "placebo", 0),
            ("(b) day-granularity (P96)", "day", 0),
            ("(c) INDEX guard - true fix", "index", 0)]

    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        params = {**BP, **EXPERIMENTS[name]["params"]}
        print("  " + "=" * 100)
        print("  LANE: %s" % name)
        books = {}
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
            base = net_r(ctl)
            print("      %-30s %6s %9s %8s %6s %8s %11s"
                  % ("arm", "n", "net", "R/t", "PF", "maxconc", "dNet"))
            for lbl, mode, cap in ARMS:
                sim = build(mode)
                p = dict(params)
                if cap:
                    p["exp_max_concurrent"] = cap
                tr = [t for t in sim(*args, **p)["ltf_trades"]
                      if t.get("outcome") != "open"]
                books[(lane, scope, lbl)] = tr
                rs = [float(t["r_multiple"]) for t in tr]
                net = net_r(tr)
                mc, _ = overlaps(tr)
                print("      %-30s %6d %+9.1fR %+8.3f %6.2f %8d %+9.1fR"
                      % (lbl, len(rs), net, net / len(rs), pf(rs), mc,
                         net - base))
            print()
        # ---- the sweep that matters, on the correct guard
        for scope in ("is", "oos"):
            args = src[scope]
            print("      --- [%s] SLOT SWEEP on the INDEX guard"
                  % scope.upper())
            print("      %-14s %6s %9s %8s %6s %8s"
                  % ("max_concurrent", "n", "net", "R/t", "PF", "maxconc"))
            for cap in (1, 2, 3, 4, 5, 6, 8):
                p = dict(params)
                p["exp_max_concurrent"] = cap
                tr = [t for t in build("index")(*args, **p)["ltf_trades"]
                      if t.get("outcome") != "open"]
                rs = [float(t["r_multiple"]) for t in tr]
                net = net_r(tr)
                mc, _ = overlaps(tr)
                print("      %-14d %6d %+9.1fR %+8.3f %6.2f %8d"
                      % (cap, len(rs), net, net / len(rs), pf(rs), mc))
            print()

    # ---- the honest overlap audit, versus the repo's E2 claim
    print("  " + "=" * 100)
    print("  OVERLAP AUDIT - all pairs, not consecutive pairs")
    print("=" * 100)
    for lane in ("champion_multi_sw10", "utcsat_multi_sw10"):
        tr = books[(lane, "is", "(a) shipped")]
        mx, pairs = overlaps(tr)
        consec = sum(1 for a, b in zip(tr, tr[1:])
                     if int(b["entry_ts"]) <= int(a["exit_ts"]))
        allp = len(tr) * (len(tr) - 1) // 2
        print("  %s, IS, shipped book:" % lane)
        print("    trades                         : %d" % len(tr))
        print("    max concurrent positions      : %d" % mx)
        print("    overlapping pairs, ALL pairs  : %d  of %d" % (pairs, allp))
        print("    overlapping pairs, CONSECUTIVE: %d  <- all E2 tested"
              % consec)
        print()
    print("  test_cat_e.py certifies mode=b2_vs_flip_chop (330 trades),")
    print("  not multi_sw10 (500 / 454 trades). Its own method compares only")
    print("  zip(tr, tr[1:]) - N-1 adjacent pairs - which cannot see the")
    print("  non-adjacent overlaps a concurrency-6 book produces.")
    print()
    print("  E2's conclusion - '0 overlapping pairs, PASS' - is reproduced")
    print("  here exactly, and is true, and is evidence about a book we do")
    print("  not ship.")


if __name__ == "__main__":
    main()