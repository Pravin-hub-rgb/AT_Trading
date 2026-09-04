"""Shared exit logic for intraday engines — single source for filter guards.

Both engines need identical semantics so a filter tweak needs one edit:
  - 5min engine: backend/src/intraday.py (loops 5min, may delegate 1min chunk)
  - 1min engine: backend/src/intraday_1m_standalone.py (pure 1min loop)
  - 1min helper: backend/src/intraday_1m.py (manage_1m_chunk for 5min+1min hybrid)

Design: pure helpers, no I/O. Keep DEFAULT_CFG in intraday.py as canonical,
helpers read cfg dict via get_* helpers so alias `cost_to_cost_r` stays synced.
"""

from __future__ import annotations


def get_breakeven_r(cfg: dict) -> float:
    """Resolve breakeven R from cfg, honoring legacy alias."""
    # Explicit breakeven_r wins; else legacy cost_to_cost_r; else disabled (0)
    if "breakeven_r" in cfg and cfg["breakeven_r"] is not None:
        try:
            return float(cfg["breakeven_r"])
        except Exception:
            return 0.0
    if "cost_to_cost_r" in cfg and cfg["cost_to_cost_r"] is not None:
        try:
            return float(cfg["cost_to_cost_r"])
        except Exception:
            return 0.0
    return 0.0


def get_rr_target(cfg: dict) -> float:
    try:
        return float(cfg.get("rr_target", 3.0))
    except Exception:
        return 3.0


def is_breakeven_enabled(cfg: dict) -> bool:
    """Single filter guard — Off (0) must be disabled, not 0R instant C2C."""
    breakeven_r = get_breakeven_r(cfg)
    rr_target = get_rr_target(cfg)
    # Off or invalid → disabled
    if breakeven_r is None or breakeven_r <= 0:
        return False
    # Course rule: only when < target and target >=1:3 (1:2 target with 2R meaningless)
    if rr_target < 3.0:
        return False
    return breakeven_r < rr_target


def update_mfe_and_check_breakeven(
    trade_dir: str,
    entry: float,
    hi: float,
    lo: float,
    risk: float,
    mfe_r_prev: float,
    breakeven_r: float,
) -> tuple[float, bool]:
    """Update mfe_r and return (new_mfe_r, breakeven_hit).

    Call only when `is_breakeven_enabled(cfg)` is True and max_profit/mfe threshold already met
    by caller (1min chunk uses max_profit, 5min uses mfe_r). This helper centralizes
    side-specific math (long: (hi-entry)/risk, short: (entry-lo)/risk) and return-to-entry check.
    """
    risk = risk or 1e-9
    if trade_dir == "long":
        mfe_r = max(mfe_r_prev, (hi - entry) / risk)
        hit = mfe_r >= breakeven_r and lo <= entry
    else:
        mfe_r = max(mfe_r_prev, (entry - lo) / risk)
        hit = mfe_r >= breakeven_r and hi >= entry
    return mfe_r, hit


def should_ft_fail(trade: dict, cur_close: float, bar_idx: int) -> bool:
    """FT-fail gate: within 2 bars, close beyond dom beyond level."""
    if trade.get("validated"):
        return False
    if bar_idx > int(trade.get("validate_until", -1)):
        return False
    # cfg gate is checked by caller (ft_fail_enabled), this is pure price check
    if trade["dir"] == "long":
        return cur_close < float(trade["dom_low"])
    else:
        return cur_close > float(trade["dom_high"])


def track_mfe_only(trade_dir: str, entry: float, hi: float, lo: float, risk: float, mfe_r_prev: float) -> float:
    """When breakeven disabled, still track mfe for stats (no exit)."""
    risk = risk or 1e-9
    if trade_dir == "long":
        return max(mfe_r_prev, (hi - entry) / risk)
    else:
        return max(mfe_r_prev, (entry - lo) / risk)
