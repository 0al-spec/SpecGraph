"""A normally finished failing test is distinct from a failed execution adapter."""

from specification_core import FirstMatch, PredicateSpec

from .model import CompletionFacts, Status

WORKFLOW_LIFECYCLE_SPEC: FirstMatch[CompletionFacts, str] = FirstMatch.with_fallback(
    (
        (PredicateSpec(lambda c: c.rejected, name="workflow.rejected"), "rejected"),
        (PredicateSpec(lambda c: not c.finalized, name="workflow.unfinalized"), "incomplete"),
        (PredicateSpec(lambda c: Status.ABORTED in c.statuses, name="workflow.aborted"), "aborted"),
        (PredicateSpec(lambda c: Status.FAILED in c.statuses, name="workflow.failed"), "failed"),
        (
            PredicateSpec(
                lambda c: any(s != Status.COMPLETED for s in c.statuses),
                name="workflow.unfinished_stages",
            ),
            "incomplete",
        ),
        (
            PredicateSpec(
                lambda c: c.producer_exit is None, name="workflow.missing_process_outcome"
            ),
            "incomplete",
        ),
        (
            PredicateSpec(
                lambda c: not c.linkage_valid or not c.collection_valid,
                name="workflow.inconsistent_outputs",
            ),
            "failed",
        ),
        (
            PredicateSpec(lambda c: c.collector_exit != 0, name="workflow.collection_failed"),
            "failed",
        ),
    ),
    "completed",
    name="verification.workflow_lifecycle",
)
