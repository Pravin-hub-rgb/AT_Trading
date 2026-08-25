import calendar
import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

from .config import DATA_DIR

NIFTY_INDEX_KEY = "NSE_INDEX|Nifty 50"
BASE_URL = "https://api.upstox.com/v3/historical-candle"

INTERVALS = {
    "daily": "days/1",
    "5min": "minutes/5",
    "1min": "minutes/1",
}

# Pacing between API calls (rate-limit guard). Long 1-min backfills run a
# touch gentler than the short daily/5min syncs.
INTER_CALL_SLEEP_S = {"daily": 1.2, "5min": 1.2, "1min": 1.5}

META_FILE = Path(DATA_DIR) / "meta.json"
DEFAULT_SETTINGS = {"auto_update": True, "update_time": "19:00", "years": 1}


# ---------------------------------------------------------------------------
# Meta / settings
# ---------------------------------------------------------------------------
def _load_meta() -> dict:
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text())
        except Exception:
            pass
    return {"settings": dict(DEFAULT_SETTINGS), "data": {}}


def _save_meta(meta: dict) -> None:
    META_FILE.write_text(json.dumps(meta, indent=2, default=str))


def get_settings() -> dict:
    meta = _load_meta()
    settings = dict(DEFAULT_SETTINGS)
    settings.update(meta.get("settings") or {})
    return settings


def set_settings(patch: dict) -> dict:
    meta = _load_meta()
    meta.setdefault("settings", {}).update({k: v for k, v in patch.items() if k in DEFAULT_SETTINGS})
    _save_meta(meta)
    return get_settings()


def _set_interval_meta(interval: str, patch: dict) -> None:
    meta = _load_meta()
    meta.setdefault("data", {}).setdefault(interval, {}).update(patch)
    _save_meta(meta)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
def _ist_now() -> datetime:
    return datetime.now().astimezone()


def _expected_latest_date() -> date:
    """Latest trading day whose candles should exist locally (IST, market close 15:30)."""
    now = _ist_now()
    today = now.date()
    if today.weekday() >= 5:  # weekend -> previous Friday
        return today - timedelta(days=today.weekday() - 4)
    if now.hour > 15 or (now.hour == 15 and now.minute >= 30):
        return today
    prev = today - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    return prev


# ---------------------------------------------------------------------------
# Upstox fetch
# ---------------------------------------------------------------------------
def build_url(instrument_key: str, api_interval: str, to_date: str, from_date: str) -> str:
    key = quote(instrument_key, safe="")
    return f"{BASE_URL}/{key}/{api_interval}/{to_date}/{from_date}"


def _retry_after_seconds(resp) -> int:
    """Parse Retry-After header if the API sends one on 429."""
    try:
        return int(resp.headers.get("Retry-After") or 0)
    except (TypeError, ValueError):
        return 0


def fetch_candles(token: str, instrument_key: str, api_interval: str, from_date: str, to_date: str) -> list:
    url = build_url(instrument_key, api_interval, to_date, from_date)
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )
    if resp.status_code == 401:
        raise RuntimeError("Invalid/expired access token (401)")
    if resp.status_code == 429:
        # rate limited: back off (honour Retry-After when present) and retry
        # once here; the caller's attempt-loop handles further retries.
        time.sleep(max(_retry_after_seconds(resp), 6))
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30,
        )
        if resp.status_code == 429:
            raise RuntimeError("Upstox rate limit persisting after backoff (429)")
    resp.raise_for_status()
    data = resp.json()
    return (data.get("data") or {}).get("candles") or []


def _to_ist(ts) -> datetime:
    if isinstance(ts, str):
        return pd.to_datetime(ts).tz_convert("Asia/Kolkata")
    unit = "ms" if ts > 1e12 else "s"
    return pd.to_datetime(ts, unit=unit, utc=True).tz_convert("Asia/Kolkata")


def process_candle(c: list) -> dict:
    ts, o, h, l, cl = c[0], c[1], c[2], c[3], c[4]
    v = c[5] if len(c) > 5 else 0
    oi = c[6] if len(c) > 6 else 0
    ist = _to_ist(ts)
    return {
        "timestamp": ist.strftime("%Y-%m-%d %H:%M:%S"),
        "ts": int(ist.timestamp()),
        "open": o,
        "high": h,
        "low": l,
        "close": cl,
        "volume": v,
        "oi": oi,
    }


