"""SERIAL SINGLE + FILTERS, AND THE HIGH-WIN-RATE CANDIDATES - run on the engine.

PART 1 - the deployment shape
    `exp_fs_single.py` established that the bare serial single book is LOSING
    out of sample (-16.3R on champion_single_sw10) and that directional FS entry
    rescues it. That rescue is a TRIGGER change, not a filter. The open question
    this file answers is whether a filter removes the losing serial trades in
    the first place, and whether trigger + filter stack or interfere.

    Filters swept, all already-registry knobs, all on the single plane:
      exp_require_dir_match  - HTF swing must agree with the LTF entry direction
      exp_max_swing_age      - only fresh swings
      exp_swingpause         - skip the pause before a break
      exp_wage_h             - hours the direction is held before the swing counts
      exp_skip_weekend       - no weekend entries
      exp_skip_utc_sat       - no UTC-Saturday entries

PART 2 - the win-rate candidates the owner remembers
    Two books were quoted from the docs as high-win-rate and are NOT currently
    pinned with a WR field anywhere in the registry:

      age10_dirmatch_multi_sw10  - signal/ANCHOR_BASIS_AUDIT.md:804 quoted it as
        "151t / +455.5R / DD 6.0 / WR 51.7%" (NET-DD 75.9). The registry pin
        says IS 150t / +417.68R, which is a different number from the same book.
        That gap is exactly what has to be settled by running it.

      B3 confirmation-entry - signal/experiments_craze.md:154 "206t / +322.2 gross /
        +278.6 net / WR 40.8% / DD 13.1 / streak 8". Registered as
        `gap_b3k2` / `gap_b3k4` on the champion lane.

    WR is computed here from the engine, both eras, and reported next to the
    book's pins so the doc figure and the engine figure can be compared
    directly rather than trusted.

READ-ONLY. No registry write.
"""
import sys, json, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs
import experiment_registry as reg

OUT = ROOT / "backtest" / "tests" / "_fs_serial_filters.json"
SINGLE = ["champion_single_sw10", "champion_single_sw20"]
FILTERS = [
    ("dirmatch", {"exp_require_dir_match": 1}),
    ("swingpause", {"exp_swingpause": 1}),
    ("dirmatch+age10", {"exp_require_dir_match": 1, "exp_max_swing_age": 10}),
    ("dirmatch+swingpause", {"exp_require_dir_match": 1, "exp_swingpause": 1}),
    ("wage10", {"exp_wage_h": 10}),
    ("skip_weekend", {"exp_skip_weekend": 1}),
    ("skip_utc_sat", {"exp_skip_utc_sat": 1}),
]
WR_BOOKS = ["age10_dirmatch_multi_sw10", "dirmatch_multi_sw10",
            "age10_dirmatch_swingpause_single_sw10", "gap_b3k2", "gap_b3k4",
            "dirmatch_single_sw10"]


def run(scope, key, extra, mpos):
    cfg = reg.EXPERIMENTS[key]
    d = EQ.load_scope(scope)
    sim = re_.build_module()
    o = dict(re_.BP)
    o.update(cfg["params"])
    o.update(extra)
    if mpos is not None:
        o["max_positions"] = mpos
    sw = d["sw10"] if cfg["swing"] == "sw10" else d["sw20"]
    fine = d["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(d["c1h"], sw, d["c15"], d["sw15"], fine_ltf=fine, **o)["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    tr = [t for t in tr if t.get("outcome") != "open"]
    rs = [float(t.get("r_multiple", 0.0)) - float(t.get("cost_r", 0.0)) for t in tr]
    eq = pk = dd = 0.0
    for r in rs:
        eq += r
        pk = max(pk, eq)
        dd = max(dd, pk - eq)
    gp = sum(r for r in rs if r > 0)
    ll = -sum(r for r in rs if r < 0)
    return {"n": len(tr), "net": round(eq, 2), "dd": round(dd, 2),
            "per": round(eq / max(len(tr), 1), 3),
            "wr": round(100.0 * sum(1 for r in rs if r > 0) / max(len(tr), 1), 1),
            "pf": round(gp / ll, 2) if ll > 0 else 0.0}
def main():
    res = {}
    print("=" * 100)
    print("PART 1 - SERIAL SINGLE (max_positions=1): does a filter beat the trigger?")
    print("=" * 100)
    for key in SINGLE:
        if key not in reg.EXPERIMENTS:
            continue
        print("\nBASE: %s" % key)
        print("%-26s | %-31s | %-31s" % ("config", "IS  n / net / DD / WR", "OOS  n / net / DD / WR"))
        print("-" * 100)
        for tag, extra in [("bare (control)", {})] + FILTERS:
            for side, snm in ((None, "break"), ("short", "FS-short"), ("long", "FS-long")):
                ex = dict(extra)
                if side:
                    ex["exp_fs_entry_side"] = side
                a = run("is", key, ex, 1)
                b = run("oos", key, ex, 1)
                nm = "%s + %s" % (tag, snm)
                res["%s|%s|is" % (key, nm)] = a
                res["%s|%s|oos" % (key, nm)] = b
                print("%-26s | %4d /%+8.1f /%6.1f /%4.1f%% | %4d /%+8.1f /%6.1f /%4.1f%%"
                      % (nm, a["n"], a["net"], a["dd"], a["wr"],
                         b["n"], b["net"], b["dd"], b["wr"]))
            print("")

    print("\n" + "=" * 100)
    print("PART 2 - WIN-RATE CANDIDATES: engine WR vs the figure quoted in the docs")
    print("=" * 100)
    print("%-38s | %-30s | %-30s" % ("book", "IS  n / net / WR", "OOS  n / net / WR"))
    print("-" * 100)
    for key in WR_BOOKS:
        if key not in reg.EXPERIMENTS:
            print("%-38s | not in registry" % key)
            continue
        p = reg.EXPERIMENTS[key]["pins"]
        a = run("is", key, {}, None)
        b = run("oos", key, {}, None)
        res["WR|%s|is" % key] = a
        res["WR|%s|oos" % key] = b
        flag = ""
        if p.get("n") and a["n"] != p["n"]:
            flag = "   <-- pin n=%s, engine n=%s" % (p["n"], a["n"])
        print("%-38s | %4d /%+8.1f /%4.1f%% | %4d /%+8.1f /%4.1f%%%s"
              % (key, a["n"], a["net"], a["wr"], b["n"], b["net"], b["wr"], flag))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()