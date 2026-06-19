from __future__ import annotations

import json
import sys
import time
import urllib.request

from env import base_url, env, env_float, env_int

API_PATH = env("URIDEMO_API_PATH")
BASE = sys.argv[1] if len(sys.argv) > 1 else base_url()
HEALTH_POLL_SECONDS = env_float("URIDEMO_HEALTH_POLL_SECONDS")
HEALTH_TIMEOUT_SECONDS = env_float("URIDEMO_HEALTH_TIMEOUT_SECONDS")
HEALTH_PATH = env("URIDEMO_HEALTH_PATH")
HTTP_TIMEOUT_SECONDS = env_float("URIDEMO_HTTP_TIMEOUT_SECONDS")
LOG_LIMIT = env_int("URIDEMO_LOG_LIMIT")

URI_DEVICE_STATE_CURRENT = env("URI_DEVICE_STATE_CURRENT")
URI_LOG_BACKEND_DEVICE_WRITE = env("URI_LOG_BACKEND_DEVICE_WRITE")
URI_LOG_BACKEND_LOGS_RECENT = env("URI_LOG_BACKEND_LOGS_RECENT")
URI_LOG_BACKEND_PROCESS_WRITE = env("URI_LOG_BACKEND_PROCESS_WRITE")
URI_LOG_FIRMWARE_DEVICE_WRITE = env("URI_LOG_FIRMWARE_DEVICE_WRITE")
URI_LOG_FRONTEND_SESSION_WRITE = env("URI_LOG_FRONTEND_SESSION_WRITE")
URI_PROCESS_SMOKE = env("URI_PROCESS_SMOKE")


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as res:
        return json.loads(res.read().decode("utf-8"))


def wait_health() -> None:
    deadline = time.time() + HEALTH_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            if request("GET", HEALTH_PATH).get("ok"):
                return
        except Exception:
            time.sleep(HEALTH_POLL_SECONDS)
    raise SystemExit(f"server did not become healthy: {BASE}")


wait_health()
request("POST", API_PATH, {
    "uri": URI_LOG_FRONTEND_SESSION_WRITE,
    "payload": {"event": "smoke.started"},
    "context": {"source": "smoke"},
})
flow = request("POST", API_PATH, {
    "uri": URI_PROCESS_SMOKE,
    "payload": {"source": "smoke"},
    "context": {"source": "smoke"},
})
if not flow.get("ok"):
    raise SystemExit(f"process smoke failed: {flow}")

state = request("POST", API_PATH, {"uri": URI_DEVICE_STATE_CURRENT})
if state.get("state", {}).get("led") is not True:
    raise SystemExit(f"LED was not set by process: {state}")

logs = request("POST", API_PATH, {
    "uri": URI_LOG_BACKEND_LOGS_RECENT,
    "payload": {"limit": LOG_LIMIT * 2},
})
uris = {entry.get("uri") for entry in logs.get("logs", [])}
required = {
    URI_LOG_BACKEND_DEVICE_WRITE,
    URI_LOG_BACKEND_PROCESS_WRITE,
    URI_LOG_FIRMWARE_DEVICE_WRITE,
    URI_LOG_FRONTEND_SESSION_WRITE,
}
missing = sorted(required - uris)
if missing:
    raise SystemExit(f"missing log entries: {missing}\n{logs}")

print(json.dumps({
    "flow_steps": [step["uri"] for step in flow["steps"]],
    "logs": logs["logs"],
    "ok": True,
    "state": state["state"],
}, indent=2, sort_keys=True))
