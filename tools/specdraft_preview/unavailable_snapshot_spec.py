"""SDPV-05: a failed first read is unavailable, not an empty notebook."""

from specification_core import PredicateSpec

from .context import DisplayFacts

UNAVAILABLE_SNAPSHOT_SPEC: PredicateSpec[DisplayFacts] = PredicateSpec(
    lambda facts: facts.read_failed and not facts.has_snapshot,
    name="specdraft_preview.unavailable_snapshot",
)
