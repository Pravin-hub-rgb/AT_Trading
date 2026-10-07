"""The open research queue must be reachable.

Every `[ ]` item in OPEN_RESEARCH_QUEUE.md has to either cite a locatable
artifact or declare `anchor: none` and say why. See queue_unanchored() in
exp_resultsdb.py for why the pin rule cannot cover this file.

These tests use synthetic queues on purpose: proving the rule passes on the
real queue is not evidence the rule works, because a rule that matched nothing
would do that too.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from exp_resultsdb import QUEUE_PATH, queue_unanchored  # noqa: E402


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "Q.md"
    p.write_text(body, encoding="utf-8")
    return p


def test_real_queue_is_fully_anchored():
    assert QUEUE_PATH.exists(), QUEUE_PATH
    assert queue_unanchored() == [], queue_unanchored()


def test_open_item_without_anchor_fails(tmp_path):
    q = _write(tmp_path, """
# Q

- `[ ]` **Something wrong** — a problem nobody can go and look at.
- `[x]` **Closed thing** — `method/SOMETHING.md`
""")
    bad = queue_unanchored(q)
    assert len(bad) == 1
    assert "Something wrong" in bad[0][1]


def test_declared_none_is_accepted_with_a_reason(tmp_path):
    q = _write(tmp_path, """
- `[ ]` **No anchor, on purpose** — anchor: none, because the data does not exist
  in this repo and the fetch is blocked. That is the whole point.
""")
    assert queue_unanchored(q) == []


def test_bare_anchor_none_is_still_a_deliberate_declaration(tmp_path):
    # The gate checks for a DECLARATION, not for the quality of the justification.
    # Typing `anchor: none` already forces the author to notice the gap, which is
    # the anti-blind-spot property that matters. Whether the reason afterwards is
    # any good is a judgement a regex cannot make, so the gate does not pretend to
    # make it.
    q = _write(tmp_path, """
- `[ ]` **Vague** — anchor: none, later.
""")
    assert queue_unanchored(q) == []


def test_anchor_does_not_leak_from_the_next_item(tmp_path):
    # A done item with a citation must not rescue the open item above it.
    q = _write(tmp_path, """
- `[ ]` **Open, unanchored** — no path anywhere in this block.
- `[x]` **Closed, anchored** — `method/WITH_A_PATH.md`
""")
    bad = queue_unanchored(q)
    assert len(bad) == 1
    assert "Open, unanchored" in bad[0][1]


def test_anchor_in_a_later_paragraph_counts(tmp_path):
    q = _write(tmp_path, """
- `[ ]` **Open but points somewhere** — blocked on a fix.
  The evidence is at `method/EVIDENCE.md`.
""")
    assert queue_unanchored(q) == []


def test_anchor_recognises_py_and_json(tmp_path):
    for ref in ("exp_thing.py", "`_thing_results.json`"):
        q = _write(tmp_path, "- `[ ]` **item** — see %s\n" % ref)
        assert queue_unanchored(q) == [], ref


def test_missing_queue_file_is_not_a_failure(tmp_path):
    # Absent must not read as verified-empty for a different reason than the
    # empty-DB bug: here there is genuinely nothing to check yet.
    assert queue_unanchored(tmp_path / "does_not_exist.md") == []


def test_done_items_are_never_checked(tmp_path):
    q = _write(tmp_path, "- `[x]` **Historical, unanchored** — no path here.\n")
    assert queue_unanchored(q) == []