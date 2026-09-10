"""Live mark detector — detects B1/B2/FLIP in real-time."""

from __future__ import annotations
import json
import time
from typing import Optional

from src.walker import FlowCandle


class LiveMarkDetector:
    """Detects B1/B2/FLIP marks in real-time as price breaks structure."""

    def __init__(self, tf: str, db=None):
        self.tf = tf
        self.db = db
        self.swing_index = 0
        self.dir: Optional[str] = None
        self.extreme: float = 0.0
        self.anchor: float = 0.0
        self.start_idx: int = 0
        self.last_mark: Optional[dict] = None
        self.has_b1 = False  # Track if current swing has had its B1
        self.bars_in_swing = 0  # Count bars in current swing (first bar can't have mark)
        self._load_state()

    def _state_key(self) -> str:
        return f"live_mark_state_{self.tf}"

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
                self.dir = state.get("dir")
                self.extreme = state.get("extreme", 0.0)
                self.anchor = state.get("anchor", 0.0)
                self.start_idx = state.get("start_idx", 0)
                self.has_b1 = state.get("has_b1", False)
                self.bars_in_swing = state.get("bars_in_swing", 0)
                print(f"[mark] {self.tf}: restored (swing_index={self.swing_index}, dir={self.dir})")
        except Exception as e:
            print(f"[mark] {self.tf}: load failed: {e}")

    def _save_state(self):
        if not self.db:
            return
        try:
            state = {
                "swing_index": self.swing_index,
                "dir": self.dir,
                "extreme": self.extreme,
                "anchor": self.anchor,
                "start_idx": self.start_idx,
                "has_b1": self.has_b1,
                "bars_in_swing": self.bars_in_swing,
                "updated_at": int(time.time()),
            }
            with self.db.transaction() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
                    (self._state_key(), json.dumps(state))
                )
        except Exception as e:
            print(f"[mark] {self.tf}: save failed: {e}")

    def align_from_backtest(self, swings: list[dict], candles: list[dict]):
        """Align detector state from backtest results."""
        if not swings or not candles:
            return
        for s in reversed(swings):
            if s.get("break_kind") and s.get("confirmed_at_idx", -1) >= 0:
                self.swing_index = s["swing_index"]
                self.dir = s["dir"]
                self.start_idx = s["seg"]["start_idx"]
                self.anchor = s["seg"]["start_px"]
                self.extreme = s["seg"]["end_px"]
                if s.get("breaks"):
                    self.last_mark = s["breaks"][-1]
                print(f"[mark] {self.tf}: aligned to sw{self.swing_index} ({self.dir})")
                break
        # Flip direction for the next swing (new swing has no B1 yet)
        if self.dir:
            self.swing_index += 1
            self.dir = "down" if self.dir == "up" else "up"
            self.anchor = self.extreme
            self.start_idx = swings[-1].get("seg", {}).get("end_idx", len(candles) - 1) + 1
            self.extreme = self.anchor
            self.has_b1 = False
            self.bars_in_swing = 0  # Will be set to 1 on first bar
            print(f"[mark] {self.tf}: next swing sw{self.swing_index} ({self.dir}) from idx {self.start_idx}")
        self._save_state()

    def process_bar(self, candle: FlowCandle, g_idx: int) -> Optional[dict]:
        """Process a new bar and detect marks in real-time.

        B1 = first break of a new swing (extreme broken for first time)
        B2 = continuation break (extreme broken again after B1)
        FLIP = reversal break (price breaks opposite direction)
        """
        if not self.dir:
            self.dir = "up"
            self.anchor = candle.close
            self.extreme = candle.high
            self.start_idx = g_idx
            self.has_b1 = False
            self.bars_in_swing = 1
            self._save_state()
            return None

        # First bar establishes the extreme - no mark possible
        if self.bars_in_swing < 2:
            self.bars_in_swing += 1
            if self.dir == "up":
                self.extreme = max(self.extreme, candle.high)
            else:
                self.extreme = min(self.extreme, candle.low)
            self._save_state()
            return None

        mark = None

        if self.dir == "up":
            if candle.high > self.extreme:
                self.extreme = candle.high
                if not self.has_b1:
                    mark = {
                        "idx": g_idx, "time": candle.date, "kind": "B1",
                        "dir": "up", "px": candle.close, "swing_no": self.swing_index,
                    }
                    self.has_b1 = True
                else:
                    mark = {
                        "idx": g_idx, "time": candle.date, "kind": "B2",
                        "dir": "up", "px": candle.close, "swing_no": self.swing_index,
                    }
            elif candle.low < self.anchor:
                mark = {
                    "idx": g_idx, "time": candle.date, "kind": "FLIP",
                    "dir": "down", "px": candle.close, "swing_no": self.swing_index,
                }
                self.swing_index += 1
                self.dir = "down"
                self.anchor = self.extreme
                self.extreme = candle.low
                self.start_idx = g_idx
                self.has_b1 = False
                self.bars_in_swing = 1
        else:
            if candle.low < self.extreme:
                self.extreme = candle.low
                if not self.has_b1:
                    mark = {
                        "idx": g_idx, "time": candle.date, "kind": "B1",
                        "dir": "down", "px": candle.close, "swing_no": self.swing_index,
                    }
                    self.has_b1 = True
                else:
                    mark = {
                        "idx": g_idx, "time": candle.date, "kind": "B2",
                        "dir": "down", "px": candle.close, "swing_no": self.swing_index,
                    }
            elif candle.high > self.anchor:
                mark = {
                    "idx": g_idx, "time": candle.date, "kind": "FLIP",
                    "dir": "up", "px": candle.close, "swing_no": self.swing_index,
                }
                self.swing_index += 1
                self.dir = "up"
                self.anchor = self.extreme
                self.extreme = candle.high
                self.start_idx = g_idx
                self.has_b1 = False
                self.bars_in_swing = 1

        if mark:
            self.last_mark = mark
            self._save_state()

        return mark

    def get_current_swing(self) -> Optional[dict]:
        if not self.dir:
            return None
        return {
            "swing_index": self.swing_index, "dir": self.dir,
            "anchor": self.anchor, "extreme": self.extreme,
            "start_idx": self.start_idx,
        }