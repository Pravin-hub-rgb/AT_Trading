import threading
import json
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from datetime import datetime

import faulthandler

# Native-crash (Windows exit code 4294967295) dumps its traceback to stderr
faulthandler.enable()

import pandas as pd
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src import config, token as token_svc
from src import upstox_fetcher as F
from src.scheduler import DataScheduler
from src import swing as swing_svc
from src import bias as bias_svc
from src import intraday as intraday_svc
from src import firstswing as fs_engine

active_operations: dict = {}

# per-config backtest results (combo switches keep separate entries so UI
# toggling doesn't thrash a single-slot cache)
_intraday_caches: "OrderedDict[tuple, tuple]" = OrderedDict()
INTRADAY_CACHE_MAX = 8
_bias_cache: dict = {"key": None, "labels": None}


def _data_key() -> tuple:
    p5 = config.DATA_DIR / "nifty_5min.csv"
    pd_ = config.DATA_DIR / "nifty_daily.csv"
    return (
        p5.stat().st_mtime_ns if p5.exists() else 0,
        pd_.stat().st_mtime_ns if pd_.exists() else 0,
    )


def _bias_labels_cached() -> list:
    """compute_bias memoized on data-file mtimes (shared by /api/bias & backtest)."""
    key = _data_key()
    if _bias_cache["key"] == key:
        return _bias_cache["labels"]
    df5 = pd.read_csv(config.DATA_DIR / "nifty_5min.csv")
    daily_path = config.DATA_DIR / "nifty_daily.csv"
    daily_df = pd.read_csv(daily_path) if daily_path.exists() else None
    labels = bias_svc.compute_bias(df5, daily_df)
    _bias_cache["key"] = key
    _bias_cache["labels"] = labels
    return labels


def _intraday_backtest(cfg: dict | None = None):
    """Run (or reuse cached) intraday backtest keyed on data mtimes + config.
    
    5min and 1min are now separate engines:
    - 5min: loops over 5min, uses 1min only for precise entry/exit (intraday.py)
    - 1min: loops directly over 1min, fully independent (intraday_1m_standalone.py)
    """
    p5 = config.DATA_DIR / "nifty_5min.csv"
    pd_ = config.DATA_DIR / "nifty_daily.csv"
    p1 = config.DATA_DIR / "nifty_1min.csv"
    if not p5.exists():
        raise FileNotFoundError("No 5min data yet. Download first.")
    # include p1 mtime in key when 1min execution (so 1min data changes bust cache)
    p1_mtime = p1.stat().st_mtime_ns if p1.exists() else 0
    key = (
        p5.stat().st_mtime_ns,
        pd_.stat().st_mtime_ns if pd_.exists() else 0,
        p1_mtime,
        tuple(sorted((cfg or {}).items())),
    )
    if key in _intraday_caches:
        _intraday_caches.move_to_end(key)
        return _intraday_caches[key]

    df5 = pd.read_csv(p5)
    daily_df = pd.read_csv(pd_) if pd_.exists() else None
    df1 = pd.read_csv(p1) if p1.exists() else None
    labels = [lb for lb in _bias_labels_cached() if lb["date"] in set(df5["timestamp"].astype(str).str[:10])]

    execution = (cfg or {}).get("execution", "5min")
    if execution == "1min":
        # 1min standalone engine: needs 1min data, no 5min loop
        if df1 is None or len(df1) == 0:
            raise FileNotFoundError("No 1min data yet. Download first.")
        import src.intraday_1m_standalone as m1_engine
        # 1min engine uses 1min df, but still needs bias labels (from 5min/daily)
        bt = m1_engine.run_backtest_1min(df1, labels, cfg=cfg)
    else:
        # 5min engine: may use 1min for precise entry/exit
        df1_for_5min = df1 if (df1 is not None and len(df1) > 0) else None
        bt = intraday_svc.run_backtest(df5, labels, cfg=cfg, df_1min=df1_for_5min)

    days_summary = [
        {
            "date": d["date"],
            # unbiased days trade via U1/U2 (first-swing direction) — show that
            "bias": d.get("effective_bias") or d["bias"],
            "raw_bias": d["bias"],
            "case": d.get("case"),
            "swing_direction": d["swing_direction"],
            "trade_mode": d.get("trade_mode"),
            "n_trades": len(d["trades"]),
            "outcomes": [t["outcome"] for t in d["trades"]],
            # full trade rows so the chart can draw position boxes without
            # a per-day fetch; events stay in /api/intraday/{date}
            "trades": d["trades"],
        }
        for d in bt["days"]
    ]
    data = {"stats": bt["stats"], "days": days_summary, "config": bt.get("config", cfg)}
    payload = (data, bt["days"])
    _intraday_caches[key] = payload
    _intraday_caches.move_to_end(key)
    while len(_intraday_caches) > INTRADAY_CACHE_MAX:
        _intraday_caches.popitem(last=False)
    return payload


