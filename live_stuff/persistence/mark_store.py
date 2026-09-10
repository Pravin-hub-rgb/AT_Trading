"""Mark store - append-only journal for marks.

Single responsibility: insert and query marks.
Marks are NEVER updated or deleted once written.
"""

import time
from typing import Optional
from .database import Database
from engine.mark import Mark


def insert_mark(db: Database, mark: Mark) -> int:
    """Insert a mark into the journal.
    
    Args:
        db: Database instance
        mark: Mark to insert
    
    Returns:
        The row id of the inserted mark
    
    Raises:
        sqlite3.IntegrityError: if mark already exists (duplicate)
    """
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO marks (ts, tf, kind, direction, price, swing_no, swing_kind, algo_version, journaled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mark.ts,
                mark.tf,
                mark.kind,
                mark.direction,
                mark.price,
                mark.swing_no,
                mark.swing_kind,
                mark.algo_version,
                int(time.time()),
            ),
        )
        return cursor.lastrowid


def insert_mark_safe(db: Database, mark: Mark) -> Optional[int]:
    """Insert a mark, ignoring duplicates.
    
    Returns:
        The row id if inserted, None if duplicate
    """
    try:
        mark_id = insert_mark(db, mark)
        mark.id = mark_id
        return mark_id
    except Exception:
        return None


def get_marks(db: Database, tf: str, from_ts: int = 0, to_ts: int = 0) -> list[Mark]:
    """Get marks for a timeframe within a time range.
    
    Args:
        db: Database instance
        tf: timeframe ("15m" or "1h")
        from_ts: start timestamp (inclusive)
        to_ts: end timestamp (inclusive), 0 = no limit
    
    Returns:
        List of Mark objects, sorted by timestamp
    """
    query = "SELECT * FROM marks WHERE tf = ?"
    params: list = [tf]
    
    if from_ts > 0:
        query += " AND ts >= ?"
        params.append(from_ts)
    
    if to_ts > 0:
        query += " AND ts <= ?"
        params.append(to_ts)
    
    query += " ORDER BY ts ASC"
    
    rows = db.conn.execute(query, params).fetchall()
    
    return [_row_to_mark(row) for row in rows]


def get_mark_by_id(db: Database, mark_id: int) -> Optional[Mark]:
    """Get a single mark by id."""
    row = db.conn.execute(
        "SELECT * FROM marks WHERE id = ?",
        (mark_id,)
    ).fetchone()
    
    if row is None:
        return None
    
    return _row_to_mark(row)


def mark_exists(db: Database, mark: Mark) -> bool:
    """Check if a mark already exists (by unique constraint)."""
    row = db.conn.execute(
        """SELECT id FROM marks 
           WHERE ts = ? AND tf = ? AND kind = ? AND direction = ? AND swing_no = ?""",
        (mark.ts, mark.tf, mark.kind, mark.direction, mark.swing_no)
    ).fetchone()
    
    return row is not None


def get_mark_count(db: Database, tf: str = "") -> int:
    """Get total number of marks, optionally filtered by timeframe."""
    if tf:
        row = db.conn.execute(
            "SELECT COUNT(*) FROM marks WHERE tf = ?",
            (tf,)
        ).fetchone()
    else:
        row = db.conn.execute("SELECT COUNT(*) FROM marks").fetchone()
    
    return row[0]


def _row_to_mark(row) -> Mark:
    """Convert a database row to a Mark object."""
    return Mark(
        id=row["id"],
        ts=row["ts"],
        tf=row["tf"],
        kind=row["kind"],
        direction=row["direction"],
        price=row["price"],
        swing_no=row["swing_no"],
        swing_kind=row["swing_kind"],
        algo_version=row["algo_version"],
        journaled_at=row["journaled_at"],
    )
