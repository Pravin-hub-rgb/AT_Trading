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
# The look-ahead list lives with the harness that proves it, so the database and
# the metrics run cannot disagree about which books are poisoned.
from exp_signal_metrics import (  # noqa: E402
    GRAVEYARD_KNOBS, Q_NOTE, quarantine_reason,
)

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
_EXTRA_METRIC_KEYS = {
    "wins":            ("wins", "win_count"),
    "losses":          ("losses", "loss_count"),
    "max_dd":          ("max_dd", "dd"),
    "avg_win":         ("avg_win",),
    "avg_loss":        ("avg_loss",),
    "payoff":          ("payoff",),
    "median_r":        ("median", "median_r"),
    "std_r":           ("std", "std_r"),
    "max_win_streak":  ("max_win_streak",),
    "max_loss_streak": ("max_loss_streak",),
    "gross_r":         ("gross_r",),
    "sum_r":           ("sum_r",),
    "wr_pct":          ("wr_pct", "win_rate_pct"),
}

# Keys promoted to their own column. sum_r and median/std stay out of this set
# because CANON already maps sum_r onto net; keeping both would let a row carry
# two different values for what reads as the same number.
_CANON_KEYS = {k for v in CANON.values() for k in v} | {
    k for keys in _EXTRA_METRIC_KEYS.values() for k in keys
}


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
    """A book's plane, by the registry's own definition.

    max_positions == 1 is the signal plane; everything else is multi. This is
    the primary axis of the whole repository, per BOOK_CATEGORIES.md.
    """
    mp = (params or {}).get("max_positions", bp.get("max_positions"))
    return "signal" if mp == 1 else "multi"


def _extra_metrics(node: dict) -> dict:
    """Lift the metrics the harnesses already compute out of extras.

    The JSONs have carried wins, losses, max_dd, avg_win, avg_loss, payoff,
    median, std and streak counts all along - 19k occurrences of max_loss_streak
    in _ddseries.json alone. They were landing in extras as JSON, so "win rate"
    and "average R per trade" could not be queried for most books. Anything not
    listed keeps going to extras.
    """
    out = {}
    for col, keys in _EXTRA_METRIC_KEYS.items():
        for k in keys:
            v = node.get(k) if isinstance(node, dict) else None
            if v is not None:
                try:
                    out[col] = float(v)
                except (TypeError, ValueError):
                    pass
                break
    return out


_EXTRA_METRIC_KEYS = {
    "wins":            ("wins", "win_count"),
    "losses":          ("losses", "loss_count"),
    "max_dd":          ("max_dd", "dd"),
    "avg_win":         ("avg_win",),
    "avg_loss":        ("avg_loss",),
    "payoff":          ("payoff",),
    "median_r":        ("median", "median_r"),
    "std_r":           ("std", "std_r"),
    "max_win_streak":  ("max_win_streak",),
    "max_loss_streak": ("max_loss_streak",),
    "gross_r":         ("gross_r",),
    "sum_r":           ("sum_r",),
    "wr_pct":          ("wr_pct", "win_rate_pct"),
}


def plane_for(conn, book: str, scope: str):
    """Resolve one row's plane: the scope first, then the registry, then unknown.

    The scope outranks the registry because it is the row's own record of how the
    measurement was taken, and the two disagree for champion_single_sw10, where
    the registry knows a signal book and the scope says max_pos=0.

    Falling back to the registry fills the 418 registry-sourced rows. What stays
    blank is the experiment base - "champion_single_sw10 | dirmatch + FS-short" -
    which is not a registered book at all. Those keep plane='' rather than
    inheriting a guess, so a filtered query says what it left out.
    """
    p = plane_from_scope(scope)
    if p:
        return p
    row = conn.execute("SELECT plane FROM books WHERE name=?", (str(book),)).fetchone()
    if row and row[0]:
        return row[0]
    return ""