def _job_running() -> bool:
    return any(op["status"] == "running" for op in active_operations.values())


def _start_update_job() -> dict | None:
    if _job_running():
        return None
    operation_id = _new_op_id("upd")
    intervals = ["daily", "5min", "1min"]
    active_operations[operation_id] = _new_op(operation_id, intervals, 0)
    thread = threading.Thread(target=_run_update, args=(operation_id, intervals), daemon=True)
    thread.start()
    return {"status": "started", "operation_id": operation_id, "mode": "update"}


def _warm_intraday():
    """Precompute default-combo backtest at startup so the first UI hit is instant."""
    try:
        _intraday_backtest({})
    except Exception:
        pass  # never block startup (e.g. no data yet)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = DataScheduler(_start_update_job)
    scheduler.start()
    threading.Thread(target=_warm_intraday, daemon=True).start()
    yield
    scheduler.stop()


app = FastAPI(title="AT Trading API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3002", "http://127.0.0.1:3002"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _new_op_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


def _new_op(operation_id: str, intervals: list, years: int) -> dict:
    return {
        "operation_id": operation_id,
        "status": "running",
        "progress": 0,
        "message": "Starting...",
        "log": [],
        "intervals": intervals,
        "years": years,
        "done_months": 0,
        "total_months": 0,
        "error": None,
        "mode": "download",
    }


def _op_progress(op: dict):
    def progress(done: int, total: int, label: str, rows: int):
        op["done_months"] = done
        op["total_months"] = total
        op["progress"] = round(done / total * 100, 1) if total else 0
        op["message"] = f"{label}: {rows} candles"
        op["log"].append(f"{label}: {rows} candles")

    return progress


def _finish_op(op: dict, ok: bool, message: str):
    if ok:
        op["status"] = "done"
        op["progress"] = 100
    else:
        op["status"] = "error"
    op["message"] = message
    op["log"].append(message)


def _run_download(operation_id: str, intervals: list, years: int):
    op = active_operations[operation_id]
    try:
        for interval in intervals:
            op["log"].append(f"--- Downloading {interval} ---")
            result = F.full_download(config.get_access_token(), interval, years, progress_cb=_op_progress(op))
            op["log"].append(f"{interval} done: {result['rows_fetched']} rows ({result['months_fetched']} months)")
        _finish_op(op, True, "Download complete")
    except Exception as e:
        _finish_op(op, False, f"Error: {e}")
        op["error"] = str(e)


def _run_update(operation_id: str, intervals: list):
    op = active_operations[operation_id]
    op["mode"] = "update"
    try:
        total_rows = 0
        for interval in intervals:
            op["log"].append(f"--- Updating {interval} ---")
            result = F.update_data(config.get_access_token(), interval, progress_cb=_op_progress(op))
            total_rows += result["rows_fetched"]
            op["log"].append(f"{interval}: {result['rows_fetched']} new rows")
        if total_rows == 0:
            _finish_op(op, True, "Already up to date — nothing to fetch")
        else:
            _finish_op(op, True, f"Update complete — {total_rows} new rows")
    except Exception as e:
        _finish_op(op, False, f"Error: {e}")
        op["error"] = str(e)


# ---------------------------------------------------------------------------
# Health / token
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "token_configured": config.token_configured()}


class TokenPayload(BaseModel):
    token: str
    api_key: str | None = None
    api_secret: str | None = None


@app.post("/api/token")
def save_token(payload: TokenPayload):
    if payload.api_key is not None:
        config.set_env_var("API_KEY", payload.api_key)
    if payload.api_secret is not None:
        config.set_env_var("API_SECRET", payload.api_secret)
    if payload.token:
        config.set_access_token(payload.token)
    return {"ok": True, "status": token_svc.get_status()}


