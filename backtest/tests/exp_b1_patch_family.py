"""Re-run EVERY registered book on the B1 arming-patched chain: old vs patched, all 161.

WHY EVERYTHING, NOT THE DROPDOWN
--------------------------------
exp_b1_fix_compare did one book and the owner accepted the chart marks. One book is not
evidence about a family. The patch re-walks the swing chain, so any book that reads the
chain can move - and not all of them move the same way, because they consume different
parts of it (FS print, B2 confirmation, swing age, direction match, HTF leg). Running
only the dropdown books would have answered the question for 11 of 161 and reported it
as if it were the family.

Both planes are included. The signal harness (exp_signal_metrics) and the multi harness
(exp_multi_metrics) deliberately refused to mix planes for RANKING, which is a
different question; here the only question is "does the chain move this book", and both
planes read the same chain through the same sim() call.

THE CHAIN IS SWAPPED, NOT THE STRATEGY
--------------------------------------
load_era() builds every swing series through src.btc.btc_routes._compute_swings. That is
the single point all chains pass through, so rebinding it to the patched builder puts a
patched chain under every book without touching strategy code, the registry, or
firstswing.py. The shipped builder is restored in a finally block.

THE PIN CHECK IS THE POINT
--------------------------
The unpatched column must reproduce each registered pin. A book whose patched number
is reported while its own unpatched run disagrees with its pin means the harness is
wrong, not the book - the two are indistinguishable from one number. Mismatches are
counted and printed, and the patched column is marked unverified if there are any.

RESUMABLE
---------
Results are appended to the output JSON after every book. This takes over an hour and
the owner is watching the chart meanwhile; a rerun must not throw away finished work.

Usage:  $env:PYTHONIOENCODING='utf-8'; python -u exp_b1_patch_family.py [limit]
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest/tests"))
sys.path.insert(0, str(ROOT / "backtest"))
sys.path.insert(0, str(ROOT / "backend"))

OUT = ROOT / "backtest/tests/_b1_patch_family.json"
ERAS = ("is", "oos")
SIDES = ("old", "new")


def load_state() -> dict:
    if OUT.exists():
        try:
            s = json.loads(OUT.read_text(encoding="utf-8"))
            if isinstance(s, dict) and "books" in s:
                return s
        except (OSError, json.JSONDecodeError):
            pass
    return {"books": [], "skipped_quarantined": {}, "old": {}, "new": {},
            "pin_mismatches": [], "complete": False}


def save(st: dict) -> None:
    OUT.write_text(json.dumps(st, indent=2, default=str) + "\n", encoding="utf-8")


def all_books() -> tuple[list[str], dict]:
    from experiment_registry import EXPERIMENTS
    from exp_signal_metrics import quarantine_reason
    import results_db as rdb
    conn = rdb.connect(Path(ROOT / "backtest/tests/results.db"))
    names = {r["name"] for r in conn.execute("SELECT name FROM books")}
    conn.close()
    names.update(k for k, v in EXPERIMENTS.items() if isinstance(v, dict))
    clean, skipped = [], {}
    for n in sorted(names):
        cfg = EXPERIMENTS.get(n)
        if not isinstance(cfg, dict):
            skipped[n] = ["not in experiment_registry"]
            continue
        bad = quarantine_reason(cfg.get("params") or {})
        if bad:
            skipped[n] = bad.split(",")
            continue
        clean.append(n)
    return clean, skipped


def run_side(state: dict, side: str, books: list[str], limit: int) -> None:
    import src.btc.btc_routes as R
    from exp_signal_metrics import load_era
    from exp_tf_family import build_family_module
    from run_experiment import BP, net_r, get_swings
    from experiment_registry import EXPERIMENTS
    from exp_full_metrics import compute

    # ARM15. The swap is a process-wide mutation, so anything between installing it
    # and the try-block used to be unprotected: build_family_module() writes and
    # imports a generated engine module, and a failure there - disk full, a lock, a
    # syntax error - propagated out without ever reaching the restore below. The
    # process then kept the patched builder installed for the rest of its life, and
    # a later run on the "old" side would have reported shipped-chain numbers while
    # measuring the patched chain. Nothing about that output would look wrong.
    #
    # So the install moves inside the try. That is the whole fix: the try now opens
    # one line earlier than the code it was protecting.
    try:
        sim = build_family_module()
        # ARM17. The old line filtered against state[side]["__all__"], a key that
        # is never written anywhere, so it always evaluated to "nothing filtered"
        # and read like a resume set that had been wired up. Resume is handled per
        # era below by `need`, which is the filter that actually works.
        todo = list(books)
        if limit:
            todo = todo[:limit]
        for era in ERAS:
            state.setdefault(side, {}).setdefault(era, {})
            need = [b for b in todo if b not in state[side][era]]
            if not need:
                continue
            print("  [%s/%s] building chains for %s ..." % (side, era, era), flush=True)
            data = load_era(era)
            t1 = time.time()
            for i, key in enumerate(need, 1):
                cfg = EXPERIMENTS[key]
                p = {**BP, **cfg["params"]}
                p.setdefault("exp_partial_r", 0.0)
                sw = get_swings(data, cfg.get("swing") or "sw10")
                try:
                    r = sim(data["c1h"], sw, data["c15"], data["sw15"],
                            fine_ltf=data["fine"], **p)
                except Exception as e:                        # noqa: BLE001
                    state[side][era][key] = {"error": str(e)}
                    print("    %-36s ERROR %s" % (key, e), flush=True)
                    continue
                tr = r["ltf_trades"] if isinstance(r, dict) else r
                cl = [t for t in tr if t.get("outcome") != "open"]
                m = compute([net_r([t]) for t in cl],
                            [t.get("entry_date", "") for t in cl])
                m["n_open"] = len(tr) - len(cl)
                pins = cfg.get("pins") or {}
                pin = pins.get("net") if era == "is" else pins.get("oos_net")
                m["pin_net"] = pin
                m["vs_pin"] = (round(m["net"] - pin, 1)
                               if (m.get("n") and pin is not None) else None)
                state[side][era][key] = m
                save(state)
                el = time.time() - t1
                eta = el / i * (len(need) - i)
                print("    [%3d/%3d] %-36s n=%4d net=%+8.1f DD=%5.1f  (%.0fs left)"
                      % (i, len(need), key, m.get("n", 0), m.get("net", 0),
                         m.get("max_dd", 0), eta), flush=True)
    finally:
        # Put the shipped builder back exactly as it was. Deleting the attribute
        # instead of reassigning it would break every later import of the route
        # module in this process, including the pin check that runs after.
        R._compute_swings = _compute_swings_shipped


def report(state: dict, books: list[str]) -> None:
    old, new = state.get("old", {}), state.get("new", {})
    # ARM16. Count what actually ran, not what was on the list. `complete` used to
    # be written unconditionally, so a two-book smoke test left a file claiming the
    # family comparison was finished - and the pin-check line below divided by the
    # full book count, so it could print "0 mismatches out of 322" while two books
    # had been measured. Nothing about that output looked wrong.
    ran, errored, skipped = 0, 0, 0
    for side in SIDES:
        for era in ERAS:
            for k in books:
                cell = (state.get(side, {}) or {}).get(era, {}) or {}
                if k not in cell:
                    skipped += 1
                elif cell[k].get("error"):
                    errored += 1
                else:
                    ran += 1
    expected = len(books) * len(SIDES) * len(ERAS)

    bad = []
    checked = 0
    for era in ERAS:
        for k in books:
            v = (old.get(era, {}) or {}).get(k, {})
            if "vs_pin" not in v or v.get("vs_pin") is None:
                continue
            checked += 1
            if abs(v["vs_pin"]) >= 0.5:
                bad.append((era, k, v["vs_pin"]))

    state["pin_mismatches"] = bad
    state["pins_checked"] = checked
    state["cells_expected"] = expected
    state["cells_ran"] = ran
    state["cells_errored"] = errored
    state["cells_skipped"] = skipped
    state["complete"] = (ran == expected and not errored)
    save(state)
    print("\n=== PIN CHECK (shipped column vs registry) ===")
    print("  %d mismatches out of %d book-era cells actually measured"
          % (len(bad), checked))
    if checked < expected and expected:
        print("  NOT a full run: %d of %d expected cells were never measured"
              % (checked, expected))
    for era, k, d in bad[:40]:
        print("    %-3s %-36s %+.1f" % (era, k, d))
    if not bad and checked == expected:
        print("  harness reproduces every pin - the patched column is trustworthy")
    elif not bad:
        print("  !! %d cells were never measured, so 'no mismatches' means nothing"
              % (expected - checked))
    else:
        print("  !! patched column is UNVERIFIED until these are explained")
    print("\n=== MOVED BOOKS (patched net differs from shipped by >=0.5R) ===")
    moved = []
    for k in books:
        for era in ERAS:
            o = (old.get(era, {}) or {}).get(k, {})
            n = (new.get(era, {}) or {}).get(k, {})
            if o.get("n") and n.get("n"):
                if abs(n["net"] - o["net"]) >= 0.5:
                    moved.append((k, era, o, n))
    for k, era, o, n in sorted(moved):
        print("  %-36s %-3s %4d->%4d  %+8.1f->%+8.1f (%+7.1f)  DD %5.1f->%5.1f"
              % (k, era, o["n"], n["n"], o["net"], n["net"], n["net"] - o["net"],
                 o["max_dd"], n["max_dd"]))
    print("  %d of %d book-era cells moved" % (len(moved), len(books) * len(ERAS)))


_compute_swings_shipped = None


def main() -> int:
    global _compute_swings_shipped
    import src.btc.btc_routes as R
    _compute_swings_shipped = R._compute_swings
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    t0 = time.time()
    state = load_state()
    books, skipped = all_books()
    state["books"], state["skipped_quarantined"] = books, skipped
    save(state)
    print("books: %d  skipped as quarantined: %d  (%.0fs elapsed)"
          % (len(books), len(skipped), time.time() - t0), flush=True)
    for side in SIDES:
        print("=== %s chain ===" % side.upper(), flush=True)
        run_side(state, side, books, limit)
    report(state, books)
    print("\nwrote %s  (%.0fs total)" % (OUT, time.time() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
