"""Only a finalized, complete, fresh and nonempty observation set can pass."""

from specification_core import FirstMatch, PredicateSpec

from .model import CompletionFacts, Status

VERIFICATION_VERDICT_SPEC: FirstMatch[CompletionFacts, str] = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: (
                    c.rejected
                    or not c.finalized
                    or not c.linkage_valid
                    or not c.collection_valid
                    or c.collector_exit != 0
                ),
                name="verification.unreliable_chain",
            ),
            "incomplete",
        ),
        (
            PredicateSpec(
                lambda c: any(s != Status.COMPLETED for s in c.statuses),
                name="verification.unfinished_stages",
            ),
            "incomplete",
        ),
        (
            PredicateSpec(lambda c: c.producer_exit is None, name="verification.missing_exit"),
            "incomplete",
        ),
        (
            PredicateSpec(
                lambda c: c.producer_exit != 0 or "failed" in c.outcomes,
                name="verification.observed_failure",
            ),
            "failed",
        ),
        (
            PredicateSpec(
                lambda c: not c.inventory_complete, name="verification.unknown_inventory"
            ),
            "incomplete",
        ),
        (
            PredicateSpec(lambda c: c.criterion_count == 0, name="verification.empty_inventory"),
            "not_applicable",
        ),
        (
            PredicateSpec(
                lambda c: (
                    not c.bindings_checked
                    or len(c.outcomes) != c.criterion_count
                    or any(outcome != "passed" for outcome in c.outcomes)
                ),
                name="verification.unresolved_criteria",
            ),
            "incomplete",
        ),
    ),
    "passed",
    name="verification.verdict",
)
