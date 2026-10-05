"""Ingest the registry and the result JSONs into the results database.

This is the migration that makes the database the home of every number. Two
sources are read, and neither is invented here:

  1. The registry pins. 209 books, two eras each. This is the authoritative
     measurement set - exp_fastcheck and exp_pinverify already reproduce them -
     so they carry harness='registry' and need no separate provenance.

  2. The result JSONs. 347 files with no shared schema. Rather than guess a
     shape, this walks each file looking for the canonical metric names and
     records what it finds under whatever key it was found under, with the
     source file on the row. A file whose shape is not recognised is counted
     and reported, never silently dropped - an unrecognised file is a question
     to answer, not a thing to forget.

Why both and not just the registry: the registry holds the books that were
pinned. The experiments that are not books - the 54-cell serial-filter sweep in
_fs_serial_filters.json, the anchor ladders, the per-lens studies - exist only
as JSON, and several of those numbers are stronger than anything pinned. They
are also the ones most likely to be quoted from prose and go stale there.

Usage:
    python exp_resultsdb.py ingest     # rebuild books + results from scratch
    python exp_resultsdb.py report     # what is in there, by plane
    python exp_resultsdb.py unmapped   # files whose shape was not recognised
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Windows consoles default to cp1252 and die on the arrows and dashes these
# documents are full of. Replace rather than fail: a gate that crashes on a
# glyph is a gate that gets switched off.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
for p in ("backtest/tests", "backtest", "backend", ""):
    sys.path.insert(0, str(ROOT / p) if p else str(ROOT))

import results_db as rdb  # noqa: E402
import experiment_registry as reg  # noqa: E402

# The three fields exp_fastcheck.py compares, plus the three every equity study
# reports. Anything else goes to extras rather than into a mislabelled column.
CANON = {
    "n": ("n", "trades", "count", "nt", "total_trades"),
    "net": ("net", "net_r", "total_r", "netR", "net_total_r", "sum_r"),
    "dd_net": ("dd_net", "dd", "maxdd", "max_dd", "max_dd_net"),
    "win": ("win", "wr", "win_rate", "winrate"),
    "pf": ("pf", "profit_factor"),
    "avg_r": ("avg_r", "avgR", "per", "expectancy"),
}
_CANON_KEYS = {k for v in CANON.values() for k in v}


def _canon_get(d: dict, want: str):
    """Pull one canonical metric out of a dict, case-insensitively."""
    if not isinstance(d, dict):
        return None
    for k in CANON[want]:
        v = d.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    low = {str(k).lower(): v for k, v in d.items()}
    for k in CANON[want]:
        v = low.get(k.lower())
        if isinstance(v, (int, float)):
            return float(v)
    return None


def plane_of(params: dict, bp: dict) -> str:
    mp = (params or {}).get("max_positions", bp.get("max_positions"))
    return "signal" if mp == 1 else "multi"


def ingest_books(conn) -> tuple[int, int]:
    """Registry -> books + results. Returns (n_books, n_result_rows).

    ALIASES rows are skipped rather than ingested: their registry value is a
    STRING naming the book they point at, not a params dict. Ingesting one would
    put a row in the database for a book that does not exist.
    """
    bp = reg.BP
    books = rows = 0
    for name, v in reg.EXPERIMENTS.items():
        if not isinstance(v, dict):
            continue
        params = v.get("params") or {}
        rdb.set_book(conn, name, plane_of(params, bp), v.get("status"), params=params)
        books += 1
        p = v.get("pins") or {}
        if not p.get("n"):
            continue
        # One registry row carries both eras, which is why the pins block uses
        # an oos_ prefix rather than being a nested dict.
        rdb.upsert_result(conn, book=name, era="is", scope="", harness="registry",
                          source_file="experiment_registry", n=p.get("n"),
                          net=p.get("net"), dd_net=p.get("dd_net"),
                          win=p.get("win"), measured_at="registry")
        rows += 1
        if p.get("oos_n") is not None:
            rdb.upsert_result(conn, book=name, era="oos", scope="",
                              harness="registry", source_file="experiment_registry",
                              n=p.get("oos_n"), net=p.get("oos_net"),
                              dd_net=p.get("oos_dd_net"), win=p.get("oos_win"),
                              measured_at="registry")
            rows += 1
    return books, rows


def _walk(node, book_hint: str, era_hint: str, harness: str, src: str,
          conn, depth: int = 0):
    """Find every dict in a JSON carrying at least two canonical metrics.

    Depth is capped at 6 on purpose. The result files nest trades and day lists
    several levels down, and a dict with a `net` three levels down is a trade,
    not a result - without the cap a single day-level file would contribute tens
    of thousands of meaningless rows.
    """
    if depth > 6:
        return 0
    ok = 0
    if isinstance(node, dict):
        n = _canon_get(node, "n")
        net = _canon_get(node, "net")
        hits = sum(1 for k in CANON if _canon_get(node, k) is not None)
        if (n is not None or net is not None) and hits >= 2:
            book = node.get("book") or node.get("lane") or book_hint
            if book:
                era = str(node.get("era") or era_hint or "").lower()
                scope = str(node.get("scope") or node.get("lens")
                            or node.get("arm") or "")
                extras = {k: v for k, v in node.items()
                          if isinstance(v, (int, float, str, bool))
                          and k not in _CANON_KEYS and k not in ("book", "lane")}
                rdb.upsert_result(
                    conn, book=str(book), era=era if era in rdb.ERAS else "",
                    scope=scope, harness=harness, source_file=src,
                    n=n, net=net, dd_net=_canon_get(node, "dd_net"),
                    win=_canon_get(node, "win"), pf=_canon_get(node, "pf"),
                    avg_r=_canon_get(node, "avg_r"), extras=extras,
                    measured_at=src)
                ok += 1
        for v in list(node.values())[:200]:
            ok += _walk(v, book_hint, era_hint, harness, src, conn, depth + 1)
    elif isinstance(node, list):
        for v in node[:4000]:
            ok += _walk(v, book_hint, era_hint, harness, src, conn, depth + 1)
    return ok


def ingest_json(conn, path: Path, harness: str) -> int:
    try:
        obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return 0
    ok = _walk(obj, path.stem.lstrip("_"), "", harness, path.name, conn)
    return ok + _ingest_keyed(conn, obj, harness, path.name)


def _ingest_keyed(conn, obj, harness: str, src: str) -> int:
    """Ingest a flat JSON whose KEYS carry the identity and whose VALUES are the
    metrics.

    _fs_serial_filters.json is 108 keys shaped "<base>|<serial filter>|<era>",
    each holding {n, net, dd, wr, pf}. Walking that as a tree finds the metrics
    but loses the key entirely, so every cell collapses onto the filename: the
    54-cell serial-filter sweep - the largest signal-plane experiment in this
    repo, and the one no document describes - ingested as a single row called
    "fs_serial_filters" with an arbitrary net. Splitting the key is the only way
    that data becomes queryable, and until it is, the database would be
    quietly understating what has already been measured.

    Splits on the last separator that yields a known era, so a base name is free
    to contain '|' itself. Anything not of this shape is left to _walk.
    """
    if not isinstance(obj, dict):
        return 0
    ok = 0
    for key, val in obj.items():
        if not isinstance(key, str) or "|" not in key:
            continue
        if not isinstance(val, dict):
            continue
        hits = sum(1 for k in CANON if _canon_get(val, k) is not None)
        if hits < 2:
            continue
        parts = key.split("|")
        era = ""
        if parts[-1].strip().lower() in rdb.ERAS:
            era = parts[-1].strip().lower()
            parts = parts[:-1]
        if not era or not parts:
            continue
        book = parts[0].strip()
        scope = " | ".join(p.strip() for p in parts[1:]) if len(parts) > 1 else ""
        n = _canon_get(val, "n")
        extras = {k: v for k, v in val.items()
                  if isinstance(v, (int, float, str, bool)) and k not in _CANON_KEYS}
        rdb.upsert_result(
            conn, book=book, era=era, scope=scope, harness=harness,
            source_file=src, n=n, net=_canon_get(val, "net"),
            dd_net=_canon_get(val, "dd_net"), win=_canon_get(val, "win"),
            pf=_canon_get(val, "pf"), avg_r=_canon_get(val, "avg_r"),
            extras=extras, measured_at=src)
        ok += 1
    return ok


def _db_numbers(conn) -> set[float]:
    """Every number the database knows, at the tolerance the verifiers use."""
    out: set[float] = set()
    for r in conn.execute("SELECT n, net, dd_net, win, pf, avg_r FROM results"):
        for v in r:
            if isinstance(v, (int, float)):
                out.add(round(float(v), 2))
    return out


def _book_names() -> set[str]:
    names = {k for k, v in reg.EXPERIMENTS.items() if isinstance(v, dict)}
    names |= set(getattr(reg, "ALIASES", {}) or {})
    rmp = ROOT / "backtest" / "tests" / "_rename_map.json"
    if rmp.exists():
        try:
            names |= set(json.loads(rmp.read_text(encoding="utf-8")).keys())
        except Exception:
            pass
    return names


# A number written as a measurement: an optional sign, digits, two decimals.
_NUM = re.compile(r"[+-]?\d+\.\d{2}")


def _quoted_numbers(path: Path, names: set[str], known: set[float], tol: float):
    """Numbers on a line that also names a book or a result key.

    The context rule is the whole design. A doc is full of numbers that are not
    measurements - a bar count, a date, a percentage of something unrelated -
    and a gate that flags those gets switched off, which is worse than no gate.
    """
    hits = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for lineno, line in enumerate(text.splitlines(), 1):
        if "|" not in line and not re.search(r"\b(net|R\b|dd|WR|PF)\b", line, re.I):
            continue
        names_here = [n for n in names if n in line]
        has_metric_word = re.search(r"\b(net|dd|wr|pf|win|trades|R)\b", line, re.I)
        if not names_here and not has_metric_word:
            continue
        for m in _NUM.finditer(line):
            v = round(float(m.group(0)), 2)
            if not any(abs(v - k) <= tol for k in known):
                hits.append((lineno, m.group(0), (names_here[:1] or [""])[0],
                             line.strip()[:88]))
    return hits


def check(verbose: bool = False) -> int:
    conn = rdb.init()
    fail = 0

    # 1. params drift
    drift = 0
    for r in conn.execute("SELECT name, params_json FROM books"
                         " WHERE params_json IS NOT NULL"):
        live = (reg.EXPERIMENTS.get(r["name"]) or {}).get("params")
        if live is None:
            continue
        if json.dumps(live, sort_keys=True) != r["params_json"]:
            print("PARAMS DRIFT  %s" % r["name"])
            drift += 1
    print("params drift            : %d" % drift)
    fail += drift

    # 2. orphan results
    reg_names = {k for k, v in reg.EXPERIMENTS.items() if isinstance(v, dict)}
    orphans = [r["book"] for r in conn.execute(
        "SELECT DISTINCT r.book FROM results r LEFT JOIN books b"
        " ON b.name = r.book WHERE b.name IS NULL")]
    print("orphan result books     : %d" % len(orphans))
    if orphans:
        # Named, not counted: these are the experiments that are not books, and
        # they are the ones most likely to be quoted from prose.
        for o in sorted(orphans)[:14]:
            print("    %s" % o)
        if len(orphans) > 14:
            print("    ... and %d more" % (len(orphans) - 14))

    # 3. the doc gate
    known = _db_numbers(conn)
    names = _book_names()
    total = 0
    for md in sorted((ROOT / "backtest" / "docs").rglob("*.md")):
        hits = _quoted_numbers(md, names, known, 0.5)
        if hits:
            total += len(hits)
            print("\n%s  (%d)" % (md.name, len(hits)))
            for lineno, num, book, line in (hits if verbose else hits[:6]):
                print("   line %-5d %-10s near %-26s | %s"
                      % (lineno, num, book or "(no book named)", line))
            if not verbose and len(hits) > 6:
                print("   ... and %d more (use -v)" % (len(hits) - 6))
    print("\ndoc numbers not in the database : %d" % total)
    fail += total
    print("=" * 62)
    if fail:
        print("FAIL - %d problem(s)" % fail)
        return 1
    print("PASS - database agrees with the registry and the docs.")
    return 0


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="results db")
    ap.add_argument("cmd", choices=["ingest", "report", "unmapped", "check"])
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        return check(a.verbose)
    conn = rdb.init()

    if a.cmd == "report":
        print("books by plane:")
        for r in conn.execute("SELECT plane, COUNT(*) c FROM books GROUP BY plane"):
            print("  %-8s %d" % (r["plane"], r["c"]))
        print("\nresults by era:")
        for r in conn.execute("SELECT era, COUNT(*) c FROM results GROUP BY era"):
            print("  %-8s %d" % (r["era"] or "(none)", r["c"]))
        print("\ntop signal books by OOS net:")
        q = ("SELECT b.name, r.n, r.net, r.dd_net FROM results r"
             " JOIN books b ON b.name=r.book"
             " WHERE b.plane='signal' AND r.era='oos' AND r.scope=''"
             " ORDER BY r.net DESC LIMIT 12")
        for r in conn.execute(q):
            print("  %-34s %5s %+9s dd %s" % (r["name"], r["n"], r["net"], r["dd_net"]))
        return 0

    if a.cmd == "unmapped":
        n = conn.execute("SELECT COUNT(DISTINCT source_file) FROM results").fetchone()[0]
        tot = len(list((ROOT / "backtest" / "tests").glob("_*.json")))
        print("result JSONs on disk : %d" % tot)
        print("contributed a row    : %d" % n)
        print("no row recognised    : %d" % (tot - n))
        return 0

    conn.execute("DELETE FROM results")
    conn.execute("DELETE FROM books")
    b, r = ingest_books(conn)
    conn.commit()
    print("registry -> %d books, %d result rows" % (b, r))
    mapped = 0
    for jf in sorted((ROOT / "backtest" / "tests").glob("_*.json")):
        stem = jf.stem.lstrip("_")
        if ingest_json(conn, jf, stem if stem.startswith("exp_") else ""):
            mapped += 1
    conn.commit()
    tot = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    print("json    -> %d of %d files contributed, %d result rows total"
          % (mapped, len(list((ROOT / "backtest" / "tests").glob("_*.json"))), tot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())