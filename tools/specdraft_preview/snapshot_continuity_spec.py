"""SDPV-05: losing a saved head is not a new valid empty notebook."""

from specification_core import PredicateSpec

from .context import SnapshotContinuityFacts

SNAPSHOT_CONTINUITY_SPEC: PredicateSpec[SnapshotContinuityFacts] = PredicateSpec(
    lambda facts: not facts.previous_revision_exists or facts.observed_revision_exists,
    name="specdraft_preview.snapshot_continuity",
)
