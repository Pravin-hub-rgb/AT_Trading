"""The results database - every measured number in this repo, in one place.

WHY THIS EXISTS

    Measured results were scattered across 347 JSON files in backtest/tests with
    no shared schema: about 28 followed one shape and the rest were each their
    own. Sixteen markdown files carried result tables as well, and one of them -
    BOOK_CATEGORIES.md - carried a number (+492.60 for
    fsent_single_sw20_short_wr) that appears nowhere else in the repository, on
    a book that turned out to be a duplicate of another. A number with one home
    is a number that can be checked. A number written into prose is a number
    nobody can check.

    So: numbers live here. Markdown carries theory and points at a row. Harnesses
    write JSON and get ingested.

THE ONE TABLE THAT MATTERS

    results - one row per (book, era, scope, harness). n / net / dd_net are the
    same three fields exp_fastcheck.py and exp_pinverify.py already compare, on
    the same 0.5 tolerance, because those are the fields the registry pins. A
    number that is not one of those three goes in extras rather than being
    forced into a column whose header would then lie about it.

    Provenance rides on results.source_file and results.harness. A result with
    no source file is not evidence, it is a rumour.

WHAT IS NOT IN HERE

    Books are not duplicated from the registry. The books table holds only what
    the registry does not already own - plane, status, note - and params_json is
    a cache that exp_resultsdb.py check fails on if it drifts. The registry stays
    the source of truth for what a book IS; this database is the record of what
    was measured.

SCHEMA

    results    the measurements. UNIQUE(book, era, scope, harness).
    books      plane + status + note, joined to the registry by name.
    harnesses  inventory of exp_*.py: what it measures, live or dead.
    docs       inventory of backtest/docs/*.md: plane, verdict, and whether it
               cites a result. This is what makes the doc gate possible.

THE GATE THAT MATTERS

    exp_resultsdb.py check re-derives nothing. It checks internal consistency:
    that every results row still names a book in the registry, that cached
    params match, and that no doc cites a number the database does not contain.
    That last one is the +492.60 check, and it is why the database has to exist
    before the docs get restructured.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "backtest" / "tests" / "results.db"

# The two eras the repo measures a book on. "scope" is a sub-slice within an era:
# a lens, a cohort, an arm.
ERAS = ("is", "oos")

RESULT_COLS = ("book", "era", "scope", "harness", "source_file",
               "n", "net", "dd_net", "win", "pf", "avg_r",
               "extras", "measured_at")

SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS books (
    name        TEXT PRIMARY KEY,
    plane       TEXT,          -- signal | multi | shared | unknown
    status      TEXT,          -- '' | reference | free text
    note        TEXT,
    params_json TEXT           -- cache of registry params; gated for drift
);

CREATE TABLE IF NOT EXISTS results (
    id          INTEGER PRIMARY KEY,
    book        TEXT NOT NULL,
    era         TEXT NOT NULL,             -- is | oos
    scope       TEXT NOT NULL DEFAULT '',  -- lens/cohort/arm within the era
    harness     TEXT NOT NULL DEFAULT '',  -- which exp_*.py produced this
    source_file TEXT,                      -- the JSON it was ingested from

    n           INTEGER,      -- trade count
    net         REAL,         -- net R, after costs
    dd_net      REAL,         -- max drawdown on the net curve
    win         REAL,         -- 0..1
    pf          REAL,         -- profit factor
    avg_r       REAL,         -- mean R per trade
    extras      TEXT,         -- anything else, as JSON

    measured_at TEXT,
    UNIQUE(book, era, scope, harness)
);

CREATE INDEX IF NOT EXISTS idx_results_era_net ON results(era, net DESC);
CREATE INDEX IF NOT EXISTS idx_results_book    ON results(book);
CREATE INDEX IF NOT EXISTS idx_results_harness ON results(harness);

CREATE TABLE IF NOT EXISTS harnesses (
    file     TEXT PRIMARY KEY,
    stage    TEXT,
    measures TEXT,
    status   TEXT,           -- live | dead | unknown
    note     TEXT
);

CREATE TABLE IF NOT EXISTS docs (
    file          TEXT PRIMARY KEY,
    plane         TEXT,
    verdict       TEXT,
    cites_results INTEGER DEFAULT 0,
    note          TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


def init(path: Path | None = None) -> sqlite3.Connection:
    conn = connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def upsert_result(conn: sqlite3.Connection, **kw) -> None:
    """One measurement. `extras` is where a non-canonical field goes, rather
    than a column being invented for it."""
    vals = []
    for c in RESULT_COLS:
        v = kw.get(c)
        if c == "extras" and isinstance(v, dict):
            v = json.dumps(v, sort_keys=True)
        vals.append("" if v is None else v)
    conn.execute(
        "INSERT OR REPLACE INTO results (%s) VALUES (%s)"
        % (",".join(RESULT_COLS), ",".join("?" * len(RESULT_COLS))),
        vals)


def set_book(conn: sqlite3.Connection, name: str, plane: str | None = None,
             status: str | None = None, note: str | None = None,
             params: dict | None = None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO books (name, plane, status, note, params_json)"
        " VALUES (?,?,?,?,?)",
        (name, plane or "", status or "", note or "",
         json.dumps(params, sort_keys=True) if params is not None else None))


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="results database")
    ap.add_argument("--db", help="path to the db (default backtest/tests/results.db)")
    ap.add_argument("--init", action="store_true", help="create tables and exit")
    ap.add_argument("--path", action="store_true", help="print the db path and exit")
    a = ap.parse_args(argv)

    if a.path:
        print(Path(a.db).resolve() if a.db else DB_PATH)
        return 0
    conn = init(Path(a.db) if a.db else None)
    if a.init:
        print("initialised %s" % (a.db or DB_PATH))
        return 0
    for t in ("books", "results", "harnesses", "docs"):
        print("%-12s %d" % (t, conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
