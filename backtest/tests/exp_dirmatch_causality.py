"""exp_dirmatch_causality - measure whether the dirmatch family is look-ahead,
rather than taking the closed doc's word for it.

WHAT IS BEING TESTED

exp_require_dir_match decides whether to take an LTF signal by asking which 15m
swing contains the entry bar and reading that swing's direction. The relevant
code, in test_experiments_craze.py:

    for _gs in swings_ltf:
        _gsi = seg.start_idx
        if 0 <= _gsi <= i:                     # the swing has STARTED
            if exp_dir_causal:                 # default 0
                if confirmed_at_idx > i: continue
            _gen_dir = 1 if _gs.dir == "up" else -1    # the FINAL direction
    if exp_require_dir_match and _gen_dir != direction:
        continue

A swing's `dir` field is only final once the swing CONFIRMS. Confirmation is
what prints the first swing and freezes the label. So the question is not
whether the code "peeks at the future" in some vague sense - it is whether the
swing it reads has confirmed by the entry bar. exp_dir_causal=1 answers yes and
exp_dir_causal=0 answers no, and the knob exists precisely so both can be run.

THE MEASUREMENT

Same book, both eras, twice: default, and with exp_dir_causal=1. If the
default is causal then the two runs are the same book and the flag is a no-op.
If the default reads an unsettled field, the flag must change the result, and
the direction it changes it in is the finding - a selection rule that only
works when it can see the answer will lose most of its edge the moment it is
made honest.

This is the instrument the closed doc says works, and it is why
exp_prefix_audit.py is not used here: that tool cleared dirmatch_multi_sw10,
which is contaminated, so its silence proves nothing. Naming the field and
asking when it settles is the direct question.

    cd backtest/tests
    python exp_dirmatch_causality.py
    python exp_dirmatch_causality.py --book dirmatch_multi_sw10
"""
import sys, time, argparse, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs, _net_stats
from src.btc.btc_engine import trade_stats
import experiment_registry as reg

# Books that carry exp_require_dir_match=1. Every one is status="reference";
# this script exists to decide whether that label is right, not to promote them.
DIRMATCH = [k for k, v in reg.EXPERIMENTS.items()
            if isinstance(v, dict) and (v.get("params") or {}).get("exp_require_dir_match")]


def measure(sim, data, cfg, extra=None):
    sw = data["sw10"] if cfg["swing"] == "sw10" else data["sw20"]
    fine = data["fine"] if cfg.get("basis", "fine") == "fine" else []
    params = {**dict(re_.BP), **cfg["params"]}
    if extra:
        params.update(extra)
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"],
             fine_ltf=fine, **params)["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    ns = _net_stats(trade_stats(tr), tr)
    return {"n": len(tr), "net": round(ns["net_total_r"], 2),
            "wr": round(ns.get("win_rate", 0.0), 1)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--book", action="append", default=[])
    ap.add_argument("--oos-only", action="store_true")
    a = ap.parse_args(argv)

    keys = a.book or sorted(DIRMATCH)
    if not keys:
        print("no book carries exp_require_dir_match - family is absent")
        return 0
    scopes = ["oos"] if a.oos_only else ["is", "oos"]
    print("=" * 78)
    print("DIRMATCH CAUSALITY - default vs exp_dir_causal=1")
    print("the default reads a swing's FINAL direction without checking the")
    print("swing had confirmed at the entry bar. This measures what that costs.")
    print("=" * 78)
    t0 = time.time()
    sim = re_.build_module()
    data = {s: EQ.load_scope(s) for s in scopes}
    print("data loaded (%.0fs)\n" % (time.time() - t0))

    for k in keys:
        cfg = reg.EXPERIMENTS[k]
        print("%s   (status=%s)" % (k, cfg.get("status", "<candidate>")))
        for scope in scopes:
            d = measure(sim, data[scope], cfg)
            c = measure(sim, data[scope], cfg, {"exp_dir_causal": 1})
            dn = d["n"] - c["n"]
            dnet = d["net"] - c["net"]
            dwr = d["wr"] - c["wr"]
            print("  %-4s default   n=%-4d net=%+9.2f  WR %4.1f%%" % (scope.upper(), d["n"], d["net"], d["wr"]))
            print("  %-4s causal    n=%-4d net=%+9.2f  WR %4.1f%%"
                  % ("", c["n"], c["net"], c["wr"]))
            print("       delta     n=%+-4d net=%+9.2f  WR %+5.1f pts" % (dn, dnet, dwr))
        print()
        sys.stdout.flush()

    print("total %.0fs" % (time.time() - t0))
    print("Read: a large delta means the default arm was using information that")
    print("was not available at the entry bar. It does not by itself say which")
    print("arm is the better book - it says the default arm is not a book that")
    print("could have been traded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())