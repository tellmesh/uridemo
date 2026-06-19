ifneq (,$(wildcard .env))
include .env
export
endif

PYTHON ?= python3
NODE ?= node
CC ?= cc

BASE_URL ?= http://$(URIDEMO_PUBLIC_HOST):$(URIDEMO_PORT)
PAYLOAD ?= {}
URI ?= $(URI_DEVICE_STATE_CURRENT)

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available commands.
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z0-9_.-]+:.*##/ {printf "%-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: serve
serve: ## Run Python backend and frontend.
	$(PYTHON) examples/python-server.py

.PHONY: node-serve
node-serve: ## Run Node parser demo server.
	$(NODE) examples/node-server.js

.PHONY: smoke
smoke: ## Run end-to-end smoke test against BASE_URL.
	$(PYTHON) examples/smoke.py $(BASE_URL)

.PHONY: shell
shell: ## Run shell URI client, pass ARGS="state|logs|call ...".
	$(PYTHON) examples/shell-client.py $(ARGS)

.PHONY: shell-health
shell-health: ## Query backend health through shell client.
	$(PYTHON) examples/shell-client.py health

.PHONY: shell-config
shell-config: ## Print backend config generated from .env.
	$(PYTHON) examples/shell-client.py config

.PHONY: shell-commands
shell-commands: ## Print URI command constants from .env.
	$(PYTHON) examples/shell-client.py commands

.PHONY: shell-state
shell-state: ## Query device state through URI shell client.
	$(PYTHON) examples/shell-client.py state

.PHONY: shell-telemetry
shell-telemetry: ## Query device telemetry through URI shell client.
	$(PYTHON) examples/shell-client.py telemetry

.PHONY: shell-led-on
shell-led-on: ## Send device LED on command through URI shell client.
	$(PYTHON) examples/shell-client.py led on

.PHONY: shell-led-off
shell-led-off: ## Send device LED off command through URI shell client.
	$(PYTHON) examples/shell-client.py led off

.PHONY: shell-ping
shell-ping: ## Send firmware-style ping through URI shell client.
	$(PYTHON) examples/shell-client.py ping

.PHONY: shell-process
shell-process: ## Run process:// smoke flow through URI shell client.
	$(PYTHON) examples/shell-client.py process

.PHONY: shell-log
shell-log: ## Write log://shell action through URI shell client.
	$(PYTHON) examples/shell-client.py log "hello from shell"

.PHONY: shell-logs
shell-logs: ## Read backend-visible logs through URI shell client.
	$(PYTHON) examples/shell-client.py logs

.PHONY: shell-call
shell-call: ## Dispatch arbitrary URI, pass URI=... PAYLOAD='{}'.
	$(PYTHON) examples/shell-client.py call "$(URI)" --payload '$(PAYLOAD)'

.PHONY: test
test: test-python test-js test-c test-examples ## Run all local tests.

.PHONY: test-python
test-python: ## Run Python package tests.
	PYTHONPATH=python pytest python/tests -q

.PHONY: test-js
test-js: ## Run JS tests.
	$(NODE) --test js/*.test.js

.PHONY: test-c
test-c: ## Compile firmware C parser with warnings as errors.
	$(CC) -Wall -Wextra -Werror -c firmware/c/uri_dispatch.c -o /tmp/uridemo-uri_dispatch.o

.PHONY: test-examples
test-examples: ## Syntax-check examples.
	$(PYTHON) -m py_compile examples/env.py examples/python-server.py examples/shell-client.py examples/smoke.py firmware/micropython/uri_dispatch.py
	$(NODE) --check examples/node-server.js

.PHONY: docker-build
docker-build: ## Build Docker image through Compose.
	docker compose build

.PHONY: docker-up
docker-up: ## Start Docker Compose service.
	docker compose up --build -d

.PHONY: docker-smoke
docker-smoke: ## Run smoke test against Compose service.
	$(PYTHON) examples/smoke.py $(BASE_URL)

.PHONY: docker-down
docker-down: ## Stop Docker Compose service.
	docker compose down

.PHONY: docker-test
docker-test: ## Start Compose, run smoke test, then stop it.
	@set -e; \
	docker compose up --build -d; \
	trap 'docker compose down' EXIT; \
	$(PYTHON) examples/smoke.py $(BASE_URL)

.PHONY: clean
clean: ## Remove generated local cache files.
	rm -rf .pytest_cache __pycache__ examples/__pycache__ python/tests/__pycache__ python/uri_dispatch/__pycache__
