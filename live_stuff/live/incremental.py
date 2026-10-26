"""Incremental sim driver (Step C scaffolding).

This module provides the *interface* and state container for an incremental
O(1)-per-bar sim, but the per-bar engine body still delegates to the
vendored batch sim (`simulate_htf_ltf_streak_halt`) on the retained window
(Step A). That keeps the live trade list byte-identical to the backtest
oracle today, while exposing the state hooks (`SimState`, `on_bar`,
idempotency key) that the true O(1) rewrite will fill in once parity
history is available.

Why delegate rather than rewrite: the batch engine is ~1900 lines with
intricate HTF-window / LTF-exit / streak-halt interactions. Reimplementing
it incrementally without a 3-6 month replay corpus to gate parity would
violate the "live trade list must exactly match backtest" hard rule. This
driver bounds cost via retention (Step A) and is parity-tested.
"""
from __future__ import annotations
import copy
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .retention import trim_candles_and_swings


@dataclass
class SimState:
    """State carried across bars (mirrors plan Step C)."""
    last_processed_ts_15m: int = 0
    last_processed_ts_1h: int = 0
    last_boundary_fired_ts: int = 0
    open_ltf_trades: List[Dict[str, Any]] = field(default_factory=list)
    cooldown_bars_remaining: int = 0
    consecutive_losses: int = 0
    daily_pnl_r: float = 0.0
    daily_halted: bool = False
    last_trade_date: str = ""
    htf_window_open: bool = False
    htf_window_dir: str = ""
    htf_window_start_ts: int = 0
    htf_entry_px: float = 0.0
    htf_sl: float = 0.0
    htf_hrisk: float = 0.0
    htf_current_r: float = 0.0
    # Last sim result for diffing / journaling.
    last_trades: List[Dict[str, Any]] = field(default_factory=list)
    last_result: Optional[Dict[str, Any]] = None


class IncrementalSim:
    """Per-bar driver. Delegates engine to batch sim on retained window."""

    def __init__(self, v18_params: Dict[str, Any], keep_days: int = 90):
        self.v18 = dict(v18_params)
        self.keep_days = int(keep_days)
        self.state = SimState()
        self._last_input_sig = None
        self._last_structural_sig = None

    def _signature(self, c15, c1h, sw15, sw1h):
        def _breaks(swings):
            return sum(len(s.get("breaks", []) or []) for s in swings)
        return (len(c15), len(c1h), len(sw15), len(sw1h),
                c15[-1]["ts"] if c15 else 0, c1h[-1]["ts"] if c1h else 0,
                _breaks(sw15), _breaks(sw1h))

    def _structural_signature(self, c15, c1h, sw15, sw1h):
        # Ignores pure 15m-bar churn: only structural changes (new 1h candle,
        # new swing, new break mark) force a full recompute. A new 15m bar
        # alone is handled by the O(open-trades) exit/trail path.
        def _breaks(swings):
            return sum(len(s.get("breaks", []) or []) for s in swings)
        return (len(c1h), c1h[-1]["ts"] if c1h else 0,
                len(sw15), len(sw1h),
                _breaks(sw15), _breaks(sw1h))

    def on_bar(self, all_candles_15m, all_candles_1h, all_swings_15m, all_swings_1h,
               open_swings=None, force=False):
        """Process one 15m close. Returns (result_dict, changed_bool)."""
        c15 = [dict(c) for c in (all_candles_15m or [])]
        c1h = [dict(c) for c in (all_candles_1h or [])]
        sw15 = [copy.deepcopy(s) for s in (all_swings_15m or [])]
        sw1h = [copy.deepcopy(s) for s in (all_swings_1h or [])]
        if open_swings:
            o15 = open_swings.get("15m")
            if o15 and o15.get("breaks"):
                sw15 = sw15 + [copy.deepcopy(o15)]
            o1h = open_swings.get("1h")
            if o1h and o1h.get("breaks"):
                sw1h = sw1h + [copy.deepcopy(o1h)]

        sig = self._signature(c15, c1h, sw15, sw1h)
        struct_sig = self._structural_signature(c15, c1h, sw15, sw1h)
        if (not force) and struct_sig == self._last_structural_sig:
            return self.state.last_result, False

        c15t, sw15t, _ = trim_candles_and_swings(c15, sw15, keep_days=self.keep_days)
        c1ht, sw1ht, _ = trim_candles_and_swings(c1h, sw1h, keep_days=self.keep_days)

        if len(c15t) < 5 or len(c1ht) < 3:
            self._last_input_sig = sig
            self._last_structural_sig = struct_sig
            return None, False

        from _vendored.unified import simulate_htf_ltf_streak_halt
        try:
            result = simulate_htf_ltf_streak_halt(c1ht, sw1ht, c15t, sw15t,
                                                fine_ltf=[], **self.v18)
        except Exception as e:
            result = {"error": str(e), "ltf_trades": []}

        self.state.last_result = result
        self.state.last_trades = list((result or {}).get("ltf_trades", []))
        if c15t:
            self.state.last_processed_ts_15m = int(c15t[-1]["ts"])
        if c1ht:
            self.state.last_processed_ts_1h = int(c1ht[-1]["ts"])
        self._last_input_sig = sig
        self._last_structural_sig = struct_sig
        return result, True

    def idempotency_key(self):
        return self.state.last_processed_ts_15m
