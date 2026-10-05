"""Inventory every backtest/docs/*.md so the docs can be filed rather than guessed at.

The signal-vs-multi split in method/BOOK_CATEGORIES.md is the primary axis: a signal
book holds exactly one position (max_positions=1), a multi book holds several.
This script decides which plane a document is about from what the document
actually says - verdict headers, the plane tables, the words it uses for the
two book types - and reports the evidence for each decision so a wrong call can
be argued with rather than believed.

It also flags the thing that has already gone wrong once: a document carrying
measured numbers. The repo rule is in method/BOOK_CATEGORIES.md - "No results here, a
number lives in experiment_registry.py and nowhere else" - and the +492.60 that
sat in that same file is what the rule exists to prevent.

Writes _docs_inventory.json. Read-only apart from that one file.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "backtest" / "docs"
OUT = ROOT / "backtest" / "tests" / "_docs_inventory.json"

# A header that states a verdict. These are the strongest signal that a document
# concluded something rather than describing a process.
VERDICT = re.compile(
    r"^\s*(?:#{1,4}\s*)?(?:\*\*)?(VERDICT|VERDICT:|CONCLUSION|CONCLUSIONS|FINAL VERDICT"
    r"|ANSWER|RESULT|RESULTS|OUTCOME|HOLD|REJECTED|ACCEPTED|CONFIRMED|CLOSED"
    r"|DECISION|STATUS)\b",
    re.IGNORECASE | re.MULTILINE)

# Process/hand-off material: describes how to run things, not what was found.
PROCESS_NAME = re.compile(
    r"^(ONBOARDING|PIPELINE|HANDOVER|EXPERIMENT_PROCESS|DOC_MAP|EXPERIMENT_INVENTORY"
    r"|ENGINE_BOOK_ARCHITECTURE|KNOB_SWEEP|TRANSCRIPT_THESIS_BACKLOG|NEXT_ROUND_BRIEF"
    r"|EXPERIMENT_LOG|EXPERIMENT_LOG_ENTRY|CHECKLIST|REPO_HANDOFF|THE_CHAMPION_HANDOFF)",
    re.IGNORECASE)

# Closed means the mechanism is not to be repeated, regardless of plane.
CLOSED_NAME = re.compile(r"^(CLOSED|ZOMBIE)", re.IGNORECASE)

# A table row carrying trades / net / dd. The shape that a results table takes.
RESULT_ROW = re.compile(
    r"\|\s*\d{2,4}\s*\|\s*[+-]?\d+\.\d{2}\s*\|",   # | 369 / +174.30 |
    re.MULTILINE)


def classify(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    low = text.lower()
    name = path.name

    ev = {}

    # --- plane evidence -----------------------------------------------------
    # The authoritative statement is an explicit max_positions=1 pairing.
    if re.search(r"max_positions\s*[=:]\s*1", low):
        ev["explicit_single"] = True
    if re.search(r"max_positions\s*[=:]\s*0", low):
        ev["explicit_multi"] = True
    # The words the repo uses for each plane.
    n_sig = len(re.findall(r"\bsig[_ ]|signal book|single[- ]position|one position", low))
    n_mul = len(re.findall(r"\bmulti\b|\bcascade\b|concurrent position", low))
    ev["sig_words"] = n_sig
    ev["multi_words"] = n_mul

    # --- verdict evidence ---------------------------------------------------
    verdicts = VERDICT.findall(text)
    ev["verdict_headers"] = len(verdicts)

    # --- results carried in the doc ----------------------------------------
    rows = RESULT_ROW.findall(text)
    ev["result_rows"] = len(rows)

    if CLOSED_NAME.match(name):
        plane = "closed"
    elif PROCESS_NAME.match(name):
        plane = "process"
    elif ev.get("explicit_single") or (n_sig > 0 and n_sig >= n_mul):
        plane = "signal"
    elif ev.get("explicit_multi") or n_mul > n_sig:
        plane = "multi"
    else:
        plane = "shared"

    return {
        "file": name,
        "plane": plane,
        "bytes": path.stat().st_size,
        "evidence": ev,
        "carries_results": len(rows) > 0,
    }


def main():
    docs = sorted(DOCS.glob("*.md"))
    recs = [classify(p) for p in docs]

    by_plane = {}
    for r in recs:
        by_plane.setdefault(r["plane"], []).append(r["file"])

    # Books named in a results table are the ones a reader might copy. Cross the
    # table rows against the registry so "carries numbers" is about book names
    # and not about any table that happens to contain digits.
    import sys
    sys.path.insert(0, str(ROOT / "backtest" / "tests"))
    try:
        import experiment_registry as reg
        book_names = {k for k, v in reg.EXPERIMENTS.items() if isinstance(v, dict)}
        book_names |= set(getattr(reg, "ALIASES", {}) or {})
    except Exception as e:  # registry must not be able to break an inventory
        book_names = set()
        print("registry unavailable:", e)

    for r in recs:
        t = (DOCS / r["file"]).read_text(encoding="utf-8", errors="replace")
        named = sorted({b for b in book_names if b in t})
        r["books_named"] = named[:40]
        r["books_named_count"] = len(named)

    OUT.write_text(json.dumps({
        "total": len(recs),
        "by_plane": {k: len(v) for k, v in sorted(by_plane.items())},
        "files_by_plane": by_plane,
        "docs": recs,
    }, indent=1), encoding="utf-8")

    print("total docs:", len(recs))
    for k, v in sorted(by_plane.items()):
        print("  %-8s %3d" % (k, len(v)))
    flagged = [r["file"] for r in recs if r["carries_results"]]
    print("\ncarry a results-shaped table: %d" % len(flagged))
    for f in sorted(flagged)[:30]:
        print("   ", f)


if __name__ == "__main__":
    main()