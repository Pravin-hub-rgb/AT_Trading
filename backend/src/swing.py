"""Swing high/low detection — port of the PineScript in docs/pinescript-swing-sr.md.

ta.pivothigh(high, n, n) / ta.pivotlow(low, n, n) are Williams fractals:
bar i is a swing high iff its high strictly exceeds all n bars on each side.
"""

from __future__ import annotations

import pandas as pd


def find_pivots(df: pd.DataFrame, n: int = 10) -> list[dict]:
    """Return all swing highs/lows in bar order.

    df must be sorted by timestamp with 'high'/'low'/'ts' columns.
    """
    n = max(1, int(n))
    highs = df["high"].to_numpy(dtype=float)
    lows = df["low"].to_numpy(dtype=float)
    ts = df["ts"].to_numpy()
    dates = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").to_numpy()
    date_only = df["timestamp"].dt.strftime("%Y-%m-%d").to_numpy()

    swings: list[dict] = []
    for i in range(n, len(df) - n):
        if highs[i] > highs[i - n : i].max() and highs[i] > highs[i + 1 : i + n + 1].max():
            swings.append(
                {
                    "kind": "high",
                    "index": i,
                    "ts": int(ts[i]),
                    "date": dates[i],
                    "date_only": date_only[i],
                    "price": float(highs[i]),
                }
            )
        if lows[i] < lows[i - n : i].min() and lows[i] < lows[i + 1 : i + n + 1].min():
            swings.append(
                {
                    "kind": "low",
                    "index": i,
                    "ts": int(ts[i]),
                    "date": dates[i],
                    "date_only": date_only[i],
                    "price": float(lows[i]),
                }
            )
    return swings


def select_sr_levels(swings: list[dict], num_levels: int = 5, lookahead: int = 50) -> list[dict]:
    """Keep the most recent num_levels highs and lows (like the Pine arrays).

    Returns extended-line specs from the swing bar to bar index+lookahead.
    """
    num_levels = max(1, int(num_levels))
    lookahead = max(1, int(lookahead))
    highs = [s for s in swings if s["kind"] == "high"]
    lows = [s for s in swings if s["kind"] == "low"]

    levels: list[dict] = []
    for arr in (highs, lows):
        for s in arr[-num_levels:]:
            levels.append(
                {
                    "kind": s["kind"],
                    "index": s["index"],
                    "price": s["price"],
                    "end_index": s["index"] + lookahead,
                }
            )
    return levels