@app.post("/api/token/validate")
def validate_token(payload: TokenPayload):
    """Validate credentials against Upstox LTP. Persists only if valid."""
    creds = {"token": payload.token, "api_key": payload.api_key, "api_secret": payload.api_secret}
    return token_svc.validate_persist(creds)


@app.get("/api/token/check")
def check_token():
    return token_svc.check_token()


@app.get("/api/token/status")
def token_status():
    return token_svc.get_status()


# ---------------------------------------------------------------------------
# Data status / settings
# ---------------------------------------------------------------------------
@app.get("/api/data/status")
def data_status():
    return F.all_data_status()


@app.get("/api/settings")
def get_settings():
    return F.get_settings()


class SettingsPayload(BaseModel):
    auto_update: bool | None = None
    update_time: str | None = None
    years: int | None = None


@app.put("/api/settings")
def put_settings(payload: SettingsPayload):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    return F.set_settings(patch)


# ---------------------------------------------------------------------------
# Download / update jobs
# ---------------------------------------------------------------------------
class DownloadPayload(BaseModel):
    interval: str = "all"  # daily | 5min | 1min | all | both (legacy = daily+5min)
    years: int = 1


@app.post("/api/data/download")
def start_download(payload: DownloadPayload):
    if _job_running():
        return JSONResponse(status_code=409, content={"detail": "Another job is already running"})
    if not token_svc.is_valid():
        return JSONResponse(status_code=400, content={"detail": "Upstox token is missing or invalid — add a valid token first"})

    interval = payload.interval
    if interval not in ("daily", "5min", "1min", "all", "both"):
        return JSONResponse(status_code=400, content={"detail": "interval must be daily | 5min | 1min | all | both"})

    intervals = {
        "both": ["daily", "5min"],
        "all": ["daily", "5min", "1min"],
    }.get(interval, [interval])
    operation_id = _new_op_id("dl")
    active_operations[operation_id] = _new_op(operation_id, intervals, payload.years)

    thread = threading.Thread(target=_run_download, args=(operation_id, intervals, payload.years), daemon=True)
    thread.start()
    return {"status": "started", "operation_id": operation_id, "mode": "download"}


@app.post("/api/data/update")
def start_update():
    if _job_running():
        return JSONResponse(status_code=409, content={"detail": "Another job is already running"})
    if not token_svc.is_valid():
        return JSONResponse(status_code=400, content={"detail": "Upstox token is missing or invalid — add a valid token first"})

    operation_id = _new_op_id("upd")
    intervals = ["daily", "5min"]
    active_operations[operation_id] = _new_op(operation_id, intervals, 0)
    thread = threading.Thread(target=_run_update, args=(operation_id, intervals), daemon=True)
    thread.start()
    return {"status": "started", "operation_id": operation_id, "mode": "update"}


@app.get("/api/data/status/{operation_id}")
def operation_status(operation_id: str):
    op = active_operations.get(operation_id)
    if not op:
        return JSONResponse(status_code=404, content={"detail": "Unknown operation"})
    return {k: v for k, v in op.items() if k != "log"} | {"log": op["log"][-100:]}


# ---------------------------------------------------------------------------
# Chart data
# ---------------------------------------------------------------------------
@app.get("/api/chart/data")
def chart_data(interval: str = "daily", limit: int | None = None):
    if interval not in ("daily", "5min", "1min"):
        return JSONResponse(status_code=400, content={"detail": "interval must be daily | 5min | 1min"})

    path = config.DATA_DIR / f"nifty_{interval}.csv"
    if not path.exists():
        return JSONResponse(status_code=404, content={"detail": f"No {interval} data yet. Download first."})

    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")
    if limit and limit > 0:
        df = df.tail(int(limit))

    candles = []
    for row in df.itertuples():
        candles.append(
            {
                "date": row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "ts": row.ts,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
                "oi": row.oi,
            }
        )

    return {"interval": interval, "count": len(candles), "candles": candles}


