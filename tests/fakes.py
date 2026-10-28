"""Fake Claude client used by tests. It never touches the network and never costs money."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class FakeMessages:
    """Stands in for client.messages. It records each call and returns or raises what the test chose."""

    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


class FakeClient:
    def __init__(self, messages: FakeMessages) -> None:
        self.messages = messages


def text_response(text: str) -> SimpleNamespace:
    """Build a response shaped like the Anthropic SDK's Message object."""
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])
