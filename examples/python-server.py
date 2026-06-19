from __future__ import annotations

import errno
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from env import env, env_int, public_config
from uri_dispatch import UriDispatcher, UriParts, parse_uri

API_PATH = env("URIDEMO_API_PATH")
CONFIG_PATH = env("URIDEMO_CONFIG_PATH")
DEVICE_ID = env("URIDEMO_DEVICE_ID")
FRONTEND_PATH = env("URIDEMO_FRONTEND_PATH")
HEALTH_PATH = env("URIDEMO_HEALTH_PATH")
LOG_LIMIT = env_int("URIDEMO_LOG_LIMIT")
LOG_STORE_LIMIT = env_int("URIDEMO_LOG_STORE_LIMIT")
PROCESS_TARGET = env("URIDEMO_PROCESS_TARGET")

URI_DEVICE_LED_SET = env("URI_DEVICE_LED_SET")
URI_DEVICE_PING_SEND = env("URI_DEVICE_PING_SEND")
URI_DEVICE_STATE_CURRENT = env("URI_DEVICE_STATE_CURRENT")
URI_DEVICE_TELEMETRY_LATEST = env("URI_DEVICE_TELEMETRY_LATEST")
URI_LOG_BACKEND_DEVICE_WRITE = env("URI_LOG_BACKEND_DEVICE_WRITE")
URI_LOG_BACKEND_LOGS_RECENT = env("URI_LOG_BACKEND_LOGS_RECENT")
URI_LOG_BACKEND_PROCESS_WRITE = env("URI_LOG_BACKEND_PROCESS_WRITE")
URI_LOG_FIRMWARE_DEVICE_WRITE = env("URI_LOG_FIRMWARE_DEVICE_WRITE")
URI_PROCESS_SMOKE = env("URI_PROCESS_SMOKE")


class DemoState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.booted_at = time.time()
        self.device = {
            "device_id": DEVICE_ID,
            "last_command": "boot",
            "last_command_uri": None,
            "led": False,
            "online": True,
        }
        self.logs: list[dict] = []

    def append_log(self, uri: str, payload: dict, context: dict, layer: str) -> dict:
        entry = {
            "context": context,
            "layer": layer,
            "payload": payload,
            "ts": time.time(),
            "uri": uri,
        }
        with self.lock:
            self.logs.append(entry)
            self.logs = self.logs[-LOG_STORE_LIMIT:]
        return entry

    def recent_logs(self, limit: int = LOG_LIMIT) -> list[dict]:
        with self.lock:
            return list(self.logs[-limit:])

    def current_state(self) -> dict:
        with self.lock:
            uptime_ms = int((time.time() - self.booted_at) * 1000)
            return {
                **self.device,
                "uptime_ms": uptime_ms,
                "uri": URI_DEVICE_STATE_CURRENT,
            }


state = DemoState()
dispatcher = UriDispatcher()


def handle_log(parts: UriParts, payload: dict, context: dict) -> dict:
    if parts.kind == "command" and parts.operation == "write":
        entry = state.append_log(parts.raw, payload, context, parts.target)
        return {"ok": True, "log": entry, "via": "log-store"}
    if parts.raw == URI_LOG_BACKEND_LOGS_RECENT:
        return {"ok": True, "logs": state.recent_logs(int(payload.get("limit") or LOG_LIMIT)), "via": "log-store"}
    raise KeyError(f"unknown log URI: {parts.raw}")


def handle_device(parts: UriParts, payload: dict, context: dict) -> dict:
    if parts.target != DEVICE_ID:
        raise KeyError(f"unknown device: {parts.target}")
    if parts.raw == URI_DEVICE_LED_SET:
        on = bool(payload.get("on"))
        with state.lock:
            state.device["led"] = on
            state.device["last_command"] = "led:on" if on else "led:off"
            state.device["last_command_uri"] = parts.raw
        state.append_log(URI_LOG_BACKEND_DEVICE_WRITE, {"event": "device.led", "on": on}, context, "backend")
        return {"ok": True, "state": state.current_state(), "via": "device-adapter"}
    if parts.raw == URI_DEVICE_PING_SEND:
        with state.lock:
            state.device["last_command"] = "ping"
            state.device["last_command_uri"] = parts.raw
        state.append_log(URI_LOG_FIRMWARE_DEVICE_WRITE, {"event": "pong", "payload": payload}, context, "firmware")
        return {"ok": True, "event": "pong", "via": "firmware-simulator"}
    if parts.raw == URI_DEVICE_STATE_CURRENT:
        return {"ok": True, "state": state.current_state(), "via": "device-adapter"}
    if parts.raw == URI_DEVICE_TELEMETRY_LATEST:
        current = state.current_state()
        return {
            "ok": True,
            "telemetry": {
                "device_id": current["device_id"],
                "led": current["led"],
                "uptime_ms": current["uptime_ms"],
                "voltage_v": 3.3,
            },
            "via": "device-adapter",
        }
    raise KeyError(f"unknown device URI: {parts.raw}")