def build_months(from_date: date, to_date: date) -> list:
    months = []
    y, m = from_date.year, from_date.month
    while date(y, m, 1) <= to_date:
        start = date(y, m, 1)
        end = date(y, m, calendar.monthrange(y, m)[1])
        if end > to_date:
            end = to_date
        if start <= to_date:
            months.append((start, end))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return months


def _csv_path(interval: str) -> Path:
    return DATA_DIR / f"nifty_{interval}.csv"


def _load_existing(path: Path):
    if not path.exists():
        return pd.DataFrame(), None
    df = pd.read_csv(path)
    if df.empty:
        return df, None
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates(subset="timestamp", keep="last").sort_values("timestamp")
    return df, df["timestamp"].max()


# ---------------------------------------------------------------------------
# Core sync engine
# ---------------------------------------------------------------------------
def _sync_interval(token: str, interval: str, requested_from: date, requested_to: date, progress_cb=None) -> dict:
    api_interval = INTERVALS[interval]
    path = _csv_path(interval)

    df, _ = _load_existing(path)
    months = build_months(requested_from, requested_to)
    total = len(months)

    ym_col = None
    if not df.empty:
        ym_col = df["timestamp"].dt.to_period("M").astype(str).to_numpy()

    total_fetched = 0
    fetched_months = 0

    for i, (s, e) in enumerate(months):
        is_last = i == total - 1
        label = f"{s.year}-{s.month:02d}"
        ym = f"{s.year}-{s.month:02d}"
        has_rows = ym_col is not None and (ym_col == ym).any()

        # Full elapsed months are trusted if present; the last month is always
        # refetched (it may hold today's partial data), and gaps are refilled.
        need_fetch = (not has_rows) or is_last
        if not need_fetch:
            if progress_cb:
                progress_cb(i + 1, total, label, 0)
            continue

        candles = None
        for attempt in range(3):
            try:
                candles = fetch_candles(token, NIFTY_INDEX_KEY, api_interval, s.isoformat(), e.isoformat())
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2)

        rows = [process_candle(c) for c in candles]
        new_rows = 0
        if rows:
            month_df = pd.DataFrame(rows)
            month_df["timestamp"] = pd.to_datetime(month_df["timestamp"])
            existing_ts = set(df["timestamp"]) if not df.empty else set()
            new_rows = int((~month_df["timestamp"].isin(existing_ts)).sum())
            df = pd.concat([df, month_df], ignore_index=True)
            df = df.drop_duplicates(subset="timestamp", keep="last").sort_values("timestamp")
            df.to_csv(path, index=False)
            ym_col = df["timestamp"].dt.to_period("M").astype(str).to_numpy()

        total_fetched += new_rows
        fetched_months += 1
        if progress_cb:
            progress_cb(i + 1, total, label, new_rows)
        time.sleep(INTER_CALL_SLEEP_S.get(interval, 1.2))

    return {
        "rows_fetched": total_fetched,
        "months_fetched": fetched_months,
        "months_scanned": total,
        "up_to_date": total_fetched == 0,
    }


def _record_interval_meta(interval: str, requested_from: date, requested_to: date, result: dict, years: int | None = None) -> None:
    path = _csv_path(interval)
    df, _ = _load_existing(path)
    first_ts = df["timestamp"].min() if not df.empty else None
    last_ts = df["timestamp"].max() if not df.empty else None
    patch = {
        "requested_from": requested_from.isoformat(),
        "requested_to": requested_to.isoformat(),
        "first_ts": first_ts.strftime("%Y-%m-%d %H:%M:%S") if first_ts is not None else None,
        "last_ts": last_ts.strftime("%Y-%m-%d %H:%M:%S") if last_ts is not None else None,
        "last_update_at": _ist_now().isoformat(),
        "last_update_status": "done" if not result["up_to_date"] else "up_to_date",
        "rows_fetched": result["rows_fetched"],
    }
    if years is not None:
        patch["requested_years"] = int(years)
    _set_interval_meta(interval, patch)


