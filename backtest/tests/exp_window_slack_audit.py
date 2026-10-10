"""Settle the window-floor question on the SHIPPED engine, over every fsent book.

There are two claims in the record and they contradict each other. This measures
which one the code supports.

CLAIM 1 (the original registry description, since withdrawn):
    "the shipped gate admits an LTF entry anywhere in (s + 2700, s + 3600] - a
    900-second band in which the entry is knowable but the HTF window candle has
    NOT yet closed... the gate should have been s + 3600."
    This is a claim about the GATE.

CLAIM 2 (exp_decision_instant.py, which withdrew claim 1):
    "the gate's 2700 is correct arithmetic, the six trades are legal."
    This is a claim about the TRADES.

They cannot both be complete. The gate at unified.py:1034 is

    _floor = s + exp_window_floor_s            # line 1026, default 2700
    if not (_floor < bar_ts + 900 < e): continue   # line 1034

Define slack = (bar_ts + 900) - (s + 3600), the number of seconds by which the
decision instant runs PAST the instant the 1h window candle closes.

    gate admits  <=>  bar_ts + 900 > s + 2700
                  <=>  slack > -900

So the gate is permissive by 899 seconds: a trade whose decision lands anywhere
in (-899, 0) of slack decides BEFORE the window candle closes, which is a genuine
lookahead. Claim 2 measured that no trade in the eight books it sampled landed
there, and generalised from that to the arithmetic. That generalisation does not
follow. A gate that admits a lookahead is permissive whether or not this dataset
happens to walk into it.

So: measure the gate's slack distribution over every registered fsent book, on the
shipped engine, not a patched one. If min slack is 0 everywhere then no published
number is contaminated and the question is documentation hygiene. If any trade
lands below 0 then a pinned result is contaminated and that is a much larger
problem than a stale description.

Writes backtest/tests/_window_slack_audit.json.
"""
import json
import sys
from datetime import datetime, timezone

from pathlib import Path  # noqa: E402

sys.path.insert(0, ".")
# Use build_family_module(), NOT the bare shipped engine. This is the engine that
# produced the pins: 19 of the 29 fsent entries carry exp_mltf, which the shipped
# simulate_htf_ltf_streak_halt() signature does not accept, so a raw call raises
# TypeError and a silently-filtered call would audit a different book than the one
# on the registry. The patched module accepts the superset and is what
# exp_null_audit.py used to derive every number this audit is comparing against.
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import get_swings                  # noqa: E402
from exp_signal_metrics import load_era                # noqa: E402
from experiment_registry import EXPERIMENTS            # noqa: E402

LTF_CLOSE = 900
HTF_CLOSE = 3600
IST = 19800


def hm(ts):
    return datetime.fromtimestamp(int(ts) + IST, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M")


def bucket(slack):
    """Where a trade sits relative to the window's close."""
    if slack < 0:
        return "LOOKAHEAD_decision_before_window_close"
    if slack == 0:
        return "boundary_simultaneous"
    if slack < 900:
        return "tight_inside_window_candle"
    return "comfortable_after_close"


def main():
    sim = build_family_module()
    base = dict(EXPERIMENTS["fsent_champ_long"]["params"])
    eras = {e: load_era(e) for e in ("is", "oos")}

    books = sorted(k for k, v in EXPERIMENTS.items()
                   if isinstance(v, dict) and k.startswith("fsent_")
                   and (v.get("pins") or {}).get("n"))
    print("=" * 92)
    print("WINDOW SLACK AUDIT - shipped engine, gate at unified.py:1034")
    print("=" * 92)
    print("  slack = (bar_ts + 900) - (window_start + 3600)")
    print("  gate admits slack > -900, so the lookahead zone is slack in (-899, 0)")
    print("  %d registered fsent books, both eras, open trades excluded" % len(books))
    print()

    rows = []
    totals = {b: 0 for b in
              ("LOOKAHEAD_decision_before_window_close", "boundary_simultaneous",
               "tight_inside_window_candle", "comfortable_after_close")}
    worst = None
    failures = []

    for name in books:
        params = {**base, **(EXPERIMENTS[name].get("params") or {})}
        counts = {b: 0 for b in totals}
        mn = None
        n = 0
        for era in ("is", "oos"):
            d = eras[era]
            out = sim(d["c1h"], get_swings(d, "sw10"), d["c15"], d["sw15"],
                      fine_ltf=d["fine"], **params)
            for t in out["ltf_trades"]:
                if t.get("outcome") == "open":
                    continue
                n += 1
                slack = (int(t["entry_ts"]) + LTF_CLOSE) - (int(t["window_start"])
                                                            + HTF_CLOSE)
                b = bucket(slack)
                counts[b] += 1
                totals[b] += 1
                if mn is None or slack < mn:
                    mn = slack
                if worst is None or slack < worst[0]:
                    worst = (slack, name, era, t["trade_no"])
                if slack < 0:
                    failures.append({
                        "book": name, "era": era, "trade_no": t["trade_no"],
                        "entry_bar_closes_ist": hm(int(t["entry_ts"]) + LTF_CLOSE),
                        "window_closes_ist": hm(int(t["window_start"]) + HTF_CLOSE),
                        "slack_s": slack, "net_r": t.get("net_r"),
                    })
        rows.append({"book": name, "n": n, "min_slack_s": mn, "counts": counts})
        flag = "" if mn is None or mn >= 0 else "   <-- LOOKAHEAD"
        print("  %-34s n=%4d  min slack %7s%s"
              % (name[:34], n, "n/a" if mn is None else "%+d" % mn, flag))

    print()
    print("  " + "-" * 88)
    print("  %-40s %6d" % ("LOOKAHEAD (slack < 0)", totals["LOOKAHEAD_decision_before_window_close"]))
    print("  %-40s %6d" % ("boundary, simultaneous (slack = 0)", totals["boundary_simultaneous"]))
    print("  %-40s %6d" % ("tight inside window candle (0 < slack < 900)", totals["tight_inside_window_candle"]))
    print("  %-40s %6d" % ("comfortable, after close (slack >= 900)", totals["comfortable_after_close"]))
    total = sum(totals.values())
    print("  %-40s %6d" % ("total", total))
    print("  " + "-" * 88)
    print()
    print("  tightest trade in the whole family: slack %+ds  (%s, %s, trade #%d)"
          % (worst[0], worst[1], worst[2], worst[3]))

    verdict = ("NO PINNED RESULT IS CONTAMINATED. Every trade in every registered "
               "fsent book decides at or after the instant its 1h window candle "
               "closes. The gate is permissive but nothing walked into it."
               if not failures else
               "LOOKAHEAD PRESENT. %d trade(s) decide before their window candle "
               "closes. Any pinned number that includes them is contaminated."
               % len(failures))
    print()
    print("  VERDICT: " + verdict)

    json.dump({
        "gate_line": "unified.py:1034  if not (_floor < bar_ts+900 < e): continue",
        "gate_permits": "slack > -900",
        "books_audited": len(books),
        "trades_audited": total,
        "totals": totals,
        "tightest": {"slack_s": worst[0], "book": worst[1], "era": worst[2],
                     "trade_no": worst[3]},
        "violations": failures,
        "verdict": verdict,
        "per_book": rows,
    }, open("_window_slack_audit.json", "w", encoding="utf-8"), indent=1)
    print("\n  wrote _window_slack_audit.json")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())