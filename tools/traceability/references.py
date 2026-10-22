"""Exact, node-local ID and static Python reference resolution."""

import re
from collections import defaultdict
from pathlib import PurePosixPath

from intent_decision_review.sources import normalized_path

from .context import Declaration, DeclaredReference, ReferenceFacts, ReferenceResolution
from .reference_status_spec import REFERENCE_STATUS_SPEC

LOCAL_KINDS = frozenset({"atom", "criterion", "rule", "obligation", "scenario", "target"})
PYTHON_KINDS = frozenset({"python_function", "python_value", "pytest_function"})


def supported_reference(kind: str, reference: str) -> bool:
    if kind in LOCAL_KINDS:
        # A range is never expanded; only an exact declared ID can resolve.
        return re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", reference) is not None
    if kind not in PYTHON_KINDS or reference.count("::") != 1:
        return False
    path, symbol = reference.split("::")
    try:
        normalized_path(path)
    except ValueError:
        return False
    if not path.endswith(".py") or re.fullmatch(r"[A-Za-z_]\w*", symbol) is None:
        return False
    return kind != "pytest_function" or (
        path.startswith("tests/")
        and PurePosixPath(path).name.startswith("test_")
        and symbol.startswith("test_")
    )


def resolve_references(
    references: tuple[DeclaredReference, ...],
    declarations: tuple[Declaration, ...],
    unavailable: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[ReferenceResolution, ...]:
    """Keep every authored link and every duplicate; never choose a first match."""
    index = defaultdict(list)
    for declaration in declarations:
        index[(declaration.kind, declaration.reference)].append(declaration)
    results = []
    for reference in references:
        key = (reference.target_kind, reference.target)
        candidates = tuple(
            sorted(index[key], key=lambda c: (c.source_path, c.source_location, c.syntax_kind))
        )
        facts = ReferenceFacts(
            supported_reference(*key),
            key not in unavailable,
            len(candidates),
            all(
                c.syntax_kind
                in (
                    {"FunctionDef", "AsyncFunctionDef"}
                    if reference.target_kind in {"python_function", "pytest_function"}
                    else {"Assign", "AnnAssign"}
                )
                for c in candidates
            )
            if reference.target_kind in PYTHON_KINDS
            else True,
        )
        results.append(
            ReferenceResolution(reference, REFERENCE_STATUS_SPEC.decide(facts).value, candidates)
        )
    return tuple(results)
