"""Backbencher engine package.

Contains:
  - v18_params: verified parameter matrix (source of truth for all constants)
  - mark: Mark dataclass for journaling
  - candle: Candle dataclass

The actual strategy logic lives in backend/src/btc/engines/htf_ltf/v18_streak_halt.py.
This package imports and wraps it - never reimplements it.
"""
