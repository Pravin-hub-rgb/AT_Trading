import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
DATA_DIR = ROOT_DIR / "data"
ENV_FILE = BACKEND_DIR / ".env"

load_dotenv(ENV_FILE)

SETTABLE_KEYS = {"ACCESS_TOKEN", "API_KEY", "API_SECRET"}


def _get(key: str) -> str:
    return os.environ.get(key, "").strip()


def get_access_token() -> str:
    return _get("ACCESS_TOKEN")


def get_api_key() -> str:
    return _get("API_KEY")


def get_api_secret() -> str:
    return _get("API_SECRET")


def token_configured() -> bool:
    return bool(get_access_token())


def set_env_var(key: str, value: str) -> None:
    if key not in SETTABLE_KEYS:
        raise ValueError(f"Not a settable env key: {key}")
    value = value.strip()
    lines = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
    found = False
    out = []
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(out) + "\n")
    os.environ[key] = value


def set_access_token(token: str) -> None:
    set_env_var("ACCESS_TOKEN", token)


DATA_DIR.mkdir(exist_ok=True)