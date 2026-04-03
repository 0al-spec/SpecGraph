"""Smoke tests for the default project scaffold."""

from specgraph import hello


def test_hello() -> None:
    assert hello() == "Hello from SpecGraph"
