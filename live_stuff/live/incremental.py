"""Incremental sim driver (Step C scaffolding)."""
from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .retention import trim_candles_and_swings


@dataclass
class SimState:
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
    last_trades: List[Dict[str, Any]] = field(default_factory=list)
    last_result: Optional[Dict[str, Any]] = None


class IncrementalSim:
    def __init__(self, v18_params: Dict[str, Any], keep_days: int = 90):
        self.v18 = dict(v18_params)
        self.keep_days = int(keep_days)
        self.state = SimState()
        self._last_input_sig = None
        self._last_structural_sig = None
        self._cached_kwargs = None
        self._cached_state = None

    def _signature(self, c15, c1h, sw15, sw1h):
        def _breaks(swings):
            return sum(len(s.get("breaks", []) or []) for s in swings)
        return (len(c15), len(c1h), len(sw15), len(sw1h),
                c15[-1]["ts"] if c15 else 0, c1h[-1]["ts"] if c1h else 0,
                _breaks(sw15), _breaks(sw1h))

    def _structural_signature(self, c15, c1h, sw15, sw1h):
        def _breaks(swings):
            return sum(len(s.get("breaks", []) or []) for s in swings)
        return (len(c1h), c1h[-1]["ts"] if c1h else 0,
                len(sw15), len(sw1h),
                _breaks(sw15), _breaks(sw1h))

    def on_bar(self, all_candles_15m, all_candles_1h, all_swings_15m, all_swings_1h,
               open_swings=None, force=False):
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
        non_structural = (not force) and (struct_sig == self._last_structural_sig)

        c15t, sw15t, _ = trim_candles_and_swings(c15, sw15, keep_days=self.keep_days)
        c1ht, sw1ht, _ = trim_candles_and_swings(c1h, sw1h, keep_days=self.keep_days)

        if len(c15t) < 5 or len(c1ht) < 3:
            self._last_input_sig = sig
            self._last_structural_sig = struct_sig
            return None, False

        if (non_structural and self._cached_kwargs is not None
                and self._cached_state is not None):
            try:
                # Safety: if previous last bar carried a filtered HTF signal,
                # that signal may become an allowed entry now -> full recompute.
                try:
                    from _vendored.btc_engine import CandleStore as _CS
                except Exception:
                    from btc_engine import CandleStore as _CS
                _prev_n = self._cached_state.get("processed_n", 0)
                _filtered = self._cached_kwargs.get("filtered", []) or []
                _candles_prev = self._cached_kwargs.get("candles_ltf", [])
                _store = _CS(_candles_prev) if _candles_prev else None
                _pending = False
                if _store is not None and isinstance(_prev_n, int) and _prev_n > 0:
                    for _sig in _filtered:
                        try:
                            _s = _sig[0] if isinstance(_sig, (tuple, list)) else _sig
                            _i = _store.pos(_s["bar"])
                        except Exception:
                            _i = -1
                        if _i == _prev_n - 1:
                            _pending = True
                            break
                if _pending:
                    raise RuntimeError("pending boundary entry")
                from live.ltf_walk import run_ltf_walk
                kw = copy.deepcopy(self._cached_kwargs)
                kw["candles_ltf"] = [dict(x) for x in c15t]
                kw["candle_ts_ltf"] = [int(x["ts"]) for x in c15t]
                kw["candle_ts_htf"] = [int(x["ts"]) for x in c1ht]
                kw["swings_ltf"] = copy.deepcopy(sw15t)
                state_in = copy.deepcopy(self._cached_state)
                result = run_ltf_walk(**kw, state=state_in)
                if not isinstance(result, dict) or result.get("error"):
                    raise RuntimeError((result or {}).get("error", "incr failed"))
                new_trades = list(result.get("ltf_trades", []))
                old_trades = list((self.state.last_result or {}).get("ltf_trades", []))
                changed = (new_trades != old_trades)
                self.state.last_result = result
                self.state.last_trades = new_trades
                self._cached_state = result.get("_state", state_in)
                self._cached_kwargs = result.get("_ltf_kwargs", kw)
                if c15t:
                    self.state.last_processed_ts_15m = int(c15t[-1]["ts"])
                if c1ht:
                    self.state.last_processed_ts_1h = int(c1ht[-1]["ts"])
                self._last_input_sig = sig
                self._last_structural_sig = struct_sig
                return result, changed
            except Exception:
                pass

        from _vendored.unified import simulate_htf_ltf_streak_halt
        try:
            result = simulate_htf_ltf_streak_halt(c1ht, sw1ht, c15t, sw15t,
                                                fine_ltf=[], **self.v18)
        except Exception as e:
            result = {"error": str(e), "ltf_trades": []}

        self.state.last_result = result
        self.state.last_trades = list((result or {}).get("ltf_trades", []))
        self._cached_kwargs = (result or {}).get("_ltf_kwargs")
        self._cached_state = (result or {}).get("_state")
        if c15t:
            self.state.last_processed_ts_15m = int(c15t[-1]["ts"])
        if c1ht:
            self.state.last_processed_ts_1h = int(c1ht[-1]["ts"])
        self._last_input_sig = sig
        self._last_structural_sig = struct_sig
        return result, True

    def idempotency_key(self):
        return self.state.last_processed_ts_15m
