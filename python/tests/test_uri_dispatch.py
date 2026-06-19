from __future__ import annotations

import pytest

from uri_dispatch import UriDispatcher, parse_uri


def test_parse_resource_uri():
    parts = parse_uri("device://device-01/led/command/set")
    assert parts.scheme == "device"
    assert parts.target == "device-01"
    assert parts.resource == "led"
    assert parts.kind == "command"
    assert parts.operation == "set"


def test_parse_short_process_uri():
    assert parse_uri("process://bridge/command/smoke").resource == "process"


def test_dispatch_by_scheme():
    dispatcher = UriDispatcher()
    dispatcher.register("log", lambda parts, payload, context: {"uri": parts.raw, "payload": payload})
    assert dispatcher.dispatch("log://frontend/session/command/write", {"event": "x"})["payload"]["event"] == "x"


def test_invalid_uri():
    with pytest.raises(ValueError):
        parse_uri("not-a-uri")
