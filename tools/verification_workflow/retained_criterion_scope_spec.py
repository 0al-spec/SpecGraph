"""Select a retained observation by its exact workspace and declaration."""

from dataclasses import dataclass

from specification_core import PredicateSpec

from traceability.criterion import CriterionSource


@dataclass(frozen=True)
class RetainedCriterionScope:
    workspace: str
    repository_id: str
    spec_id: str
    source: CriterionSource


@dataclass(frozen=True)
class RetainedCriterionScopeMatch:
    selected: RetainedCriterionScope
    recorded: RetainedCriterionScope


RETAINED_CRITERION_SCOPE_SPEC: PredicateSpec[RetainedCriterionScopeMatch] = PredicateSpec(
    lambda facts: facts.selected == facts.recorded,
    name="verification.retained_criterion_exact_scope",
)
