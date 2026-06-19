from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

from env import base_url, env, env_float, env_int, public_config

API_PATH = env("URIDEMO_API_PATH")
BASE_URL = base_url()
CONFIG_PATH = env("URIDEMO_CONFIG_PATH")
HEALTH_PATH = env("URIDEMO_HEALTH_PATH")
HTTP_TIMEOUT_SECONDS = env_float("URIDEMO_HTTP_TIMEOUT_SECONDS")
LOG_LIMIT = env_int("URIDEMO_LOG_LIMIT")

URI_DEVICE_LED_SET = env("URI_DEVICE_LED_SET")
URI_DEVICE_PING_SEND = env("URI_DEVICE_PING_SEND")
URI_DEVICE_STATE_CURRENT = env("URI_DEVICE_STATE_CURRENT")
URI_DEVICE_TELEMETRY_LATEST = env("URI_DEVICE_TELEMETRY_LATEST")
URI_LOG_BACKEND_ACTION_WRITE = env("URI_LOG_BACKEND_ACTION_WRITE")
URI_LOG_BACKEND_LOGS_RECENT = env("URI_LOG_BACKEND_LOGS_RECENT")
URI_LOG_FIRMWARE_ACTION_WRITE = env("URI_LOG_FIRMWARE_ACTION_WRITE")
URI_LOG_FRONTEND_ACTION_WRITE = env("URI_LOG_FRONTEND_ACTION_WRITE")
URI_LOG_SHELL_ACTION_WRITE = env("URI_LOG_SHELL_ACTION_WRITE")
URI_PROCESS_SMOKE = env("URI_PROCESS_SMOKE")


def parse_json(raw: str | None, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    if raw is None:
        return fallback or {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON: {raw}") from exc
    if not isinstance(value, dict):
        raise SystemExit("JSON value must be an object")
    return value


def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise SystemExit(f"HTTP {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"cannot reach {url}: {exc.reason}") from exc


def endpoint(base_url: str, api_path: str) -> str:
    return base_url.rstrip("/") + api_path


def dispatch(
    base_url: str,
    api_path: str,
    uri: str,
    payload: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return request_json("POST", endpoint(base_url, api_path), {
        "context": {"source": "shell", "transport": "backend-http", **(context or {})},
        "payload": payload or {},
        "uri": uri,
    })


def print_json(data: dict[str, Any], pretty: bool) -> None:
    if pretty:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(json.dumps(data, sort_keys=True))


def command_uri_map() -> dict[str, str]:
    return {
        key: value
        for key, value in public_config().items()
        if key.startswith("URI_")
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="URI shell client for uridemo")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--api-path", default=API_PATH)
    parser.add_argument("--pretty", action="store_true", default=True)
    sub = parser.add_subparsers(dest="command", required=True)

    call = sub.add_parser("call", help="dispatch any URI")
    call.add_argument("uri")
    call.add_argument("--payload", default="{}")
    call.add_argument("--context", default="{}")

    sub.add_parser("state", help="query firmware-style device state")
    sub.add_parser("telemetry", help="query firmware-style telemetry")
    sub.add_parser("ping", help="send firmware-style ping")
    sub.add_parser("process", help="run process flow")
    sub.add_parser("commands", help="print URI constants loaded from .env")
    sub.add_parser("config", help="read backend config generated from .env")
    sub.add_parser("health", help="read backend health endpoint")

    led = sub.add_parser("led", help="set firmware-style LED state")
    led.add_argument("state", choices=["on", "off"])

    logs = sub.add_parser("logs", help="query backend-visible logs")
    logs.add_argument("--limit", type=int, default=LOG_LIMIT)

    log = sub.add_parser("log", help="write log:// entry for a layer")
    log.add_argument("message", nargs="?", default="")
    log.add_argument("--event", default="shell.message")
    log.add_argument("--layer", choices=["backend", "firmware", "frontend", "shell"], default="shell")
    log.add_argument("--detail", default="{}")
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "commands":
        return {"ok": True, "uris": command_uri_map()}
    if args.command == "config":
        return request_json("GET", args.base_url.rstrip("/") + CONFIG_PATH)
    if args.command == "health":
        return request_json("GET", args.base_url.rstrip("/") + HEALTH_PATH)
    if args.command == "call":
        return dispatch(args.base_url, args.api_path, args.uri, parse_json(args.payload), parse_json(args.context))
    if args.command == "state":
        return dispatch(args.base_url, args.api_path, URI_DEVICE_STATE_CURRENT)
    if args.command == "telemetry":
        return dispatch(args.base_url, args.api_path, URI_DEVICE_TELEMETRY_LATEST)
    if args.command == "ping":
        return dispatch(args.base_url, args.api_path, URI_DEVICE_PING_SEND, {"source": "shell"})
    if args.command == "process":
        return dispatch(args.base_url, args.api_path, URI_PROCESS_SMOKE, {"source": "shell"})
    if args.command == "led":
        return dispatch(args.base_url, args.api_path, URI_DEVICE_LED_SET, {"on": args.state == "on"})
    if args.command == "logs":
        return dispatch(args.base_url, args.api_path, URI_LOG_BACKEND_LOGS_RECENT, {"limit": args.limit})
    if args.command == "log":
        uri_by_layer = {
            "backend": URI_LOG_BACKEND_ACTION_WRITE,
            "firmware": URI_LOG_FIRMWARE_ACTION_WRITE,
            "frontend": URI_LOG_FRONTEND_ACTION_WRITE,
            "shell": URI_LOG_SHELL_ACTION_WRITE,
        }
        return dispatch(args.base_url, args.api_path, uri_by_layer[args.layer], {
            "detail": parse_json(args.detail),
            "event": args.event,
            "message": args.message,
        })
    raise SystemExit(f"unknown command: {args.command}")


def main() -> int:
    args = build_parser().parse_args()
    print_json(run(args), args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
