"""Project-selected immutable ontology capture and scoped verification."""

from .capture import capture_project_context
from .model import CheckResult, ContextResult

__all__ = ["CheckResult", "ContextResult", "capture_project_context"]
