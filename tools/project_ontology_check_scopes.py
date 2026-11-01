"""Explicit assessment requests for context-bound ontology advisory reports."""

from dataclasses import dataclass

CHECK_SCOPES = ("domain_vocabulary", "specification_metamodel")
DEFAULT_SCOPES = ("domain_vocabulary",)
SCOPED_ANALYSIS_PROFILE = "specgraph-scoped-ontology-advisory-v1"
SCOPED_SCHEMA_VERSION = 2


@dataclass(frozen=True, slots=True)
class ScopeFacts:
    requested: tuple[str, ...]
    outcomes: tuple[str, ...]


def normalize_requested_scopes(value: object) -> tuple[str, ...]:
    """Validate boundary data and canonicalize ordering without adding requests."""
    if not isinstance(value, (tuple, list)) or any(
        not isinstance(scope, str) or scope not in CHECK_SCOPES for scope in value
    ):
        raise ValueError("requested_scopes must be a list or tuple of supported check scopes")
    if len(set(value)) != len(value):
        raise ValueError("requested_scopes must not contain duplicates")
    return tuple(scope for scope in CHECK_SCOPES if scope in value)
