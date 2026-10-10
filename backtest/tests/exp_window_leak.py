"""The shipped floor admits entries 15 minutes before the window candle closes.

Making exp_window_floor_s a parameter exposed the arithmetic: the gate is
`_floor < entry_ts` with `_floor = s + 2700`, so an entry is admitted anywhere in
(s + 2700, s + 3600] - a 900-second band during which the LTF entry is knowable
but the HTF window candle has NOT closed. C15's own comment says the start is
knowable from the flip candle CLOSE, which is s + 3600.

exp_window_floor_causality.py counted 6 such trades in fsent_champ_long, worst 15
minutes early. That is not this file's finding to explain away, so this file
measures what they are worth.

Three questions, and the answers are not the same shape:
  1. How much P&L do the 6 trades carry? If they lose, removing them is a small
     correction. If they win, the book has been flattered.
  2. What does the book look like with the floor at the causal minimum, 3600?
  3. Does the same leak exist in the OTHER books, or is it specific to this one?
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS             # noqa: E402

HTF_CLOSE = 3600


def cell(ts):
    d = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    return "%d-%s" % (d.year, "H1" if d.month <= 6 else "H2")


def collect(sim, E, book, swing, over):
    out = []
    for era in ("is", "oos"):
        d = E[era]
        p = {**EXPERIMENTS[book]["params"], **over}
        o = sim(d["c1h"], get_swings(d, swing), d["c15"], d["sw15"],
                fine_ltf=d["fine"], **p)
        for t in sorted([t for t in o["ltf_trades"] if t.get("outcome") != "open"],
                        key=lambda t: int(t["entry_ts"])):
            out.append((era, t, net_r([t])))
    return out


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    res = {}

    # ---------------- 1. what are the 6 trades worth ----------------
    print("=" * 100)
    print("1. THE 6 LOOKAHEAD TRADES IN fsent_champ_long - what are they worth?")
    print("=" * 100)
    rows = collect(sim, E, "fsent_champ_long", "sw10", {})
    bad = [(e, t, r) for e, t, r in rows
           if int(t["window_start"]) + HTF_CLOSE - int(t["entry_ts"]) > 0]
    tot_bad = sum(r for _e, _t, r in bad)
    tot_all = sum(r for _e, _t, r in rows)
    print("  %-12s %6s %9s %8s %8s" % ("entry", "era", "R", "early s", "early min"))
    for e, t, r in sorted(bad, key=lambda z: int(z[1]["entry_ts"])):
        lead = int(t["window_start"]) + HTF_CLOSE - int(t["entry_ts"])
        print("  %-12s %6s %+9.2f %8d %8.1f"
              % (datetime.fromtimestamp(int(t["entry_ts"]), tz=timezone.utc)
                 .strftime("%Y-%m-%d"), e.upper(), r, lead, lead / 60.0))
    print("\n  these 6 trades total %+.2fR out of the book's %+.2fR (%.1f%%)"
          % (tot_bad, tot_all, 100.0 * abs(tot_bad) / max(1e-9, abs(tot_all))))
    print("  verdict: %s" % ("the leak FLATTERS the book - removing those trades costs R"
                              if tot_bad > 0 else
                              "the leak COSTS the book - removing them would help, so it is "
                              "still a leak but a cheap one"))
    res["leak"] = dict(n=len(bad), net=round(tot_bad, 2), book_net=round(tot_all, 2))

    # ---------------- 2. the book at the causal minimum ----------------
    print("\n" + "=" * 100)
    print("2. fsent_champ_long at the CAUSAL floor (3600) vs the shipped 2700")
    print("=" * 100)
    print("  %-14s %5s %9s %8s %8s %10s %s"
          % ("floor", "n", "net", "ddIS", "ddOOS", "retention", "neg cells"))
    fix = {}
    for f in (2700, 3600, 5400, 7200):
        rows = collect(sim, E, "fsent_champ_long", "sw10", {"exp_window_floor_s": f})
        isr = [r for e, _t, r in rows if e == "is"]
        oosr = [r for e, _t, r in rows if e == "oos"]
        per = defaultdict(list)
        for _e, t, r in rows:
            per[cell(t["entry_ts"])].append(r)
        neg = sorted(c for c in per if sum(per[c]) < 0)
        dd = {}
        for nm, rs in (("is", isr), ("oos", oosr)):
            c = pk = m = 0.0
            for x in rs:
                c += x
                pk = max(pk, c)
                m = max(m, pk - c)
            dd[nm] = m
        ret = (sum(oosr) / len(oosr)) / (sum(isr) / len(isr)) * 100 if isr and oosr else 0
        print("  %-14d %5d %+9.2f %8.2f %8.2f %9.0f%%  %s"
              % (f, len(rows), sum(r for _e, _t, r in rows), dd["is"], dd["oos"],
                 ret, neg or "NONE"))
        fix[f] = dict(n=len(rows), net=round(sum(r for _e, _t, r in rows), 2),
                      dd_is=round(dd["is"], 2), dd_oos=round(dd["oos"], 2),
                      neg=neg)
    res["floor_fix"] = fix

    # ---------------- 3. does it hit other books ----------------
    print("\n" + "=" * 100)
    print("3. IS THE LEAK SPECIFIC TO fsent_champ_long, OR IN EVERY fsent BOOK?")
    print("=" * 100)
    print("  %-34s %6s %12s" % ("book", "trades", "lookaheads"))
    leaks = {}
    for book, swing in (("fsent_champ_long", "sw10"),
                        ("fsent_champ_long_mcloff", "sw10"),
                        ("fsent_champ_long_mcloff_htf15", "htf15"),
                        ("fsent_sig_multi", "sw10"),
                        ("fsent_sig_full", "sw10"),
                        ("fsent_champ_short", "sw10"),
                        ("fsent_champ_long_htf15", "htf15"),
                        ("fsent_champ_long_htfesmcl4", "sw10")):
        rows = collect(sim, E, book, swing, {})
        n = sum(1 for _e, _t, _r in rows
                if int(_t["window_start"]) + HTF_CLOSE - int(_t["entry_ts"]) > 0)
        rv = sum(r for _e, t, r in rows
                 if int(t["window_start"]) + HTF_CLOSE - int(t["entry_ts"]) > 0)
        print("  %-34s %6d %8d  (%+.2fR from the leaked trades)"
              % (book[:34], len(rows), n, rv))
        leaks[book] = dict(n=len(rows), lookaheads=n, leak_net=round(rv, 2))
    res["leaks"] = leaks

    with open("_window_floor_leak.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, default=str)
    print("\n  wrote _window_floor_leak.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())