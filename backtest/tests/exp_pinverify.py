"""exp_pinverify - re-derive every registry pin from the engine.

Run this whenever the registry changes, and before claiming any book is
measured. Comparing the registry against a stored measurement only proves the
file was not edited; this re-runs the engine.

    cd backtest/tests
    python exp_pinverify.py            # verify all
    python exp_pinverify.py gap_bm09   # verify a subset

Writes _pinverify_results.json incrementally and prints progress, because a
207-book run takes a while and a silent run is indistinguishable from a hung
one. The 2026-10-02 twelve-book inheritance fault was invisible until this was
run - see the implicit-inheritance check in exp_origin_lookahead.py for the
other half of that story.
"""
import sys, json, time, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
from src.btc.btc_routes import _trade_costs, _net_stats
from src.btc.btc_engine import trade_stats
import experiment_registry as reg

OUT = ROOT / "backtest" / "tests" / "_pinverify_results.json"
TOL = 0.5   # the runner's own tolerance; matches what run_experiment.py checks


def main(argv):
    keys = argv[1:]
    books = [k for k, v in reg.EXPERIMENTS.items()
             if isinstance(v, dict) and (v.get("pins") or {}).get("n")]
    if keys:
        unknown = [k for k in keys if k not in books]
        if unknown:
            print("no such book: %s" % ", ".join(unknown))
            return 2
        books = keys

    res = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    print("verifying %d book(s) on %s" % (len(books), reg.BP.get("cooldown_bars") and "BP"))
    t0 = time.time()
    data = re_.get_data()
    sim = re_.build_module()

    def flush():
        OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")

    for i, key in enumerate(books, 1):
        cfg = reg.EXPERIMENTS[key]
        ts = time.time()
        try:
            sw = re_.get_swings(data, cfg["swing"])
            fine = data["fine"] if cfg.get("basis", "fine") == "fine" else []
            tr = sim(data["c1h"], sw, data["c15"], data["sw15"],
                     fine_ltf=fine, **{**dict(re_.BP), **cfg["params"]})["ltf_trades"]
            _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
            nt = _net_stats(trade_stats(tr), tr)["net_total_r"]
            dd = re_._net_dd(tr)
            p = cfg["pins"]
            ok = (p["n"] == len(tr) and abs((p.get("net") or 0) - nt) < TOL
                  and abs((p.get("dd_net") or 0) - dd) < TOL)
            res[key] = {"n": len(tr), "net": round(nt, 2), "dd_net": round(dd, 2),
                        "pin_n": p["n"], "pin_net": p["net"], "pin_dd_net": p.get("dd_net"),
                        "OK": ok, "secs": round(time.time() - ts, 1)}
        except Exception as e:
            res[key] = {"err": repr(e)[:140], "OK": False,
                        "secs": round(time.time() - ts, 1)}
        flush()
        r = res[key]
        if "err" in r:
            print("[%3d/%3d] %-38s ERROR %s" % (i, len(books), key, r["err"][:70]))
        elif r["OK"]:
            print("[%3d/%3d] %-38s OK   n=%4d %+9.2f dd %6.2f  (%.1fs)"
                  % (i, len(books), key, r["n"], r["net"], r["dd_net"], r["secs"]))
        else:
            print("[%3d/%3d] %-38s FAIL engine %d/%+.2f/%.2f  pin %s/%s/%s"
                  % (i, len(books), key, r["n"], r["net"], r["dd_net"],
                     r["pin_n"], r["pin_net"], r["pin_dd_net"]))
        sys.stdout.flush()

    bad = [k for k in books if not res[k].get("OK")]
    print("")
    print("checked %d book(s) in %.0fs; %d mismatch(es)" % (len(books), time.time() - t0, len(bad)))
    if bad:
        for k in bad:
            print("  %s: %s" % (k, json.dumps(res[k])))
        return 1
    print("every pin re-derived from the engine matches")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
