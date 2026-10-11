"""exp_repin_stale - re-derive pins whose recorded value the engine no longer produces.

WHY THIS IS NOT exp_pinrefresh.py
================================
exp_pinrefresh selects on `pins is None` - a pin that is ABSENT. This selects on
a pin that is STALE: present, non-null, and no longer what the engine produces.
After C17 (2026-10-07, method/C17_WINDOW_END_CAUSALITY.md) that is 214 of the
215 pinned books, and every one of them has to be re-measured or the registry
publishes numbers the engine contradicts.

    exp_pinrefresh   a pin is missing              -> GENERATION, write one
    this             a pin is present and wrong    -> CORRECTION, rewrite it

Running exp_pinverify against these books is the detection step and it already
reports them; this is the measurement step.

SAFETY, mirroring exp_pinrefresh
================================
* dry run by default, nothing written
* `--write` writes a JSON card AND a registry patch file; it never edits the
  registry itself, so the change is still reviewed before it lands
* every book's OLD pin is carried into the output beside the new one, so the
  discrepancy stays visible instead of being overwritten out of history
* `status: "reference"` books are skipped. A reference book's whole point is
  that its number must not be quotable, and a pin is the most quotable thing in
  this repo. Same reason exp_pinrefresh skips them.
* only keys the old pin already had are rewritten, so a book that never carried
  `win` does not acquire one
* books whose movement is larger than the C17 range seen anywhere in the blast
  radius are flagged `REVIEW`, not silently accepted

Usage:
    cd backtest/tests
    python exp_repin_stale.py                       # dry run, stale per pinverify
    python exp_repin_stale.py --select all          # re-measure every pinned book
    python exp_repin_stale.py --book champion_multi_sw10 --book fsent_champ_long
    python exp_repin_stale.py --write --patch        # emit cards + patch file
"""
import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_          # noqa: E402
import exp_equity_quality as EQ       # noqa: E402
from src.btc.btc_routes import _trade_costs, _net_stats   # noqa: E402
from src.btc.btc_engine import trade_stats                 # noqa: E402
import experiment_registry as reg                          # noqa: E402

PINVERIFY = ROOT / "backtest/tests/_pinverify_results.json"
CARD = ROOT / "backtest/tests/_repin_stale.json"
PATCH = ROOT / "backtest/tests/_repin_stale_patch.py"

# Fields this tool measures, per era. Only those already present in a book's
# existing pin get rewritten.
IS_FIELDS = ("n", "net", "dd_net", "win")
OOS_FIELDS = ("oos_n", "oos_net", "oos_dd_net", "oos_win")

# The C17 blast radius moved n by -11..+17 and net by -51..+88 across 214 books.
# Anything outside that envelope did not come from this fix and gets flagged.
OUTLIER_DN = 25
OUTLIER_DNET = 120.0


def stale_from_pinverify():
    """Books whose IS pin is recorded as not holding, from the last verify run."""
    if not PINVERIFY.exists():
        return None
    res = json.loads(PINVERIFY.read_text(encoding="utf-8"))
    out = [k for k, v in res.items()
           if isinstance(v, dict) and v.get("OK") is False and "err" not in v]
    return sorted(out)


