"""SG-SPEC-0071 / PE-TEST-IDENTITY: evidence belongs to this execution."""

from specification_core import PredicateSpec

from .context import SnapshotContext, TestObservationContext
from .snapshot_spec import SOURCE_SNAPSHOT_SPEC

TEST_OBSERVATION_SPEC: PredicateSpec[TestObservationContext] = PredicateSpec(
    lambda c: (
        SOURCE_SNAPSHOT_SPEC.is_satisfied_by(SnapshotContext(c.expected_source, c.observed_source))
        and c.observed_execution == c.expected_execution
        and c.observed_obligations == c.expected_obligations
    ),
    name="publication.test_observation_matches",
)
