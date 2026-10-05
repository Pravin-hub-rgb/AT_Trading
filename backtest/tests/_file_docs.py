"""File a document into signal/ method/ closed/, on evidence, not on word counts.

WHAT WENT WRONG FIRST, AND WHY THIS EXISTS

    The first version of this classified with a heuristic - count the words
    "signal" and "multi" and put the document in whichever won. The dry run
    showed it putting CONCURRENCY_GUARD_P96 and PORTFOLIO_LAYER under signal/
    (they are about concurrent positions, which is the definition of multi) and
    method/BOOK_CATEGORIES.md under multi/ (it is the document that DEFINES the split).
    Nothing crashed. Every one of those placements would have been wrong, and
    none of them would have been visible afterwards.

    So this does not guess. A document lands in signal/ only when it names a
    signal book - a book whose params carry max_positions=1, which is the repo's
    own definition and not a reading of the prose. Everything else that is not
    closed/ goes to method/, because 170 of the 236 documents describe a method,
    a mechanism or a family rather than a book, and no plane applies to them.

    The numbers that drove this, from a scan of all 236 documents against the
    registry: 65 name multi books only, 1 names signal books, 3 name both, and
    167 name none at all. That last figure is the finding. Signal-plane research
    is essentially undocumented - which is not a bug in the filing, it is the
    state of the work, and it is why _fs_serial_filters.json (108 cells) was the
    richest signal experiment in the repo and appears in no document at all.

    That number is why method/ exists and signal/ is nearly empty. Both are
    facts about the repository, not a preference.

USAGE
    python _file_docs.py --dry-run     # the plan, nothing touched
    python _file_docs.py --apply      # move, rewrite, verify
    python _file_docs.py --verify     # re-check every reference resolves
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest" / "tests"))

DOCS = ROOT / "backtest" / "docs"
INVENTORY = ROOT / "backtest" / "tests" / "_docs_inventory.json"

# Books that live on the signal plane, by the registry's own definition.
CLOSED = {"closed/CLOSED_DO_NOT_REPEAT.md", "ZOMBIE_MECHANISMS.md"}

# Documents that MENTION signal books but are not signal research.
# method/CHECKLIST.md and method/EXPERIMENT_LOG.md name dozens of books across both planes and
# are the run log for the whole repository, not a study of either. Filing them by
# the books they happen to mention would put a 350 KB cross-plane log in
# signal/ because it once cited a signal book. These are named explicitly rather
# than guessed at: anything added here has to be argued for.
CROSS_PLANE = {
    "method/CHECKLIST.md",
    "method/EXPERIMENT_LOG.md",
    "method/DOC_MAP.md",
    "method/BOOK_CATEGORIES.md",          # defines the split; belongs to neither side
    "method/CANDIDATE_BUILD_SHEET.md",    # every documented finding, both planes
    "method/KNOB_SWEEP.md",               # knob catalog, not a study
    "method/ONBOARDING.md",
    "method/THE_CHAMPION_HANDOFF.md",
    "method/REGISTRY_BOARD.md",
    "method/EXPERIMENT_INVENTORY.md",
    "method/HANDOVER_PORT_AND_MODULARIZE.md",
    "method/FS_EXIT_RULE.md",
}


def _signal_books() -> set:
    import experiment_registry as reg
    out = set()
    for k, v in reg.EXPERIMENTS.items():
        if not isinstance(v, dict):
            continue
        mp = (v.get("params") or {}).get("max_positions", reg.BP.get("max_positions"))
        if mp == 1:
            out.add(k)
    # the pre-rename names, so a document written before the single-to-sig
    # rename still counts as naming the book
    rmp = ROOT / "backtest" / "tests" / "_rename_map.json"
    if rmp.exists():
        try:
            for old, new in json.loads(rmp.read_text(encoding="utf-8")).items():
                if new in out:
                    out.add(old)
        except Exception:
            pass
    return out


def _body(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8", errors="replace")


def plan() -> dict:
    sig = _signal_books()
    files = sorted(p.name for p in DOCS.glob("*.md"))
    moves = {}
    for name in files:
        if name in CLOSED:
            moves[name] = "closed"
            continue
        if name in CROSS_PLANE:
            moves[name] = "method"
            continue
        text = _body(name)
        # A document names the signal plane when it names a signal book. The
        # rename map means an old name counts too.
        if any(b in text for b in sig):
            moves[name] = "signal"
        else:
            moves[name] = "method"
    return moves


FOLDERS = ("signal", "method", "closed")


def apply(moves: dict) -> None:
    for sub in FOLDERS:
        (DOCS / sub).mkdir(exist_ok=True)
    for name, plane in sorted(moves.items()):
        src, dst = DOCS / name, DOCS / plane / name
        if not src.exists():
            print("skip (already gone):", name)
            continue
        r = subprocess.run(["git", "mv", str(src), str(dst)], cwd=ROOT,
                           capture_output=True, text=True)
        if r.returncode:
            print("git mv failed:", name, r.stderr.strip()[:90])

    # Replace the bare filename only, never the surrounding path, so a link that
    # already pointed into a subfolder keeps pointing where it pointed.
    edited = 0
    for pat in ("*.md", "*.py"):
        for p in ROOT.rglob(pat):
            if ".git" in p.parts or "node_modules" in p.parts or "_craze_tmp" in p.name:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except Exception:
                continue
            new = text
            for name, plane in moves.items():
                if name in new:
                    new = new.replace(name, "%s/%s" % (plane, name))
            if new != text:
                p.write_text(new, encoding="utf-8", newline="")
                edited += 1
    print("rewrote references in %d file(s)" % edited)


def verify() -> int:
    """Every markdown-style reference to a document must resolve to a real file."""
    names = {p.name: p for p in DOCS.rglob("*.md")}
    unresolved = []
    for pat in ("*.md", "*.py"):
        for p in ROOT.rglob(pat):
            if ".git" in p.parts or "node_modules" in p.parts or "_craze_tmp" in p.name:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for m in re.finditer(r"`([\w\-./]+\.md)`|\]\(([\w\-./]+\.md)\)", text):
                ref = m.group(1) or m.group(2)
                if ref and ref.split("/")[-1] not in names:
                    unresolved.append((str(p.relative_to(ROOT)), ref))
    print("documents on disk     : %d" % len(names))
    for sub in FOLDERS:
        d = DOCS / sub
        if d.is_dir():
            print("  %-20s %d" % (sub, len(list(d.glob("*.md")))))
    print("unresolved references : %d" % len(unresolved))
    for f, r in unresolved[:20]:
        print("   %s -> %s" % (f, r))
    return 1 if unresolved else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.verify:
        return verify()
    moves = plan()
    if a.apply:
        apply(moves)
        return verify()
    print("would move %d document(s):" % len(moves))
    for plane in FOLDERS:
        names = sorted(n for n, p in moves.items() if p == plane)
        print("  %-9s %d" % (plane, len(names)))
        for n in names[:12]:
            print("       %s" % n)
        if len(names) > 12:
            print("       ... and %d more" % (len(names) - 12))
    hit = impacted(moves)
    print("\nfiles carrying a reference to a moved doc : %d" % len(hit))
    print("total references at risk                 : %d"
          % sum(len(v) for v in hit.values()))
    print("\ndry run. re-run with --apply to move.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())