"""htf_ltf v1_5m — 1h Flip cap16 + 5m Decisive inside HTF window. Isolated."""
from .v1_15m import simulate_htf_ltf_15m as simulate_htf_ltf_5m  # re-export with 5m LTF minBars 14 vs 15m 50

# For 5m, we need minBars 14 (5m) vs 15m's 50. The v1_15m engine already handles LTF minBars via swings_ltf passed in.
# This file is just an alias for imports that expect v1_5m.
from .v1_15m import simulate_htf_ltf_15m
__all__ = ["simulate_htf_ltf_5m", "simulate_htf_ltf_15m"]
