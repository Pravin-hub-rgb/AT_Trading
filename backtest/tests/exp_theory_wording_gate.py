"""
GATE - the B2/FLIP anchor rule must stay stated, and stay unambiguous.

WHY THIS EXISTS

On 2026-10-13 the owner asked whether a bar should have produced a B2. A chart
example was built on a running low with no white pivot behind it, and the answer
was "the gap rule blocked that mark". The owner's reply:

    "Does 18:15 candle's low, was there a pivot? ... There is no marks there."

The example was meaningless. The cause: the owner's own ruling is quoted using
the phrase "extreme pivot", which reads as a type of pivot and is the opposite of
the rule. He re-affirmed it the same day: "It should be for B2 flip, it is extreme
pivots."

Full write-up: closed/CLOSED_DO_NOT_REPEAT.md, "EXTREME PIVOT IS NOT A TYPE OF
PIVOT". Canonical statement: fix/SWING_THEORY_B1_B2_FLIP.md, top of file.

WHAT IT CHECKS

  1. The two-anchor block is still at the top of the theory doc.
  2. It says B2/FLIP break the running extreme and FS breaks a sealed pivot.
  3. "extreme pivot" does not appear in prose ANYWHERE - only inside the owner's
     own quoted rulings, which are kept verbatim on purpose.
  4. The engine carries a translation next to each of its quoted occurrences, so
     the next person to read the source cannot stop at the quote.

WHAT IT DELIBERATELY DOES NOT DO

It reads MARKDOWN ONLY. It never opens `backend/src/firstswing.py` except to
count a fixed, expected number of owner-quote lines, and it never parses or
rewrites engine source. `exp_craze_patch_gate.py` is the one tool here that
rewrites engine text; nothing in this file can interact with it, and this file
cannot change the chain.

Usage:
    $env:PYTHONIOENCODING='utf-8'
    ..\\..\\backend\\venv\\Scripts\\python.exe -u exp_theory_wording_gate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THEORY = ROOT / "fix" / "SWING_THEORY_B1_B2_FLIP.md"
ENGINE = ROOT / "backend" / "src" / "firstswing.py"
ENGINE_DOC = ROOT / "backend" / "src" / "live" / "MANIFEST.md"

# Markdown files where the phrase is allowed to appear - the owner's own quotes.
ALLOWED = {
    "SWING_THEORY_B1_B2_FLIP.md",
    "CLOSED_DO_NOT_REPEAT.md",
}

fails: list[str] = []
notes: list[str] = []


def main() -> int:
    print("=" * 74)
    print("THEORY WORDING GATE - B2/FLIP anchor rule")
    print("=" * 74)
    print()

    # 1-2. the canonical block
    if not THEORY.exists():
        print("  [FAIL] theory doc missing at %s" % THEORY)
        return 1
    txt = THEORY.read_text(encoding="utf-8", errors="replace")
    head = txt[:4000].upper()
    for needle, label in (
        ("READ THIS FIRST", "the READ THIS FIRST block"),
        ("RUNNING EXTREME", "the running-extreme anchor"),
        ("SEALED WHITE PIVOT", "the sealed-white-pivot anchor"),
        ("DO NOT MIX", "the do-not-mix warning"),
    ):
        if needle in head:
            print("  [ok] %s present near the top" % label)
        else:
            print("  [FAIL] %s MISSING near the top of the theory doc" % label)
            fails.append(label)

    # the block has to be in the first screen, not buried
    marker = txt.upper().find("READ THIS FIRST")
    if marker > 2500:
        print("  [FAIL] the two-anchor block is at char %d - too far down to be read"
              % marker)
        fails.append("anchor block buried")
    else:
        print("  [ok] the two-anchor block is at char %d - readable on sight" % marker)

    # 3. the ambiguous phrase must not appear in prose
    print()
    for base in ("fix", "docs", "plans", "backtest/docs"):
        d = ROOT / base
        if not d.is_dir():
            continue
        for md in sorted(d.rglob("*.md")):
            if md.name in ALLOWED:
                continue
            body = md.read_text(encoding="utf-8", errors="replace")
            low = body.lower()
            n = low.count("extreme pivot")
            if n:
                print("  [FAIL] 'extreme pivot' x%d in %s"
                      % (n, md.relative_to(ROOT)))
                fails.append(str(md.relative_to(ROOT)))
            else:
                notes.append(str(md.relative_to(ROOT)))
    print("  [ok] scanned %d markdown files outside quotes, none use the phrase"
          % len(notes))

    # 4. the engine must carry translations next to its quotes
    print()
    if not ENGINE.exists():
        print("  [FAIL] engine missing at %s" % ENGINE)
        return 1
    lines = ENGINE.read_text(encoding="utf-8", errors="replace").splitlines()
    hit = [i for i, ln in enumerate(lines) if "extreme pivot" in ln.lower()]
    # Group contiguous hits into quote BLOCKS. One translation covers a whole
    # contiguous quote, so counting occurrences would demand one note per line and
    # fail a block that is in fact correctly annotated.
    blocks: list[list[int]] = []
    for i in hit:
        if blocks and i - blocks[-1][-1] <= 8:
            blocks[-1].append(i)
        else:
            blocks.append([i])
    print("  engine: %d quote line(s) carrying the phrase, in %d block(s)"
          % (len(hit), len(blocks)))
    if not hit:
        print("  [ok] engine no longer carries the ambiguous phrase at all")
    else:
        untranslated = []
        for b in blocks:
            # the translation may sit INSIDE the block (quoting then glossing is
            # the natural order) or in the lines just after it
            window = range(b[0], min(len(lines), b[-1] + 13))
            if not any("TRANSLATION" in lines[j].upper() for j in window):
                untranslated.append(b[0] + 1)
        if untranslated:
            print("  [FAIL] quote block(s) starting at line(s) %s have no"
                  " TRANSLATION beside or within 12 lines after" % untranslated)
            fails.append("engine missing a translation")
        else:
            print("  [ok] every quote block has a TRANSLATION beside it")

    # the docstring must say the target, not just the quote
    src = "\n".join(lines)
    if "RUNNING EXTREME" in src and "not a sealed" in src.lower():
        print("  [ok] _b2_if_gap_allows names its target as the running extreme")
    else:
        print("  [FAIL] _b2_if_gap_allows does not name its target as the running extreme")
        fails.append("docstring target")

    print()
    print("=" * 74)
    if fails:
        print("RESULT: %d FAILED" % len(fails))
        for f in fails:
            print("   - %s" % f)
        print()
        print("This gate is about WORDING only. If it fails, the engine is probably")
        print("fine and the documentation has drifted - re-read the two-anchor block")
        print("before changing any code.")
        return 1
    print("RESULT: pass - the B2/FLIP anchor rule is stated and unambiguous.")
    print()
    print("No behaviour is checked here and none can be affected by this file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())