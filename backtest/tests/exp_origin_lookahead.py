"""STOP SOURCES: only values settled at the entry bar may set the stop.

Rewritten 2026-10-02. The previous version truncated the swing chain at each
swing's CONFIRMATION, found seg.start_px unchanged, and concluded the origin
pivot was causal. That was the wrong question. After a swing confirms its chain
is frozen by definition, so stability there is guaranteed and proves nothing.
It also said the opposite of the rule this check enforces.

The distinction that matters:

    SETTLED at entry      the extreme of start..break. Every bar in that
                          range has closed. leg and leg_no_entry read exactly
                          this, and it is the only permitted stop source.

    NOT settled at entry  seg_start, the swing structural extreme. At a flip or
                          B2 entry the swing is still forming and its extreme
                          is not final until the first-swing print, which is
                          after the entry bar. It does not revise afterwards -
                          that is what made it look safe - but stability is not
                          availability.

So the check no longer tries to prove a negative about a value. It asserts the
rule: these two sources are permitted, and any book reaching for seg_start is
failing regardless of what the number looks like afterwards.

Run:  cd backtest/tests && python exp_origin_lookahead.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "backtest" / "tests" / "experiment_registry.py"
ROUTE = ROOT / "backend" / "src" / "btc" / "btc_routes.py"

PERMITTED = ("leg", "leg_no_entry")
# Research baseline, deliberately kept so the before/after comparison stays
# reproducible. Not in the dropdown. Removing it removes this entry rather
# than needing an edit to the check.
#
# These used to be keyed by line number ("btc_routes.py:1441"). That silently
# rotted: the route file grew, pivot_rule="origin" moved to line 1481, the
# allowlist no longer matched, and the gate started reporting a documented
# exception as UNAUTHORISED. Key on the book key, and on the FILE for the
# route, then assert the expected count so a NEW unauthorised use in that file
# still fails instead of riding the blanket exemption.
RESEARCH_BOOKS = {"champion_multi_sw10"}
RESEARCH_FILES = {"btc_routes.py"}          # expect exactly this many
RESEARCH_FILE_COUNT = {"btc_routes.py": 1}


def main():
    print("=" * 66)
    print("STOP SOURCE RULE - only entry-time-settled values may set a stop")
    print("=" * 66)
    print("permitted : pivot_rule in %s" % (PERMITTED,))
    print("forbidden : seg_start / pivot_rule origin")
    print("             the swing structural extreme is not settled at a flip or")
    print("             B2 entry; it finalises on the first-swing print, after the")
    print("             entry bar. It never revises, which is why it looked safe,")
    print("             but it had not settled at the entry.")
    print()

    findings = []
    if REGISTRY.exists():
        src = REGISTRY.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'"([A-Za-z0-9_]+)"\s*:\s*\{(.*?)\n    \}', src, re.S):
            key, body = m.group(1), m.group(2)
            for rule in re.findall(r'"pivot_rule":\s*"([^"]+)"', body):
                if rule not in PERMITTED:
                    findings.append((key, "pivot_rule=" + rule))
    if ROUTE.exists():
        for i, line in enumerate(ROUTE.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            for rule in re.findall(r'pivot_rule="([^"]+)"', line):
                if rule not in PERMITTED:
                    findings.append(("btc_routes.py:%d" % i, "pivot_rule=" + rule))

    if findings:
        for key, why in findings:
            if key in RESEARCH_BOOKS:
                tag = "research baseline"
            elif key.split(":")[0] in RESEARCH_FILES:
                tag = "research baseline (%s)" % key
            else:
                tag = "UNAUTHORISED"
            print("  %-32s %-24s [%s]" % (key, why, tag))
        print()

        bad = [f for f in findings
               if f[0] not in RESEARCH_BOOKS
               and f[0].split(":")[0] not in RESEARCH_FILES]

        # A file-level exemption must not become a blanket pass: if the route
        # grows a second forbidden stop source, that one is unauthorised.
        for fname, expected in RESEARCH_FILE_COUNT.items():
            got = len([f for f in findings if f[0].split(":")[0] == fname])
            if got > expected:
                print("  NOTE %s now has %d forbidden stop sources, %d were"
                      " documented as research-only." % (fname, got, expected))
                for key, why in findings:
                    if key.split(":")[0] == fname:
                        print("       %s  %s" % (key, why))
                print()
                bad += [f for f in findings if f[0].split(":")[0] == fname
                        and f not in bad]

        if bad:
            print("RESULT: FAIL - %d book(s) reach for a stop source that is not" % len(bad))
            print("        settled at the entry bar.")
            return 1
        print("RESULT: PASS with exceptions - only the research baseline still names")
        print("        a forbidden source, deliberately, so the comparison reproduces.")
        return 0

    print("RESULT: PASS - every stop source is settled at the entry bar.")
    return 0


def check_registry_hygiene():
    """Catches two silent-failure classes that both bit us on 2026-10-02.

    1. A book key defined TWICE in the EXPERIMENTS literal. Python dicts are
       last-wins, so the first copy becomes dead text that still reads as a
       valid entry. The causalsl family was defined twice each and nobody could
       see it by reading the file - the running config was the second copy and
       the first was invisible.

    2. A scope loader missing a swing key some books depend on.
       exp_equity_quality.load_scope('oos') did not build sw20, so every sw20
       book raised KeyError out of sample while its sw10 twin measured fine.
       That failure looks like "this book cannot be tested OOS", which is
       indistinguishable from a real answer unless you go looking for it.

    Both are cheap to detect statically, so they are checked rather than left to
    be rediscovered.
    """
    print("=" * 66)
    print("REGISTRY HYGIENE - no duplicate keys, no missing scope keys")
    print("=" * 66)

    problems = []

    # --- 1. duplicate entry keys -------------------------------------------
    if REGISTRY.exists():
        src = REGISTRY.read_text(encoding="utf-8", errors="replace")
        keys = re.findall(r'\n    "([A-Za-z0-9_]+)":\s*[\{\"]', src)
        counts = {}
        for k in keys:
            counts[k] = counts.get(k, 0) + 1
        dupes = {k: v for k, v in counts.items() if v > 1}
        print("  registry entries parsed : %d" % len(keys))
        if dupes:
            for k, v in sorted(dupes.items()):
                print("  DUPLICATE KEY %-34s defined %d times" % (k, v))
            problems.append("%d key(s) defined more than once" % len(dupes))
        else:
            print("  duplicate keys          : none")

    # --- 2. every swing key a book uses must exist in every scope -----------
    for p in ("backtest/tests", "backtest", "backend", ""):
        sys.path.insert(0, str(ROOT / p) if p else str(ROOT))
    try:
        import experiment_registry as reg
    except Exception as e:
        print("  could not import registry: %r" % (e,))
        return 1

    needed = set()
    for key, cfg in reg.EXPERIMENTS.items():
        if isinstance(cfg, dict):
            needed.add(cfg.get("swing"))
    needed.discard(None)
    print("  swing keys books use    : %s" % ", ".join(sorted(needed)))

    try:
        import run_experiment as re_
        is_keys = set(re_.get_data().keys())
    except Exception as e:
        print("  IS loader failed: %r" % (e,))
        problems.append("IS loader failed")
        is_keys = None

    if is_keys is not None:
        miss = sorted(k for k in needed if k not in is_keys)
        if miss:
            for k in miss:
                print("  MISSING IN IS LOADER    %s" % k)
            problems.append("IS loader missing %s" % ", ".join(miss))
        else:
            print("  IS loader covers them   : yes")

    # OOS loader source is inspected rather than called - calling it loads a
    # second candle file, which is the expensive part.
    try:
        import inspect
        import exp_equity_quality as EQ
        src_oos = inspect.getsource(EQ.load_scope)
        oos_keys = set(re.findall(r'"(\w+)":', src_oos))
        oos_keys |= set(re.findall(r'^\s*(\w+)\s*=\s*_compute_swings', src_oos, re.M))
    except Exception as e:
        print("  could not read OOS loader: %r" % (e,))
        oos_keys = None
        problems.append("could not read OOS loader")

    if oos_keys is not None:
        miss = sorted(k for k in needed if k not in oos_keys)
        if miss:
            for k in miss:
                print("  MISSING IN OOS LOADER  %-20s books needing it will raise"
                      " KeyError on the OOS scope" % k)
            problems.append("OOS loader missing %s" % ", ".join(miss))
        else:
            print("  OOS loader covers them  : yes")

    bad_alias = {a: t for a, t in reg.ALIASES.items() if t not in reg.EXPERIMENTS}
    if bad_alias:
        for a, t in sorted(bad_alias.items()):
            print("  BROKEN ALIAS %-34s -> %s" % (a, t))
        problems.append("%d broken alias(es)" % len(bad_alias))
    else:
        print("  aliases resolve         : %s" % (reg.ALIASES or "none"))

    print()
    if problems:
        print("RESULT: FAIL")
        for p in problems:
            print("        - %s" % p)
        return 1
    print("RESULT: PASS - no duplicate keys, and every scope loader builds every")
    print("        swing key the registry asks for.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main() or check_registry_hygiene())