def plane_from_scope(scope: str):
    """A result's plane, from the scope the experiment recorded on the row.

    The scopes in _fs_single.json and _fs_serial_filters.json say it outright -
    "serial max_pos=1 | short" versus "multi max_pos=0 | short" - and that is
    authoritative in a way the book NAME is not.

    This matters because one name carries both meanings. champion_single_sw10 is
    a signal book after the single-to-sig rename (champion_sig_sw10,
    max_positions=1), and it is simultaneously the base of a multi-position
    experiment recorded under its old name. Trusting the name filed 32 rows on
    the wrong plane and left them with no plane at all, which is how "top
    signal" came to return +426 and +492 for books holding several positions.

    Returns None when the scope does not say, so the caller falls back to the
    registry rather than guessing.
    """
    if not scope:
        return None
    m = re.search(r"max_pos\s*=\s*(\d+)", scope)
    if not m:
        return None
    return "signal" if int(m.group(1)) == 1 else "multi"


def ingest_books(conn) -> tuple[int, int]:
    """Registry -> books + results. Returns (n_books, n_result_rows).

    ALIASES rows are skipped rather than ingested: their registry value is a
    STRING naming the book they point at, not a params dict. Ingesting one would
    put a row in the database for a book that does not exist.
    """
    bp = reg.BP
    books = rows = quar = 0
    for name, v in reg.EXPERIMENTS.items():
        if not isinstance(v, dict):
            continue
        params = v.get("params") or {}
        # A book that reads a field not settled at its decision bar keeps its
        # numbers in this database - they are the evidence that the look-ahead was
        # caught - but they are flagged so a ranking cannot pick them. Left
        # unflagged, a query returns +444R books that cannot be traded.
        bad = quarantine_reason(params)
        rdb.set_book(conn, name, plane_of(params, bp), v.get("status"),
                     params=params,
                     quarantined=bad or "", q_note=Q_NOTE if bad else None)
        books += 1
        if bad:
            quar += 1
        p = v.get("pins") or {}
        if not p.get("n"):
            continue
        # One registry row carries both eras, which is why the pins block uses
        # an oos_ prefix rather than being a nested dict. The plane comes from
        # the registry's own max_positions, computed once above.
        rdb.upsert_result(conn, book=name, era="is", scope="", harness="registry",
                          source_file="experiment_registry",
                          plane=plane_of(params, bp),
                          n=p.get("n"),
                          net=p.get("net"), dd_net=p.get("dd_net"),
                          win=p.get("win"), measured_at="registry")
        rows += 1
        if p.get("oos_n") is not None:
            rdb.upsert_result(conn, book=name, era="oos", scope="",
                              harness="registry", source_file="experiment_registry",
                              plane=plane_of(params, bp),
                              n=p.get("oos_n"), net=p.get("oos_net"),
                              dd_net=p.get("oos_dd_net"), win=p.get("oos_win"),
                              measured_at="registry")
            rows += 1
    return books, rows, quar


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
                    plane=plane_for(conn, book, scope),
                    n=n, net=net, dd_net=_canon_get(node, "dd_net"),
                    win=_canon_get(node, "win"), pf=_canon_get(node, "pf"),
                    avg_r=_canon_get(node, "avg_r"), extras=extras,
                    **_extra_metrics(node),
                    measured_at=src)
                ok += 1
        # An era is often a KEY rather than a value: {"is": {...}, "oos": {...}}.
        # Iterating values alone loses which one was which, so every row came out
        # with era='' - and the filter that asks for the out-of-sample number
        # finds nothing. Fifty-eight files are shaped this way.
        for era_key in rdb.ERAS:
            if era_key in node and isinstance(node[era_key], (dict, list)):
                ok += _walk(node[era_key], book_hint, era_key, harness, src,
                            conn, depth + 1)

        for v in list(node.values())[:200]:
            if isinstance(v, (dict, list)):
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
            source_file=src, plane=plane_for(conn, book, scope),
            n=n, net=_canon_get(val, "net"),
            dd_net=_canon_get(val, "dd_net"), win=_canon_get(val, "win"),
            pf=_canon_get(val, "pf"), avg_r=_canon_get(val, "avg_r"),
            extras=extras, measured_at=src,
            **_extra_metrics(val))
        ok += 1
    return ok


