"""Monthly/quarterly bucketing (CSV-local calendar) + Pearson correlation.

Both books (stat-arb and the v18 champion baseline) bucket by the calendar
month of the EXIT in the CSV-local clock - the same clock the exit_date
strings use - so the two series line up without timezone conversions.
"""
from __future__ import annotations

import math


def month_key(dt):
    return "%04d-%02d" % (dt.year, dt.month)


def quarter_key(dt):
    return "%04dQ%d" % (dt.year, (dt.month - 1) // 3 + 1)


def month_range(start_dt, end_dt):
    out = []
    y, m = start_dt.year, start_dt.month
    while (y, m) <= (end_dt.year, end_dt.month):
        out.append("%04d-%02d" % (y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def pearson(a, b):
    if len(a) != len(b) or len(a) < 3:
        return None
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 1e-18 or vb <= 1e-18:
        return None
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return cov / math.sqrt(va * vb)
