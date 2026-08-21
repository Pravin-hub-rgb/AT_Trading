import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

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

active_operations: dict = {}


def _job_running() -> bool:
    return any(op["status"] == "running" for op in active_operations.values())


def _start_update_job() -> dict | None:
    if _job_running():
        return None
    operation_id = _new_op_id("upd")
    intervals = ["daily", "5min"]
    active_operations[operation_id] = _new_op(operation_id, intervals, 0)
    thread = threading.Thread(target=_run_update, args=(operation_id, intervals), daemon=True)
    thread.start()
    return {"status": "started", "operation_id": operation_id, "mode": "update"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = DataScheduler(_start_update_job)
    scheduler.start()
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
    interval: str = "both"  # daily | 5min | both
    years: int = 1


@app.post("/api/data/download")
def start_download(payload: DownloadPayload):
    if _job_running():
        return JSONResponse(status_code=409, content={"detail": "Another job is already running"})
    if not token_svc.is_valid():
        return JSONResponse(status_code=400, content={"detail": "Upstox token is missing or invalid — add a valid token first"})

    interval = payload.interval
    if interval not in ("daily", "5min", "both"):
        return JSONResponse(status_code=400, content={"detail": "interval must be daily | 5min | both"})

    intervals = ["daily", "5min"] if interval == "both" else [interval]
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
    if interval not in ("daily", "5min"):
        return JSONResponse(status_code=400, content={"detail": "interval must be daily | 5min"})

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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8003)