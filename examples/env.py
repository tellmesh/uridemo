from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"

_LOADED = False
_DOTENV_KEYS: set[str] = set()


def _parse_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if not key:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_env(path: Path = ENV_PATH, override: bool = False) -> dict[str, str]:
    global _LOADED
    if _LOADED and not override:
        return dict(os.environ)
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_line(line)
            if not parsed:
                continue
            key, value = parsed
            _DOTENV_KEYS.add(key)
            if override or key not in os.environ:
                os.environ[key] = value
    _LOADED = True
    return dict(os.environ)


def env(name: str, default: str | None = None) -> str:
    load_env()
    value = os.environ.get(name, default)
    if value is None:
        raise KeyError(f"missing {name} in {ENV_PATH}")
    return value


def env_int(name: str, default: int | None = None) -> int:
    fallback = None if default is None else str(default)
    return int(env(name, fallback))


def env_float(name: str, default: float | None = None) -> float:
    fallback = None if default is None else str(default)
    return float(env(name, fallback))


def base_url() -> str:
    load_env()
    override = os.environ.get("URIDEMO_BASE_URL")
    if override:
        return override
    return f"http://{env('URIDEMO_PUBLIC_HOST')}:{env('URIDEMO_PORT')}"


def node_base_url() -> str:
    load_env()
    override = os.environ.get("URIDEMO_NODE_BASE_URL")
    if override:
        return override
    return f"http://{env('URIDEMO_NODE_HOST')}:{env('URIDEMO_NODE_PORT')}"


def public_config() -> dict[str, str]:
    load_env()
    return {
        key: os.environ[key]
        for key in sorted(_DOTENV_KEYS)
        if key.startswith("URIDEMO_") or key.startswith("URI_")
    }