@app.get("/api/swings")
def get_swings(interval: str = "daily", pivot: int = 10, levels: int = 5, lookahead: int = 50):
    if interval not in ("daily", "5min"):
        return JSONResponse(status_code=400, content={"detail": "interval must be daily | 5min"})

    path = config.DATA_DIR / f"nifty_{interval}.csv"
    if not path.exists():
        return JSONResponse(status_code=404, content={"detail": f"No {interval} data yet. Download first."})

    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")

    swings = swing_svc.find_pivots(df, max(1, int(pivot)))
    sr_levels = swing_svc.select_sr_levels(swings, max(1, int(levels)), max(1, int(lookahead)))

    return {
        "interval": interval,
        "pivot": max(1, int(pivot)),
        "levels": max(1, int(levels)),
        "lookahead": max(1, int(lookahead)),
        "swings": swings,
        "sr_levels": sr_levels,
    }


@app.get("/api/swings/whole_day")
def get_whole_day_swings(
    interval: str = "1min",
    sustain_bars: int = 7,
    swing_count: str = "whole",
):
    """Whole-day alternating swing detection.

    Detects multiple swings per day, assigning each a swing_index (0, 1, 2, ...).

    Args:
        interval: 1min only (whole-day swing is 1min-only feature)
        sustain_bars: N-bar sustain requirement (default 7)
        swing_count: "whole" for all swings, or an integer string like "3" for N swings per day.

    Returns:
        {
            "interval": str,
            "swing_count": str,
            "swings": [ {day, swing_index, seg, source, dir, ...} ]
        }
    """
    if interval != "1min":
        return JSONResponse(status_code=400, content={"detail": "whole-day swings only available for interval=1min"})
    if interval not in ("daily", "5min", "1min"):
        return JSONResponse(status_code=400, content={"detail": "interval must be daily | 5min | 1min"})

    path = config.DATA_DIR / f"nifty_{interval}.csv"
    if not path.exists():
        return JSONResponse(status_code=404, content={"detail": f"No {interval} data yet. Download first."})

    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").drop_duplicates(subset="timestamp", keep="last")

    from src.intraday import FlowCandle
    candles: list[FlowCandle] = []
    for _, row in df.iterrows():
        candles.append(FlowCandle(
            date=row["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
        ))

    from src.firstswing import compute_swing_results
    sc: int | str
    if swing_count == "whole":
        sc = "whole"
    else:
        try:
            sc = max(1, int(swing_count))
        except ValueError:
            sc = "whole"
    swings = compute_swing_results(candles, opts={"sustain_bars": sustain_bars, "minBars": 14, "timeCap": "09:29"}, swing_count=sc)

    return {
        "interval": interval,
        "swing_count": swing_count,
        "sustain_bars": sustain_bars,
        "swings": swings,
    }


@app.get("/api/bias")
def get_bias(limit: int | None = None):
    """Initial-bias labels (pre-open): previous-day close reads + daily-swing overview."""
    path = config.DATA_DIR / "nifty_5min.csv"
    if not path.exists():
        return JSONResponse(status_code=404, content={"detail": "No 5min data yet. Download first."})

    labels = _bias_labels_cached()
    if limit and limit > 0:
        labels = labels[-int(limit) :]

    counts = {"bullish": 0, "bearish": 0, "unbiased": 0}
    for lb in labels:
        counts[lb["bias"]] += 1

    return {"count": len(labels), "summary": counts, "bias": labels}


@app.get("/api/intraday/backtest")
def intraday_backtest(
    sl_mode: str = "avg",
    execution: str = "5min",
    trailing: str = "off",
    trail_distance_r: float = 1.0,
    gap_pct: float = 0.27,
    sl_pivot_buffer: float = 1.0,
    ft_fail_enabled: bool = True,
    entry_method: str = "pace_break",
    swing_mode: str = "opposite_swing_needed",
    rr_target: float = 3.0,
    swing_traverse: bool = True,
    min_sl_pts: float = 13.0,
):
    """Full-history intraday results for one experiment combo.

    Switches (best-combo search): sl_mode avg|avg075|avg05|fixed8|prev_pivot,
    execution 5min|1min, trailing off|ladder, gap_pct in PERCENT (0.27 = 0.27%),
    sl_pivot_buffer in points (default 1.0) for prev_pivot mode,
    ft_fail_enabled (default True): early exit when close beyond dom_level within 2 bars (S5:98),
    entry_method (default pace_break): pace_break | pivot_break,
    swing_mode (default opposite_swing_needed): none | opposite_swing_needed (1min only),
    rr_target (default 3.0): fixed target in R; only used when trailing=off,
    swing_traverse (default True): reference swing follows extensions (1min engine).
    swing_traverse (default True): reference swing follows extensions (1min engine).
    """
    cfg = {
        "sl_mode": sl_mode,
        "execution": execution,
        "trailing": trailing,
        "trail_distance_r": trail_distance_r,
        # UI/API speak percent; engine expects fraction (0.27% -> 0.0027)
        "gap_pct": float(gap_pct) / 100.0,
        "sl_pivot_buffer": float(sl_pivot_buffer),
        "ft_fail_enabled": ft_fail_enabled,
        "entry_method": entry_method,
        "swing_mode": swing_mode,
        "rr_target": float(rr_target),
        "swing_traverse": bool(swing_traverse),
        "min_sl_pts": float(min_sl_pts),
    }
    try:
        data, _ = _intraday_backtest(cfg)
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"detail": str(e)})
    return data


