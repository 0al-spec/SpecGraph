"""Evaluate complete expected observations separately from binding integrity."""

from specification_core import FirstMatch, PredicateSpec

from .criterion import CriterionDecisionFacts, Outcome

FAILURE_STATUSES = frozenset({"AMBIGUOUS", "FAILED", "UNDEFINED"})

CRITERION_OBSERVATION_OUTCOME_SPEC: FirstMatch[CriterionDecisionFacts, Outcome] = (
    FirstMatch.with_fallback(
        (
            (
                PredicateSpec(
                    lambda c: not c.has_binding or bool(c.findings & {"invalid", "conflict"}),
                    name="criterion.unreliable_binding",
                ),
                "unavailable",
            ),
            (
                PredicateSpec(
                    lambda c: bool(c.step_statuses & FAILURE_STATUSES) or c.measurement_mismatch,
                    name="criterion.observed_failure",
                ),
                "failed",
            ),
            (
                PredicateSpec(lambda c: "PENDING" in c.step_statuses, name="criterion.pending"),
                "pending",
            ),
            (
                PredicateSpec(lambda c: "SKIPPED" in c.step_statuses, name="criterion.skipped"),
                "skipped",
            ),
            (
                PredicateSpec(lambda c: c.run_success is False, name="criterion.unsuccessful_run"),
                "partial",
            ),
            (
                PredicateSpec(
                    lambda c: (
                        c.run_success is True
                        and c.case_finished
                        and c.step_statuses == {"PASSED"}
                        and c.measurements_complete
                        and not c.measurement_mismatch
                        and not c.findings
                    ),
                    name="criterion.all_expected_observations_pass",
                ),
                "passed",
            ),
            (
                PredicateSpec(lambda c: bool(c.step_statuses), name="criterion.partial"),
                "partial",
            ),
        ),
        "unavailable",
        name="criterion.observed_outcome",
    )
)
