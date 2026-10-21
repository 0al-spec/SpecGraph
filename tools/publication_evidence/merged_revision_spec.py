"""SG-SPEC-0071 / PE-ACCEPTANCE: merged PR for this repository and revision."""

from specification_core import PredicateSpec

from .context import MergedRevisionContext

MERGED_REVISION_SPEC: PredicateSpec[MergedRevisionContext] = PredicateSpec(
    lambda c: (
        bool(c.merged_at)
        and c.observed_revision == c.expected_revision
        and c.observed_repository == c.expected_repository
        and c.pull_number > 0
    ),
    name="publication.merged_revision",
)
