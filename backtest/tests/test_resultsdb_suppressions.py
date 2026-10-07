"""The doc gate's two suppressions must not be able to hide a real failure.

A suppression that makes a gate quieter is only safe if it can be shown not to
cover a case that should fail. These tests pin that property from both sides:
each suppression is asserted to fire on its own case, AND asserted NOT to fire on
the neighbouring case that must still fail.

  Suppression A - the C17 banner. A document carrying <!-- C17-NOTICE --> has
    declared itself a dated record, so its pins are before-columns. The banner is
    a reversible opt-out: delete it and the doc is read as current again. The
    test that matters is the second one - same wrong number, no banner, still a
    hit - because that is what stops "banner'd" from silently becoming "any doc".

  Suppression B - the line names no config that exists in the registry. A stale
    registry pin must name a registry book; if the config is absent the number
    is prose, a retired config or a typo. The test that matters is the second
    one - same wrong number, line DOES name a real book, still a hit - because
    that is what stops this from becoming "any line without a book name".

Neither suppression touches _quoted_numbers' first filter (a line must look like
a measurement at all), and neither can make a wrong CURRENT claim pass on a book
that exists and has not opted out.

Run:  cd backtest/tests && python -m pytest test_resultsdb_suppressions.py -q
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "backend"))

WRONG = 123.45          # not in `known`, so it is a candidate hit
KNOWN_SET = {533.37, 239.59}


def _num(rec):
    """Hit/exempt records carry the matched text, not a float."""
    return float(rec[1])


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def _scan(path, names=("fsent_champ_long",)):
    from exp_resultsdb import _quoted_numbers, SUPPRESS_BANNER, SUPPRESS_NO_BOOK
    hits, exempt, supp = _quoted_numbers(path, set(names), KNOWN_SET, 0.5,
                                        set(), set())
    reasons = {r for r, _ in supp}
    return hits, reasons


def test_banner_suppresses_a_wrong_pin(tmp_path):
    """Suppression A fires on its own case."""
    from exp_resultsdb import SUPPRESS_BANNER
    p = _write(tmp_path, "dated.md",
               "<!-- C17-NOTICE -->\n"
               "| book | IS net |\n"
               "|---|---|\n"
               "| `fsent_champ_long` | %+.2f |\n" % WRONG)
    hits, reasons = _scan(p)
    assert not hits, "banner'd doc still failed: %r" % (hits,)
    assert reasons == {SUPPRESS_BANNER}, "wrong suppression reason: %r" % reasons


def test_banner_is_reversible_so_a_wrong_current_claim_still_fails(tmp_path):
    """THE GUARD. Same number, same book, banner removed -> it must fail again.

    If this ever passes, "banner" has quietly become "ignored", and a doc that
    deleted its opt-out to start making current claims would get no gate at all.
    """
    p = _write(tmp_path, "current.md",
               "| book | IS net |\n"
               "|---|---|\n"
               "| `fsent_champ_long` | %+.2f |\n" % WRONG)
    hits, _ = _scan(p)
    assert hits, "a wrong current pin on a real book passed the gate"
    assert abs(_num(hits[0]) - WRONG) < 0.005, "flagged the wrong number: %r" % (hits,)


def test_banner_only_counts_near_the_top_of_the_file(tmp_path):
    """Bounds suppression A: a stray marker deep in a doc opts out nothing."""
    filler = ("padding line to push the marker past the read window\n" * 200)
    p = _write(tmp_path, "deep.md",
               filler +
               "| book | IS net |\n|---|---|\n"
               "| `fsent_champ_long` | %+.2f |\n" % WRONG +
               "<!-- C17-NOTICE -->\n")
    hits, reasons = _scan(p)
    assert hits, "a marker 200 lines down suppressed a live doc"
    assert not reasons, "deep marker produced a suppression: %r" % reasons


def test_absent_config_is_not_compared(tmp_path):
    """Suppression B fires on its own case: the config is not in the registry."""
    from exp_resultsdb import SUPPRESS_NO_BOOK
    p = _write(tmp_path, "retired.md",
               "| arm | NET R |\n|---|---|\n"
               "| pivot_rule origin arm, NET | %+.2f |\n" % WRONG)
    hits, exempt, supp = __import__("exp_resultsdb")._quoted_numbers(
        p, {"fsent_champ_long"}, KNOWN_SET, 0.5, set(), set())
    assert not hits, "a retired config's number was compared as a live pin"
    assert {r for r, _ in supp} == {SUPPRESS_NO_BOOK}, \
        "wrong suppression reason: %r" % {r for r, _ in supp}


def test_present_config_is_still_compared(tmp_path):
    """THE GUARD. Same number on a line that DOES name a real book -> still fails.

    This is what keeps suppression B from widening into "any line without a book
    name", which would have retired a genuine stale pin.
    """
    p = _write(tmp_path, "live.md",
               "| arm | NET R |\n|---|---|\n"
               "| `fsent_champ_long` plus a retired note | %+.2f |\n" % WRONG)
    hits, _ = _scan(p)
    assert hits, "a stale pin on a real book was suppressed"
    assert abs(_num(hits[0]) - WRONG) < 0.005, "flagged the wrong number: %r" % (hits,)


def test_suppressions_do_not_disturb_the_exempt_channel(tmp_path):
    """A quarantined-book number stays exempt, not suppressed, and not a hit."""
    p = _write(tmp_path, "quar.md",
               "| book | IS net |\n|---|---|\n"
               "| `fsent_dirmatch_long` | %+.2f |\n" % WRONG)
    hits, exempt, supp = __import__("exp_resultsdb")._quoted_numbers(
        p, {"fsent_dirmatch_long"}, KNOWN_SET, 0.5,
        {"fsent_dirmatch_long"}, set())
    assert not hits and not supp, "quarantined book leaked: %r %r" % (hits, supp)
    assert len(exempt) == 1, "quarantined number left the exempt channel"
