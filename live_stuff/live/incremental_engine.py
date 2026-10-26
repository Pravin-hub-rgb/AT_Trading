"""Experimental O(window) incremental sim engine (parity-gated)."""
import copy

from .retention import trim_candles_and_swings


def _shift_swings(swings, offset):
    out = []
    for s in swings:
        s = copy.deepcopy(s)
        seg = s.get("seg") or {}
        si = seg.get("start_idx")
        ei = seg.get("end_idx")
        if ei is None or ei < offset:
            continue
        if si is not None:
            seg["start_idx"] = max(0, int(si) - offset)
        seg["end_idx"] = int(ei) - offset
        new_breaks = []
        for b in (s.get("breaks") or []):
            b = copy.deepcopy(b)
            if isinstance(b, dict):
                for k in ("idx", "bar", "i"):
                    if k in b and isinstance(b[k], int):
                        b[k] = max(0, b[k] - offset)
                new_breaks.append(b)
            else:
                new_breaks.append(b)
        s["breaks"] = new_breaks
        s["seg"] = seg
        out.append(s)
    return out


class IncrementalEngine:
    def __init__(self, v18, keep_days=90, window_bars=96 * 14):
        self.v18 = v18
        self.keep_days = keep_days
        self.window_bars = window_bars
        self._cache = None

    def _sig(self, c15, c1h, sw15, sw1h):
        def _br(swings):
            return sum(len(s.get("breaks", []) or []) for s in swings)
        return (len(c15), len(c1h), len(sw15), len(sw1h),
                c15[-1]["ts"] if c15 else 0, c1h[-1]["ts"] if c1h else 0,
                _br(sw15), _br(sw1h))

    def on_bar(self, all_candles_15m, all_candles_1h, all_swings_15m, all_swings_1h,
               open_swings=None, force=False):
        from _vendored.unified import simulate_htf_ltf_streak_halt

        c15 = list(all_candles_15m)
        c1h = list(all_candles_1h)
        sw15 = list(all_swings_15m)
        sw1h = list(all_swings_1h)
        if open_swings:
            o15 = open_swings.get("15m")
            if o15 and o15.get("breaks"):
                sw15 = sw15 + [copy.deepcopy(o15)]
            o1h = open_swings.get("1h")
            if o1h and o1h.get("breaks"):
                sw1h = sw1h + [copy.deepcopy(o1h)]

        sig = self._sig(c15, c1h, sw15, sw1h)
        c15t, sw15t, off15 = trim_candles_and_swings(c15, sw15, keep_days=self.keep_days)
        c1ht, sw1ht, off1h = trim_candles_and_swings(c1h, sw1h, keep_days=self.keep_days)

        if len(c15t) < 5 or len(c1ht) < 3:
            return None, False

        cache = self._cache
        use_tail = (not force and cache is not None and cache["sig"] != sig
                    and len(c15t) >= cache["len15"] and cache["len15"] > 0
                    and c15t[cache["len15"] - 1]["ts"] == cache["c15t"][cache["len15"] - 1]["ts"])

        if not use_tail:
            result = simulate_htf_ltf_streak_halt(c1ht, sw1ht, c15t, sw15t,
                                                 fine_ltf=[], **self.v18)
            self._cache = {"sig": sig, "result": result, "len15": len(c15t),
                           "c15t": c15t, "c1ht": c1ht, "sw15t": sw15t, "sw1ht": sw1ht}
            return result, True

        try:
            cache_res = cache["result"] or {}
            cache_trades = list(cache_res.get("ltf_trades", []))
            open_trades = [t for t in cache_trades if not t.get("exit_ts") and not t.get("exit_price")]
            if open_trades:
                min_entry = min(int(t.get("entry_ts", 0)) for t in open_trades)
                ws = 0
                for i, c in enumerate(c15t):
                    if int(c["ts"]) >= min_entry:
                        ws = i
                        break
            else:
                ws = max(0, len(c15t) - self.window_bars)
            ws = max(0, min(ws, len(c15t) - 1))
            if len(c15t) - ws < 10:
                ws = max(0, len(c15t) - self.window_bars)

            win_start_ts = int(c15t[ws]["ts"])
            prefix_closed = [t for t in cache_trades
                             if t.get("exit_ts") and int(t.get("exit_ts", 0)) < win_start_ts]

            w_c15 = c15t[ws:]
            hs = 0
            for i, c in enumerate(c1ht):
                if int(c["ts"]) + 3600 >= win_start_ts:
                    hs = max(0, i - 2)
                    break
            w_c1h = c1ht[hs:]
            w_sw15 = _shift_swings(sw15t, ws)
            w_sw1h = _shift_swings(sw1ht, hs)

            w_result = simulate_htf_ltf_streak_halt(w_c1h, w_sw1h, w_c15, w_sw15,
                                                  fine_ltf=[], **self.v18)
            w_trades = list(w_result.get("ltf_trades", []))

            seen = set()
            merged = []
            for t in prefix_closed + w_trades:
                key = int(t.get("entry_ts", 0))
                if key in seen:
                    continue
                seen.add(key)
                merged.append(t)
            for t in open_trades:
                key = int(t.get("entry_ts", 0))
                if key not in seen and not t.get("exit_ts"):
                    seen.add(key)
                    merged.append(copy.deepcopy(t))

            result = dict(w_result)
            result["ltf_trades"] = merged
            self._cache = {"sig": sig, "result": result, "len15": len(c15t),
                           "c15t": c15t, "c1ht": c1ht, "sw15t": sw15t, "sw1ht": sw1ht}
            return result, True
        except Exception:
            result = simulate_htf_ltf_streak_halt(c1ht, sw1ht, c15t, sw15t,
                                                 fine_ltf=[], **self.v18)
            self._cache = {"sig": sig, "result": result, "len15": len(c15t),
                           "c15t": c15t, "c1ht": c1ht, "sw15t": sw15t, "sw1ht": sw1ht}
            return result, True