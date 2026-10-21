"""SG-SPEC-0071 / PE-SUITE: shared fresh and retained test-result policy."""

from specification_core import FirstMatch, PredicateSpec

from .context import TestSuiteContext

TEST_SUITE_SPEC: FirstMatch[TestSuiteContext, str] = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: c.exit_code != 0 or "observed_failure" in c.outcomes,
                name="publication.suite_failed",
            ),
            "observed_failure",
        ),
        (
            PredicateSpec(
                lambda c: (
                    c.declared_result == "observed_success"
                    and c.outcomes == frozenset({"observed_success"})
                    and c.observed_count == c.required_count
                ),
                name="publication.suite_complete",
            ),
            "observed_success",
        ),
    ),
    "missing",
    name="publication.test_suite",
)
