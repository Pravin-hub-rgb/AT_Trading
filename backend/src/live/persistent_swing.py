"""Persistent SwingEngine - maintains state across restarts.

Parity with compute_btc_swings (btc_swing.py):
  After a swing declares, backtest starts the NEXT engine at end_idx+1 and
  RE-FEEDS every bar through the declaration bar (and beyond). Live used to
  jump to declaration_bar+1 and skip that range — chains diverged after swing 1.
  This wrapper buffers candles and replays end_idx+1..current through the new
  engine so the live chain matches the backtest stitch exactly.
"""

from __future__ import annotations
import json
from typing import Optional

from src.firstswing import SwingEngine
from src.walker import FlowCandle


class PersistentSwingEngine:
    """SwingEngine wrapper with state persistence + backtest-identical stitching."""

    def __init__(self, tf: str, db=None, opts: Optional[dict] = None):
        self.tf = tf
        self.db = db
        self.opts = opts or {"minBars": 50}
        # BTC 24/7: match compute_btc_swings which forces timeCap="00:00"
        if isinstance(self.opts, dict) and "timeCap" not in self.opts:
            self.opts = {**self.opts, "timeCap": "00:00"}
        self.eng = SwingEngine(self.opts)
        self.swing_index = 0
        self.next_start_pos = 0
        self.ts_map: dict[int, str] = {}
        self._candles: dict[int, FlowCandle] = {}
        self._pending: list[dict] = []
        self._pos: int = 0  # next bar index to feed the current engine
        self._load_state()

    def _state_key(self) -> str:
        return f"swing_state_{self.tf}"

    def _load_state(self):
        if not self.db:
            return
        try:
            row = self.db.conn.execute(
                "SELECT value FROM meta WHERE key = ?",
                (self._state_key(),)
            ).fetchone()
            if row:
                state = json.loads(row["value"])
                self.swing_index = state.get("swing_index", 0)
                self.next_start_pos = state.get("next_start_pos", 0)
                self._pos = state.get("_pos", self.next_start_pos)
                self._pending = state.get("_pending", []) or []
                e = self.eng
                e.dir = state.get("dir")
                e.armed = state.get("armed", False)
                e.declared = state.get("declared", False)
                e.start_idx = state.get("start_idx", -1)
                e.start_px = state.get("start_px", float("nan"))
                e.end_idx = state.get("end_idx", -1)
                e.end_px = state.get("end_px", float("nan"))
                e.confirmed_at_idx = state.get("confirmed_at_idx", -1)
                e.state = state.get("state", "watch")
                e.bars_seen = state.get("bars_seen", 0)
                e.defer_same_bar_arm = state.get("defer_same_bar_arm", False)
                e._pending_arm = state.get("_pending_arm", False)
                raw_marks = state.get("break_marks", [])
                try:
                    from src.firstswing import FsBreakMark as _FBM
                    restored = []
                    for m in raw_marks:
                        if isinstance(m, dict):
                            restored.append(_FBM(idx=int(m["idx"]), time=str(m["time"]), kind=m["kind"], dir=m["dir"], px=float(m["px"])))
                        else:
                            restored.append(m)
                    e.break_marks = restored
                except Exception:
                    e.break_marks = raw_marks if isinstance(raw_marks, list) else []
                e.seed_idx = state.get("seed_idx", -1)
                print(f"[swing] {self.tf}: restored (swing_index={self.swing_index}, armed={e.armed}, dir={e.dir})")
        except Exception as e:
            print(f"[swing] {self.tf}: load failed: {e}")

    def _save_state(self):
        if not self.db:
            return
        try:
            e = self.eng
            ser_marks = []
            for m in (e.break_marks or []):
                try:
                    ser_marks.append({"idx": int(m.idx), "time": str(m.time), "kind": str(m.kind), "dir": str(m.dir), "px": float(m.px)})
                except Exception:
                    if isinstance(m, dict):
                        ser_marks.append(m)
            state = {
                "swing_index": self.swing_index,
                "next_start_pos": self._pos,
                "_pos": self._pos,
                "_pending": self._pending,
                "dir": e.dir,
                "armed": e.armed,
                "declared": e.declared,
                "start_idx": e.start_idx,
                "start_px": e.start_px,
                "end_idx": e.end_idx,
                "end_px": e.end_px,
                "confirmed_at_idx": e.confirmed_at_idx,
                "state": e.state,
                "bars_seen": e.bars_seen,
                "defer_same_bar_arm": e.defer_same_bar_arm,
                "_pending_arm": e._pending_arm,
                "break_marks": ser_marks,
                "seed_idx": e.seed_idx,
            }
            with self.db.transaction() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (self._state_key(), json.dumps(state))
                )
        except Exception as e:
            print(f"[swing] {self.tf}: save failed: {e}")

    def _build_result(self) -> dict:
        eng = self.eng
        src_kind = "SUS" if eng.confirm_source == "sustain" else "FS"
        decisive = eng.break_marks[-1] if eng.break_marks else None
        bk = decisive.kind if decisive else None
        # Mirror compute_btc_swings fs_at marker (chop cross may move the marker)
        fs_at_idx = eng.confirmed_at_idx
        fs_at_time = eng.confirmed_at_time
        if (
            eng.confirm_source == "chop"
            and eng.last_chop_cross_idx >= 0
            and eng.last_chop_cross_idx >= eng.end_idx
        ):
            fs_at_idx = eng.last_chop_cross_idx
            if eng.ts_map:
                fs_at_time = eng.ts_map.get(fs_at_idx, fs_at_time)
            elif 0 <= fs_at_idx:
                fs_at_time = str(fs_at_time)

        result = {
            "swing_index": self.swing_index,
            "seg": {
                "dir": "B" if eng.dir == "up" else "S",
                "start_idx": eng.start_idx,
                "start_time": eng.start_time,
                "start_px": eng.start_px,
                "end_idx": eng.end_idx,
                "end_px": eng.end_px,
                "end_time": eng.end_time,
            },
            "source": eng.confirm_source,
            "dir": eng.dir,
            "kind": src_kind,
            "break_kind": bk,
            "breaks": [
                {
                    "idx": b.idx,
                    "time": b.time,
                    "kind": b.kind,
                    "dir": b.dir,
                    "px": b.px,
                    "swing_no": self.swing_index,
                }
                for b in eng.break_marks
            ],
            "confirmed_at_idx": eng.confirmed_at_idx,
            "confirmed_at_time": eng.confirmed_at_time,
            "fs_at_idx": fs_at_idx,
            "fs_at_time": fs_at_time,
        }
        return result

    def _new_engine(self, first: bool = False) -> None:
        old_ts_map = self.eng.ts_map.copy()
        self.eng = SwingEngine(self.opts)
        # First swing: no defer (matches compute_btc_swings swing_index==0)
        self.eng.defer_same_bar_arm = not first
        self.eng.ts_map = old_ts_map

    def process_bar(self, candle: FlowCandle, g_idx: int) -> Optional[dict]:
        """Process a single bar. Returns swing dict if a swing completed.

        Multiple swings may complete while catching up after a declaration;
        extras are queued and returned on subsequent calls (same order as
        compute_btc_swings would emit them).
        """
        self._candles[g_idx] = candle
        self.ts_map[g_idx] = candle.date
        # Prune candle buffer far behind the feed cursor (memory bound)
        if g_idx > self._pos + 4096:
            cut = self._pos - 64
            for k in [k for k in self._candles if k < cut]:
                del self._candles[k]

        # Feed from _pos through g_idx — same cursor rule as compute_btc_swings.
        # Always advance first so queued emissions never starve the bar feed.
        while self._pos <= g_idx:
            if self.eng.declared:
                break
            c = self._candles.get(self._pos)
            if c is None:
                self._pos += 1
                continue

            self.eng.process_bar(c, self._pos)

            if not self.eng.declared or self.eng.start_idx < 0:
                self._pos += 1
                continue

            # Swing declared at self._pos
            result = self._build_result()
            self.swing_index += 1

            # Backtest stitch: next engine starts at end_idx+1 (may rewind)
            if self.eng.end_idx >= 0:
                new_start = self.eng.end_idx + 1
            else:
                new_start = self._pos + 1
            self.next_start_pos = new_start
            self._new_engine(first=False)
            self._pos = new_start
            self._pending.append(result)
            # Loop continues: re-feeds new_start..g_idx (and beyond as received)

        if self._pending:
            out = self._pending.pop(0)
            self._save_state()
            return out
        self._save_state()
        return None

    def get_open_swing(self) -> Optional[dict]:
        """Get the current open swing (not yet declared) for state continuity."""
        e = self.eng
        if not e.dir:
            return None
        return {
            "swing_index": self.swing_index,
            "seg": {
                "dir": "B" if e.dir == "up" else "S",
                "start_idx": e.start_idx if e.start_idx >= 0 else None,
                "start_time": e.start_time if e.start_idx >= 0 else None,
                "start_px": e.start_px if e.start_idx >= 0 else None,
                "end_idx": None,
                "end_px": None,
            },
            "source": None,
            "dir": e.dir,
            "kind": None,
            "break_kind": None,
            "breaks": [
                {
                    "idx": b.idx,
                    "time": b.time,
                    "kind": b.kind,
                    "dir": b.dir,
                    "px": b.px,
                    "swing_no": self.swing_index,
                }
                for b in e.break_marks
            ],
            "confirmed_at_idx": -1,
            "confirmed_at_time": None,
            "_open": True,
        }
