import json
from collections.abc import Callable
from typing import Any

import pytest

from anki_rpc import Client


def make_transport(responses: list[dict[str, Any]]) -> Callable[[str, bytes, float], bytes]:
    """Returns a fake transport that pops responses from the front of the list."""
    queue = list(responses)

    def transport(url: str, body: bytes, timeout: float) -> bytes:
        assert queue, "transport called more times than expected"
        return json.dumps(queue.pop(0)).encode()

    return transport


def ok(result: Any) -> dict[str, Any]:
    return {"result": result, "error": None}


def err(message: str) -> dict[str, Any]:
    return {"result": None, "error": message}


@pytest.fixture
def make_client():
    def factory(responses: list[dict[str, Any]], **kwargs: Any) -> Client:
        return Client(transport=make_transport(responses), **kwargs)
    return factory
