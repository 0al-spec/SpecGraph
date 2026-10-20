"""SG-SPEC-0071 / PE-SNAPSHOT: equality of the relevant source bytes."""

from specification_core import PredicateSpec

from .context import SnapshotContext

SOURCE_SNAPSHOT_SPEC: PredicateSpec[SnapshotContext] = PredicateSpec(
    lambda c: c.expected == c.observed,
    name="publication.source_snapshot_matches",
)
