"""
CLI configuration — stores TSK key and base URL in ~/.selfconnect/config.json
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".selfconnect"
CONFIG_FILE = CONFIG_DIR / "config.json"


def _load() -> dict:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2))
    CONFIG_FILE.chmod(0o600)  # owner-read-only


def get_tsk_key() -> Optional[str]:
    """Return TSK key from env var or config file."""
    return os.environ.get("SELFCONNECT_TSK_KEY") or _load().get("tsk_key")


def get_base_url() -> str:
    return (
        os.environ.get("SELFCONNECT_BASE_URL")
        or _load().get("base_url")
        or "https://api.selfconnect.ai"
    )


def save_credentials(tsk_key: str, base_url: str = "https://api.selfconnect.ai") -> None:
    data = _load()
    data["tsk_key"] = tsk_key
    data["base_url"] = base_url
    _save(data)


def clear_credentials() -> None:
    data = _load()
    data.pop("tsk_key", None)
    _save(data)


def is_logged_in() -> bool:
    return bool(get_tsk_key())
