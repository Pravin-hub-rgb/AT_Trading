"""Z-signal construction and the pre-registered spread backtest loop.

Conventions (binding, see exp_stat_arb docstring):
- z_t = (S_t - rolling_mean) / rolling_std over the hedge window, ddof=0,
  closed bars [t-w+1, t]; NaN until warmup or zero variance.
- Decisions on close t; fills at close t+1 (both legs, log closes).
- Stop checked before target on the same bar; max hold = 168 bars from entry
  fill to exit fill (forced at entry_bar + 168).
- Cooldown: entry fill must be > 24 bars after the previous exit fill.
- Entry only inside a registered results window (checked at the FILL bar);
  gates (half-life, PC1, hedge finite) evaluated at the SIGNAL bar.
- One position, no overlap, no same-bar flip.
"""
from __future__ import annotations

import math

NAN = float("nan")
HL_MIN_BARS = 24
HL_MAX_BARS = 288
COOLDOWN_BARS = 24
MAX_HOLD = 168


def _psum(xs):
    ps = [0.0]
    for x in xs:
        ps.append(ps[-1] + x)
    return ps


def _win(ps, a, b):
    return ps[b + 1] - ps[a]


def rolling_z(s, w):
    n = len(s)
    z, sd = [NAN] * n, [NAN] * n
    f = 0
    while f < n and not (s[f] == s[f]):
        f += 1
    if f >= n:
        return z, sd
    xs = s[f:]
    ps, p2 = _psum(xs), _psum([v * v for v in xs])
    for t in range(f + w - 1, n):
        a, b = t - w + 1 - f, t - f
        m = _win(ps, a, b) / w
        var = _win(p2, a, b) / w - m * m
        sd_t = math.sqrt(var) if var > 0.0 else 0.0
        sd[t] = sd_t
        z[t] = (s[t] - m) / sd_t if sd_t > 1e-12 else NAN
    return z, sd


def hl_gate(hl):
    return [
        (h == h) and h >= HL_MIN_BARS and h <= HL_MAX_BARS
        for h in hl
    ]


def run_backtest(ts, logs, z, sd, hvecs, hl_ok, pc_ok, band, windows,
                 cooldown=COOLDOWN_BARS, maxhold=MAX_HOLD):
    entry_z, exit_z, stop_z = band
    n = len(ts)
    trades = []
    pos = None
    pending_exit = None
    pending_enter = None
    last_exit = -(10 ** 9)

    def window_of(t):
        tdt = ts[t]
        for wstart, wend, era in windows:
            if wstart <= tdt < wend:
                return era
        return None

    for t in range(n):
        if pending_exit is not None and pos is not None:
            pos["exit_bar"] = t
            pos["exit_reason"] = pending_exit
            trades.append(pos)
            pos = None
            pending_exit = None
            last_exit = t

        if pos is not None and (t - pos["entry_bar"]) >= maxhold:
            pos["exit_bar"] = t
            pos["exit_reason"] = "maxhold"
            trades.append(pos)
            pos = None
            last_exit = t

        if pending_enter is not None and pos is None:
            era = window_of(t)
            if era is None or (t - last_exit) <= cooldown:
                pending_enter = None
            else:
                ent = dict(pending_enter)
                ent["entry_bar"] = t
                ent["era"] = era
                ent["log_entry"] = [lg[t] for lg in logs]
                pos = ent
                pending_enter = None

        zt = z[t]
        zfin = zt == zt

        if pos is not None:
            if zfin:
                if (pos["dir"] == 1 and zt <= -stop_z) or (pos["dir"] == -1 and zt >= stop_z):
                    pending_exit = "stop"
                elif (pos["dir"] == 1 and zt >= -exit_z) or (pos["dir"] == -1 and zt <= exit_z):
                    pending_exit = "target"
            continue

        if pending_enter is None and zfin and hl_ok[t] and pc_ok[t]:
            h = hvecs[t]
            if h is not None and h[0] >= 0.1 and sd[t] == sd[t] and t + 1 <= n - 1:
                if zt >= entry_z:
                    d = -1
                elif zt <= -entry_z:
                    d = 1
                else:
                    d = 0
                if d != 0:
                    pending_enter = {
                        "signal_bar": t, "dir": d, "h": tuple(h),
                        "sigma": sd[t], "entry_z_param": entry_z,
                        "stop_z": stop_z, "z_actual": zt,
                    }

    if pos is not None:
        last = n - 1
        if last > pos["entry_bar"]:
            pos["exit_bar"] = last
            pos["exit_reason"] = "eod"
            trades.append(pos)
        else:
            pos["exit_bar"] = last
            pos["exit_reason"] = "eod0"
            trades.append(pos)
    return trades
