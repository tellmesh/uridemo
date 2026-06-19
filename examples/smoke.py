from __future__ import annotations

import json
import sys
import time
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080"


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as res:
        return json.loads(res.read().decode("utf-8"))


def wait_health() -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            if request("GET", "/health").get("ok"):
                return
        except Exception:
            time.sleep(0.2)
    raise SystemExit(f"server did not become healthy: {BASE}")


wait_health()
request("POST", "/api/dispatch", {
    "uri": "log://frontend/session/command/write",
    "payload": {"event": "smoke.started"},
    "context": {"source": "smoke"},
})
flow = request("POST", "/api/dispatch", {
    "uri": "process://bridge/command/smoke",
    "payload": {"source": "smoke"},
    "context": {"source": "smoke"},
})
if not flow.get("ok") or flow.get("flow_id") != "bridge.smoke":
    raise SystemExit(f"process smoke failed: {flow}")

state = request("POST", "/api/dispatch", {"uri": "device://device-01/state/query/current"})
if state.get("state", {}).get("led") is not True:
    raise SystemExit(f"LED was not set by process: {state}")

logs = request("POST", "/api/dispatch", {
    "uri": "log://backend/logs/query/recent",
    "payload": {"limit": 100},
})
uris = {entry.get("uri") for entry in logs.get("logs", [])}
required = {
    "log://frontend/session/command/write",
    "log://backend/process/command/write",
    "log://backend/device/command/write",
    "log://firmware/device-01/command/write",
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
