"""swing_engine.py — Re-export shim for backward compatibility.

All swing logic lives in firstswing.py (SwingEngine).
This module re-exports the old names so existing imports don't break.
"""

from .firstswing import (  # noqa: F401
    SwingEngine,
    FirstSwingEngine,
    FsV2Engine,
    FsBreakMark,
    FlowSegment,
    FsV2Result,
    Lvl,
    compute_swing_results,
    compute_whole_day_swings,
    compute_fs_v2_results,
    compute_fs_v2_declared,
)

# Legacy alias
LegacyFsV2Engine = FsV2Engine
