from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))

from uri_dispatch import UriDispatcher, UriParts, parse_uri


class DemoState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.booted_at = time.time()
        self.device = {
            "device_id": "device-01",
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
            self.logs = self.logs[-200:]
        return entry

    def recent_logs(self, limit: int = 50) -> list[dict]:
        with self.lock:
            return list(self.logs[-limit:])

    def current_state(self) -> dict:
        with self.lock:
            uptime_ms = int((time.time() - self.booted_at) * 1000)
            return {
                **self.device,
                "uptime_ms": uptime_ms,
                "uri": "device://device-01/state/query/current",
            }


state = DemoState()
dispatcher = UriDispatcher()


def handle_log(parts: UriParts, payload: dict, context: dict) -> dict:
    if parts.kind == "command" and parts.operation == "write":
        entry = state.append_log(parts.raw, payload, context, parts.target)
        return {"ok": True, "log": entry, "via": "log-store"}
    if parts.kind == "query" and parts.target == "backend" and parts.resource == "logs":
        return {"ok": True, "logs": state.recent_logs(int(payload.get("limit") or 50)), "via": "log-store"}
    raise KeyError(f"unknown log URI: {parts.raw}")


def handle_device(parts: UriParts, payload: dict, context: dict) -> dict:
    if parts.target != "device-01":
        raise KeyError(f"unknown device: {parts.target}")
    if parts.kind == "command" and parts.resource == "led" and parts.operation == "set":
        on = bool(payload.get("on"))
        with state.lock:
            state.device["led"] = on
            state.device["last_command"] = "led:on" if on else "led:off"
            state.device["last_command_uri"] = parts.raw
        state.append_log("log://backend/device/command/write", {"event": "device.led", "on": on}, context, "backend")
        return {"ok": True, "state": state.current_state(), "via": "device-adapter"}
    if parts.kind == "command" and parts.resource == "ping":
        with state.lock:
            state.device["last_command"] = "ping"
            state.device["last_command_uri"] = parts.raw
        state.append_log("log://firmware/device-01/command/write", {"event": "pong", "payload": payload}, context, "firmware")
        return {"ok": True, "event": "pong", "via": "firmware-simulator"}
    if parts.kind == "query" and parts.resource == "state":
        return {"ok": True, "state": state.current_state(), "via": "device-adapter"}
    if parts.kind == "query" and parts.resource == "telemetry":
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
    if parts.target != "bridge" or parts.operation != "smoke":
        raise KeyError(f"unknown process URI: {parts.raw}")
    steps = []
    for uri, step_payload in [
        ("log://backend/process/command/write", {"event": "process.started", "payload": payload}),
        ("device://device-01/led/command/set", {"on": True}),
        ("device://device-01/ping/command/send", {"source": "process"}),
        ("device://device-01/telemetry/query/latest", {}),
        ("log://backend/logs/query/recent", {"limit": 50}),
    ]:
        steps.append({"uri": uri, "result": dispatcher.dispatch(uri, step_payload, {**context, "process": parts.raw})})
    return {"ok": True, "flow_id": "bridge.smoke", "steps": steps, "via": "process"}


dispatcher.register("device", handle_device)
dispatcher.register("log", handle_log)
dispatcher.register("process", handle_process)


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json(200, {"ok": True, "service": "uridemo"})
        elif path == "/":
            self._static("/examples/frontend.html")
        else:
            self._static(path)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()
        if path != "/api/dispatch":
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
        raw = candidate.read_bytes()
        content_type = "text/html; charset=utf-8" if candidate.suffix == ".html" else "text/javascript; charset=utf-8"
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> int:
    host = os.environ.get("URIDEMO_HOST", "0.0.0.0")
    port = int(os.environ.get("URIDEMO_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"uridemo listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
