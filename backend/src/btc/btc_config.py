"""BTC/ETH data config — reads CSVs from <repo>/data/btc/, data/btc-fut/, data/eth-fut/.

CSV format: timestamp,open,high,low,close,x,y
    - timestamps are raw IST wall-clock strings (e.g. 2025-01-01 05:30:00),
      continuous 24/7 series; nothing is shifted in the file
    - `ts` is derived: the wall-clock string interpreted as UTC epoch minus
      the IST offset, so the frontend chart (which adds IST back for display)
      shows the original wall time — same convention as the Nifty data pipeline.
"""
from pathlib import Path

import pandas as pd

import os

# btc_config.py -> parents: [0]=btc, [1]=src, [2]=backend, [3]=repo root
BACKEND_DIR = Path(__file__).resolve().parents[2]
ROOT_DIR = Path(__file__).resolve().parents[3]
BTC_DATA_DIR = ROOT_DIR / "data" / "btc"

# The Bybit datasets are the only ones every registry pin was measured against,
# and the only ones that cannot be re-derived to match: Bybit revises historical
# closes, so a fresh download no longer reproduces the recorded numbers.
#
# They used to live at <repo>/data/bybit and were lost, because `data/` is
# gitignored - so they were untracked, and the one command that deletes
# untracked files (`git clean -fdx`) deleted them. No commit, no branch and no
# reflog could restore that. Moving them out of the repo is the actual fix.
#
# BTC_BYBIT_DATA_DIR -> <repo>/../btc_data/is  (IS,  2023-01-01 -> 2026-09-13)
# BTC_BYBIT_OOS_DATA_DIR -> .../oos            (OOS, 2021-01-01 -> 2022-12-31)
# Override the root with the BTC_BYBIT_DATA_DIR environment variable.
# btc_csv_path / load_btc_df / btc_bybit_csv_path / btc_bybit_oos_dir
# BTC_BYBIT_ROOT -> <repo>/../btc_data, overridable with BTC_BYBIT_DATA_DIR.
#
# The old location is still accepted first, so a checkout that still has its
# data/ folder keeps working untouched. Only when that is missing does the new
# outside-the-repo location get used. Nothing falls back to a fresh download:
# Bybit revises historical closes, so a re-download produces different numbers
# from every pin in the registry.
BTC_BYBIT_ROOT = Path(os.environ.get("BTC_BYBIT_DATA_DIR", str(ROOT_DIR.parent / "btc_data")))
_BTC_BYBIT_LEGACY = ROOT_DIR / "data" / "bybit"
_BTC_BYBIT_OOS_LEGACY = ROOT_DIR / "data" / "unseen" / "bybit"
BTC_BYBIT_DATA_DIR = _BTC_BYBIT_LEGACY if _BTC_BYBIT_LEGACY.is_dir() else BTC_BYBIT_ROOT / "is"
BTC_BYBIT_OOS_DATA_DIR = (_BTC_BYBIT_OOS_LEGACY if _BTC_BYBIT_OOS_LEGACY.is_dir()
                         else BTC_BYBIT_ROOT / "oos")


def btc_bybit_oos_dir() -> Path:
    """The out-of-sample Bybit directory. Named for the 9 harnesses that pin
    UNSEEN_DIR by hand; use this instead of hardcoding the path."""
    return BTC_BYBIT_OOS_DATA_DIR


IST_OFFSET_SEC = 5 * 3600 + 30 * 60  # 19800

# Supported symbols — maps to data directory and CSV prefix
SYMBOLS: dict[str, dict] = {
    "BTCUSDT": {"dir": ROOT_DIR / "data" / "btc", "label": "BTC Spot"},
    "BTCUSDT_PERP": {"dir": ROOT_DIR / "data" / "btc-fut", "label": "BTC Perp (Binance)"},
    "ETHUSDT_PERP": {"dir": ROOT_DIR / "data" / "eth-fut", "label": "ETH Perp (Binance)"},
    "BTCUSDT_BYBIT": {"dir": BTC_BYBIT_DATA_DIR, "label": "BTC Perp (Bybit)"},
}

# Default symbols for backward compat
BTC_TFS: dict[str, str] = {
    "1m": "BTCUSDT_1m.csv",
    "5m": "BTCUSDT_5m.csv",
    "15m": "BTCUSDT_15m.csv",
    "1h": "BTCUSDT_1h.csv",
    "4h": "BTCUSDT_4h.csv",
}


def btc_csv_path(tf: str, symbol: str = "BTCUSDT") -> Path:
    if tf not in BTC_TFS:
        raise ValueError(f"tf must be one of {sorted(BTC_TFS)}")
    sym_cfg = SYMBOLS.get(symbol, SYMBOLS["BTCUSDT"])
    data_dir = sym_cfg["dir"]
    # Map symbol to CSV filename:
    # BTCUSDT -> BTCUSDT_{tf}.csv (spot)
    # BTCUSDT_PERP -> BTCUSDT_{tf}.csv (Binance perp, same prefix as spot)
    # ETHUSDT_PERP -> ETHUSDT_{tf}.csv
    # BTCUSDT_BYBIT -> BTCUSDT_{tf}.csv (Bybit perp, same prefix as spot)
    csv_prefix = symbol.replace("_PERP", "").replace("_BYBIT", "")
    csv_name = f"{csv_prefix}_{tf}.csv"
    return data_dir / csv_name


# mtime-keyed frame cache — CSVs are static; re-parse only when the file changes
_df_cache: dict[tuple, pd.DataFrame] = {}
_DF_CACHE_MAX = 5


def load_btc_df(tf: str, symbol: str = "BTCUSDT") -> pd.DataFrame:
    """Load one BTC/ETH timeframe CSV (sorted/deduped, derived `ts` epoch s)."""
    path = btc_csv_path(tf, symbol)
    if not path.exists():
        raise FileNotFoundError(f"{symbol} {tf} data missing: {path}")
    key = (symbol, tf, path.stat().st_mtime_ns)
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
