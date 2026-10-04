"""SWING-SIZE EXIT AT FS + GRAY - the owner's proposal, measured.

THE PROPOSAL
    Enter at B2/flip exactly as the book does. When the swing that opened the
    trade CONFIRMS (its FS print), measure how big that swing turned out to be -
    |end_px - start_px| over ATR - and if it was small, exit there.

    This is NOT the room-threshold exit that is already closed. That one asked
    "how far did price travel from OUR entry" and it lost in both eras. This one
    asks about the SWING'S OWN LEG, which is a different quantity: a trade can be
    in a large swing and still have gone badly, and vice versa.

    The quantity is knowable when used. `end_px` and `start_px` are settled at or
    before `confirmed_at_idx`, and the FS bar has already closed when we read it.
    This is the fix for M2, not a repeat of it: M2 read the same field at the
    ENTRY bar, which is why it was retrospective. Read at the FS bar it is just
    a settled fact about the past.

THE GRAY HALF, which is the part that matters
    Every earlier FS-exit arm lost partly through a crossover: closing a loser
    early frees the slot, `cooldown_bars` and `max_consecutive_losses` then let
    the next signal open a brand-new trade, and that new trade displaces the
    winners the exit was trying to protect. `exp_fs_move_to_be` measured it
    plainly: 518 trades instead of 499, IS +239.12R -> +174.58R.

    With `exp_fs_gray` the engine also arms `busy_until` on such an exit, so the
    engine stays occupied and no replacement trade can enter. The exit becomes
    "get out and stay out" instead of "get out and let something else in".

    Both are swept, because the whole question is whether the signal is real
    underneath the churn.

READ-ONLY with respect to the registry. The two knobs are default-off.
"""
import sys, json, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs
import experiment_registry as reg

OUT = ROOT / "backtest" / "tests" / "_fs_small_swing.json"
BASE_BOOKS = ["champion_multi_sw10_leg", "fsent_champ_long"]
THRESHOLDS = [3.0, 4.0, 5.0, 6.0]


def run(scope, key, thresh, gray):
    cfg = reg.EXPERIMENTS[key]
    d = EQ.load_scope(scope)
    sim = re_.build_module()
    o = dict(re_.BP)
    o.update(cfg["params"])
    if thresh:
        o["exp_fs_small_swing"] = thresh
        o["exp_fs_gray"] = bool(gray)
    sw = d["sw10"] if cfg["swing"] == "sw10" else d["sw20"]
    fine = d["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=fine, **o)["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    tr = [t for t in tr if t.get("outcome") != "open"]
    eq = pk = dd = 0.0
    hits = 0
    for t in tr:
        r = float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0))
        eq += r
        pk = max(pk, eq)
        dd = max(dd, pk - eq)
        if t.get("outcome") == "fs_small_swing":
            hits += 1
    return {"n": len(tr), "net": round(eq, 2), "dd": round(dd, 2),
            "per": round(eq / max(len(tr), 1), 3), "exits": hits}


def main():
    res = {}
    print("=" * 100)
    print("SWING-SIZE EXIT AT FS. Swing leg |end_px-start_px| / ATR(20). Exit if it is SMALL.")
    print("Gray = keep the slot occupied after the exit so no replacement trade can enter.")
    print("=" * 100)
    for key in BASE_BOOKS:
        p = reg.EXPERIMENTS[key]["pins"]
        print("\nBASE: %s  (pinned IS %sR / OOS %sR)" % (key, p.get("net"), p.get("oos_net")))
        print("%-30s | %-31s | %-31s" % ("arm", "IS  n / net / DD / R-per", "OOS  n / net / DD / R-per"))
        print("-" * 100)
        c_is = run("is", key, 0, False)
        c_oos = run("oos", key, 0, False)
        res["%s|control" % key] = {"is": c_is, "oos": c_oos}
        print("%-30s | %4d /%+8.1f /%6.1f /%+.3f | %4d /%+8.1f /%6.1f /%+.3f"
              % ("control", c_is["n"], c_is["net"], c_is["dd"], c_is["per"],
                 c_oos["n"], c_oos["net"], c_oos["dd"], c_oos["per"]))
        for th in THRESHOLDS:
            for gray in (False, True):
                a = run("is", key, th, gray)
                b = run("oos", key, th, gray)
                nm = "swing < %.1f ATR %s" % (th, "+ GRAY" if gray else "      ")
                res["%s|%s" % (key, nm.strip())] = {"is": a, "oos": b}
                mark = "  dIS %+.1f  dOOS %+.1f" % (a["net"] - c_is["net"], b["net"] - c_oos["net"])
                if a["net"] > c_is["net"] and b["net"] > c_oos["net"]:
                    mark += "  <-- BETTER BOTH"
                print("%-30s | %4d /%+8.1f /%6.1f /%+.3f | %4d /%+8.1f /%6.1f /%+.3f%s"
                      % (nm, a["n"], a["net"], a["dd"], a["per"],
                         b["n"], b["net"], b["dd"], b["per"], mark))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
