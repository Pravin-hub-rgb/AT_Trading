"""FS-TO-BREAKEVEN ACROSS BOOKS - does the A rule hold on anything but champion?

THE RULE, in engine terms now (not an overlay)
    When the swing that opened a trade CONFIRMS (its FS print, at/after the
    extreme), that trade's stop is lifted to entry. The ratchet is one-sided, so
    this can only rescue a loser and never touches a winner's stop.

    On the 1m fine loop the stop is re-armed at the FS bar and enforced in the
    SAME bar, matching the D3 ordering the engine already uses for its other
    ratchet events (unified.py:1018-1032): armed at the event instant, enforced
    immediately. So a trade that gaps back through entry on that minute closes
    at entry, not at the original stop.

WHY THIS FILE EXISTS
    A won on the champion multi book: IS +239.12R -> +349.90R, DD 46.9 -> 27.7,
    with the trade count unchanged at 499. A single book result is a single
    book result. This asks the only question that matters before adopting
    anything: does it hold on books with different filters, different swing
    widths and different entry density - including the UNFILTERED baselines.

BOOKS CHOSEN ON PURPOSE
    champion_single_sw10   - the single-plane book, same swing width as champion
    champion_multi_sw10_leg- the book A was found on (control)
    trail_half_skipn6_dr3  - the highest IS book in the registry (+615R)
    trail_half_skipn3_nodelay - second highest, and a DIFFERENT family
    dirmatch_multi_sw10    - highest OOS book in the registry (+172R)
    utcsat_entry_minus_1   - a shipping candidate, weekended

    The trails/skipn books are the strongest books in the repo, so if the rule
    helps only weak books it is not worth shipping. If it helps them too, that
    is the interesting result.

Read-only with respect to the registry. Nothing here writes a pin; the numbers
are engine output on both eras and are not yet pinned books.
"""
import sys, json, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs, _net_stats
from src.btc.btc_engine import trade_stats
import experiment_registry as reg

OUT = ROOT / "backtest" / "tests" / "_fs_be_books.json"

BOOKS = ["champion_multi_sw10_leg", "champion_single_sw10",
         "trail_half_skipn6_dr3", "trail_half_skipn3_nodelay",
         "dirmatch_multi_sw10", "utcsat_entry_minus_1"]


def stats(tr):
    n, net, dd = 0, 0.0, 0.0
    for t in tr:
        if t.get("outcome") == "open":
            continue
        n += 1
        net += float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0))
    return n, net


def curve(tr):
    eq = pk = dd = 0.0
    n = 0
    for t in tr:
        if t.get("outcome") == "open":
            continue
        n += 1
        eq += float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0))
        pk = max(pk, eq)
        dd = max(dd, pk - eq)
    return n, eq, dd


def run(scope, key, be):
    cfg = reg.EXPERIMENTS[key]
    d = EQ.load_scope(scope)
    sim = re_.build_module()
    o = dict(re_.BP)
    o.update(cfg["params"])
    o["exp_fs_move_to_be"] = bool(be)
    sw = d["sw10"] if cfg["swing"] == "sw10" else d["sw20"]
    fine = d["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=fine, **o)["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    n, net, dd = curve(tr)
    return {"n": n, "net": round(net, 2), "dd": round(dd, 2),
            "per": round(net / max(n, 1), 3)}
def main():
    print("=" * 104)
    print("FS-TO-BREAKEVEN ACROSS BOOKS  (engine knob exp_fs_move_to_be)")
    print("delta = with BE minus control. Positive net AND positive delta is the whole point.")
    print("=" * 104)
    res = {}
    for key in BOOKS:
        if key not in reg.EXPERIMENTS:
            print("\n%s : not in registry, skipped" % key)
            continue
        p = reg.EXPERIMENTS[key]["pins"]
        print("\n### %s   (pinned IS %sR / OOS %sR)" % (key, p.get("net"), p.get("oos_net")))
        print("%-8s | %-29s | %-29s | %s"
              % ("era", "control  n / net / DD / R-per", "FS->BE    n / net / DD / R-per", "delta"))
        print("-" * 104)
        res[key] = {}
        for scope in ("is", "oos"):
            a = run(scope, key, False)
            b = run(scope, key, True)
            res[key][scope] = {"control": a, "be": b}
            dn, dd = b["net"] - a["net"], b["dd"] - a["dd"]
            if dn > 0 and dd <= 0:
                mark = "  <-- BETTER: more R, less DD"
            elif dn > 0:
                mark = "  <-- more R, but more DD"
            elif dn < 0:
                mark = "  <-- WORSE"
            else:
                mark = "  <-- flat"
            print("%-8s | %4d /%+8.2f /%6.1f /%+.3f | %4d /%+8.2f /%6.1f /%+.3f | %+7.2fR /%+5.1fDD%s"
                  % (scope.upper(), a["n"], a["net"], a["dd"], a["per"],
                     b["n"], b["net"], b["dd"], b["per"], dn, dd, mark))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()