@app.get("/api/intraday/{date}")
def intraday_day(
    date: str,
    sl_mode: str = "avg",
    execution: str = "5min",
    trailing: str = "off",
    trail_distance_r: float = 1.0,
    gap_pct: float = 0.27,
    sl_pivot_buffer: float = 1.0,
    ft_fail_enabled: bool = True,
    entry_method: str = "pace_break",
    swing_mode: str = "opposite_swing_needed",
    rr_target: float = 3.0,
    swing_traverse: bool = True,
    min_sl_pts: float = 13.0,
):
    """Single-day detail: trades + full event timeline for chart annotation."""
    cfg = {
        "sl_mode": sl_mode,
        "execution": execution,
        "trailing": trailing,
        "trail_distance_r": trail_distance_r,
        "gap_pct": float(gap_pct) / 100.0,
        "sl_pivot_buffer": float(sl_pivot_buffer),
        "ft_fail_enabled": ft_fail_enabled,
        "entry_method": entry_method,
        "swing_mode": swing_mode,
        "rr_target": float(rr_target),
        "swing_traverse": bool(swing_traverse),
        "min_sl_pts": float(min_sl_pts),
    }
    try:
        _, days = _intraday_backtest(cfg)
    except FileNotFoundError as e:
        return JSONResponse(status_code=404, content={"detail": str(e)})

    for d in days:
        if d["date"] == date:
            return d
    return JSONResponse(status_code=404, content={"detail": f"No backtest day for {date}"})


# ===== First-Swing manual ground truth (user-drawn) =====

_FS_FILE = config.DATA_DIR / "first_swing_manual.json"


class FsPoint(BaseModel):
    time: str  # "HH:MM"
    kind: str  # "H" | "L"
    px: float


class FsDay(BaseModel):
    start: FsPoint
    end: FsPoint


def _fs_read() -> dict:
    if not _FS_FILE.exists():
        return {}
    try:
        raw = json.loads(_FS_FILE.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


@app.get("/api/firstswing/manual")
def firstswing_get():
    data = _fs_read()
    return {"count": len(data), "days": data}


@app.post("/api/firstswing/manual")
def firstswing_upsert(day: str, mark: FsDay):
    """Upsert one day's hand-drawn first swing. day = YYYY-MM-DD."""
    if len(day) != 10 or day[4] != "-" or day[7] != "-":
        return JSONResponse(status_code=400, content={"detail": "day must be YYYY-MM-DD"})
    if mark.start.kind not in ("H", "L") or mark.end.kind not in ("H", "L"):
        return JSONResponse(status_code=400, content={"detail": "kind must be H or L"})

    data = _fs_read()
    data[day] = {
        "start": {"time": mark.start.time, "kind": mark.start.kind, "px": mark.start.px},
        "end": {"time": mark.end.time, "kind": mark.end.kind, "px": mark.end.px},
    }
    _FS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True, "day": day, "count": len(data)}


@app.delete("/api/firstswing/manual/{day}")
def firstswing_delete(day: str):
    data = _fs_read()
    if day in data:
        del data[day]
        _FS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {"ok": True, "deleted": day, "count": len(data)}
    return JSONResponse(status_code=404, content={"detail": f"{day} not marked"})


# ===== First-Swing Engine (computed via WalkerEngine + FirstSwingEngine) =====

class FlowCandleInput(BaseModel):
    """Input candle for first-swing computation."""
    date: str       # ISO datetime string like "2025-08-28T09:15:00"
    open: float
    high: float
    low: float
    close: float


