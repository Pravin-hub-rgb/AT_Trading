"""Bounded retention for the sim input windows.

The vendored batch sim (`simulate_htf_ltf_streak_halt`) walks the entire
candle/swing arrays on every 15m close, but its HTF side only depends on the
last ~CAP_DAYS of history (htf_cap_days, default 16). Older candles and swings
are dead weight that only grow cost and memory.

This module trims a (candles, swings) pair to a trailing window while
re-indexing every swing idx field so the trimmed arrays stay internally
consistent (swing indices remain valid positions into the trimmed candle
array). Used on the *sim input* only; the full stores in `all_candles_*` /
`all_swings_*` and the DB are untouched, so crash recovery and swing-engine
state are unaffected.

Correctness rule (bulk swing removal): the trim boundary is never allowed to
cut through the middle of a swing. If a retained swing starts before the
calendar cutoff, the cutoff is pulled back to that swing's start_idx so the
whole swing (and its start bar) stays in the window. This keeps every retained
swing's `seg.start_idx >= 0` and prevents the SL slice in `_collect_signals`
from clamping a negative start to 0 (which would corrupt the stop for the
straddling swing). Swings that end before the cutoff are dropped in bulk.

Parity guarantee: running the sim on the full vs. trimmed inputs must yield
identical ltf_trades (verified by tests/test_retention_parity.py).
"""
import copy


_IDX_KEYS = {"idx", "start_idx", "end_idx", "confirmed_at_idx", "fs_at_idx"}


def _reindex(obj, offset):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in _IDX_KEYS or (isinstance(k, str) and k.endswith("_idx")):
                if isinstance(v, bool):
                    out[k] = v
                elif isinstance(v, int):
                    out[k] = v - offset if v >= 0 else v
                else:
                    out[k] = _reindex(v, offset)
            elif isinstance(v, (dict, list)):
                out[k] = _reindex(v, offset)
            else:
                out[k] = v
        return out
    if isinstance(obj, list):
        return [_reindex(x, offset) for x in obj]
    return obj


def _seg(sw):
    return sw.get("seg") if isinstance(sw, dict) else None


def _end_idx(sw):
    seg = _seg(sw)
    if isinstance(seg, dict):
        ei = seg.get("end_idx", -1)
        if isinstance(ei, int):
            return ei
    return -1


def _start_idx(sw):
    seg = _seg(sw)
    if isinstance(seg, dict):
        si = seg.get("start_idx", None)
        if isinstance(si, int):
            return si
    return None


def trim_candles_and_swings(candles, swings, keep_days=90, min_keep=200):
    """Return (candles, swings, offset) trimmed to the trailing window.

    offset is the number of leading candles dropped (0 if nothing trimmed).
    Swings whose end_idx falls before the cutoff are dropped in bulk; the
    cutoff is pulled back to cover any retained swing that straddles it, so
    no retained swing ends up with a negative start_idx.
    """
    candles = [dict(c) for c in (candles or [])]
    swings = [copy.deepcopy(s) for s in (swings or [])]
    if not candles:
        return candles, swings, 0

    last_ts = candles[-1]["ts"]
    cutoff = last_ts - int(keep_days) * 86400

    offset = 0
    for i, c in enumerate(candles):
        if c["ts"] >= cutoff:
            offset = i
            break
    else:
        offset = len(candles)

    # Never trim below min_keep bars (keeps swing detection context).
    if offset > len(candles) - min_keep:
        offset = max(0, len(candles) - min_keep)
    if offset <= 0:
        return candles, swings, 0

    # Bulk swing boundary: pull offset back to cover any retained swing whose
    # start lies before the calendar cutoff (iterative fixpoint).
    changed = True
    while changed:
        changed = False
        new_offset = offset
        for sw in swings:
            ei = _end_idx(sw)
            # dropped under current offset -> skip
            if ei >= 0 and ei < offset:
                continue
            si = _start_idx(sw)
            if si is not None and si >= 0 and si < offset:
                if si < new_offset:
                    new_offset = si
                    changed = True
        if new_offset < offset:
            offset = max(0, new_offset)
            if offset <= 0:
                return candles, swings, 0

    new_candles = [dict(c) for c in candles[offset:]]
    new_swings = []
    for sw in swings:
        ei = _end_idx(sw)
        if ei >= 0 and ei < offset:
            continue
        new_swings.append(_reindex(sw, offset))

    # Safety net: drop any swing that still has a negative start_idx.
    cleaned = []
    for sw in new_swings:
        si = _start_idx(sw)
        if si is not None and si < 0:
            continue
        cleaned.append(sw)
    return new_candles, cleaned, offset
