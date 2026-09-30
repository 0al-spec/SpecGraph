"""Typed inputs and shared artifact interpretation for lifecycle specifications."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from specification_core import FirstMatch, TraceRecorder


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _status_has_token(status: str, token: str) -> bool:
    tokens = {part for part in re.split(r"[^a-z0-9]+", status.lower()) if part}
    if not tokens:
        return False
    if token == "blocked" and ("unblocked" in tokens or tokens == {"not", "blocked"}):
        return False
    return token in tokens


def _status_is_blocked(status: str) -> bool:
    return _status_has_token(status, "blocked")


def _status_is_failed(status: str) -> bool:
    return _status_has_token(status, "failed") or _status_has_token(status, "failure")


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _summary(artifacts: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    return _dict(_dict(artifacts.get(key)).get("summary"))


@dataclass(frozen=True)
class LifecycleStateContext:
    artifacts: dict[str, dict[str, Any]]

    def artifact(self, key: str) -> dict[str, Any]:
        return _dict(self.artifacts.get(key))

    def has_content(self, key: str) -> bool:
        return bool(self.artifacts.get(key))

    def summary(self, key: str) -> dict[str, Any]:
        return _dict(self.artifact(key).get("summary"))

    @staticmethod
    def mapping(value: Any) -> dict[str, Any]:
        return _dict(value)

    @staticmethod
    def text(value: Any, default: str = "") -> str:
        return _text(value, default)

    @staticmethod
    def integer(value: Any, default: int = 0) -> int:
        return _int(value, default)

    @staticmethod
    def is_failed(status: str) -> bool:
        return _status_is_failed(status)

    @staticmethod
    def is_blocked(status: str) -> bool:
        return _status_is_blocked(status)


def decide(
    spec: FirstMatch[LifecycleStateContext, str],
    context: LifecycleStateContext,
    recorder: TraceRecorder | None,
) -> str:
    value = spec.decide(context, recorder=recorder).value
    if value is None:
        raise AssertionError(f"{spec.name} must always return a lifecycle state")
    return value
