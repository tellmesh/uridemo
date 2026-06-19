def parse_uri(uri):
    scheme, rest = uri.split("://", 1)
    target, path = rest.split("/", 1)
    parts = path.split("/")
    if len(parts) == 2 and parts[0] in ("command", "query"):
        resource, kind, operation = scheme, parts[0], parts[1]
    elif len(parts) == 3 and parts[1] in ("command", "query"):
        resource, kind, operation = parts[0], parts[1], parts[2]
    else:
        raise ValueError("invalid URI: %s" % uri)
    return {
        "raw": uri,
        "scheme": scheme,
        "target": target,
        "resource": resource,
        "kind": kind,
        "operation": operation,
    }
