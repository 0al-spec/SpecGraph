"""SG-SPEC-0071 / PE-CASE: unique execution, failure before success."""

from specification_core import FirstMatch, PredicateSpec

from .context import TestCaseContext

TEST_CASE_SPEC: FirstMatch[TestCaseContext, str] = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(lambda c: c.occurrence_count != 1, name="publication.case_not_unique"),
            "missing",
        ),
        (PredicateSpec(lambda c: c.failed, name="publication.case_failed"), "observed_failure"),
        (
            PredicateSpec(lambda c: not c.skipped, name="publication.case_completed"),
            "observed_success",
        ),
    ),
    "missing",
    name="publication.test_case",
)
