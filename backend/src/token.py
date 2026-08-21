import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

from .config import DATA_DIR, get_access_token, get_api_key, get_api_secret

STATE_FILE = Path(DATA_DIR) / "token_state.json"
CACHE_HOURS = 6
LTP_URL = "https://api.upstox.com/v2/market-quote/ltp"
INSTRUMENT_KEY = "NSE_INDEX|Nifty 50"


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_status() -> dict:
    token = get_access_token()
    state = _load_state()
    masked = f"****...{token[-4:]}" if len(token) > 4 else ("***" if token else None)
    return {
        "configured": bool(token),
        "api_key_configured": bool(get_api_key()),
        "api_secret_configured": bool(get_api_secret()),
        "token_length": len(token),
        "masked_token": masked,
        "valid": state.get("valid"),
        "last_price": state.get("last_price"),
        "last_validated_at": state.get("last_validated_at"),
        "updated_at": state.get("updated_at"),
    }


def validate_token(token: str) -> dict:
    """Save token then validate against the LTP quote API.

    The historical-candle API accepts bad tokens, so the LTP endpoint is the
    only reliable validity check.
    """
    from .config import set_access_token

    set_access_token(token)

    result = _ltp_check(token)
    result["updated_at"] = datetime.now().astimezone().isoformat()
    result["last_validated_at"] = result["updated_at"]
    state = _load_state()
    state.update(result)
    _save_state(state)
    return result


def validate_persist(creds: dict) -> dict:
    """Validate without persisting first; persist only on success.

    Empty/missing fields fall back to the currently configured values, so a
    failed validation can never clobber a working token.
    """
    from .config import set_env_var

    token = (creds.get("token") or "").strip() or get_access_token()
    api_key = (creds.get("api_key") or "").strip() or get_api_key()
    api_secret = (creds.get("api_secret") or "").strip() or get_api_secret()

    result = _ltp_check(token)
    result["updated_at"] = datetime.now().astimezone().isoformat()
    result["last_validated_at"] = result["updated_at"]

    if result.get("valid"):
        if (creds.get("token") or "").strip():
            set_env_var("ACCESS_TOKEN", token)
        if (creds.get("api_key") or "").strip():
            set_env_var("API_KEY", api_key)
        if (creds.get("api_secret") or "").strip():
            set_env_var("API_SECRET", api_secret)

    state = _load_state()
    state.update(result)
    _save_state(state)
    return result


def check_token() -> dict:
    token = get_access_token()
    if not token:
        return {"valid": False, "message": "No token configured"}
    result = _ltp_check(token)
    result["updated_at"] = datetime.now().astimezone().isoformat()
    result["last_validated_at"] = result["updated_at"]
    state = _load_state()
    state.update(result)
    _save_state(state)
    return result


def _ltp_check(token: str) -> dict:
    key = quote(INSTRUMENT_KEY, safe="")
    url = f"{LTP_URL}?instrument_key={key}"
    try:
        resp = requests.get(
            url,
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as e:
        return {
            "valid": False,
            "last_price": None,
            "status_code": None,
            "message": f"Network error: {e}",
        }

    if resp.status_code in (401, 403):
        return {
            "valid": False,
            "last_price": None,
            "status_code": resp.status_code,
            "message": f"Token rejected by Upstox ({resp.status_code})",
        }
    if resp.status_code != 200:
        return {
            "valid": False,
            "last_price": None,
            "status_code": resp.status_code,
            "message": f"Upstox returned {resp.status_code}",
        }

    data = resp.json()
    quote_data = None
    for val in (data.get("data") or {}).values():
        if val.get("instrument_token") == INSTRUMENT_KEY or "Nifty 50" in str(val.get("instrument_token", "")):
            quote_data = val
            break
    if quote_data is None:
        return {
            "valid": False,
            "last_price": None,
            "status_code": resp.status_code,
            "message": "No quote data returned — token may be invalid",
        }
    last_price = quote_data.get("last_price")
    return {
        "valid": True,
        "last_price": float(last_price),
        "status_code": resp.status_code,
        "message": f"Token valid — Nifty 50 LTP {float(last_price):.2f}",
    }


def is_valid(cached_ok: bool = True) -> bool:
    """True if a valid token is configured (optionally within the cache window)."""
    state = _load_state()
    if state.get("valid") is True:
        if not cached_ok:
            return True
        last = state.get("last_validated_at")
        if last:
            try:
                ts = datetime.fromisoformat(last)
                if (datetime.now(ts.tzinfo) - ts).total_seconds() < CACHE_HOURS * 3600:
                    return True
            except Exception:
                pass
        # valid but cache stale -> re-validate
        return check_token().get("valid") is True
    return check_token().get("valid") is True