"""Static sweep: which exp_* knobs exist in an engine, and which are harness-only?

WHY THIS FILE EXISTS. `exp_max_concurrent` was described in three documents as a
real feature - "ALIVE deployment enabler" in ANCHOR_BASIS_AUDIT.md:346-347,
"untested" in ENGINE_SHELF.md:25, "max concurrent 3-6" in RISK_CONCURRENCY.md - and
it has ZERO occurrences anywhere under backend/src. It exists only as a source
patch injected by test_experiments_craze.py:106 (the default) and :760-763 (the
enforcement block).

That is worse than C16's SL misplacement, which was a real bug in real code:

              C16                        exp_max_concurrent
  in engine   yes                        NO
  patch       text-injected              text-injected
  default     harmful                    SILENT no-op at 0

At the default of 0 the injected block does nothing, so every experiment that did
not set the flag ran uncapped and looked correct. Nothing could fail, so nothing
was ever validated.

THE GENERAL FORM OF THE BUG. One feature is one instance. Any `exp_*` name that
craze.py injects but no engine implements is a research fiction that reads as a
real knob, and it produces the same three artefacts: an anchor, a shelf entry, and
a risk note. This file is the cheap test for the whole class.

WHAT IT IS NOT. It does not check whether a knob is CORRECT - only whether any
engine mentions it. A knob that exists but is wired to the wrong timestamp passes
here, which is exactly the case `exp_max_concurrent`'s `_now_ts = candle_ts[i]`
was. Existence is necessary, not sufficient. Read the second half of the report
before citing any row.

Read-only, no engine runs, seconds.

  python -u backtest/checks/exp_engine_knobs.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend" / "src"
CRAZE = ROOT / "backtest" / "tests" / "test_experiments_craze.py"

KNOB = re.compile(r"\bexp_[a-z0-9_]+\b")


def engine_files():
    return sorted(SRC.rglob("*.py"))


def main():
    if not CRAZE.exists():
        print("  craze.py not found - nothing to audit")
        return
    craze_src = CRAZE.read_text(encoding="utf-8", errors="replace")
    files = engine_files()
    blob = {f: f.read_text(encoding="utf-8", errors="replace") for f in files}

    injected = sorted(set(KNOB.findall(craze_src)))
    in_engine = {}
    for k in injected:
        hits = [f.relative_to(ROOT).as_posix() for f, t in blob.items()
                if k in t]
        in_engine[k] = hits

    backed = [k for k in injected if in_engine[k]]
    fiction = [k for k in injected if not in_engine[k]]

    print("=" * 88)
    print("  ENGINE KNOBS: which exp_* exist in an engine, which are harness-only?")
    print("=" * 88)
    print("  engines scanned: %d files under backend/src" % len(files))
    print("  exp_* referenced by test_experiments_craze.py: %d" % len(injected))
    print()

    print("-" * 88)
    print("  BACKED BY AN ENGINE  (%d)  -- at least one hit under backend/src" % len(backed))
    print("-" * 88)
    for k in backed:
        print("    %-32s %s" % (k, ", ".join(p.split("/")[-1]
                                            for p in in_engine[k][:3])))
    if not backed:
        print("    (none)")

    print()
    print("-" * 88)
    print("  HARNESS-ONLY  (%d)  -- ZERO engine hits, injected by craze.py" % len(fiction))
    print("-" * 88)
    print("    %-32s %s" % ("KNOB", "injected at"))
    for k in fiction:
        where = []
        for m in re.finditer(re.escape(k), craze_src):
            ln = craze_src[:m.start()].count("\n") + 1
            where.append(str(ln))
            if len(where) >= 3:
                break
        print("    %-32s craze.py:%s" % (k, ", ".join(where)))
    print()

    # inverse direction: engine knobs craze never injects
    eng_only = set()
    for f, t in blob.items():
        for k in KNOB.findall(t):
            if k not in injected:
                eng_only.add(k)
    if eng_only:
        print("-" * 88)
        print("  IN AN ENGINE, NEVER INJECTED BY craze.py  (%d)"
              % len(eng_only))
        print("-" * 88)
        for k in sorted(eng_only):
            print("    %s" % k)
        print("  These cannot be swept through craze. They need a different path.")
        print()
    # --- the one existence question that has a cheap answer -----------
    import glob as _g
    docs = {}
    for _p in _g.glob(str(ROOT / "backtest/docs/*.md")) + _g.glob(str(ROOT / "*.md")):
        docs[Path(_p).name] = Path(_p).read_text(encoding="utf-8", errors="replace")
    engine_knobs = set()
    for _f, _t in blob.items():
        engine_knobs |= set(KNOB.findall(_t))
    print()
    print("-" * 88)
    print("  ENGINE-NATIVE AND LABELLED UNTESTED  <- the cheap existence question")
    print("-" * 88)
    print("  %d knob(s) exist in backend/src: %s"
          % (len(engine_knobs), ", ".join(sorted(engine_knobs))))
    found = []
    for k in sorted(engine_knobs):
        for name, t in docs.items():
            for m in re.finditer(re.escape(k), t):
                win = t[max(0, m.start() - 260):m.end() + 260].lower()
                if "untested" in win:
                    found.append((k, name, t[:m.start()].count("\n") + 1))
                    break
    for k, name, ln in found:
        print("    %-20s %s:%d" % (k, name, ln))
    if not found:
        print("    (none)  ->  CLASS CLOSED 2026-10-01")
        print()
        print("    A knob that is real, built into an engine, and still labelled")
        print("    untested is the one existence question worth time, because it")
        print("    means nobody ever ran a feature the engine already has. None")
        print("    here, so the sweep is not needed. Answered by query, not by")
        print("    auditing targets by hand.")
    else:
        print("    ^ exist in an engine AND called untested. Run these.")


    print("=" * 88)
    print("  HOW TO READ THIS")
    print("=" * 88)
    print("  A HARNESS-ONLY row means: any number produced by setting this knob")
    print("  describes a code path that exists only in the harness. It is not")
    print("  wrong by itself - the harness is the research instrument - but it")
    print("  cannot be described as a feature of an engine, and no document")
    print("  should call it a deployment enabler.")
    print()
    print("  This check proves EXISTENCE only. It does not prove the wiring is")
    print("  correct: exp_max_concurrent existed here by name yet its enforcement")
    print("  used candle_ts[i] where the engine convention is ts + 900.")
    print("  Existence is necessary, not sufficient.")


if __name__ == "__main__":
    main()