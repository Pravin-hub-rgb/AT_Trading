"""exp_doc_c17_notice - flag the documents whose numbers predate the C17 gate fix.

WHY A NOTICE AND NOT A REWRITE
==============================
`_multi_metrics.json` and `_signal_metrics.json` were re-measured after C17 and
their three generated docs regenerated, so the rankings are current. What is left
is 21 hand-written documents. Their numbers are not table cells to be refreshed;
they are evidence inside an argument, measured on a stated date, and the prose
around them reasons about those exact figures. Rewriting the figures would make
the argument internally inconsistent and would silently falsify the document's
own measurement date. A dated notice keeps the record and stops the number being
read as current.

WHAT IT DOES
============
Inserts one notice block directly under each document's H1, and refreshes the
board's headline champion line from the live registry pin. Idempotent: a doc that
already carries the notice is left alone. Exits non-zero if any targeted doc is
missing, so coverage cannot silently shrink.

Usage:
    cd backtest/tests
    python exp_doc_c17_notice.py            # dry run, prints the plan
    python exp_doc_c17_notice.py --write
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend"):
    sys.path.insert(0, str(ROOT / p))

MARK = "<!-- C17-NOTICE -->"

NOTICE = """
{d}
> **C17 NOTICE (2026-10-07).** The figures in this document were measured before
> the C17 gate fix, which removed a lookahead from the HTF window gate and
> invalidated 214 of 215 registry pins. They are kept as the dated record they
> were, and they are **not** what the engine produces today - do not quote them
> as current. Current numbers: `python exp_pinverify.py` (re-derives every pin),
> `docs/method/C17_WINDOW_END_CAUSALITY.md` (what changed and why),
> `docs/multi/MULTI_RANKINGS.md` and `docs/signal/SIGNAL_RANKINGS.md`
> (regenerated from a post-C17 measurement).
"""

# Docs whose numbers the scan found stale, minus the three regenerated ones and
# the C17 doc itself, which quotes old and new on purpose.
TARGETS = [
    "backtest/docs/method/REGISTRY_BOARD.md",
    "backtest/docs/method/FS_EXIT_RULE.md",
    "backtest/docs/method/FS_SIGNAL_TWEAKS.md",
    "backtest/docs/method/BOOK_CATEGORIES.md",
    "backtest/docs/method/CHECKLIST.md",
    "backtest/docs/method/ENTRY_FILL_P90.md",
    "backtest/docs/method/KNOB_SWEEP.md",
    "backtest/docs/method/CHAMPION_DEPLOYABILITY_P99.md",
    "backtest/docs/method/CONCURRENCY_P117_P120.md",
    "backtest/docs/method/HANDOFF_V19_ORDER_DEPENDENCE.md",
    "backtest/docs/method/HANDOVER_PORT_AND_MODULARIZE.md",
    "backtest/docs/method/HANDOVER_SESSION.md",
    "backtest/docs/method/ROUND_INDEX_P55_P69.md",
    "backtest/docs/method/ROUND_SUMMARY_P55_P95.md",
    "backtest/docs/method/EXPERIMENT_LOG.md",
    "backtest/docs/method/PROMPT_FOR_SECOND_RESEARCHER.md",
    "backtest/docs/method/reality of champion.md",
    "backtest/docs/closed/CLOSED_DO_NOT_REPEAT.md",
    "backtest/docs/signal/ANCHOR_BASIS_AUDIT.md",
    "backtest/docs/signal/STRATEGY_SCORECARD.md",
]

BOARD = "backtest/docs/method/REGISTRY_BOARD.md"
CHAMPION = "champion_multi_sw10_leg"


def champion_line():
    import experiment_registry as reg
    p = (reg.EXPERIMENTS.get(CHAMPION) or {}).get("pins") or {}
    return ("Generated from the registry. **2026-10-04, pins refreshed 2026-10-07 "
            "after C17.** Shipped champion `%s`: IS %d / %+.2f / dd %.2f   "
            "OOS %d / %+.2f / dd %.2f."
            % (CHAMPION, p.get("n", 0), p.get("net") or 0.0, p.get("dd_net") or 0.0,
               p.get("oos_n", 0), p.get("oos_net") or 0.0,
               p.get("oos_dd_net") or 0.0))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)

    missing = [t for t in TARGETS if not (ROOT / t).exists()]
    if missing:
        print("TARGET DOCS MISSING: %s" % ", ".join(missing))
        return 1

    print("=" * 78)
    print("C17 DOC NOTICE - %d doc(s)   (%s)"
          % (len(TARGETS), "WRITING" if a.write else "dry run, nothing written"))
    print("=" * 78)
    touched = skipped = 0
    for rel in TARGETS:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        if MARK in text:
            print("  %-52s already has the notice" % rel)
            skipped += 1
            continue
        m = re.search(r"^# .*$", text, re.M)
        block = (NOTICE.format(d=MARK).rstrip("\n")
                 + "\n" + "-" * 78)
        if m:
            new = text[:m.end()] + "\n\n" + block + text[m.end():]
            where = "under the H1"
        else:
            # Not every doc in this repo opens with a markdown heading -
            # ROUND_SUMMARY_P55_P95.md starts mid-sentence with "big pickle:" and
            # EXPERIMENT_LOG.md opens straight into a table row. Prepending is the
            # only placement that cannot land inside someone's prose.
            new = block + "\n\n" + text
            where = "at the top (no H1 in this file)"
        if rel == BOARD:
            new = re.sub(r"^Generated from the registry\..*$", champion_line(),
                         new, count=1, flags=re.M)
            print("  %-52s notice + champion line refreshed" % rel)
        else:
            print("  %-52s notice %s" % (rel, where))
        if a.write:
            path.write_text(new, encoding="utf-8")
        touched += 1
    print("\n%d to update, %d already current" % (touched, skipped))
    if not a.write:
        print("DRY RUN. Re-run with --write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
