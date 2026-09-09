import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.live import params
print("OK", params.STRATEGY, params.MODE, params.CHOP_THRESHOLD,
      params.COOLDOWN_BARS, params.MAX_CONSECUTIVE_LOSSES)