def _ingest_metrics_file(conn, src, harness: str) -> int:
    """A per-book metrics JSON -> results rows on one harness name.

    Both planes produce the same shape from the same compute(): 18 metrics per
    (book, era), computed from the engine. exp_signal_metrics.py writes
    _signal_metrics.json for the max_positions=1 books, exp_multi_metrics.py
    writes _multi_metrics.json for the rest, and they land on different harness
    names so the two planes are never joined by accident - a 500-trade multi book
    and a 150-trade signal book are not comparable by total R.

    These rows supersede the registry pins numerically, so a query that wants the
    full metric set must read harness='signal_metrics' (or 'multi_metrics')
    rather than 'registry'. Both are kept - the pin is the claim, this is the
    re-measurement, and the difference between them is worth being able to ask
    about.
    """
    if not src.exists():
        return 0
    payload = json.loads(src.read_text(encoding="utf-8"))
    ok = 0
    for era, books in (payload.get("configs") or {}).items():
        if era not in rdb.ERAS:
            continue
        for book, m in (books or {}).items():
            if not m or not m.get("n"):
                continue
            if m.get("error"):
                continue
            rdb.upsert_result(
                conn, book=book, era=era, scope="",
                harness=harness, source_file=src.name,
                plane=plane_for(conn, book, ""),
                n=m.get("n"), net=m.get("net"), dd_net=m.get("max_dd"),
                win=(m["wr"] / 100.0) if m.get("wr") is not None else None,
                pf=m.get("pf"), avg_r=m.get("avgR"),
                median_r=m.get("median"), max_dd=m.get("max_dd"),
                avg_win=m.get("avg_win"), avg_loss=m.get("avg_loss"),
                payoff=m.get("payoff"), std_r=m.get("stdR"),
                wins=m.get("n_wins"), losses=m.get("n_losses"),
                max_loss_streak=m.get("max_streak"),
                extras={k: v for k, v in m.items()
                        if k not in ("n", "net", "wr", "pf", "avgR", "median",
                                     "max_dd", "max_streak", "avg_win",
                                     "avg_loss", "payoff", "stdR",
                                     "n_wins", "n_losses", "error")},
                measured_at=src.name)
            ok += 1
    return ok


def ingest_signal_metrics(conn) -> int:
    """_signal_metrics.json -> results rows on harness='signal_metrics'."""
    src = ROOT / "backtest" / "tests" / "_signal_metrics.json"
    return _ingest_metrics_file(conn, src, "signal_metrics")


def ingest_multi_metrics(conn) -> int:
    """_multi_metrics.json -> results rows on harness='multi_metrics'.

    Separate from the signal rows on purpose: see _ingest_metrics_file. Missing
    file is not an error - the plane simply has not been measured yet.
    """
    src = ROOT / "backtest" / "tests" / "_multi_metrics.json"
    return _ingest_metrics_file(conn, src, "multi_metrics")


def _graveyard() -> set[str]:
    """Books whose pins were deliberately removed.

    A number belonging to one of these is ABSENT from the database by design,
    and the documents that quote them are doing the right thing:
    closed/CLOSED_DO_NOT_REPEAT.md records what was measured before the family was
    closed, and that record is why anyone can tell the next person not to redo
    it. Flagging those lines would mean failing the documents whose entire job is
    to remember a dead end, and a gate that fails that way gets switched off.

    So a line naming a quarantined book is exempt - and counted separately, so
    the exemption stays visible instead of quietly becoming invisible.
    """
    out = set()
    for k, v in reg.EXPERIMENTS.items():
        if not isinstance(v, dict):
            continue
        # Graveyard = pins removed because the family read the future.
        # status reference = pins never written because the book loses in both
        # eras. Both are deliberate, and both are quoted in the documents that
        # record why they are not candidates.
        if (v.get("graveyard") or v.get("graveyard_knobs")
                or v.get("status") == "reference"):
            out.add(k)
    return out


ARTEFACTS_PATH = ROOT / "backtest" / "docs" / "_artefacts.json"


