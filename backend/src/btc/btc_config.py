"""BTC data config — reads CSVs from <repo>/data/btc/.

CSV format: timestamp,open,high,low,close,x,y
    - timestamps are raw IST wall-clock strings (e.g. 2025-01-01 05:30:00),
      continuous 24/7 series; nothing is shifted in the file
    - `ts` is derived: the wall-clock string interpreted as UTC epoch minus
      the IST offset, so the frontend chart (which adds IST back for display)
      shows the original wall time — same convention as the Nifty data pipeline.
"""
from pathlib import Path

import pandas as pd

# btc_config.py -> parents: [0]=btc, [1]=src, [2]=backend, [3]=repo root
BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[3]
BTC_DATA_DIR = ROOT_DIR / "data" / "btc"

IST_OFFSET_SEC = 5 * 3600 + 30 * 60  # 19800

# One dataset, one CSV per timeframe. The CSVs hold the full merged series:
# in-sample window (2025-01-01 -> 2025-10-01, preserved in
# data/btc/backup_insample/) PLUS the Binance extension (2025-10-01 -> now).
# Refresh new candles with: python debug/_btc_fetch_update.py --tf 5m
BTC_TFS: dict[str, str] = {
    "1m": "BTCUSDT_1m.csv",
    "5m": "BTCUSDT_5m.csv",
    "15m": "BTCUSDT_15m.csv",
    "1h": "BTCUSDT_1h.csv",
    "4h": "BTCUSDT_4h.csv",
}


def btc_csv_path(tf: str) -> Path:
    if tf not in BTC_TFS:
        raise ValueError(f"tf must be one of {sorted(BTC_TFS)}")
    return BTC_DATA_DIR / BTC_TFS[tf]


# mtime-keyed frame cache — CSVs are static; re-parse only when the file changes
_df_cache: dict[tuple, pd.DataFrame] = {}
_DF_CACHE_MAX = 3


def load_btc_df(tf: str) -> pd.DataFrame:
    """Load one BTC timeframe CSV (sorted/deduped, derived `ts` epoch s)."""
    path = btc_csv_path(tf)
    if not path.exists():
        raise FileNotFoundError(f"BTC data file missing: {path}")
    key = (tf, path.stat().st_mtime_ns)
    cached = _df_cache.get(key)
    if cached is not None:
        return cached

    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = (
        df.sort_values("timestamp")
        .drop_duplicates(subset="timestamp", keep="last")
        .reset_index(drop=True)
    )
    # naive IST wall time -> UTC epoch seconds (chart adds IST back to display)
    df["ts"] = (df["timestamp"].astype("int64") // 10**9) - IST_OFFSET_SEC

    if len(_df_cache) >= _DF_CACHE_MAX:
        _df_cache.clear()
    _df_cache[key] = df
    return df
