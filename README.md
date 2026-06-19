# uridemo

Only-GitHub URI dispatcher demo for frontend, backend, and firmware-style code.

This repo is intentionally usable without npm or PyPI publishing:

- `js/` exposes a browser/Node ESM URI parser and DOM action dispatcher.
- `python/` exposes the same parser and a small dispatcher registry.
- `firmware/` contains tiny C and MicroPython parsers for constrained runtimes.
- `examples/` contains an end-to-end demo with `device://`, `process://`, and `log://`.
- `docker-compose.yml` runs the backend and static frontend.
- `.env` is the single source of truth for ports, HTTP paths, device ids, and demo URI commands.
- `Makefile` wraps the common backend, shell client, test, and Docker commands.

## URI Shape

```text
scheme://target[/resource]/(command|query)/operation
```

Examples:

```text
device://device-01/led/command/set
device://device-01/ping/command/send
process://bridge/command/smoke
log://frontend/session/command/write
log://backend/logs/query/recent
```

`log://` is first-class: frontend, backend, and firmware-style clients can write
logs through URI commands, and the frontend reads backend logs through
`log://backend/logs/query/recent`.

## Run Locally

```bash
make serve
```

The default port comes from `.env`:

```bash
URIDEMO_PORT=39785
```

If the configured port is already in use, the Python server prints a friendly
message and, when `URIDEMO_PORT_FALLBACK=auto`, binds an available port instead
of raising a traceback.

Open:

```text
http://127.0.0.1:39785/
```

Smoke test:

```bash
make smoke
```

## Shell Client

The shell client dispatches the same URI commands through the backend HTTP
transport. It uses URI constants from `.env`, so the shell, frontend, backend,
and firmware-style adapter share one command contract.

```bash
make shell-commands
make shell-state
make shell-led-on
make shell-ping
make shell-process
make shell-log
make shell-logs
make shell-call
```

Direct usage:

```bash
python3 examples/shell-client.py led on
python3 examples/shell-client.py log --layer firmware "firmware log from shell"
```

## Docker Compose

```bash
make docker-up
```

The host and container port are read from `.env`:

```bash
URIDEMO_PORT=39785
```

Open:

```text
http://127.0.0.1:39785/
```

Smoke against compose:

```bash
make docker-smoke
```

Stop compose:

```bash
make docker-down
```

Run all local checks:

```bash
make test
```

## Use From GitHub

Python:

```bash
pip install "git+https://github.com/tellmesh/uridemo.git@main#subdirectory=python"
```

Browser/Node can import or vendor `js/index.js` directly from a checkout,
submodule, subtree, or raw GitHub URL.
