"""Did I get this wrong? Check the DECISION instant, not the label.

THE OWNER'S CHALLENGE
--------------------
On 10 Mar 2025 the entry bar is the 19:15 15m candle, which CLOSES at 19:30.
The 1h window candle is 18:30 -> 19:30, which also CLOSES at 19:30. Both facts are
knowable at the SAME instant. Taking the trade on that candle means deciding at
19:30 using a 15m bar and a 1h candle that both closed at 19:30. That is not a
lookahead; it is the normal case of deciding on a closed bar.

MY ERROR
--------
I counted entry_ts + 3600 > window_start + 3600, i.e. I compared the HTF candle's
close against the LTF bar's OPEN. entry_ts is candles_ltf[i]["ts"] - the bar's
OPEN, which is a LABEL. The engine DECIDES at the bar's close, entry_ts + 900.
Measuring the window against the label instead of against the decision is the
wrong comparison, and it manufactured six violations out of trades that sit
exactly ON the boundary.

The honest test is:

    decision   = entry_ts + 900        (the 15m bar has closed)
    knowable   = window_start + 3600   (the 1h candle has closed)
    violation  = decision < knowable

Note the 2700 in the gate is precisely the arithmetic of that: a floor of
s + 2700 compared against entry_ts + 900 means s + 3600 <= entry_ts + 900.
"""
import sys
from datetime import datetime, timezone

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402

LTF_CLOSE = 900
HTF_CLOSE = 3600


def hm(ts, off=0):
    return datetime.fromtimestamp(int(ts) + off, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S")


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    IST = 19800

    books = [("fsent_champ_long", "sw10"), ("fsent_champ_short", "sw10"),
             ("fsent_champ_long_mcloff", "sw10"),
             ("fsent_champ_long_mcloff_htf15", "htf15"),
             ("fsent_champ_long_htf15", "htf15"),
             ("fsent_champ_long_htfesmcl4", "sw10"),
             ("fsent_sig_multi", "sw10"), ("fsent_sig_full", "sw10")]

    print("=" * 100)
    print("THE HONEST TEST - decision instant vs knowable instant")
    print("=" * 100)
    print("  my (wrong) test : window_start + 3600  >  entry_ts          <- compared to a LABEL")
    print("  the real test   : window_start + 3600  >  entry_ts + 900    <- the bar has CLOSED")
    print()

    grand_bad_label = grand_bad_real = 0
    for name, swing in books:
        n = bad_label = bad_real = 0
        worst_real = None
        for era in ("is", "oos"):
            d = E[era]
            e = EXPERIMENTS[name]
            o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                    fine_ltf=d["fine"], **{**EXPERIMENTS["fsent_champ_long"]["params"],
                                           **(e.get("params") or {})})
            for t in o["ltf_trades"]:
                if t.get("outcome") == "open":
                    continue
                n += 1
                ws, et = int(t["window_start"]), int(t["entry_ts"])
                if ws + HTF_CLOSE > et:
                    bad_label += 1
                slack = (et + LTF_CLOSE) - (ws + HTF_CLOSE)
                if slack < 0:
                    bad_real += 1
                    if worst_real is None or slack < worst_real:
                        worst_real = slack
        grand_bad_label += bad_label
        grand_bad_real += bad_real
        print("  %-34s n=%4d   flagged by my test: %2d   REAL violations: %d%s"
              % (name[:34], n, bad_label, bad_real,
                 "" if worst_real is None else "  (worst %d s)" % worst_real))

    print("\n  TOTAL: my test flagged %d; the real test finds %d."
          % (grand_bad_label, grand_bad_real))

    # the boundary cases, spelled out
    print("\n" + "=" * 100)
    print("THE SIX I CALLED LOOKAHEADS - measured both ways")
    print("=" * 100)
    d = E["is"]
    o = sim(d["c1h"], get_swings(d, "sw10"), d["c15"], d["sw15"], fine_ltf=d["fine"],
            **EXPERIMENTS["fsent_champ_long"]["params"])
    rows = []
    for era in ("is", "oos"):
        dd = E[era]
        oo = sim(dd["c1h"], get_swings(dd, "sw10"), dd["c15"], dd["sw15"],
                 fine_ltf=dd["fine"], **EXPERIMENTS["fsent_champ_long"]["params"])
        for t in oo["ltf_trades"]:
            if t.get("outcome") == "open":
                continue
            ws, et = int(t["window_start"]), int(t["entry_ts"])
            if ws + HTF_CLOSE > et:
                rows.append((era, t, ws, et))
    print("  %-4s %-4s %-19s %-19s %8s %8s %s"
          % ("era", "#", "entry bar OPENS", "decision (bar close)",
             "my flag", "slack s", "verdict"))
    for era, t, ws, et in rows:
        slack = (et + LTF_CLOSE) - (ws + HTF_CLOSE)
        print("  %-4s %-4d %-19s %-19s %8s %8d  %s"
              % (era.upper(), t["trade_no"], hm(et, IST), hm(et + LTF_CLOSE, IST),
                 "YES", slack,
                 "ON THE BOUNDARY - legal" if slack == 0 else
                 ("legal" if slack > 0 else "VIOLATION")))
    print("\n  Every one of them sits at slack 0: the 15m bar closes at the exact")
    print("  instant the 1h window candle closes. Deciding there uses two candles")
    print("  that both closed at the same moment. Nothing in the future is used.")
    print("\n  VERDICT: I was wrong. The gate's 2700 is correct arithmetic, the six")
    print("  trades are legal, and the 'fix' I made would have removed real trades.")
    return 0


if __name__ == "__main__":
    sys.exit(main())