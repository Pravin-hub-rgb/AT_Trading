"""DIRECTIONAL FS ON THE SINGLE PLANE - the signal book, not the multi book.

WHY THIS FILE EXISTS
    Everything shipped so far on the FS-entry knob was measured on MULTI books
    (champion multi, utcsat multi, dirmatch multi). The owner's plan is the
    reverse order: start from a SIGNAL book, because capital does not allow
    several simultaneous positions, and only deploy multi once there is capital
    for it. So the first thing needed is a single-position book.

    The bare single baseline is `champion_single_sw10` - 503 trades / +170.91R in
    sample, 295 / +78.57R out of sample, with no filter knobs of its own beyond
    the shared base. That is the starting point.

TWO AXES, NOT ONE
    1. The trigger: control (break/break), FS long, FS short, FS both. Same knob
       as the multi books, `exp_fs_entry_side`.
    2. The position gate: `max_positions`. 0 = unlimited positions at once
       (the multi behaviour), 1 = strictly one at a time. The owner cannot
       afford concurrent losers, so 1 is the arm that matters. It is also the
       stricter test of any edge: a rule that only pays because it can hold six
       positions at once is not a rule a small account can use.

    Both axes are swept because they are not independent. Serialising throws
    away trades, so a trigger that is good at stacking may be useless when only
    one slot exists.

READ-ONLY. No engine change, no registry write.
"""
import sys, json, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs
import experiment_registry as reg

OUT = ROOT / "backtest" / "tests" / "_fs_single.json"
BASES = ["champion_single_sw10", "champion_single_sw20"]
SIDES = ["", "long", "short", "both"]
GATES = [("multi  max_pos=0", 0), ("serial max_pos=1", 1)]


def run(scope, key, side, mpos):
    cfg = reg.EXPERIMENTS[key]
    d = EQ.load_scope(scope)
    sim = re_.build_module()
    o = dict(re_.BP)
    o.update(cfg["params"])
    if side:
        o["exp_fs_entry_side"] = side
    o["max_positions"] = mpos
    sw = d["sw10"] if cfg["swing"] == "sw10" else d["sw20"]
    fine = d["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=fine, **o)["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    tr = [t for t in tr if t.get("outcome") != "open"]
    eq = pk = dd = 0.0
    wins = 0
    for t in tr:
        r = float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0))
        eq += r
        if r > 0:
            wins += 1
        pk = max(pk, eq)
        dd = max(dd, pk - eq)
    gp = sum(max(r, 0.0) for r in (float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0)) for t in tr))
    ll = -sum(min(float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0)), 0.0) for t in tr)
    return {"n": len(tr), "net": round(eq, 2), "dd": round(dd, 2),
            "per": round(eq / max(len(tr), 1), 3),
            "wr": round(100.0 * wins / max(len(tr), 1), 1),
            "pf": round(gp / ll, 2) if ll > 0 else 0.0}
def main():
    res = {}
    for key in BASES:
        if key not in reg.EXPERIMENTS:
            print("%s : not in registry" % key)
            continue
        p = reg.EXPERIMENTS[key]["pins"]
        print("\n" + "=" * 100)
        print("SINGLE BASE: %s   (pinned IS %sR / OOS %sR)" % (key, p.get("net"), p.get("oos_net")))
        print("=" * 100)
        for glabel, mpos in GATES:
            print("\n  --- position gate: %s ---" % glabel)
            print("  %-20s | %-33s | %-33s"
                  % ("trigger", "IS  n / net / DD / R-per / WR", "OOS  n / net / DD / R-per / WR"))
            print("  " + "-" * 100)
            base_is = base_oos = None
            for side in SIDES:
                a = run("is", key, side, mpos)
                b = run("oos", key, side, mpos)
                nm = "control" if not side else "FS %s" % side
                if not side:
                    base_is, base_oos = a, b
                    mark = ""
                else:
                    mark = "  dIS %+.1f  dOOS %+.1f" % (a["net"] - base_is["net"],
                                                        b["net"] - base_oos["net"])
                res["%s|%s|%s|is" % (key, glabel, side or "control")] = a
                res["%s|%s|%s|oos" % (key, glabel, side or "control")] = b
                print("  %-20s | %4d /%+8.1f /%6.1f /%+.3f /%4.1f%% | %4d /%+8.1f /%6.1f /%+.3f /%4.1f%%%s"
                      % (nm, a["n"], a["net"], a["dd"], a["per"], a["wr"],
                         b["n"], b["net"], b["dd"], b["per"], b["wr"], mark))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()