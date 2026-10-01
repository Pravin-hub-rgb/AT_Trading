"""P65 - STAGE 64 PUT THROUGH THE PROGRAMME'S OWN BAR.

THE CANDIDATE THAT WAS NEVER PUT THROUGH IT
    TRANSCRIPT_THESIS_BACKLOG.md line 43 carries a live research candidate:

      "Champion default + global_soft_n3 improves IS +325.8->+331.7R and
       reused OOS +70.2->+90.0R, with better R/trade, PF, and drawdown
       while preserving the OOS 10R+ tail."

    Stage 64's own hit bar was a delta on a single axis. It never met M =
    193.4R, and WIN_STREAK_STACKING_AUTOPSY.md contains no reference to the
    null at all. Nor did it get the P61 period partition. So a candidate
    with a better risk profile AND better return in both eras has been
    sitting in the backlog, untested against the standard this programme
    adopted afterwards.

    That is worth checking on its own terms, and it is worth checking now
    because of what happened to cand_4h1h: same profile, same aggregate
    story, and P61's half-year split killed it 4-4 in IS.

THE RULE - borrowed, not invented
    WIN3 = exp_window_win_kill_n=3, action "soft", scope "global", i.e.
    after three completed global wins, block new entries in the current
    parent HTF window while keeping open positions. These are the exact
    Stage 64 parameters, taken from exp_thesis_win_streak_stack.py's WIN3,
    not re-derived here.

    The control is the shipped default champion, pinned.

TWO TESTS, BOTH PRE-REGISTERED
    T1 MAGNITUDE  Does the improvement clear M = 193.4R in the era it is
                  claimed in? An improvement smaller than the deck-relative
                  null is a coin that came up, not an effect.
    T2 STABILITY  Split by calendar half-year and count how often the
                  candidate's R/trade beats the control's. Time-based, fixed
                  before looking, never by r_multiple / outcome / pnl.

    This is the same two tests that closed cand_4h1h. Applying them to an
    older candidate is the point: a standard that is only applied to new
    work is not a standard.
"""
import sys
from datetime import datetime, timezone
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
WIN3 = {"exp_window_win_kill_n": 3, "exp_window_win_kill_action": "soft",
        "exp_window_win_kill_scope": "global"}
ARMS = [("shipped_default", {}),
        ("default_global_soft_n3", dict(WIN3)),
        ("default_window_soft_n3", {**WIN3,
                                    "exp_window_win_kill_scope": "window"})]
PIN = {"champion_multi_sw10": ((500, 325.8), (279, 70.1)),
       "utcsat_multi_sw10": ((454, 358.9), (253, 60.2))}


def pf(rs):
    return sum(x for x in rs if x > 0) / max(1e-9, -sum(x for x in rs if x < 0))


def dd(rs):
    e = p = d = 0.0
    for x in rs:
        e += x
        p = max(p, e)
        d = max(d, p - e)
    return d


