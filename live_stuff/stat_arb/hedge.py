"""Rolling hedge estimators: OLS beta on log prices and 3-asset PCA PC1.

All estimators are causal: bar t uses closed bars [t-w+1, t] only. Implemented
with prefix sums so every bar is O(1); pure python, no numpy.

OLS arm:  beta_t = Cov(logBTC, logETH) / Var(logETH) over the window;
          hedge vector h = (1, -beta_t); spread S is the regression residual
          (window intercept included, see ols_residual) so S is the
          cointegration deviation, not the raw level difference.
PCA arm:  covariance matrix of the 3 log-price columns over the window,
          PC1 via power iteration (deterministic, 60 iters, fixed start);
          loadings sign-fixed so the BTC component is positive;
          spread S = h . (logP - window_means) with h = PC1 loading vector;
          explained = lambda1 / trace (entry gate >= 0.70).
Hedge vector convention: h[0] (BTC) > 0; leg dollars = dir * 10000 * h_i / h_0
so the BTC leg is always dir * $10k.
"""
from __future__ import annotations

import math

NAN = float("nan")


def _psum(xs):
    ps = [0.0]
    for x in xs:
        ps.append(ps[-1] + x)
    return ps


def _win(ps, a, b):
    return ps[b + 1] - ps[a]


def _nan(n):
    return [NAN] * n


def rolling_ols_beta(x, y, w):
    n = len(x)
    px, py = _psum(x), _psum(y)
    pxy = _psum([a * b for a, b in zip(x, y)])
    pyy = _psum([v * v for v in y])
    out = _nan(n)
    for t in range(w - 1, n):
        a = t - w + 1
        sy = _win(py, a, t)
        den = _win(pyy, a, t) - sy * sy / w
        if abs(den) < 1e-18:
            continue
        num = _win(pxy, a, t) - _win(px, a, t) * sy / w
        out[t] = num / den
    return out


def ols_spread(x, y, w):
    beta = rolling_ols_beta(x, y, w)
    sp = _nan(len(x))
    for t, b in enumerate(beta):
        if b == b:
            sp[t] = x[t] - b * y[t]
    return beta, sp


def rolling_demean(x, w):
    """Window mean of x over [t-w+1, t] (NaN for t < w-1)."""
    n = len(x)
    px = _psum(x)
    out = _nan(n)
    for t in range(w - 1, n):
        a = t - w + 1
        out[t] = _win(px, a, t) / w
    return out


def ols_residual(lb, le, w):
    """Cointegration residual: S_t = (lb_t - mean_lb_w) - beta_t*(le_t - mean_le_w).

    This is the OLS regression residual with the window intercept included
    (alpha_hat = mean_lb - beta*mean_le). Using raw lb - beta*le without the
    intercept makes S follow the wandering alpha -> window sigma is inflated
    by the intercept walk and z decouples from actual leg P&L.
    Returns (beta, spread); spread is NaN for t < w-1.
    """
    beta = rolling_ols_beta(lb, le, w)
    mlb, mle = rolling_demean(lb, w), rolling_demean(le, w)
    n = len(lb)
    sp = _nan(n)
    for t in range(w - 1, n):
        if beta[t] == beta[t]:
            sp[t] = (lb[t] - mlb[t]) - beta[t] * (le[t] - mle[t])
    return beta, sp


def rolling_pca(xs, w):
    """xs: 3 series of log prices. Returns (hvecs, spread, explained)."""
    n = len(xs[0])
    ps = [_psum(v) for v in xs]
    p2 = [_psum([v * v for v in s]) for s in xs]
    pair_idx = ((0, 1), (0, 2), (1, 2))
    pab = {ij: _psum([xs[ij[0]][k] * xs[ij[1]][k] for k in range(n)]) for ij in pair_idx}
    hvecs, spread, explained = _nan(n), _nan(n), _nan(n)
    for t in range(w - 1, n):
        a = t - w + 1
        m = [_win(ps[i], a, t) / w for i in range(3)]
        cov = [[0.0] * 3 for _ in range(3)]
        for i in range(3):
            cov[i][i] = _win(p2[i], a, t) / w - m[i] * m[i]
        for i, j in pair_idx:
            c = _win(pab[(i, j)], a, t) / w - m[i] * m[j]
            cov[i][j] = cov[j][i] = c
        trace = cov[0][0] + cov[1][1] + cov[2][2]
        if trace <= 1e-18:
            continue
        v = [1.0, 1.0, 1.0]
        v = [c / math.sqrt(3.0) for c in v]
        for _ in range(60):
            u = [
                cov[0][0] * v[0] + cov[0][1] * v[1] + cov[0][2] * v[2],
                cov[1][0] * v[0] + cov[1][1] * v[1] + cov[1][2] * v[2],
                cov[2][0] * v[0] + cov[2][1] * v[1] + cov[2][2] * v[2],
            ]
            nv = math.sqrt(u[0] * u[0] + u[1] * u[1] + u[2] * u[2])
            if nv < 1e-15:
                break
            v = [c / nv for c in u]
        lam = sum(v[i] * sum(cov[i][j] * v[j] for j in range(3)) for i in range(3))
        if v[0] < 0:
            v = [-c for c in v]
        hvecs[t] = tuple(v)
        spread[t] = sum(v[i] * (xs[i][t] - m[i]) for i in range(3))
        explained[t] = lam / trace if trace > 0 else NAN
    return hvecs, spread, explained
