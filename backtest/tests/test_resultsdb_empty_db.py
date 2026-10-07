"""check() must not pass on an empty database.

The failure this exists to prevent
----------------------------------
results_db.init() runs executescript(SCHEMA) and nothing else: it creates the
tables, it does not ingest rows. results.db is gitignored, so a fresh clone has
no rows in `books`.

Before the guard, check() walked

    SELECT name, params_json FROM books WHERE params_json IS NOT NULL

over an empty table, iterated zero times, printed "params drift: 0", and
returned 0 - PASS. It was reporting agreement with nothing. And the damage is
not visible in check() at all, because the same empty table is where the work
lists come from:

    exp_multi_metrics.multi_books()  -> SELECT name FROM books WHERE plane='multi'
    exp_signal_metrics.signal_books() -> SELECT name FROM books WHERE plane='signal'

So on a fresh clone the two harnesses behind MULTI_RANKINGS, SIGNAL_RANKINGS and
SIGNAL_RESULTS would sweep zero books, write a valid-looking JSON, and print
"ran 0/0".

Asserted here:
  1. check() returns non-zero against an empty database (the regression).
  2. the message names the command that fixes it, so the failure is actionable.
  3. a table-only init() really does leave zero books - if this ever stops being
     true the guard is protecting against nothing and should be revisited.

Run:  cd backtest/tests && python -m pytest test_resultsdb_empty_db.py -q
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "backend"))


def _empty_db(tmp_path):
    """A results.db path that init() has created tables in but never filled."""
    import results_db as rdb
    path = tmp_path / "empty_results.db"
    rdb.init(path).close()
    return path


def test_init_alone_leaves_the_books_table_empty(tmp_path):
    """init() creates tables; it does not ingest. This is why the guard exists."""
    import results_db as rdb
    path = _empty_db(tmp_path)
    conn = rdb.connect(path)
    try:
        assert path.exists(), "init() should have created the file"
        n_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        n_results = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
        assert n_books == 0, "init() must not invent books, got %d" % n_books
        assert n_results == 0, "init() must not invent results, got %d" % n_results
    finally:
        conn.close()


def test_check_fails_on_an_empty_database(tmp_path, capsys):
    """The regression: this used to return 0 and print PASS."""
    from exp_resultsdb import check
    rc = check(db=_empty_db(tmp_path))
    out = capsys.readouterr().out
    assert rc != 0, "check() passed vacuously on an empty database"
    assert "EMPTY DATABASE" in out, "failure did not name itself: %r" % out


def test_check_failure_tells_you_the_fix(tmp_path, capsys):
    """A green check is bad enough; a red one with no instruction is worse."""
    from exp_resultsdb import check
    check(db=_empty_db(tmp_path))
    out = capsys.readouterr().out
    assert "ingest" in out, "failure did not name the repair command: %r" % out