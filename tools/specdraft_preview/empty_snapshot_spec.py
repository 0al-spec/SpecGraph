"""SDPV-01: only a successful empty read is an empty sketch."""

from specification_core import PredicateSpec

from .context import DisplayFacts

EMPTY_SNAPSHOT_SPEC: PredicateSpec[DisplayFacts] = PredicateSpec(
    lambda facts: not facts.read_failed and not facts.has_nodes,
    name="specdraft_preview.empty_snapshot",
)
