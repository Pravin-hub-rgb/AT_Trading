"""Rolling Ornstein-Uhlenbeck half-life on the spread series.

At bar t (closed bars only): regress dS_j = S_j - S_{j-1} on S_{j-1} over the
last w observations (j in [t-w+1, t]). Slope b < 0 means mean reversion;
half-life = ln(2) / (-b) in bars, inf otherwise. OU window is fixed at 288
bars (72h) per the pre-registered construction (hedge/z windows follow the
arm, OU does not). Prefix sums keep every bar O(1).
"""
from __future__ import annotations

import math

OU_WINDOW = 288
NAN = float("nan")


def _psum(xs):
    ps = [0.0]
    for x in xs:
        ps.append(ps[-1] + x)
    return ps


def _win(ps, a, b):
    return ps[b + 1] - ps[a]


def half_life(s, w=OU_WINDOW):
    """Half-life in bars for each bar t (NaN until enough finite obs)."""
    n = len(s)
    out = [NAN] * n
    f = 0
    while f < n and not (s[f] == s[f]):
        f += 1
    if f >= n - 1:
        return out
    # observation j (needs s[j-1], s[j] finite) is valid for j >= f+1
    xs, ds, prod, sq = [], [], [], []
    for j in range(f + 1, n):
        x = s[j - 1]
        d = s[j] - s[j - 1]
        xs.append(x)
        ds.append(d)
        prod.append(x * d)
        sq.append(x * x)
    px, pd = _psum(xs), _psum(ds)
    pxd, pxx = _psum(prod), _psum(sq)
    off = f + 1
    for t in range(f + w, n):
        a, b = t - w + 1 - off, t - off
        sx, sy = _win(px, a, b), _win(pd, a, b)
        cov = _win(pxd, a, b) - sx * sy / w
        var = _win(pxx, a, b) - sx * sx / w
        if abs(var) < 1e-18:
            continue
        slope = cov / var
        out[t] = math.log(2.0) / (-slope) if slope < -1e-12 else math.inf
    return out