def full_download(token: str, interval: str, years: int, progress_cb=None) -> dict:
    to_date = _ist_now().date()
    from_date = to_date - timedelta(days=int(years) * 365)
    result = _sync_interval(token, interval, from_date, to_date, progress_cb)
    _record_interval_meta(interval, from_date, to_date, result, years=years)
    return result


def update_data(token: str, interval: str, progress_cb=None) -> dict:
    meta = _load_meta().get("data", {}).get(interval) or {}
    settings = get_settings()
    years = meta.get("requested_years") or settings.get("years") or 1

    to_date = _ist_now().date()
    if meta.get("requested_from") and meta.get("requested_to"):
        requested_from = date.fromisoformat(meta["requested_from"])
        requested_to = date.fromisoformat(meta["requested_to"])
        # keep the same window, but extend to today if the stored window ended earlier
        requested_to = max(requested_to, to_date)
    else:
        requested_from = to_date - timedelta(days=int(years) * 365)
        requested_to = to_date

    result = _sync_interval(token, interval, requested_from, requested_to, progress_cb)
    _record_interval_meta(interval, requested_from, requested_to, result)
    return result


# ---------------------------------------------------------------------------
# Status / freshness
# ---------------------------------------------------------------------------
def interval_status(interval: str) -> dict:
    path = _csv_path(interval)
    meta = _load_meta().get("data", {}).get(interval) or {}

    base = {"interval": interval, "exists": False, "row_count": 0}

    if not path.exists():
        base.update(
            {
                "is_fresh": False,
                "days_behind": None,
                "coverage": 0,
                "missing_months": [],
                "first_ts": None,
                "last_ts": None,
                "badge": "no_data",
                "message": "No data downloaded yet",
            }
        )
        return base

    df, _ = _load_existing(path)
    rows = len(df)
    first_ts = df["timestamp"].min()
    last_ts = df["timestamp"].max()
    expected = _expected_latest_date()
    is_fresh = last_ts.date() >= expected
    days_behind = max((expected - last_ts.date()).days, 0)

    total_months = present_months = 0
    missing = []
    requested_from = meta.get("requested_from")
    requested_to = meta.get("requested_to")
    if requested_from and requested_to:
        months = build_months(date.fromisoformat(requested_from), date.fromisoformat(requested_to))
        total_months = len(months)
        ym_set = set(df["timestamp"].dt.to_period("M").astype(str))
        for s, _e in months:
            ym = f"{s.year}-{s.month:02d}"
            if ym in ym_set:
                present_months += 1
            else:
                missing.append(ym)

    coverage = round(present_months / total_months * 100) if total_months else (100 if rows else 0)

    if rows == 0:
        badge, message = "no_data", "No data downloaded yet"
    elif is_fresh:
        badge, message = "fresh", f"Up to date — latest {last_ts.strftime('%d %b %Y, %H:%M')}"
    elif days_behind > 0 and missing:
        badge = "partial"
        message = f"Stale ({days_behind}d behind) + missing {len(missing)} month(s): {', '.join(missing[:5])}"
    elif days_behind > 0:
        badge, message = "stale", (
            f"Stale — {days_behind} day(s) behind (latest {last_ts.strftime('%d %b %Y')}, expected {expected})"
        )
    else:
        badge = "partial"
        message = f"Partial — missing {len(missing)} month(s): {', '.join(missing[:5])}"

    base.update(
        {
            "exists": True,
            "row_count": rows,
            "first_ts": first_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "last_ts": last_ts.strftime("%Y-%m-%d %H:%M:%S"),
            "last_date": last_ts.date().isoformat(),
            "expected_date": expected.isoformat(),
            "is_fresh": is_fresh,
            "days_behind": days_behind,
            "coverage": coverage,
            "total_months": total_months,
            "present_months": present_months,
            "missing_months": missing,
            "badge": badge,
            "message": message,
            "requested_from": requested_from,
            "requested_to": requested_to,
            "last_update_at": meta.get("last_update_at"),
            "last_update_status": meta.get("last_update_status"),
        }
    )
    return base


def all_data_status() -> dict:
    return {
        "daily": interval_status("daily"),
        "5min": interval_status("5min"),
        "1min": interval_status("1min"),
    }