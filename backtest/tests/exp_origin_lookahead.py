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
from collections import defaultdict

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

    # --- 3. no book may SILENTLY INHERIT a base knob that its siblings declare
    #
    # This is the fault that produced nine wrong pins on 2026-10-02 and it is
    # invisible from any single book. A book's params dict is merged onto BP, so
    # any base knob it does not name is taken from BP's default. Twelve books
    # were written without cooldown_bars: BP says 10, the sweep they were
    # measured against used 8, and each of them quietly measured a different
    # book than its own pin claimed. Nothing flagged it - the knob is wired,
    # the pin was copied from a run that had it right, and no gate compared a
    # book's DECLARED knobs against its INHERITED ones.
    #
    # The check is: group books by the config they share, and if the books in a
    # group agree on a knob, every book in that group must state it. A book that
    # omits it is inheriting, and inheriting is fine only when nothing says
    # otherwise.
    print()
    print("  implicit-inheritance check (books must declare what siblings declare)")

    # the champion-base fingerprint: the knobs that identify the book family
    def family_of(params):
        return (params.get("mode"), params.get("ext_stop_r"), params.get("chop_thresh"),
                params.get("sl_buf_atr"), params.get("window_end"))

    fams = defaultdict(list)
    for key, cfg in reg.EXPERIMENTS.items():
        if isinstance(cfg, dict):
            fams[family_of(cfg.get("params", {}))].append((key, cfg.get("params", {})))
    CORE = ("cooldown_bars", "max_consecutive_losses", "exp_persist", "exp_partial_r", "htf_rr")
    n_groups = 0
    for fam, members in sorted(fams.items(), key=lambda kv: -len(kv[1])):
        if len(members) < 3:
            continue                       # too small for agreement to mean anything
        n_groups += 1
        for knob in CORE:
            stated = {k: p[knob] for k, p in members if knob in p}
            if len(stated) < 2 or len({repr(v) for v in stated.values()}) < 2:
                continue                   # nobody disagrees, so nothing to catch
            # If the knob is not in BP either, then omitting it means "take the
            # engine default", which is a real and stable choice - not an
            # accidental dependence on a base that could move. Only complain
            # when the inherited value actually comes from BP.
            try:
                import run_experiment as _re_
                if knob not in _re_.BP:
                    continue
            except Exception:
                continue
            missing = [k for k, p in members if knob not in p]
            if missing:
                vals = sorted({repr(v) for v in stated.values()})
                print("    %-22s family %s disagrees on %s %s" %
                      (fam, len(members), knob, vals))
                print("      %d book(s) INHERIT it instead of declaring it: %s" %
                      (len(missing), ", ".join(sorted(missing)[:4])))
                problems.append("%d book(s) inherit %s inside one family"
                                % (len(missing), knob))
    if not problems:
        print("    %d families checked, no book inherits a contested knob" % n_groups)

    # --- 4. no params dict may name the same knob twice
    #
    # A Python dict literal silently keeps the LAST value for a repeated key, so
    # a book written as {"cooldown_bars": 8, ..., "cooldown_bars": 15} measures 15
    # and reads as 8 to anyone scanning the file. Seven books were written that
    # way during this session. The values happened to match what the sweep
    # measured, so no pin was wrong - but the file does not describe itself, and
    # the next edit would be operating on a lie.
    print()
    # --- 5. nothing that lost money or did nothing may be a CANDIDATE
    #
    # A registry book means "a thing worth acting on". Thirty books here measure
    # a negative net or a knob that provably does not fire - they are kept,
    # because the measurement is real and exp_pinverify still checks it, but
    # they are status="reference" so nobody reads them as live candidates.
    #
    # The rule for anything added from here: a negative or inert result goes in
    # a doc as one line, not into the registry.
    print()
    # --- 6. the candidate rule must still select what it selected
    #
    # CANDIDATE_RULES is written against the shipped champion rather than against
    # absolute R, because absolute numbers rot: this same book measured
    # +325.78R in September and +239.12R today on the same 500 trades. If the
    # champion changes, the bar moves with it, and this line is what notices if
    # the rule and the board have drifted apart.
    print()
    print("  candidate rule (IS net, OOS net and OOS dd vs the shipped champion)")
    try:
        base = reg.EXPERIMENTS[reg.CANDIDATE_RULES["baseline_book"]]["pins"]
        print("    baseline %-30s IS %+.2f  OOS %+.2f  OOS dd %.2f"
              % (reg.CANDIDATE_RULES["baseline_book"], base["net"],
                 base["oos_net"], base["oos_dd_net"]))
        cands = [k for k in reg.EXPERIMENTS
                 if isinstance(reg.EXPERIMENTS[k], dict) and reg.is_candidate(k)]
        print("    %d book(s) beat the champion on all three" % len(cands))
        for k in sorted(cands, key=lambda x: -reg.EXPERIMENTS[x]["pins"]["oos_net"])[:6]:
            q = reg.EXPERIMENTS[k]["pins"]
            print("      %-34s OOS %+7.2f  dd %5.2f" % (k, q["oos_net"], q["oos_dd_net"]))
        if not cands:
            problems.append("candidate rule selects nothing")
    except Exception as e:
        print("    could not evaluate the candidate rule: %r" % (e,))
        problems.append("candidate rule failed")

    print("  candidate hygiene (a losing or inert book must be marked reference)")
    unmarked = []
    for key, cfg in reg.EXPERIMENTS.items():
        if not isinstance(cfg, dict):
            continue
        p2 = cfg.get("pins", {})
        if not p2.get("n"):
            continue
        if cfg.get("status") == "reference":
            continue
        if p2["net"] < 0 or "inert" in key:
            unmarked.append(key)
    if unmarked:
        for k in sorted(unmarked):
            print("    %-38s net %s but not marked reference"
                  % (k, reg.EXPERIMENTS[k]["pins"]["net"]))
        problems.append("%d losing/inert book(s) not marked reference" % len(unmarked))
    else:
        n_ref = sum(1 for c in reg.EXPERIMENTS.values()
                    if isinstance(c, dict) and c.get("status") == "reference")
        n_all = sum(1 for c in reg.EXPERIMENTS.values()
                    if isinstance(c, dict) and c.get("pins", {}).get("n"))
        print("    %d of %d books marked reference; the rest are candidates"
              % (n_ref, n_all))

    print("  duplicate-params-key check (a repeated key silently keeps the last)")
    n_dup = 0
    cur_lines = src.split("\n")
    starts = [i for i, l in enumerate(cur_lines)
              if re.match(r'    "[A-Za-z0-9_.]+":\s*\{', l)]
    for n2, st in enumerate(starts):
        en = starts[n2 + 1] if n2 + 1 < len(starts) else len(cur_lines)
        m2 = re.match(r'    "([A-Za-z0-9_.]+)"', cur_lines[st])
        if not m2:
            continue
        for i in range(st, en):
            if '"params":' not in cur_lines[i]:
                continue
            j = i
            while j < en and not re.search(r'\}\s*,\s*$', cur_lines[j]):
                j += 1
            body = "\n".join(cur_lines[i:j + 1])
            names = re.findall(r'"([a-z0-9_]+)":', body)
            seen2 = set()
            for nm in names:
                if nm in seen2:
                    print("    %-34s params names %r more than once"
                          % (m2.group(1), nm))
                    n_dup += 1
                seen2.add(nm)
            break
    if not n_dup:
        print("    no book names the same knob twice")
    else:
        problems.append("%d duplicate params key(s)" % n_dup)

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


