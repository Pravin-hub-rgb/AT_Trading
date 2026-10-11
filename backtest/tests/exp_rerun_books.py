"""Re-run every registered book against the fixed engine, in batches, resumably.

WHY THIS EXISTS
---------------
The per-kind B1 guard landed in firstswing.py and moved fsent_champ_long from
528 trades / +533.37R to 536 / +553.30 on IS. Every other book was measured on
the pre-fix chain, so every pin outside that one book is stale. ARM3 already
established that the earlier family run is void for the in-sample half.

Owner: "poori book he re run karni pdegi, first top contender of multi and sig karo
first round phir rest on those 200+ books, like 40-50 on one run, with progress and
with delta change report."

So: batches of 40-50, round 1 is the top contenders of both planes, round 2 is the
rest, and every batch prints measured-vs-pinned as it goes.

THE htf15 TRAP, WHICH IS THE REASON THIS IS NOT exp_repin_stale.py
--------------------------------------------------------------------
exp_repin_stale.measure() did `data["sw10"] if cfg["swing"] == "sw10" else
data["sw20"]`, so all three htf15 books ran on the sw20 chain and reported a
confident number for the wrong strategy. Two of the three are the top two multi
books by pinned IS net, so the exact books this re-run exists to check were being
measured wrong. Fixed in exp_repin_stale.py; exp_fastcheck.py already did it
correctly and its dict lookup is what is used here.

Nothing is re-pinned by this. It measures and reports a delta. The registry is not
edited.

RESUME
------
State is appended to _rerun_state.json after every book and read back on start, so
a batch that dies at book 37 of 50 resumes at 38 instead of redoing 37 books.
"""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1] / "backend"))

import exp_repin_stale as repin
from experiment_registry import EXPERIMENTS, ALIASES

STATE = HERE / "_rerun_state.json"
DB = HERE / "results.db"
BATCH = 40


def resolve(key):
    cfg = EXPERIMENTS.get(key)
    if cfg is None:
        return None
    if isinstance(cfg, str):                     # alias row
        cfg = EXPERIMENTS.get(cfg)
        if cfg is None:
            return None
    if not cfg.get("pins"):
        return None
    return cfg


def plane_of(cfg):
    """Same rule results_db uses: plane is a fact about max_positions, not the name."""
    bp = dict(repin.re_.BP)
    mp = (cfg.get("params") or {}).get("max_positions", bp.get("max_positions"))
    return "signal" if mp == 1 else "multi"


def load_db():
    if not DB.exists():
        raise SystemExit("results.db missing - run: python exp_resultsdb.py ingest")
    return sqlite3.connect(str(DB))


def quarantined():
    c = load_db()
    try:
        rows = c.execute("SELECT name FROM books WHERE quarantined IS NOT NULL "
                         "AND quarantined != ''").fetchall()
        return {r[0] for r in rows}
    except sqlite3.Error:
        return set()
    finally:
        c.close()


def universe():
    """Every runnable book: registered, has pins, not quarantined, not an alias."""
    q = quarantined()
    out = []
    for k in EXPERIMENTS:
        if k.startswith("_"):
            continue
        cfg = resolve(k)
        if cfg is None or k in q:
            continue
        out.append((k, cfg, plane_of(cfg)))
    return out


def rank(univ, scope):
    """Rank by pinned IS net (or OOS when asked) inside a plane."""
    field = "net" if scope == "is" else "oos_net"
    r = []
    for k, cfg, plane in univ:
        v = (cfg["pins"] or {}).get(field)
        if v is not None:
            r.append((k, cfg, plane, float(v)))
    r.sort(key=lambda t: -t[3])
    return r


def select(univ, round_no, top_multi, top_sig, scope="is"):
    ranked = rank(univ, scope)
    multi = [t for t in ranked if t[2] == "multi"]
    sig = [t for t in ranked if t[2] == "signal"]
    if round_no == 1:
        pick = multi[:top_multi] + sig[:top_sig]
    else:
        pick = multi[top_multi:] + sig[top_sig:]
    return pick


def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_state(st):
    STATE.write_text(json.dumps(st, indent=1, sort_keys=True), encoding="utf-8")


