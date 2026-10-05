"""exp_pinrefresh - MEASURE the books that have no pins, and propose pins for them.

WHY THIS EXISTS, AND WHY IT IS NOT exp_pinverify

44 registry books carry `"pins": None`. They are not stale - they are absent.
Every one of them was renamed from `single_` to `sig_` and, in the same edit,
given max_positions=1. The old pins belonged to a multi-position book, so
carrying them forward would have been a lie: the pin would have been recorded
for a different architecture. Blanking them was the honest move and it is why
the count exists.

But a book with no pin is a book nobody can quote, and 44 of them is a third of
the signal family. So they have to be measured. That is GENERATION, not
verification, which is the whole difference from exp_pinverify.py:

  exp_pinverify    re-derives a pin that already exists and compares. An
                   existing pin is a claim to be tested.
  this            runs a book that has no pin and produces one. A new pin is a
                   measurement being recorded for the first time.

Running exp_pinverify over these books does nothing: it selects on
`(pins or {}).get("n")`, so every one of them is skipped. That is correct
behaviour there and useless here.

SAFETY

Dry-run by default. It prints what it would write and writes nothing, because
a pin is a published number and pinning 44 books in one pass is how a whole
family gets a fresh unearned claim. `--write` is a separate, deliberate act,
and it writes a patch file rather than editing the registry, so the change is
still reviewed before it lands.

It also refuses to pin a book that looks contaminated, and it does not touch
`fsent_sig_fs_mom`, whose knobs were written from prose rather than from a
sweep artifact and which does not reproduce its recorded 285/+208.16.

    cd backtest/tests
    python exp_pinrefresh.py                      # dry run, all unpinned
    python exp_pinrefresh.py --book champion_sig_sw10
    python exp_pinrefresh.py --write              # emit the patch
"""
import sys, json, time, argparse, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs, _net_stats
from src.btc.btc_engine import trade_stats
import experiment_registry as reg

# Never auto-pin, for two different reasons.
#
# 1. fsent_sig_fs_mom - its params were written from prose, not from a sweep
#    artifact, and fastcheck does not reproduce the recorded 285/+208.16; it
#    gets 235/+262.29. Pinning it would put a number in the registry that the
#    engine does not produce, which is what a pin exists to prevent.
NEVER_PIN = {
    "fsent_sig_fs_mom",
}

# 2. Every book already marked status="reference". These measured LARGE -
#    age10_dirmatch_swingpause_sig_sw10 comes in at IS +397.95 / OOS +52.41 -
#    which is exactly why they need to stay unpinned. exp_require_dir_match
#    reads the swing's final direction, settled a median 8h AFTER the entry bar
#    (CLOSED_DO_NOT_REPEAT.md), so the number is an artefact of reading the
#    future, not an edge. A pin is a claim that the engine reproduces a book;
#    for a contaminated book it would be a claim that the leak is real and
#    reproducible, and these numbers are the most quotable in the file. Leave
#    them None on purpose - `pins: None` and `status: reference` are the same
#    statement: measured, kept for the record, never a candidate.


def unpinned():
    return [k for k, v in reg.EXPERIMENTS.items()
            if isinstance(v, dict) and v.get("pins") is None]


def measure(sim, data, cfg):
    sw = data["sw10"] if cfg["swing"] == "sw10" else data["sw20"]
    fine = data["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"],
             fine_ltf=fine, **{**dict(re_.BP), **cfg["params"]})["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    st = trade_stats(tr)
    ns = _net_stats(st, tr)
    return {
        "n": len(tr),
        "net": round(ns["net_total_r"], 2),
        "dd_net": round(re_._net_dd(tr), 2),
        "win": round(ns.get("win_rate", 0.0), 4),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--book", action="append", default=[],
                    help="only this book (repeatable)")
    ap.add_argument("--oos-only", action="store_true")
    ap.add_argument("--write", action="store_true",
                    help="write the suggested pins to _pinrefresh.json")
    ap.add_argument("--patch", action="store_true",
                    help="also print a registry patch snippet")
    a = ap.parse_args(argv)

    keys = a.book or unpinned()
    if not keys:
        print("every book has a pin")
        return 0
    unknown = [k for k in keys if k not in reg.EXPERIMENTS]
    if unknown:
        print("no such book: %s" % ", ".join(unknown))
        return 2

    skipped = [k for k in keys if k in NEVER_PIN]
    # Skip reference books and the explicit denylist. A reference book's whole
    # point is that its number must not be quotable, and a pin is the most
    # quotable thing in this repo.
    ref = [k for k in keys if reg.EXPERIMENTS[k].get("status") == "reference"]
    keys = [k for k in keys
            if k not in NEVER_PIN and reg.EXPERIMENTS[k].get("status") != "reference"]
    if skipped:
        print("REFUSING to pin %s (see NEVER_PIN)" % ", ".join(skipped))
    if ref:
        print("SKIPPING %d reference book(s) - measured for the record, never pinned:"
              % len(ref))
        for k in sorted(ref):
            print("    %-44s status=reference" % k)
    if not keys:
        print("\nnothing to pin: every requested book is denied or reference")
        return 0

    scopes = ["oos"] if a.oos_only else ["is", "oos"]
    print("=" * 74)
    print("PIN REFRESH - %d book(s), scope(s): %s   (dry run, nothing written)"
          % (len(keys), " + ".join(s.upper() for s in scopes)))
    print("=" * 74)
    t0 = time.time()
    sim = re_.build_module()
    data = {s: EQ.load_scope(s) for s in scopes}
    print("data loaded (%.0fs)\n" % (time.time() - t0))

    out = {}
    for i, k in enumerate(keys, 1):
        cfg = reg.EXPERIMENTS[k]
        row = {}
        for scope in scopes:
            try:
                row[scope] = measure(sim, data[scope], cfg)
            except Exception as e:
                row[scope] = {"err": repr(e)[:120]}
        out[k] = row
        isr, oosr = row.get("is", {}), row.get("oos", {})
        if "err" in isr or "err" in oosr:
            print("  [%2d/%2d] %-42s ERROR %s"
                  % (i, len(keys), k, (isr.get("err") or oosr.get("err"))[:60]))
        else:
            print("  [%2d/%2d] %-42s IS %4d / %+8.2f   OOS %4d / %+8.2f"
                  % (i, len(keys), k, isr["n"], isr["net"], oosr["n"], oosr["net"]))
        sys.stdout.flush()

    if not a.write:
        print("\n%d book(s) measured in %.0fs. Nothing written." % (len(out), time.time() - t0))
        print("Re-run with --write to save these to _pinrefresh.json.")
        return 0

    dst = ROOT / "backtest/tests/_pinrefresh.json"
    dst.write_text(json.dumps(out, indent=1, sort_keys=True), encoding="utf-8")
    print("\nwrote %s (%d books)" % (dst.name, len(out)))

    if a.patch:
        print("\n# registry patch (paste into the right registry/*.py module):")
        for k, r in sorted(out.items()):
            if "err" in r.get("is", {}) or "err" in r.get("oos", {}):
                continue
            i, o = r["is"], r["oos"]
            print('    "%s": {' % k)
            print('          "pins": {"n": %d, "net": %s, "dd_net": %s, "win": %s,'
                  % (i["n"], i["net"], i["dd_net"], i["win"]))
            print('                   "oos_n": %d, "oos_net": %s, "oos_dd_net": %s,'
                  % (o["n"], o["net"], o["dd_net"]))
            print('                   "oos_win": %s},' % o["win"])
            print('      },')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())