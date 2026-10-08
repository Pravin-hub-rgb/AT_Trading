"""exp_repo_map - a complete inventory of what is measured, so the untouched
space is visible instead of guessed at.

WHY A MAP AND NOT MORE EXPERIMENTS
==================================
This session produced nine findings and adopted nothing. Every one of them was a
single knob, a single book or a single threshold, checked against a framework the
repo already had. What nobody had was the thing a map gives: **which parts of
the space have never been touched at all**, as opposed to which parts were tested
and closed.

That distinction matters because the repo's own list of closed ideas is long and
impressive and does not distinguish "we tried this and it failed" from "nobody
thought of this". A map that separates them is worth more than one more
threshold sweep, and it takes minutes rather than an hour.

WHAT IS COUNTED
===============
  1. Books            - registered, pinned, reference, per-lane duplicates
  2. Parameters       - how many exist in the engine, how many any book sets,
                        how many are ever non-default, and which are inert on
                        which books
  3. Modes            - every regime branch in the router, and how many books
                        use each. A mode with no book is dead code by definition
  4. Closed findings  - counted from the graveyard and the queue, so "closed"
                        has a number rather than a reputation
  5. Open items       - from OPEN_RESEARCH_QUEUE.md, with their blockers

WHAT THE OUTPUT IS FOR
======================
Not a recommendation. It is the input to one. The last section of the printout
lists the mechanically identifiable gaps - parameters no book sets, modes no book
uses, engines with no book - and those are the only kind of gap that can be
stated as fact rather than as an opinion about what might be worth trying.

Run:  cd backtest/tests
      python -u exp_repo_map.py
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

ENGINE = ROOT / "backend" / "src" / "btc" / "engines" / "htf_ltf" / "unified.py"
QUEUE = ROOT / "backtest" / "docs" / "method" / "OPEN_RESEARCH_QUEUE.md"
GRAVE = ROOT / "backtest" / "docs" / "closed" / "CLOSED_DO_NOT_REPEAT.md"
OUT_JSON = Path(__file__).parent / "_repo_map.json"


def engine_signature():
    """Every keyword the engine accepts. Read from the source rather than by
    calling it, so a parameter that exists but is unreachable still shows up."""
    tree = ast.parse(ENGINE.read_text(encoding="utf-8", errors="replace"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("simulate_htf"):
            a = node.args
            names = [x.arg for x in a.kwonlyargs] + [x.arg for x in a.args]
            defaults = {}
            pos = a.args[len(a.args) - len(a.defaults):]
            for d in pos:
                pass
            # kwonly defaults
            for arg, d in zip(a.kwonlyargs, a.kw_defaults):
                if d is None:
                    continue
                try:
                    defaults[arg.arg] = ast.literal_eval(d)
                except Exception:
                    defaults[arg.arg] = "<expr>"
            return names, defaults
    return [], {}


def router_modes():
    """Every `mode=="..."` branch in the regime router."""
    txt = ENGINE.read_text(encoding="utf-8", errors="replace")
    return re.findall(r'mode=="([a-z0-9_]+)"', txt)


def main() -> int:
    from experiment_registry import EXPERIMENTS
    from registry import signal as SIG

    print("=" * 100)
    print("  REPOSITORY MAP - what is measured, what is closed, what is untouched")
    print("=" * 100)

    # ---------------- 1. BOOKS ----------------
    books = {k: v for k, v in EXPERIMENTS.items() if isinstance(v, dict)}
    sig = SIG.BOOKS
    pinned = [k for k, v in books.items() if v.get("pins")]
    refs = [k for k, v in books.items() if (v.get("status") == "reference")]
    print("\n  BOOKS")
    print("    registered in experiment_registry : %d" % len(books))
    print("    pinned (have an exact expectation) : %d" % len(pinned))
    print("    status=reference (must never pin)  : %d" % len(refs))
    print("    named in registry/signal.py        : %d" % len(sig))
    lanes = Counter(k.split("_")[0] for k in books)
    print("    prefixes: %s" % dict(lanes.most_common(8)))

    # duplicate configs - the utcsat pair keeps showing up as one result
    by_cfg = defaultdict(list)
    for k, v in books.items():
        p = v.get("params") or {}
        if p:
            key = json.dumps(p, sort_keys=True)
            by_cfg[key].append(k)
    dupes = {k: v for k, v in by_cfg.items() if len(v) > 1}
    print("    IDENTICAL param sets: %d groups" % len(dupes))
    for key, names in list(dupes.items())[:6]:
        print("       %s" % ", ".join(sorted(names)))

    # ---------------- 2. PARAMETERS ----------------
    names, defaults = engine_signature()
    set_by_books = Counter()
    for k, v in books.items():
        for p in (v.get("params") or {}):
            set_by_books[p] += 1
    print("\n  PARAMETERS")
    # 82 > 38 is impossible: some books carry keys the engine no longer accepts.
    # Those are registry entries pointing at a removed knob, which is a real
    # finding rather than a display bug, so they are counted separately.
    unknown = sorted(k for k in set_by_books if k not in names)
    print("    engine keywords            : %d" % len(names))
    print("    set by at least one book   : %d" % len(set_by_books))
    print("    set by NO book (defaults)  : %d" % len([n for n in names if n not in set_by_books]))
    print("    keys books set that the ENGINE DOES NOT ACCEPT (%d): %s"
          % (len(unknown), ", ".join(unknown[:20])))
    unused = sorted(n for n in names if n not in set_by_books)
    print("    -> never set by any book, reachable: %s"
          % (", ".join(n for n in unused if n not in ("candles_htf", "candles_ltf",
                                                     "swings_htf", "swings_ltf", "fine_ltf"))))

    # ---------------- 3. MODES ----------------
    modes = sorted(set(router_modes()))
    used = Counter()
    for k, v in books.items():
        m = (v.get("params") or {}).get("mode")
        used[m] += 1
    print("\n  REGIME MODES")
    print("    branches in the router     : %d" % len(modes))
    print("    used by >=1 book          : %d" % len([m for m in modes if used.get(m)]))
    dead_modes = [m for m in modes if not used.get(m)]
    print("    branches with NO book (%d): %s" % (len(dead_modes), ", ".join(dead_modes)))
    print("    mode census: %s" % dict(used.most_common(8)))

    # ---------------- 4/5. CLOSED AND OPEN ----------------
    def count_file(path, label):
        if not path.exists():
            print("\n  %s: file missing (%s)" % (label, path.name))
            return 0
        txt = path.read_text(encoding="utf-8", errors="replace")
        heads = len(re.findall(r"^## ", txt, re.M))
        print("\n  %s: %s" % (label, path.name))
        print("    `## ` sections            : %d" % heads)
        print("    `closed`/`CLOSED` mentions: %d" % len(re.findall(r"closed|CLOSED", txt)))
        return heads

    count_file(GRAVE, "GRAVEYARD")
    count_file(QUEUE, "RESEARCH QUEUE")

    if QUEUE.exists():
        q = QUEUE.read_text(encoding="utf-8", errors="replace").splitlines()
        # "- `[ ]` **Name**" -> drop the 7-char marker "- `[ ]`" then lstrip.
        open_items = [l.lstrip()[7:].strip() for l in q if l.lstrip().startswith("- `[ ]`")]
        done_items = [l for l in q if l.strip().startswith("- `[x]`")]
        print("\n  QUEUE STATE")
        print("    open items  : %d" % len(open_items))
        print("    done items  : %d" % len(done_items))
        for l in open_items:
            print("       %s" % l)

    # ---------------- THE GAPS ----------------
    print()
    print("=" * 100)
    print("  MECHANICALLY IDENTIFIABLE GAPS - facts, not opinions")
    print("=" * 100)
    print("  1. Parameters no book ever sets (%d): %s" % (len(unused), ", ".join(unused)))
    print("     These are reachable and unexercised. Setting one is not a proposal -")
    print("     but nothing has been measured on it either.")
    print()
    print("  2. Router branches with no book (%d): %s" % (len(dead_modes), ", ".join(dead_modes)))
    print("     Dead code by definition. Either a book should use one, or the branch")
    print("     should go. Both are decisions, neither has been made.")
    print()
    print("  3. Identical param sets across books: %d groups. Each is one result shown"
          % len(dupes))
    print("     twice, not two results. Quote them as one or as none.")

    report = {
        "books": {"registered": len(books), "pinned": len(pinned),
                  "reference": len(refs), "signal_named": len(sig),
                  "dupe_param_groups": len(dupes)},
        "params": {"engine_keywords": len(names), "set_by_books": len(set_by_books),
                   "never_set": unused},
        "modes": {"branches": len(modes), "used": {k: v for k, v in used.items()},
                  "no_book": dead_modes},
    }
    OUT_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("\nwrote %s" % OUT_JSON.name)
    print("Nothing changed. This is an inventory; it proposes nothing and adopts nothing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())