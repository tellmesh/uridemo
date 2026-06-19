# URI Dispatch Spec

`uridemo` uses one URI grammar across frontend, backend, and firmware adapters.

```text
scheme://target[/resource]/(command|query)/operation
```

Parsed fields:

| Field | Example | Description |
|---|---|---|
| `scheme` | `device` | Capability package or domain. |
| `target` | `device-01` | Concrete device, process, service, or actor. |
| `resource` | `led` | Optional resource. Defaults to the scheme for short URIs like `process://bridge/command/smoke`. |
| `kind` | `command` | `command` mutates or triggers; `query` reads. |
| `operation` | `set` | Operation name. |

## Required Schemes

### `device://`

```text
device://device-01/led/command/set
device://device-01/ping/command/send
device://device-01/state/query/current
device://device-01/telemetry/query/latest
```

### `process://`

```text
process://bridge/command/smoke
```

### `log://`

```text
log://frontend/session/command/write
log://frontend/action/command/write
log://backend/logs/query/recent
log://firmware/device-01/command/write
```

`log://` is the cross-layer logging plane. The frontend writes session/action
logs, backend handlers write backend logs, firmware-style clients write firmware
logs, and the UI queries backend-visible logs with `log://backend/logs/query/recent`.

## Dispatch Model

1. Frontend reads `data-uri` or `href="#scheme://..."`.
2. Frontend posts `{uri, payload, context}` to `/api/dispatch`.
3. Backend parses URI and routes by `scheme`.
4. Backend maps `device://` to device/transport state, `process://` to local flows, and `log://` to a log store.
5. Firmware adapters can parse the same URI or receive backend-translated transport topics.
