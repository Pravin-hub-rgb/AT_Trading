"""Mark data structure - immutable once created.

A mark is generated when a swing extreme is broken.
B1 = first break, B2 = second break, FLIP = opposite direction break.

Only B2 and FLIP are tradeable. B1 is informational.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Mark:
    """Swing break mark - immutable once written to journal.
    
    Attributes:
        ts: candle close time when mark fired
        tf: timeframe ("15m" or "1h")
        kind: mark type ("B1", "B2", "FLIP")
        direction: "long" or "short"
        price: mark price (close of breaking candle)
        swing_no: which swing this mark belongs to
        swing_kind: "up" or "down"
        algo_version: version of algorithm that generated this mark
        journaled_at: wall clock timestamp when written to journal
        id: database row id (set by mark_store after insert)
    """
    ts: int
    tf: str
    kind: str
    direction: str
    price: float
    swing_no: int
    swing_kind: str
    algo_version: int = 1
    journaled_at: Optional[int] = None
    id: Optional[int] = None

    @property
    def is_tradeable(self) -> bool:
        """Only B2 and FLIP marks can enter trades."""
        return self.kind in ("B2", "FLIP")

    @property
    def is_long(self) -> bool:
        return self.direction == "long"

    @property
    def is_short(self) -> bool:
        return self.direction == "short"

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "id": self.id,
            "ts": self.ts,
            "tf": self.tf,
            "kind": self.kind,
            "direction": self.direction,
            "price": self.price,
            "swing_no": self.swing_no,
            "swing_kind": self.swing_kind,
            "algo_version": self.algo_version,
            "journaled_at": self.journaled_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Mark":
        """Create Mark from dict."""
        return cls(
            id=d.get("id"),
            ts=int(d["ts"]),
            tf=d["tf"],
            kind=d["kind"],
            direction=d["direction"],
            price=float(d["price"]),
            swing_no=int(d["swing_no"]),
            swing_kind=d["swing_kind"],
            algo_version=int(d.get("algo_version", 1)),
            journaled_at=d.get("journaled_at"),
        )