def _artefacts() -> dict:
    """Numbers a document quotes on purpose that are not measurements.

    The reason field is mandatory and the loader drops any entry without one.
    That is the whole point: an unexplained exemption is a number nobody has
    vouched for, which is the same failure as the +492.60 in a smaller costume.
    Suppressing a finding has to be written down, and written down where the next
    person reads it.
    """
    if not ARTEFACTS_PATH.exists():
        return {}
    try:
        data = json.loads(ARTEFACTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: dict = {}
    for e in (data.get("entries") or []):
        doc = (e.get("doc") or "").strip()
        if not doc or not (e.get("reason") or "").strip():
            continue
        try:
            num = round(float(e.get("number")), 2)
        except (TypeError, ValueError):
            continue
        out.setdefault(doc, set()).add(num)
    return out


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


def _rename_map() -> dict:
    rmp = ROOT / "backtest" / "tests" / "_rename_map.json"
    if not rmp.exists():
        return {}
    try:
        return json.loads(rmp.read_text(encoding="utf-8"))
    except Exception:
        return {}


# A number written as a measurement: an optional sign, digits, two decimals.
# A leading - is a sign only when nothing touches it. In `abs(net-325.78)` and
# `+291.02-146.90` the dash is an operator and the number is positive, and
# reading it as negative makes the gate fire on the most-quoted number in the
# repo. A letter or digit right before the dash is the tell.
_NUM = re.compile(r"(?<![A-Za-z0-9_.])[+-]?\d+\.\d{2}")


def _quoted_numbers(path: Path, names: set[str], known: set[float], tol: float,
                   exempt_books: set[str], artefacts: set[float]):
    """Numbers on a line that also names a book or a result key.

    The context rule is the whole design. A doc is full of numbers that are not
    measurements - a bar count, a date, a percentage of something unrelated -
    and a gate that flags those gets switched off, which is worse than no gate.

    Returns (hits, exempt). `exempt` covers a number quoted next to a quarantined
    book - absent from the database by design - and a number the document has
    registered as an artefact with a written reason.
    """
    hits = []
    exempt = []
    text = path.read_text(encoding="utf-8", errors="replace")
    rmap = _rename_map()
    for lineno, line in enumerate(text.splitlines(), 1):
        if "|" not in line and not re.search(r"\b(net|R\b|dd|WR|PF)\b", line, re.I):
            continue
        names_here = [n for n in names if n in line]
        has_metric_word = re.search(r"\b(net|dd|wr|pf|win|trades|R)\b", line, re.I)
        if not names_here and not has_metric_word:
            continue
        is_quarantine = any(n in exempt_books or rmap.get(n) in exempt_books
                            for n in names_here)
        for m in _NUM.finditer(line):
            v = round(float(m.group(0)), 2)
            if any(abs(v - k) <= tol for k in known):
                continue
            rec = (lineno, m.group(0), (names_here[:1] or [""])[0],
                   line.strip()[:88])
            if is_quarantine or any(abs(v - a) <= tol for a in artefacts):
                exempt.append(rec)
            else:
                hits.append(rec)
    return hits, exempt


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
    grave = _graveyard()
    arts = _artefacts()
    total = exc = 0
    for md in sorted((ROOT / "backtest" / "docs").rglob("*.md")):
        hits, ex = _quoted_numbers(md, names, known, 0.5, grave,
                                    arts.get(md.name, set()))
        exc += len(ex)
        if hits:
            total += len(hits)
            print("\n%s  (%d)" % (md.name, len(hits)))
            for lineno, num, book, line in (hits if verbose else hits[:6]):
                print("   line %-5d %-10s near %-26s | %s"
                      % (lineno, num, book or "(no book named)", line))
            if not verbose and len(hits) > 6:
                print("   ... and %d more (use -v)" % (len(hits) - 6))
    print("\ndoc numbers not in the database   : %d" % total)
    print("exempt - quarantined books, history: %d  [%d books]"
          % (exc, len(grave)))
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
        qn = conn.execute("""SELECT COUNT(*) FROM books
                             WHERE quarantined<>''""").fetchone()[0]
        print("  of which quarantined (look-ahead, never rank): %d" % qn)
        for r in conn.execute("""SELECT name, plane, quarantined FROM books
                                 WHERE quarantined<>'' ORDER BY plane, name"""):
            print("    %-40s %-7s %s" % (r["name"][:40], r["plane"], r["quarantined"]))
        print("\nresults by era:")
        for r in conn.execute("SELECT era, COUNT(*) c FROM results GROUP BY era"):
            print("  %-8s %d" % (r["era"] or "(none)", r["c"]))
        print("\ntop signal books by OOS net, with the full metric set")
        print("(signal plane, quarantined excluded, n>=30, metrics re-measured)")
        q = ("SELECT i.book, i.n isn, i.net isnet, i.avg_r isavg, i.win iswin,"
             " i.pf ispf, i.max_dd isdd,"
             " json_extract(i.extras,'$.top5_share_pct') ist5,"
             " o.n, o.net, o.avg_r, o.win, o.pf, o.max_dd,"
             " json_extract(o.extras,'$.top5_share_pct') ost5"
             " FROM results i JOIN results o"
             "   ON o.book=i.book AND o.harness='signal_metrics' AND o.era='oos'"
             " JOIN books b ON b.name=i.book"
             " WHERE i.harness='signal_metrics' AND i.era='is'"
             "   AND b.plane='signal' AND b.quarantined=''"
             "   AND i.n>=30 AND o.n>=30"
             " ORDER BY CAST(o.net AS REAL) DESC LIMIT 12")
        print("  %-26s %5s %7s %6s %6s %5s %6s %4s | %5s %7s %6s %6s %5s %6s %4s"
              % ("book", "ISn", "ISnet", "R/trd", "wr%", "PF", "DD", "t5",
                 "OOSn", "OOSnet", "R/trd", "wr%", "PF", "DD", "t5"))
        for r in conn.execute(q):
            def n(v, w, p=2):
                return ("%*.*f" % (w, p, float(v))) if v not in (None, "") \
                    else " " * w
            def pc(v):
                return "%5.1f%%" % (float(v) * 100) if v not in (None, "") else "    -"
            print("  %-26s %5s %7s %6s %6s %5s %6s %4s | %5s %7s %6s %6s %5s %6s %4s"
                  % (r["book"][:26], r["isn"], n(r["isnet"], 7, 1), n(r["isavg"], 6),
                     pc(r["iswin"]), n(r["ispf"], 5), n(r["isdd"], 6, 1),
                     n(r["ist5"], 4, 0),
                     r["n"], n(r["net"], 7, 1), n(r["avg_r"], 6), pc(r["win"]),
                     n(r["pf"], 5), n(r["max_dd"], 6, 1), n(r["ost5"], 4, 0)))
        return 0

    if a.cmd == "unmapped":
        n = conn.execute("SELECT COUNT(DISTINCT source_file) FROM results").fetchone()[0]
        files = sorted((ROOT / "backtest" / "tests").glob("_*.json"))
        seen = {r["source_file"] for r in conn.execute(
            "SELECT DISTINCT source_file FROM results")}
        miss = [p for p in files if p.name not in seen]
        print("result JSONs on disk : %d" % len(files))
        print("contributed a row    : %d" % n)
        print("no row recognised    : %d" % len(miss))
        if a.verbose:
            print()
            for p in miss:
                print("  %-56s %8.1f KB" % (p.name, p.stat().st_size / 1024))
        return 0

    conn.execute("DELETE FROM results")
    conn.execute("DELETE FROM books")
    b, r, quar = ingest_books(conn)
    conn.commit()
    print("registry -> %d books (%d quarantined), %d result rows"
          % (b, quar, r))
    mapped = 0
    for jf in sorted((ROOT / "backtest" / "tests").glob("_*.json")):
        stem = jf.stem.lstrip("_")
        if ingest_json(conn, jf, stem if stem.startswith("exp_") else ""):
            mapped += 1
    conn.commit()
    tot = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    print("json    -> %d of %d files contributed, %d result rows total"
          % (mapped, len(list((ROOT / "backtest" / "tests").glob("_*.json"))), tot))
    sm = ingest_signal_metrics(conn)
    mm = ingest_multi_metrics(conn)
    conn.commit()
    tot = conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    print("metrics -> %d signal rows (_signal_metrics.json), "
          "%d multi rows (_multi_metrics.json), %d total" % (sm, mm, tot))
    if not sm:
        print("metrics -> no _signal_metrics.json yet "
              "(run: python backtest/tests/exp_signal_metrics.py)")
    if not mm:
        print("metrics -> no _multi_metrics.json yet "
              "(run: python backtest/tests/exp_multi_metrics.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())