def measure(sim, data, cfg):
    # Was: data["sw10"] if cfg["swing"] == "sw10" else data["sw20"]. That silently
    # ran every htf15 book on the sw20 chain instead of erroring, so the three
    # htf15 books measured the wrong strategy and reported a confident number for
    # it. Two of them - fsent_champ_long_htf15_htffs and
    # fsent_champ_long_mcloff_htf15 - are the top two multi books by pinned IS net,
    # so the books that matter most were the ones measured wrong. A KeyError here
    # is the correct outcome for an unknown swing key.
    sw = {"sw10": data["sw10"], "sw20": data["sw20"],
          "sw15": data["sw15"], "htf15": data["htf15"]}[cfg["swing"]]
    fine = data["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"],
             fine_ltf=fine, **{**dict(re_.BP), **cfg["params"]})["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    ns = _net_stats(trade_stats(tr), tr)
    # UNIT. _net_stats reports win_rate as a PERCENT with one decimal
    # (round(100.0*wins/n, 1), btc_routes.py:407). Every one of the 86 win /
    # oos_win values already in registry/*.py is a FRACTION with three decimals
    # (0.102 .. 0.242, zero percent-style), so writing the raw percent would
    # turn 0.24 into 24.1. Converted here, once, at the measurement site.
    return {
        "n": len(tr),
        "net": round(ns["net_total_r"], 2),
        "dd_net": round(re_._net_dd(tr), 2),
        "win": round(ns.get("win_rate", 0.0) / 100.0, 3),
    }


def new_pin(old, is_r, oos_r):
    """Overwrite only the keys the old pin carried, keeping its shape."""
    p = dict(old or {})
    for k in IS_FIELDS:
        if k in p and k in is_r:
            p[k] = is_r[k]
    for k in OOS_FIELDS:
        src = "n" if k == "oos_n" else "net" if k == "oos_net" else \
              "dd_net" if k == "oos_dd_net" else "win"
        if k in p and src in oos_r:
            p[k] = oos_r[src]
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--book", action="append", default=[])
    ap.add_argument("--select", choices=["pinverify", "all"], default="pinverify",
                    help="pinverify = only books the last verify flagged; "
                         "all = every pinned book")
    ap.add_argument("--oos-only", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help="write _repin_stale.json and _repin_stale_patch.py")
    ap.add_argument("--patch", action="store_true",
                    help="also print the patch to stdout")
    a = ap.parse_args(argv)

    if a.book:
        keys = list(dict.fromkeys(a.book))
    elif a.select == "all":
        keys = sorted(k for k, v in reg.EXPERIMENTS.items()
                      if isinstance(v, dict) and (v.get("pins") or {}).get("n"))
    else:
        keys = stale_from_pinverify()
        if keys is None:
            print("no %s - run exp_pinverify.py first, or use --select all"
                  % PINVERIFY.name)
            return 2

    unknown = [k for k in keys if k not in reg.EXPERIMENTS]
    if unknown:
        print("no such book: %s" % ", ".join(unknown))
        return 2

    ref = [k for k in keys if reg.EXPERIMENTS[k].get("status") == "reference"]
    keys = [k for k in keys
            if reg.EXPERIMENTS[k].get("status") != "reference"
            and (reg.EXPERIMENTS[k].get("pins") or {}).get("n")]
    if ref:
        print("SKIPPING %d reference book(s) - never pinned:" % len(ref))
        for k in sorted(ref):
            print("    %-44s status=reference" % k)
    if not keys:
        print("\nnothing to do: every requested book is unpinned or reference")
        return 0

    scopes = ["oos"] if a.oos_only else ["is", "oos"]
    print("=" * 78)
    print("STALE RE-PIN - %d book(s), scope(s): %s   (%s)"
          % (len(keys), " + ".join(s.upper() for s in scopes),
             "dry run, nothing written" if not a.write else "WRITING"))
    print("=" * 78)
    t0 = time.time()
    sim = re_.build_module()
    data = {s: EQ.load_scope(s) for s in scopes}
    print("data loaded (%.0fs)\n" % (time.time() - t0))

    out = {}
    reviews = []
    for i, k in enumerate(keys, 1):
        cfg = reg.EXPERIMENTS[k]
        old = dict(cfg.get("pins") or {})
        row = {"old_pin": old}
        ok = True
        for scope in scopes:
            try:
                row[scope] = measure(sim, data[scope], cfg)
            except Exception as e:
                row[scope] = {"err": repr(e)[:120]}
                ok = False
        if ok:
            row["new_pin"] = new_pin(old, row["is"], row["oos"])
            dn = row["new_pin"].get("n", 0) - old.get("n", 0)
            dnet = row["new_pin"].get("net", 0.0) - (old.get("net") or 0.0)
            row["delta"] = {"dn": dn, "dnet": round(dnet, 2)}
            if abs(dn) > OUTLIER_DN or abs(dnet) > OUTLIER_DNET:
                row["REVIEW"] = "outside the C17 envelope (dn=%d dnet=%.2f)" % (dn, dnet)
                reviews.append(k)
        out[k] = row
        if not ok:
            print("  [%3d/%3d] %-42s ERROR %s"
                  % (i, len(keys), k, (row["is"].get("err") or row["oos"].get("err"))[:60]))
        else:
            i_r, o_r = row["is"], row["oos"]
            print("  [%3d/%3d] %-42s IS %4d/%+8.2f (%+3d/%+7.2f)   "
                  "OOS %4d/%+8.2f   %s"
                  % (i, len(keys), k,
                     i_r["n"], i_r["net"], row["delta"]["dn"], row["delta"]["dnet"],
                     o_r["n"], o_r["net"],
                     "REVIEW" if row.get("REVIEW") else ""))
        sys.stdout.flush()

    print("\n%d book(s) measured in %.0fs" % (len(out), time.time() - t0))
    moved = [k for k, r in out.items() if "new_pin" in r
             and (r["new_pin"].get("n") != r["old_pin"].get("n")
                  or r["new_pin"].get("net") != r["old_pin"].get("net")
                  or r["new_pin"].get("oos_net") != r["old_pin"].get("oos_net"))]
    print("books whose pin actually changes: %d" % len(moved))
    if reviews:
        print("\n%d book(s) OUTSIDE the C17 envelope - review before accepting:"
              % len(reviews))
        for k in reviews:
            print("    %-42s %s" % (k, out[k]["REVIEW"]))

    if not a.write:
        print("\nNothing written. Re-run with --write to emit the card and patch.")
        return 0

    CARD.write_text(json.dumps(out, indent=1, sort_keys=True, default=str) + "\n",
                    encoding="utf-8")
    lines = ["# generated by exp_repin_stale.py -- review, then paste by hand.",
             "# old pins are in _repin_stale.json; nothing here is applied automatically.",
             ""]
    for k, r in sorted(out.items()):
        if "new_pin" not in r:
            continue
        lines.append('    "%s": {' % k)
        p = r["new_pin"]
        lines.append('          "pins": {"n": %s, "net": %s, "dd_net": %s,' %
                     (p.get("n"), p.get("net"), p.get("dd_net")))
        lines.append('                   "oos_n": %s, "oos_net": %s, "oos_dd_net": %s},'
                     % (p.get("oos_n"), p.get("oos_net"), p.get("oos_dd_net")))
        lines.append('      },')
    PATCH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nwrote %s (%d books)" % (CARD.name, len(out)))
    print("wrote %s (%d pin lines)" % (PATCH.name, len(moved)))
    print("registry NOT edited - the patch is for review.")
    if a.patch:
        print("\n" + PATCH.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
