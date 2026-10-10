"""exp_fastcheck - pin verification for the books that actually matter, fast.

WHY THIS EXISTS
    exp_pinverify.py re-derives all 207 pinned books. That is the right check
    before a registry-wide claim, but it is the wrong check while
    EXPERIMENTING: it walks every book including the 75 below the line and the
    30 inert reference rows, so one FS knob edit costs ~30 minutes before you
    learn whether it broke the book you were actually working on.

    This asks the narrow question instead: "did the books I care about
    change?" - the shortlisted books, top of the board first, both eras, all
    pinned fields.

    cd backtest/tests
    python exp_fastcheck.py                 # top 12 by IS net, IS + OOS
    python exp_fastcheck.py --top 25        # deeper
    python exp_fastcheck.py fsexit4_c fsexit6_c
    python exp_fastcheck.py --all           # fall back to the slow sweep's job
    python exp_fastcheck.py --oos-only      # OOS pass only

A pin is not self-attesting. Both this and exp_pinverify.py exist because the
registry is only worth what the engine reproduces - see the 2026-10-02
twelve-book inheritance fault, where every pin was copied from a run that had
the right knob and nothing compared the two.
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

TOL = 0.5   # same tolerance run_experiment.py and exp_pinverify.py use
FIELDS = ("n", "net", "dd_net")


def _pinned():
    return [k for k, v in reg.EXPERIMENTS.items()
            if isinstance(v, dict) and (v.get("pins") or {}).get("n")]


def _shortlisted():
    """The same rule the board uses: a size filter, not a verdict."""
    out = []
    for k, v in reg.EXPERIMENTS.items():
        # EXPERIMENTS holds a few alias rows whose value is a STRING pointing
        # at the real book. They are not books, so they have no pins and must
        # not reach .get(). _pinned() already guards for this; this one did
        # not, which made `exp_fastcheck --top N` raise AttributeError before
        # checking anything.
        if not isinstance(v, dict):
            continue
        p = v.get("pins") or {}
        if not p.get("n"):
            continue
        if (p.get("net", -1e9) >= reg.SHORTLIST_IS_MIN
                and p.get("oos_net", -1e9) >= reg.SHORTLIST_OOS_MIN):
            out.append(k)
    out.sort(key=lambda k: -(reg.EXPERIMENTS[k]["pins"].get("net") or 0))
    return out


def measure(sim, data, cfg):
    """Re-run the engine for one book and return its pinned fields."""
    sw = {"sw10": data["sw10"], "sw20": data["sw20"],
          "sw15": data["sw15"], "htf15": data["htf15"]}[cfg["swing"]]
    fine = data["fine"] if cfg.get("basis", "fine") == "fine" else []
    tr = sim(data["c1h"], sw, data["c15"], data["sw15"],
             fine_ltf=fine, **{**dict(re_.BP), **cfg["params"]})["ltf_trades"]
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
    return {"n": len(tr),
            "net": _net_stats(trade_stats(tr), tr)["net_total_r"],
            "dd_net": re_._net_dd(tr)}


def wanted(scope, p):
    """The pinned fields this scope is supposed to reproduce."""
    if scope == "is":
        return {"n": p["n"], "net": p["net"], "dd_net": p.get("dd_net")}
    return {"n": p.get("oos_n"), "net": p.get("oos_net"), "dd_net": p.get("oos_dd_net")}


def compare(scope, exp, got):
    """Exact on n, TOL on the two R fields. Returns a list of disagreements."""
    bad = []
    for f in FIELDS:
        want = exp[f]
        if want is None:
            continue           # scope not pinned for this book; nothing to prove
        diff = abs(got[f] - want)
        if f == "n":
            if diff:
                bad.append("%s want %s got %s" % (f, want, got[f]))
        elif diff > TOL:
            bad.append("%s want %.2f got %.2f" % (f, want, got[f]))
    return bad
def main(argv=None):
    ap = argparse.ArgumentParser(description="fast pin check for the top books")
    ap.add_argument("books", nargs="*", help="book names; default is the top of the shortlist")
    ap.add_argument("--top", type=int, default=12, help="how many shortlisted books (default 12)")
    ap.add_argument("--all", action="store_true", help="every pinned book - as slow as exp_pinverify.py")
    ap.add_argument("--oos-only", action="store_true", help="skip the IS pass")
    ap.add_argument("--json", metavar="PATH", help="also write the rows here")
    a = ap.parse_args(argv)

    all_pinned = _pinned()
    books = a.books if a.books else (_shortlisted()[:a.top] if not a.all else all_pinned)

    unknown = [b for b in books if b not in all_pinned]
    if unknown:
        print("not pinned books: %s" % ", ".join(unknown))
        return 2
    if not books:
        print("nothing to check")
        return 0

    scopes = ["oos"] if a.oos_only else ["is", "oos"]
    print("=" * 70)
    print("FAST PIN CHECK - %d book(s), scope(s): %s"
          % (len(books), " + ".join(s.upper() for s in scopes)))
    print("=" * 70)

    t0 = time.time()
    from progress import Announce, Bar
    n_scope = len(scopes)
    per = 25                       # measured: ~25s per book per scope on this box
    est = int(per * len(books) * n_scope)
    with Announce("loading candles + swings",
                  "%ds" % (est // 3),
                  "engine build + 1h/15m swing chains"):
        sim = re_.build_module()
        data = {s: EQ.load_scope(s) for s in scopes}
    print("data loaded (%.0fs)\n" % (time.time() - t0))
    print("  estimating ~%ds total (%ds/book/scope). bar below.\n" % (est, per))
    bar = Bar(max(1, len(books) * n_scope), "starting")

    fails, rows = [], []
    for i, name in enumerate(books, 1):
        cfg, p = reg.EXPERIMENTS[name], reg.EXPERIMENTS[name]["pins"]
        book_bad = []
        for scope in scopes:
            t1 = time.time()
            try:
                got = measure(sim, data[scope], cfg)
            except Exception as e:
                book_bad.append("%s raised %s" % (scope, repr(e)[:70]))
                rows.append({"book": name, "scope": scope, "err": repr(e)[:120]})
                bar.update("%s/%s ERR" % (name, scope))
                continue
            bad = compare(scope, wanted(scope, p), got)
            rows.append({"book": name, "scope": scope, "OK": not bad,
                         **{k: round(float(v), 2) for k, v in got.items()},
                         "bad": bad})
            book_bad += ["%s %s" % (scope, b) for b in bad]
            bar.update("%s %s" % (name, scope))
        fails += ["%s: %s" % (name, b) for b in book_bad]
        print("  [%2d/%2d] %-40s %s (%.0fs)"
              % (i, len(books), name, "OK" if not book_bad else "FAIL  " + "; ".join(book_bad),
                 time.time() - t0))
    bar.close("done")

    print()
    for r in rows:
        if "err" in r:
            print("    %-40s %-3s ERROR %s" % (r["book"], r["scope"], r["err"]))
        else:
            print("    %-40s %-3s n=%-4d net=%+8.2f dd=%6.2f  %s"
                  % (r["book"], r["scope"], r["n"], r["net"], r["dd_net"],
                     "OK" if r["OK"] else "MISMATCH " + "; ".join(r["bad"])))
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")

    print("\ntotal %.0fs" % (time.time() - t0))
    if fails:
        print("RESULT: FAIL - %d disagreement(s):" % len(fails))
        for f in fails:
            print("        - %s" % f)
        return 1
    print("RESULT: PASS - %d book(s) re-derived from the engine, every pinned field"
          % len(books))
    print("        reproduced on %s." % " and ".join(s.upper() for s in scopes))
    print("        NOT checked: %d of %d pinned books. The registry-wide claim is"
          % (len(all_pinned) - len(books), len(all_pinned)))
    print("        exp_pinverify.py's, and this does not discharge it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())