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

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "backtest" / "tests" / "experiment_registry.py"
ROUTE = ROOT / "backend" / "src" / "btc" / "btc_routes.py"

PERMITTED = ("leg", "leg_no_entry")
# Research baseline, deliberately kept so the before/after comparison stays
# reproducible. Not in the dropdown. Removing it removes this entry rather
# than needing an edit to the check.
RESEARCH_ONLY = {"champion_multi_sw10", "btc_routes.py:1441"}


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
            tag = "research baseline" if key in RESEARCH_ONLY else "UNAUTHORISED"
            print("  %-32s %-24s [%s]" % (key, why, tag))
        print()
        bad = [f for f in findings if f[0] not in RESEARCH_ONLY]
        if bad:
            print("RESULT: FAIL - %d book(s) reach for a stop source that is not" % len(bad))
            print("        settled at the entry bar.")
            return 1
        print("RESULT: PASS with exceptions - only the research baseline still names")
        print("        a forbidden source, deliberately, so the comparison reproduces.")
        return 0

    print("RESULT: PASS - every stop source is settled at the entry bar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
