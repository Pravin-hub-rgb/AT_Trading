"""Rewrite the fsent registry pins after the C15 start-side fix.

A pin is a claim about a measurement. After the gate changed, all 28 fsent pins
are stale by a little, and a stale pin is worse than a missing one because
exp_fastcheck, exp_resultsdb and every doc compare against it - they would all
agree with each other and all be wrong.

This writes the pins and prints every single field it changes, so the diff is
reviewable rather than a silent rewrite. It touches pins only. Descriptions,
statuses and retirement are not its business.
"""
import json
import re
import sys

sys.path.insert(0, ".")
from exp_tf_family import build_family_module          # noqa: E402
from run_experiment import net_r, get_swings            # noqa: E402
from exp_signal_metrics import load_era                 # noqa: E402
from experiment_registry import EXPERIMENTS, BP          # noqa: E402
from exp_period_autopsy import dd_of                    # noqa: E402
from src.btc.btc_routes import _trade_costs, _net_stats  # noqa: E402
from src.btc.btc_engine import trade_stats              # noqa: E402

REG = "registry/signal.py"
FIELDS = ("n", "net", "dd_net", "win", "oos_n", "oos_net", "oos_dd_net", "oos_win")


def pins_for(sim, d, book):
    e = EXPERIMENTS[book]
    p = {**dict(BP), **(e.get("params") or {})}
    o = sim(d["c1h"], get_swings(d, e.get("swing") or "sw10"), d["c15"], d["sw15"],
            fine_ltf=d["fine"], **p)
    tr = [dict(t) for t in o["ltf_trades"]]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    n = len(tr)
    net = _net_stats(trade_stats(tr), tr)["net_total_r"]
    done = [t for t in tr if t.get("outcome") != "open"]
    dd = dd_of([net_r([t]) for t in done])
    wins = sum(1 for t in done if net_r([t]) > 0)
    return {"n": n, "net": round(net, 2), "dd_net": round(dd, 2),
            "win": round(100.0 * wins / n, 1) / 100.0}


def render(vals):
    order = ["n", "net", "dd_net", "win", "oos_n", "oos_net", "oos_dd_net", "oos_win"]
    parts = []
    for k in order:
        v = vals[k]
        parts.append('"%s": %s' % (k, repr(v) if not isinstance(v, float)
                                    else ("%.2f" % v)))
    return "{" + ", ".join(parts) + "}"


def main():
    sim = build_family_module()
    E = {e: load_era(e) for e in ("is", "oos")}
    text = open(REG, encoding="utf-8").read()

    books = [k for k, v in EXPERIMENTS.items()
             if k.startswith("fsent") and isinstance(v, dict) and (v.get("pins") or {}).get("n")]
    print("=" * 100)
    print("REWRITING %d PINS after the C15 start-side fix" % len(books))
    print("=" * 100)

    changed = 0
    log = []
    for b in books:
        pi = pins_for(sim, E["is"], b)
        po = pins_for(sim, E["oos"], b)
        new = dict(pi)
        new.update({"oos_n": po["n"], "oos_net": po["net"],
                    "oos_dd_net": po["dd_net"], "oos_win": po["win"]})
        old = {k: EXPERIMENTS[b]["pins"].get(k) for k in FIELDS}
        if all(abs((old[k] or 0) - new[k]) < 0.005 for k in FIELDS):
            continue
        m = re.search(r'"%s":\s*\{\s*"desc".*?"pins":\s*(\{[^}]*\})' % re.escape(b),
                      text, re.S)
        if not m:
            print("  %-36s SKIPPED - pin block not found in source" % b[:36])
            continue
        text = text[:m.start(1)] + render(new) + text[m.end(1):]
        diffs = ", ".join("%s %s->%s" % (k, old[k], new[k])
                          for k in FIELDS
                          if abs((old[k] or 0) - new[k]) >= 0.005)
        print("  %-36s %s" % (b[:36], diffs))
        log.append(dict(book=b, old=old, new=new))
        changed += 1

    open(REG, "w", encoding="utf-8").write(text)
    print("\n  %d pin blocks rewritten in %s" % (changed, REG))
    with open("_repin_applied.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=1, default=str)
    print("  wrote _repin_applied.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())