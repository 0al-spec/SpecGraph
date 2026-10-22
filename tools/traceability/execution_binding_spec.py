"""A retained run is identifiable only by the explicit GitHub execution tuple."""

from specification_core import PredicateSpec

from .execution import ExecutionBindingFacts

EXECUTION_BINDING_SPEC: PredicateSpec[ExecutionBindingFacts] = PredicateSpec(
    lambda c: (
        c.expected == c.observed
        and c.expected.provider == "github_actions"
        and len(c.expected.run_id) <= 20
        and c.expected.run_id.isascii()
        and c.expected.run_id.isdecimal()
        and int(c.expected.run_id) > 0
        and len(c.expected.run_attempt) <= 20
        and c.expected.run_attempt.isascii()
        and c.expected.run_attempt.isdecimal()
        and int(c.expected.run_attempt) > 0
        and c.expected.uri == f"https://github.com/{c.repository}/actions/runs/{c.expected.run_id}"
    ),
    name="publication.retained_execution_identity",
)