def fmt_delta(old, new):
    if old is None or new is None:
        return "n/a"
    d = float(new) - float(old)
    return "%+.2f" % d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--top-multi", type=int, default=24)
    ap.add_argument("--top-sig", type=int, default=17)
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--scope", choices=["is", "oos"], default="is")
    ap.add_argument("--limit", type=int, default=0, help="0 = all, for a smoke test")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    univ = universe()
    pick = select(univ, args.round, args.top_multi, args.top_sig, args.scope)
    if args.limit:
        pick = pick[:args.limit]

    print("=" * 78)
    print("BOOK RE-RUN  round %d   (ranked by pinned %s net)" % (args.round, args.scope))
    print("=" * 78)
    print("  registry      %d runnable books (%d multi, %d signal)"
          % (len(univ), sum(1 for t in univ if t[2] == "multi"),
             sum(1 for t in univ if t[2] == "signal")))
    print("  quarantined   %d skipped (look-ahead)" % len(quarantined()))
    print("  round %d picks %d books, batch size %d -> %d batch(es)"
          % (args.round, len(pick), args.batch,
             (len(pick) + args.batch - 1) // args.batch))
    print()

    if args.dry_run:
        for i, (k, cfg, plane, pin) in enumerate(pick, 1):
            p = cfg["pins"] or {}
            print("  %3d. %-36s %-6s swing=%-6s IS n=%-5s net=%-8s"
                  % (i, k, plane, cfg["swing"], p.get("n"), p.get("net")))
        return 0

    state = load_state()
    data = {"is": None, "oos": None}
    sim = None

    done = moved = same = 0
    t0 = time.time()
    out_path = HERE / ("_rerun_round%d.json" % args.round)

    for k, cfg, plane, _pin in pick:
        st = state.get(k)
        if st and st.get("round") == args.round and st.get("done"):
            done += 1
            continue
        if sim is None:
            import test_experiments_craze as craze
            sim = craze.build_module()
            print("  engine built in %.1fs\n" % (time.time() - t0))

        row = {"book": k, "plane": plane, "swing": cfg["swing"],
               "pins": cfg["pins"], "eras": {}}
        err = None
        for era in ("is", "oos"):
            try:
                if data[era] is None:
                    from exp_signal_metrics import load_era
                    print("  loading %s data ..." % era, flush=True)
                    data[era] = load_era(era)
                got = repin.measure(sim, data[era], cfg)
                row["eras"][era] = got
            except Exception as e:                       # keep going, record it
                row["eras"][era] = {"error": "%s: %s" % (type(e).__name__, e)}
                err = str(e)
        row["done"] = True
        row["round"] = args.round
        state[k] = row
        save_state(state)

        pis, pos = row["eras"].get("is", {}), row["eras"].get("oos", {})
        pin = cfg["pins"] or {}
        if pis.get("error") or pos.get("error"):
            print("  [ERR] %-34s %s" % (k, pis.get("error") or pos.get("error")))
            continue
        dn = pis["n"] - pin.get("n", 0)
        dnet = pis["net"] - pin.get("net", 0)
        don = pos["n"] - (pin.get("oos_n") or 0)
        d_onet = pos["net"] - (pin.get("oos_net") or 0)
        moved_now = abs(dnet) >= 0.5 or abs(d_onet) >= 0.5 or dn or don
        moved += bool(moved_now)
        same += (not moved_now)
        done += 1
        el = time.time() - t0
        print("  [%3d/%3d] %-34s IS n %+4d net %+7s | OOS n %+4d net %+7s  %s"
              % (done, len(pick), k, dn, fmt_delta(pin.get("net"), pis["net"]),
                 don, fmt_delta(pin.get("oos_net"), pos["net"]),
                 "%5.0fs" % el), flush=True)

    print()
    print("=" * 78)
    print("ROUND %d SUMMARY" % args.round)
    print("=" * 78)
    print("  books measured      %d" % done)
    print("  moved               %d" % moved)
    print("  unchanged           %d" % same)
    print("  elapsed             %.0fs" % (time.time() - t0))
    print("  state               %s" % STATE.name)
    print("  pins changed        NONE - this file never edits the registry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
