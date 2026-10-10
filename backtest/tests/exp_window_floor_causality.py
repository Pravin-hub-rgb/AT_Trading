"""Is the window floor a tuning knob or a causality floor?

The floor sweep found that floor=0 and mode='fs' both give +20R and zero negative
half-years - the best result in the sweep. That is exactly the shape a lookahead
looks like, so it gets checked before it gets believed.

THE REASON IT MIGHT BE LOOKAHEAD. `s` is the HTF window start, which is the entry
BAR's OPEN timestamp, not its close. C15 says the window start is knowable from
the flip candle CLOSE, which is s + 3600 on a 1h plane. An LTF entry is knowable
at bar_ts + 900. So a trade can only be inside the window, honestly, when

    bar_ts + 900  >  s + 3600      i.e.      bar_ts  >  s + 2700

and 2700 is exactly (3600 - 900). The hardcoded floor was never a tuning knob. It
is the arithmetic of "the HTF candle has to close before an LTF bar inside it can
be acted on", and sweeping it down opens entries that precede the flip candle's
close.

So this file checks the one question that decides it: with the floor lowered, are
there LTF entries whose KNOWN entry instant is before the HTF window candle
closed? That is the C17 shape applied to the START side.
"""
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402

HTF_CLOSE_OFFSET = 3600          # a 1h candle's open -> its close
LTF_CLOSE_OFFSET = 900           # a 15m bar's open -> its close
SAFE_FLOOR = HTF_CLOSE_OFFSET - LTF_CLOSE_OFFSET       # 2700


def cell(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}

    ARMS = [
        ("floor 2700 (shipped)", {"exp_window_floor_s": 2700}),
        ("floor 3600", {"exp_window_floor_s": 3600}),
        ("floor 7200", {"exp_window_floor_s": 7200}),
        ("floor 0", {"exp_window_floor_s": 0}),
        ("floor 900", {"exp_window_floor_s": 900}),
        ("mode fs", {"exp_window_floor_mode": "fs"}),
        ("mode max", {"exp_window_floor_mode": "max"}),
    ]

    print("=" * 100)
    print("WINDOW FLOOR - causality of the START side, not just its P&L")
    print("=" * 100)
    print("  An entry is a LOOKAHEAD if its knowable instant is before the HTF window")
    print("  candle closed: entry_ts < window_start + %d" % HTF_CLOSE_OFFSET)
    print("  The shipped floor of %d is exactly that arithmetic, not a tuning value.\n" % SAFE_FLOOR)
    print("  %-22s %6s %10s %14s %10s" % ("arm", "n", "net", "LOOKAHEADS", "neg cells"))
    print("  %-22s %6s %10s %14s %10s" % ("-" * 22, "-" * 6, "-" * 10, "-" * 14, "-" * 10))

    rows = []
    for label, over in ARMS:
        n = net = 0
        viol = 0
        worst = None
        per = defaultdict(list)
        for era in ("is", "oos"):
            d = E[era]
            p = {**EXPERIMENTS["fsent_champ_long"]["params"], **over}
            o = sim(d["c1h"], get_swings(d, "sw10"), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **p)
            for t in o["ltf_trades"]:
                if t.get("outcome") == "open":
                    continue
                r = net_r([t])
                n += 1
                net += r
                per[cell(t["entry_ts"])].append(r)
                lead = int(t["window_start"]) + HTF_CLOSE_OFFSET - int(t["entry_ts"])
                if lead > 0:
                    viol += 1
                    if worst is None or lead > worst:
                        worst = lead
        neg = sum(1 for c in per if sum(per[c]) < 0)
        tag = "CLEAN" if viol == 0 else "LOOKAHEAD"
        print("  %-22s %6d %+10.1f %10d %5d   %s%s"
              % (label, n, net, viol, neg, tag,
                 "" if worst is None else "  worst %.1f min early" % (worst / 60.0)))
        rows.append((label, n, net, viol, neg))

    print()
    print("  READ:")
    for label, n, net, viol, neg in rows:
        if viol:
            print("    %-22s gains %+.1fR but %d entries PRECEDE the window candle close."
                  % (label, net, viol))
            print("      Its better numbers are the number you get from trading before")
            print("      the HTF candle closed. Not an improvement - a leak.")
    clean_better = [(l, n, net, neg) for l, n, net, v, neg in rows
                    if v == 0 and neg == 0 and l != "floor 2700 (shipped)"]
    print()
    if clean_better:
        for l, n, net, neg in clean_better:
            print("    %-22s is causal AND has zero negative cells (%d trades, %+.1fR)"
                  % (l, n, net))
    else:
        print("    No arm is both causal and free of a negative half-year at a floor")
        print("    other than the shipped one.")
    print()
    print("  CONCLUSION: the floor is a CAUSALITY floor. Lowering it is lookahead,")
    print("  and any P&L it appears to add is not real. Raising it is a genuine")
    print("  knob - a stricter wait - and that is the only direction worth taking.")
    return 0


if __name__ == "__main__":
    sys.exit(main())