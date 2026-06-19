# uridemo

Only-GitHub URI dispatcher demo for frontend, backend, and firmware-style code.

This repo is intentionally usable without npm or PyPI publishing:

- `js/` exposes a browser/Node ESM URI parser and DOM action dispatcher.
- `python/` exposes the same parser and a small dispatcher registry.
- `firmware/` contains tiny C and MicroPython parsers for constrained runtimes.
- `examples/` contains an end-to-end demo with `device://`, `process://`, and `log://`.
- `docker-compose.yml` runs the backend and static frontend.

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
python3 examples/python-server.py
```

If `8080` is already in use:

```bash
URIDEMO_PORT=39785 python3 examples/python-server.py
python3 examples/smoke.py http://127.0.0.1:39785
```

Open:

```text
http://127.0.0.1:8080/
```

Smoke test:

```bash
python3 examples/smoke.py
```

## Docker Compose

```bash
docker compose up --build
```

The host port defaults to `18080`. Override it when needed:

```bash
URIDEMO_PORT=35921 docker compose up --build
```

Open:

```text
http://127.0.0.1:18080/
```

Smoke against compose:

```bash
python3 examples/smoke.py http://127.0.0.1:18080
```

## Use From GitHub

Python:

```bash
pip install "git+https://github.com/tellmesh/uridemo.git@main#subdirectory=python"
```

Browser/Node can import or vendor `js/index.js` directly from a checkout,
submodule, subtree, or raw GitHub URL.
