"""A consumer may bind fresh identities, but cannot change the selected obligations."""

from dataclasses import dataclass

from specification_core import PredicateSpec

from .execution_model import BoundRun
from .model import CriterionTarget


@dataclass(frozen=True)
class BindingSelection:
    targets: tuple[CriterionTarget, ...]
    bound: BoundRun


def complete_binding(selection: BindingSelection) -> bool:
    bound = selection.bound
    rows = {row.pointer: row for row in bound.criteria}
    if not bound.producer_run_id or len(rows) != len(bound.criteria):
        return False
    if set(rows) != {target.source.pointer for target in selection.targets}:
        return False
    for target in selection.targets:
        row = rows[target.source.pointer]
        steps = dict(row.steps)
        if not row.case_id or not row.case_started_id or row.attempt != 0:
            return False
        if len(steps) != len(row.steps) or not all(steps.values()):
            return False
        if set(steps) != {expected.assertion_id for expected in target.expectations}:
            return False
    return True


EXECUTION_BINDING_SPEC: PredicateSpec[BindingSelection] = PredicateSpec(
    complete_binding,
    name="verification.fresh_identity_binding",
)
