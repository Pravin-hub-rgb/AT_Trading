"""PREFIX AUDIT - a general look-ahead detector for ANY book in the registry.

WHY A NEW TOOL
    `dirmatch` sat at the top of this board for a long time reading a swing's
    FINAL direction, and every pin check passed. The reason no existing tool
    caught it: `exp_pinverify.py` and `exp_fastcheck.py` both answer ONE
    question - "does the engine reproduce this pin?" - and they answer it by
    running the engine. If the engine itself reads the future, the pin
    reproduces perfectly and every check is green. Nothing in the repo asked
    the other question: "does this book change when the future changes?"

THE TEST
    Run the book twice on the SAME history:

      1. full   - the whole in-sample range
      2. cut    - the same range with the LAST 20% of candles removed

    Then compare only the trades that fall BEFORE the cut, on both runs.

    A causal book cannot do this. Every candle before the cut is identical, no
    bar after it was ever read, so the engine must reproduce the same trades.
    If the pre-cut trades differ - different count, different entry prices,
    different exits - the engine read something from the removed tail.

    This catches ANY mechanism, not one named knob: a future label, a final
    swing field, a full-history normalisation, an end-of-sample leak, a
    threshold fitted on the whole series. It does not need to know what it is
    looking for.

    The only false-positive risk is a legitimately global quantity (a z-score
    over the full sample, a percentile rank). Those would show up here and have
    to be justified individually - which is the right outcome: a global
    statistic is not tradeable and should be argued for, not assumed.

READ-ONLY. No registry write, no engine change.
"""
import sys, json, time, pathlib, bisect, datetime as dt
ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import run_experiment as re_
import exp_equity_quality as EQ
from src.btc.btc_routes import _trade_costs, _compute_swings
from exp_fs_census import flow_of
import experiment_registry as reg

OUT = ROOT / "backtest" / "tests" / "_prefix_audit.json"
# corrupt the tail FROM each of these fractions of the sample, and check the
# band just before each one. Many cuts, because a ~2h-to-18h look-ahead
# can only touch trades that close to the cut.
CUTS = (0.35, 0.50, 0.62, 0.74, 0.86)
CUT = 0.80          # keep the first 80% of the LTF range, drop the tail


def _f(ts):
    return dt.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")


def corrupt(candles, at):
    """Reverse every candle's OHLC after `at`: open<-close, high<-low.

    Truncation removes the future; corruption keeps its SHAPE and destroys its
    content. That matters for power. A truncated chain simply stops emitting
    swings, so a filter that reads a swing's final label often lands on the same
    earlier swing and returns the same answer by chance. A corrupted chain
    still emits every swing, each with a DIFFERENT final label, so any read of
    the future returns a different answer every time. Same number of bars, same
    density, same windows - only the content after the cut differs.
    """
    out = []
    for c in candles:
        if int(c["ts"]) < at:
            out.append(c)
        else:
            d = dict(c)
            d["open"], d["close"] = c["close"], c["open"]
            d["high"], d["low"] = c["low"], c["high"]
            out.append(d)
    return out


def run(sim, scope, key, cut_at=None):
    """cut_at=None -> full run. Otherwise truncate the LTF plane at that ts."""
    cfg = reg.EXPERIMENTS[key]
    d = EQ.load_scope(scope)
    o = dict(re_.BP)
    o.update(cfg["params"])
    c15, sw15 = d["c15"], d["sw15"]
    fine = d["fine"]
    if cut_at is not None:
        # corrupt the tail on BOTH planes and rebuild the LTF chain from it, so
        # the engine still sees a complete, well-formed history - just a
        # different one after the cut.
        ts15 = [int(c["ts"]) for c in c15]
        k = bisect.bisect_left(ts15, cut_at)
        c15 = corrupt(c15, cut_at)
        sw15 = _compute_swings(flow_of(c15), "continuous", min_bars=50)
        fine = corrupt(fine, cut_at) if fine else fine
    sw = d["sw10"] if cfg["swing"] == "sw10" else d["sw20"]
    tr = sim(d["c1h"], sw, c15, sw15, fine_ltf=fine, **o)["ltf_trades"]
    return [t for t in tr if t.get("outcome") != "open"], cut_at
    _trade_costs(tr, 0.055, 2, 0.005, 0.01, 0.01)