class FsBreakMarkOut(BaseModel):
    """B1/B2/FLIP marker output."""
    idx: int
    time: str
    kind: str       # "B1" | "B2" | "FLIP"
    dir: str        # "up" | "down"
    px: float


class FlowSegmentOut(BaseModel):
    """First-swing segment: start -> end with direction."""
    dir: str        # "B" (buying) | "S" (selling)
    start_idx: int
    start_px: float
    end_idx: int
    end_px: float


class FsV2ResultOut(BaseModel):
    """One day's first-swing result."""
    day: str
    outcome: str             # always "real" (only declared swings returned)
    conf_idx: int            # global candle index of the CONFIRM bar
    seg: FlowSegmentOut
    source: str | None       # "chop" | "sustain" | null
    dir: str                 # "up" | "down"
    breaks: list[FsBreakMarkOut]


@app.post("/api/firstswing/compute")
def compute_first_swing(candles: list[FlowCandleInput]) -> list[FsV2ResultOut]:
    """Run first-swing detection on provided candles.

    Candles should be sorted by date globally. Returns one result per day with
    a declared swing (real outcome). Includes B1/B2/FLIP break marks and the
    FS segment (start/end points).
    """
    from src.walker import FlowCandle

    # Convert to internal format
    flow_candles = [
        FlowCandle(
            date=c.date,
            open=float(c.open),
            high=float(c.high),
            low=float(c.low),
            close=float(c.close),
        )
        for c in candles
    ]

    results = fs_engine.compute_fs_v2_results(flow_candles)

    return [
        FsV2ResultOut(
            day=r.day,
            outcome=r.outcome,
            conf_idx=r.conf_idx,
            seg=FlowSegmentOut(
                dir=r.seg.dir,
                start_idx=r.seg.start_idx,
                start_px=r.seg.start_px,
                end_idx=r.seg.end_idx,
                end_px=r.seg.end_px,
            ),
            source=r.source,
            dir=r.dir,
            breaks=[
                FsBreakMarkOut(
                    idx=b.idx,
                    time=b.time,
                    kind=b.kind,
                    dir=b.dir,
                    px=b.px,
                )
                for b in r.breaks
            ],
        )
        for r in results
    ]


# ── Single source of truth: Python engine for first + second swing (replaces TS in-browser) ──
class FirstSecondRequest(BaseModel):
    candles: list[FlowCandleInput]
    opts: dict | None = None  # {timeCap, sustainBars, minBars}
    include_second: bool = True


class FirstSecondResponse(BaseModel):
    first: list[FsV2ResultOut]
    second: list[FsV2ResultOut]


def _filter_breaks_per_swing(breaks: list) -> list:
    """Keep first B1 + last decisive (last non-B1). Collapses FLIP@10:16+FLIP@10:17 → FLIP@10:17."""
    if len(breaks) <= 1:
        return breaks
    first = next((b for b in breaks if getattr(b, "kind", None) == "B1"), breaks[0])
    non_b1 = [b for b in breaks if getattr(b, "kind", None) != "B1"]
    if not non_b1:
        return [first]
    last = non_b1[-1]
    return [first, last]