def handle_process(parts: UriParts, payload: dict, context: dict) -> dict:
    if parts.raw != URI_PROCESS_SMOKE or parts.target != PROCESS_TARGET:
        raise KeyError(f"unknown process URI: {parts.raw}")
    steps = []
    for uri, step_payload in [
        (URI_LOG_BACKEND_PROCESS_WRITE, {"event": "process.started", "payload": payload}),
        (URI_DEVICE_LED_SET, {"on": True}),
        (URI_DEVICE_PING_SEND, {"source": "process"}),
        (URI_DEVICE_TELEMETRY_LATEST, {}),
        (URI_LOG_BACKEND_LOGS_RECENT, {"limit": LOG_LIMIT}),
    ]:
        steps.append({"uri": uri, "result": dispatcher.dispatch(uri, step_payload, {**context, "process": parts.raw})})
    return {"ok": True, "flow_id": f"{PROCESS_TARGET}.smoke", "steps": steps, "via": "process"}


dispatcher.register(parse_uri(URI_DEVICE_STATE_CURRENT).scheme, handle_device)
dispatcher.register(parse_uri(URI_LOG_BACKEND_LOGS_RECENT).scheme, handle_log)
dispatcher.register(parse_uri(URI_PROCESS_SMOKE).scheme, handle_process)


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == HEALTH_PATH:
            self._json(200, {"ok": True, "service": "uridemo"})
        elif path == CONFIG_PATH:
            self._json(200, {"ok": True, "config": public_config()})
        elif path == "/":
            self._static(FRONTEND_PATH)
        else:
            self._static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()
        if path != API_PATH:
            self._json(404, {"ok": False, "error": f"unknown endpoint: {path}"})
            return
        uri = str(body.get("uri") or "")
        payload = body.get("payload") or {}
        context = body.get("context") or {}
        try:
            parts = parse_uri(uri)
            result = dispatcher.dispatch(uri, payload, {
                **context,
                "cqrs": parts.to_dict(),
            })
        except ValueError as exc:
            self._json(400, {"ok": False, "error": str(exc), "uri": uri})
            return
        except KeyError as exc:
            self._json(404, {"ok": False, "error": str(exc), "uri": uri})
            return
        self._json(200, {"uri": uri, **result})

    def log_message(self, _fmt: str, *_args) -> None:
        return

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, status: int, data: dict) -> None:
        raw = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _static(self, path: str) -> None:
        candidate = (ROOT / path.lstrip("/")).resolve()
        if not str(candidate).startswith(str(ROOT)) or not candidate.is_file():
            self._json(404, {"ok": False, "error": "not found"})
            return
        if candidate == (ROOT / FRONTEND_PATH.lstrip("/")).resolve():
            html = candidate.read_text(encoding="utf-8")
            html = html.replace("__URIDEMO_CONFIG__", json.dumps(public_config(), ensure_ascii=False, sort_keys=True))
            raw = html.encode("utf-8")
        else:
            raw = candidate.read_bytes()
        content_type = "text/html; charset=utf-8" if candidate.suffix == ".html" else "text/javascript; charset=utf-8"
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def bind_server(host: str, port: int) -> ReusableThreadingHTTPServer:
    try:
        return ReusableThreadingHTTPServer((host, port), Handler)
    except OSError as exc:
        if exc.errno != errno.EADDRINUSE:
            raise
        if env("URIDEMO_PORT_FALLBACK", "strict").lower() not in {"auto", "random", "1", "true"}:
            raise SystemExit(f"Cannot bind {host}:{port}: address already in use") from exc
        server = ReusableThreadingHTTPServer((host, 0), Handler)
        actual_port = server.server_address[1]
        print(f"Port {port} is busy; using {actual_port}.", file=sys.stderr, flush=True)
        return server


def main() -> int:
    host = os.environ.get("URIDEMO_BIND_HOST", env("URIDEMO_BIND_HOST"))
    port = int(os.environ.get("URIDEMO_PORT", env("URIDEMO_PORT")))
    server = bind_server(host, port)
    actual_port = server.server_address[1]
    public_host = env("URIDEMO_PUBLIC_HOST", "127.0.0.1")
    print(f"uridemo listening on http://{public_host}:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("uridemo stopped", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
