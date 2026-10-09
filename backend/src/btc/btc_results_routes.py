"""/api/btc/results - the /results page's data source.

This serves a COMMITTED ARTIFACT, and that is a deliberate choice rather than a
shortcut. The research is finished, every pin is reproduced by exp_fastcheck, and
the numbers on this page are the same numbers the docs in backtest/docs/method
quote. An endpoint that re-ran the engine on every page load would eventually
disagree with those docs by a rounding step, and there would be no way to tell
which side was wrong. Here there is exactly one source of truth and it is
regenerable with one command:

    python backtest/tests/exp_results_export.py

So the staleness question has an answer instead of being an accident: the file
carries `generated_from`, and this endpoint reports the artifact's mtime so the
page can show when it was built.

It serves from backtest/tests/, which is a sibling of the backend package rather
than part of it. That is the one coupling this adds, and it is deliberately a file
path and not an import: the Python experiment registry lives there and is the
source of truth for what a book IS. Importing it would drag the whole backtest
harness into the server process.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/btc", tags=["results"])

# server.py sits at backend/server.py; the artifact at backtest/tests/_results.json
_HERE = os.path.dirname(os.path.abspath(__file__))          # backend/src/btc
_BACKEND = os.path.abspath(os.path.join(_HERE, os.pardir, os.pardir))
ARTIFACT = os.path.join(_BACKEND, os.pardir, "backtest", "tests", "_results.json")

_cache: dict = {"data": None, "mtime": None}


def _load(force: bool = False) -> dict:
    """Read the artifact, re-reading only when the file changed on disk.

    The mtime check is what makes a regeneration show up without a server
    restart. Without it, `force` would be the only refresh and the common case -
    re-run the exporter, reload the browser - would silently serve stale numbers,
    which is the exact failure mode the artifact approach was chosen to avoid.
    """
    if not os.path.exists(ARTIFACT):
        raise HTTPException(
            status_code=503,
            detail=(
                "results artifact missing. Run: python backtest/tests/exp_results_export.py"
            ),
        )
    mtime = os.path.getmtime(ARTIFACT)
    if force or _cache["data"] is None or _cache["mtime"] != mtime:
        with open(ARTIFACT, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        _cache["data"] = data
        _cache["mtime"] = mtime
    return _cache["data"]


@router.get("/results")
def get_results(refresh: bool = False, family: Optional[str] = None):
    """Every book with its full metric set and per-trade equity series.

    `family` filters to "multi" or "sig" server-side so the page does not have to
    ship both families when the user only wants one. `refresh` re-reads the file
    even when its mtime is unchanged.
    """
    data = _load(force=refresh)
    books = data.get("books", [])
    if family in ("multi", "sig"):
        books = [b for b in books if b.get("family") == family]
    out = dict(data)
    out["books"] = books
    out["artifact_mtime"] = _cache["mtime"]
    out["count"] = len(books)
    return JSONResponse(out)


@router.get("/results/{book_name}")
def get_book(book_name: str):
    """One book's record, including its equity series."""
    data = _load()
    for b in data.get("books", []):
        if b.get("name") == book_name:
            return JSONResponse(b)
    raise HTTPException(status_code=404, detail="book not found: %s" % book_name)