@app.post("/api/swings/first_second")
def compute_first_second(req: FirstSecondRequest) -> FirstSecondResponse:
    """Single source of truth — Python SwingEngine for both first and second swings.

    Replaces frontend in-browser computeFsV2Results + computeSecondSwingResults.
    Returns filtered break marks (first B1 + last FLIP/B2 per swing).
    """
    from src.walker import FlowCandle
    from src.firstswing import SwingEngine

    opts = req.opts or {"timeCap": "09:29"}
    # Normalize opts keys (frontend uses timeCap, sustainBars; backend uses timeCap/sustain_bars)
    if "sustainBars" in opts and "sustain_bars" not in opts:
        opts["sustain_bars"] = opts["sustainBars"]
    if "minBars" in opts and "min_bars" not in opts:
        opts["min_bars"] = opts["minBars"]

    flow_candles = [
        FlowCandle(
            date=c.date,
            open=float(c.open),
            high=float(c.high),
            low=float(c.low),
            close=float(c.close),
        )
        for c in req.candles
    ]

    # First swing — grouped by day, one result per day
    first_raw = fs_engine.compute_fs_v2_results(flow_candles, opts)

    # Apply per-swing filter (first B1 + last decisive) for chart cleanliness
    first_filtered: list[FsV2ResultOut] = []
    for r in first_raw:
        filtered_breaks = _filter_breaks_per_swing(r.breaks)
        first_filtered.append(
            FsV2ResultOut(
                day=r.day,
                outcome=r.outcome,
                conf_idx=r.conf_idx,
                seg=FlowSegmentOut(
                    dir=r.seg.dir,
                    start_idx=r.seg.start_idx,
                    start_px=r.seg.start_px,
                    end_idx=r.seg.end_idx,
                    end_px=r.seg.end_px,
                ),
                source=r.source,
                dir=r.dir,
                breaks=[
                    FsBreakMarkOut(idx=b.idx, time=b.time, kind=b.kind, dir=b.dir, px=b.px)
                    for b in filtered_breaks
                ],
            )
        )

    if not req.include_second:
        return FirstSecondResponse(first=first_filtered, second=[])

    # Second swing — seed from first swing endIdx+1, fresh engine per day
    # Mirror frontend/src/lib/flowline.ts:1271 computeSecondSwingResults
    from collections import defaultdict

    # Build fs1 lookup and group candles by day
    fs1_by_day: dict[str, FsV2ResultOut] = {r.day: r for r in first_raw if r.seg is not None}
    by_day: dict[str, list[tuple[int, FlowCandle]]] = defaultdict(list)
    for g_idx, c in enumerate(flow_candles):
        by_day[c.date[:10]].append((g_idx, c))

    second_out: list[FsV2ResultOut] = []
    for day, items in by_day.items():
        fs1 = fs1_by_day.get(day)
        if fs1 is None or fs1.seg is None or fs1.conf_idx < 0:
            continue
        seed_idx = fs1.seg.end_idx + 1
        after = [(gi, cc) for gi, cc in items if gi >= seed_idx]
        if not after:
            continue
        eng = SwingEngine(opts)
        for gi, cc in after:
            eng.process_bar(cc, gi)
        if not eng.declared or eng.start_idx < 0:
            continue
        raw_breaks = list(eng.break_marks)
        filtered = _filter_breaks_per_swing(raw_breaks)
        second_out.append(
            FsV2ResultOut(
                day=day,
                outcome="real",
                conf_idx=eng.confirmed_at_idx,
                seg=FlowSegmentOut(
                    dir="B" if eng.dir == "up" else "S",
                    start_idx=eng.start_idx,
                    start_px=eng.start_px,
                    end_idx=eng.end_idx,
                    end_px=eng.end_px,
                ),
                source=eng.confirm_source,
                dir=eng.dir,
                breaks=[
                    FsBreakMarkOut(idx=b.idx, time=b.time, kind=b.kind, dir=b.dir, px=b.px)
                    for b in filtered
                ],
            )
        )

    return FirstSecondResponse(first=first_filtered, second=second_out)


class EnvelopeViolationOut(BaseModel):
    idx: int
    side: str
    px: float
    markerIdx: int
    markerTime: str
    markerKind: str
    markerPx: float
    day: str


@app.post("/api/walker/flowline")
def walker_flowline(candles: list[FlowCandleInput]) -> dict:
    """Walker flow-line — per-day pivots chained into B/S segments (visual)."""
    from src.walker import FlowCandle, compute_algo_flowline

    flow = [
        FlowCandle(date=c.date, open=float(c.open), high=float(c.high), low=float(c.low), close=float(c.close))
        for c in candles
    ]
    segs = compute_algo_flowline(flow)
    return {
        "segments": [
            {"dir": s.dir, "start_idx": s.start_idx, "start_px": s.start_px, "end_idx": s.end_idx, "end_px": s.end_px}
            for s in segs
        ]
    }


@app.post("/api/walker/envelope")
def walker_envelope(candles: list[FlowCandleInput]) -> dict:
    """Envelope violations — per-day pivot breach check."""
    from src.walker import FlowCandle
    from src.envelope import compute_envelope_violations

    flow = [
        FlowCandle(date=c.date, open=float(c.open), high=float(c.high), low=float(c.low), close=float(c.close))
        for c in candles
    ]
    viols = compute_envelope_violations(flow)
    return {
        "violations": [
            {
                "idx": v.idx, "side": v.side, "px": v.px,
                "markerIdx": v.markerIdx, "markerTime": v.markerTime,
                "markerKind": v.markerKind, "markerPx": v.markerPx, "day": v.day,
            }
            for v in viols
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003)