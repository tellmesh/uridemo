from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

URI_PATTERN = re.compile(
    r"^(?P<scheme>[a-z][a-z0-9+.-]*)://"
    r"(?P<target>[^/]+)/"
    r"(?:(?P<resource>[^/]+)/)?"
    r"(?P<kind>command|query)/"
    r"(?P<operation>[^/?#]+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UriParts:
    raw: str
    scheme: str
    target: str
    resource: str
    kind: str
    operation: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def parse_uri(uri: str) -> UriParts:
    match = URI_PATTERN.match(str(uri or "").strip())
    if not match:
        raise ValueError(f"invalid URI: {uri}")
    groups = match.groupdict()
    scheme = groups["scheme"].lower()
    return UriParts(
        raw=uri,
        scheme=scheme,
        target=groups["target"],
        resource=groups.get("resource") or scheme,
        kind=groups["kind"].lower(),
        operation=groups["operation"],
    )


Handler = Callable[[UriParts, dict[str, Any], dict[str, Any]], dict[str, Any]]


class UriDispatcher:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, scheme: str, handler: Handler) -> None:
        self._handlers[scheme] = handler

    def dispatch(
        self,
        uri: str,
        payload: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        parts = parse_uri(uri)
        handler = self._handlers.get(parts.scheme)
        if not handler:
            raise KeyError(f"unknown URI scheme: {parts.scheme}")
        return handler(parts, payload or {}, context or {})


__all__ = ["URI_PATTERN", "UriDispatcher", "UriParts", "parse_uri"]
