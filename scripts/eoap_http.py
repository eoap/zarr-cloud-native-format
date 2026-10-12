"""Bounded HTTPS downloads for published schemas and release tooling."""

import json
from urllib.parse import urlsplit

import requests


def read_https(url: str, timeout: float = 30) -> bytes:
    """Read a published HTTPS resource and reject unsupported URI schemes."""
    if urlsplit(url).scheme != "https":
        raise ValueError("Published resources require HTTPS")
    with requests.get(url, timeout=timeout) as response:
        response.raise_for_status()
        content: bytes = response.content
        return content


def read_json_object(url: str) -> dict[str, object]:
    """Read a JSON object without claiming a specific schema model."""
    value: object = json.loads(read_https(url))
    if not isinstance(value, dict):
        raise ValueError("Published schema must be a JSON object")
    result: dict[str, object] = value
    return result
