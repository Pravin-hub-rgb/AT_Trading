"""Persistent SwingEngine - maintains state across restarts."""

from __future__ import annotations
import json
from typing import Optional

from src.firstswing import SwingEngine
from src.walker import FlowCandle


class PersistentSwingEngine:
    """SwingEngine wrapper with state persistence."""

    def __init__(self, tf: str, db=None, opts: Optional[dict] = None):
        self.tf = tf
        self.db = db
        self.opts = opts or {"minBars": 50}
        self.eng = SwingEngine(self.opts)
        self.swing_index = 0
        self.next_start_pos = 0
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
                # Restore FsBreakMark dataclass list from serialized dicts
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
            # Serialize FsBreakMark dataclasses to plain dicts for JSON
            ser_marks = []
            for m in (e.break_marks or []):
                try:
                    ser_marks.append({"idx": int(m.idx), "time": str(m.time), "kind": str(m.kind), "dir": str(m.dir), "px": float(m.px)})
                except Exception:
                    # Already a dict (from restored state)
                    if isinstance(m, dict):
                        ser_marks.append(m)
            state = {
                "swing_index": self.swing_index,
                "next_start_pos": self.next_start_pos,
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

    def process_bar(self, candle: FlowCandle, g_idx: int) -> Optional[dict]:
        """Process a single bar. Returns swing dict if a swing completed."""
        if self.eng.declared:
            return None

        self.eng.process_bar(candle, g_idx)

        if not self.eng.declared or self.eng.start_idx < 0:
            self._save_state()
            return None

        src_kind = "SUS" if self.eng.confirm_source == "sustain" else "FS"
        decisive = self.eng.break_marks[-1] if self.eng.break_marks else None
        bk = decisive.kind if decisive else None

        result = {
            "swing_index": self.swing_index,
            "seg": {
                "dir": "B" if self.eng.dir == "up" else "S",
                "start_idx": self.eng.start_idx,
                "start_px": self.eng.start_px,
                "end_idx": self.eng.end_idx,
                "end_px": self.eng.end_px,
                "end_time": self.eng.end_time,
            },
            "source": self.eng.confirm_source,
            "dir": self.eng.dir,
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
                for b in self.eng.break_marks
            ],
            "confirmed_at_idx": self.eng.confirmed_at_idx,
            "confirmed_at_time": self.eng.confirmed_at_time,
        }

        self.swing_index += 1
        self.next_start_pos = self.eng.end_idx + 1 if self.eng.end_idx >= 0 else g_idx + 1

        self.eng = SwingEngine(self.opts)
        self.eng.defer_same_bar_arm = True
        self.eng.seed_idx = self.next_start_pos

        self._save_state()
        return result

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