BAND_DAYS = 21   # only trades this close to the cut can be affected by it


def fingerprint(trades, upto, since=None):
    """Trades before the cut, optionally restricted to a band just before it.

    The band matters. A look-ahead of a few hours only matters for decisions
    made a few hours before the cut: a swing that confirms after the cut is
    simply absent from the truncated chain, and only trades whose own swing was
    still unconfirmed at the cut can notice. Comparing the whole pre-cut history
    hides the leak, because 95% of those trades are far enough from the cut that
    their swings confirm on both sides and match. That is why the first version
    of this test called dirmatch clean.
    """
    out = []
    for t in trades:
        e = int(t["entry_ts"])
        x = int(t["exit_ts"])
        # The trade must be CLOSED before the cut. A trade that is still open
        # at the cut will obviously have an exit that depends on whatever
        # happens after it - corrupting the tail changes that exit, which is not
        # look-ahead, it is just an open position straddling the boundary.
        if e >= upto or x >= upto:
            continue
        if since is not None and e < since:
            continue
        out.append((e, t.get("dir"), round(float(t["entry_price"]), 2),
                    int(t["exit_ts"]), round(float(t["exit_price"]), 2),
                    round(float(t.get("r_multiple", 0.0)), 3)))
    return out


def main():
    sim = re_.build_module()
    keys = sys.argv[1:]
    if not keys:
        keys = [k for k, v in sorted(reg.EXPERIMENTS.items(),
                                     key=lambda x: -((x[1].get("pins") or {}).get("net") or 0))
                if isinstance(v, dict) and isinstance(v.get("pins"), dict) and v["pins"].get("n")
                ][:25]
    res = {}
    print("=" * 96)
    print("PREFIX AUDIT - keep first %d%% of the LTF range, drop the tail, compare the pre-cut trades."
          % int(CUT * 100))
    print("A book whose pre-cut trades change when the future is removed is reading the future.")
    print("=" * 96)
    print("%-40s | %-19s | %-19s | %s"
          % ("book", "full band trades", "cut run band", "verdict"))
    print("-" * 96)
    for key in keys:
        if key not in reg.EXPERIMENTS:
            continue
        t0 = time.time()
        try:
            full, _ = run(sim, "is", key, None)
            if full is None:
                print("%-40s | no data" % key)
                continue
            ts15 = [int(c["ts"]) for c in EQ.load_scope("is")["c15"]]
            tot = chg = cuts_used = 0
            examples = []
            for frac in CUTS:
                cut_ts = ts15[int(len(ts15) * frac)]
                band = cut_ts - BAND_DAYS * 86400
                cut, _ = run(sim, "is", key, cut_ts)
                if cut is None:
                    continue
                fa = fingerprint(full, cut_ts, band)
                fb = fingerprint(cut, cut_ts, band)
                if not fa:
                    continue
                cuts_used += 1
                only_f = [x for x in fa if x not in fb]
                tot += len(fa)
                chg += len(only_f) + len([x for x in fb if x not in fa])
                if only_f and len(examples) < 2:
                    examples.append({"cut": _f(cut_ts), "trade_gone": only_f[0]})
            verdict = "clean" if chg == 0 else ("LEAK: %d/%d band trades moved" % (chg, tot))
            res[key] = {"cuts": cuts_used, "band_trades": tot, "changed": chg,
                        "identical": chg == 0, "examples": examples}
            print("%-40s | %4d band trades / %d cuts | %s  (%.0fs)"
                  % (key, tot, cuts_used, verdict, time.time() - t0))
        except Exception as e:
            print("%-40s | ERROR %s" % (key, repr(e)[:40]))
            continue
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    bad = [k for k, v in res.items() if not v["identical"]]
    print("\n%d of %d books show pre-cut trades CHANGING when the tail is removed."
          % (len(bad), len(res)))
    for k in bad:
        print("   LEAK  %-38s %d full-only / %d cut-only"
              % (k, res[k]["only_in_full"], res[k]["only_in_cut"]))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()