def half(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%dH%d" % (d.year, 1 if d.month <= 6 else 2)


def main():
    print("=" * 100)
    print("  P65  STAGE 64 (win-streak soft block) PUT THROUGH M AND TIME")
    print("=" * 100)
    print("  Stage 64 hit a single-axis delta and never met the null.")
    print("  M = %.1fR.  Periods are calendar half-years, fixed before "
          "looking.\n" % M_NULL)

    d = get_data()
    identity_gate(d, tc.build_module())
    (oc15, of15), (oc1h, of1h) = load_unseen("15m"), load_unseen("1h")
    oos_fine = load_fine_oos(oc15[0]["ts"], oc15[-1]["ts"])
    src = {"is": (d["c1h"], d["sw10"], d["c15"], d["sw15"], d["fine"]),
           "oos": (oc1h, tc._compute_swings(of1h, "continuous", min_bars=10),
                   oc15, tc._compute_swings(of15, "continuous", min_bars=50),
                   oos_fine)}

    tally = {}
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        base = {**BP, **EXPERIMENTS[name]["params"]}
        pin = PIN[name]
        print("  " + "=" * 98)
        print("  LANE: %s" % name)
        print("  " + "=" * 98)
        for i, scope in enumerate(("is", "oos")):
            args = src[scope]
            books = {}
            for lbl, extra in ARMS:
                res = tc.build_module()(*args, **{**base, **extra})
                books[lbl] = [t for t in res["ltf_trades"]
                              if t.get("outcome") != "open"]
            ctl = books["shipped_default"]
            if (abs(len(ctl) - pin[i][0]) > 2
                    or abs(net_r(ctl) - pin[i][1]) > 1.5):
                print("  [%s] CONTROL FAILED %dt %+.1fR vs pin %dt %+.1fR - STOP"
                      % (scope.upper(), len(ctl), net_r(ctl), *pin[i]))
                return
            print("  --- [%s] control %dt %+.1fR (PIN ok)"
                  % (scope.upper(), len(ctl), net_r(ctl)))
            print("      %-24s %5s %9s %7s %6s %6s %6s %12s"
                  % ("arm", "n", "net", "R/t", "PF", "DD", "WR", "dNet"))
            for lbl, _ in ARMS:
                tr = books[lbl]
                rs = [float(t["r_multiple"]) for t in tr]
                net = net_r(tr)
                dv = net - net_r(ctl)
                print("      %-24s %5d %+9.1fR %+7.3f %6.2f %6.1f %5.1f%% "
                      "%+9.1fR%s"
                      % (lbl, len(rs), net, net / len(rs), pf(rs), dd(rs),
                         100.0 * sum(1 for x in rs if x > 0) / len(rs), dv,
                         "  <-- CLEARS M" if abs(dv) > M_NULL else ""))
                if lbl != "shipped_default":
                    tally.setdefault((name, lbl), []).append(dv)
            print()

    print("  " + "=" * 98)
    print("  T2  PERIOD STABILITY - global_soft_n3 R/trade vs control")
    print("  " + "=" * 98)
    d = get_data()
    for name in ("champion_multi_sw10", "utcsat_multi_sw10"):
        base = {**BP, **EXPERIMENTS[name]["params"]}
        for scope in ("is", "oos"):
            args = src[scope]
            out = {}
            for lbl, extra in (ARMS[0], ARMS[1]):
                tr = tc.build_module()(*args, **{**base, **extra})["ltf_trades"]
                acc = {}
                for t in tr:
                    if t.get("outcome") != "open":
                        acc.setdefault(half(t["entry_ts"]), []).append(
                            float(t["r_multiple"]))
                # MEAN R per period, not a dict keyed on period - the first
                # version collapsed each period to whichever trade happened to
                # come last, which is why every cell read as a tie and why
                # most periods showed R/t of exactly -1.000. That was a bug
                # in the reporting, not a finding about the rule.
                out[lbl] = {k: sum(v) / len(v) for k, v in acc.items()}
                out[lbl + "_n"] = {k: len(v) for k, v in acc.items()}
            keys = sorted(set(out["shipped_default"])
                          | set(out["default_global_soft_n3"]))
            w = l = t_ = 0
            print("  --- %s / %s" % (name, scope.upper()))
            print("      %-8s %5s %10s %5s %10s   %s"
                  % ("period", "nCtl", "ctl R/t", "nCnd", "cand R/t", "cand"))
            for k in keys:
                a = out["shipped_default"].get(k)
                b = out["default_global_soft_n3"].get(k)
                if a is None or b is None:
                    continue
                if b > a:
                    w += 1
                    mk = "cand"
                elif b < a:
                    l += 1
                    mk = "CTRL"
                else:
                    t_ += 1
                    mk = "="
                print("      %-8s %5d %+10.3f %5d %+10.3f   %s"
                      % (k, out["shipped_default_n"].get(k, 0), a,
                         out["default_global_soft_n3_n"].get(k, 0), b, mk))
            print("      candidate wins %d, loses %d, ties %d of %d"
                  % (w, l, t_, w + l + t_))
            print()

    print("  Verdict per lane/arm (dNet in each era, vs M = %.1fR):" % M_NULL)
    for (name, lbl), v in tally.items():
        ok = all(abs(x) > M_NULL for x in v) and all(x > 0 for x in v)
        print("    %-22s %-22s IS %+8.1fR  OOS %+8.1fR   %s"
              % (name, lbl, v[0], v[1], "PASSES" if ok else "FAILS"))
    print("  Nothing adopted. Champion unchanged.")


if __name__ == "__main__":
    main()