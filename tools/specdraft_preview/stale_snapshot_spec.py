"""SDPV-05: retain a prior good snapshot when the next read fails."""

from specification_core import PredicateSpec

from .context import DisplayFacts

STALE_SNAPSHOT_SPEC: PredicateSpec[DisplayFacts] = PredicateSpec(
    lambda facts: facts.read_failed and facts.has_snapshot,
    name="specdraft_preview.stale_snapshot",
)
