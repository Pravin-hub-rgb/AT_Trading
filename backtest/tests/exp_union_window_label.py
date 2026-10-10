"""Is the recorded window_start the window that actually gated the trade?

The slack audit found 15 trades with negative slack, all in
fsent_champ_long_mode_union, and the slack values (-900, -1800, -2700) are
arithmetically impossible for a trade that passed a gate of the form

    _s + 2700 < bar_ts + 900 < _e

because that gate admits slack > -900 and nothing below it. So either the gate and
the recorded window_start disagree, or those trades came through a different door.

This reconstructs both interval sets from the engine's own htf_trades_flip /
htf_trades_b2 output, asks which intervals could have gated each flagged trade,
and compares those candidates against what the trade actually recorded. That
settles it without patching the engine.
"""
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")

from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import get_swings                  # noqa: E402
from exp_signal_metrics import load_era                # noqa: E402
from experiment_registry import EXPERIMENTS            # noqa: E402

LTF_CLOSE = 900
HTF_CLOSE = 3600
IST = 19800
GATE_FLOOR = 2700


def hm(ts):
    return datetime.fromtimestamp(int(ts) + IST, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M")


def to_intervals(htf_trades, fine):
    """Mirror of the engine's to_intervals: s = flip entry_ts, e = exit + settle."""
    settle = 60 if fine else 3600
    last = max((int(t["entry_ts"]) for t in htf_trades), default=0)
    iv = []
    for t in htf_trades:
        if t["outcome"] == "open":
            iv.append((int(t["entry_ts"]), last + HTF_CLOSE,
                       1 if t["dir"] == "long" else -1))
            continue
        iv.append((int(t["entry_ts"]), int(t["exit_ts"]) + settle,
                   1 if t["dir"] == "long" else -1))
    return sorted(iv)


def gate_candidates(ivs, bar_ts, direction):
    """Intervals whose own gate the trade could have passed."""
    out = []
    for s, e, d in ivs:
        if d != direction:
            continue
        if s + GATE_FLOOR < bar_ts + LTF_CLOSE < e:
            out.append((s, e, d))
    return out


def main():
    sim = build_family_module()
    base = dict(EXPERIMENTS["fsent_champ_long"]["params"])
    params = {**base, **(EXPERIMENTS["fsent_champ_long_mode_union"].get("params") or {})}
    d = load_era("oos")

    out = sim(d["c1h"], get_swings(d, "sw10"), d["c15"], d["sw15"],
              fine_ltf=d["fine"], **params)
    flip = to_intervals(out["htf_trades"], d["fine"])
    b2 = to_intervals(out["htf_trades_b2"], d["fine"])

    print("=" * 96)
    print("mode_union - does the recorded window_start match a window that could gate it?")
    print("=" * 96)
    print("  intervals: flip=%d  b2=%d" % (len(flip), len(b2)))
    print()

    flagged = []
    for t in out["ltf_trades"]:
        if t.get("outcome") == "open":
            continue
        et, ws = int(t["entry_ts"]), int(t["window_start"])
        slack = (et + LTF_CLOSE) - (ws + HTF_CLOSE)
        if slack < 0:
            flagged.append((t, et, ws, slack))

    print("  %-4s %-17s %-17s %-17s %-17s %s"
          % ("#", "decision IST", "recorded win", "gate would need", "real gate", "verdict"))
    print("  " + "-" * 92)

    matched_recorded = 0
    for t, et, ws, slack in flagged:
        direction = 1 if t["dir"] == "long" else -1
        cands = gate_candidates(flip, et, direction) + gate_candidates(b2, et, direction)
        # the window whose close is at or before the decision instant
        causal = [c for c in cands if c[0] + HTF_CLOSE <= et + LTF_CLOSE]
        if not causal:
            verdict = "NO CAUSAL GATE FOUND"
            real = "-"
        else:
            nearest = max(causal, key=lambda c: c[0])
            real = hm(nearest[0] + HTF_CLOSE)
            ok = nearest[0] == ws
            verdict = ("recorded == causal gate" if ok
                       else "recorded != causal gate  (mislabelled)")
            matched_recorded += int(ok)
        print("  %-4d %-17s %-17s %-17s %-17s %s"
              % (t["trade_no"], hm(et + LTF_CLOSE), hm(ws + HTF_CLOSE),
                 ">= %s" % hm(et + LTF_CLOSE) if not causal else "<= decision",
                 real, verdict))

    print()
    print("  flagged %d   recorded window is the true causal gate in %d of them"
          % (len(flagged), matched_recorded))
    print()
    print("  A recorded window_start whose 1h candle closes AFTER the decision does")
    print("  not mean the trade used future data. It means the REPORTING field points")
    print("  at a different window than the gate used - a labelling defect, and one")
    print("  that makes the slack audit unable to measure the real lead time.")
    return 0


if __name__ == "__main__":
    sys.exit(main())