"""RFC 0226: unavailable or unsupported resolution is incomplete, not absent."""

from specification_core import PredicateSpec

from .evidence import ResolutionCompletenessFacts

RESOLUTION_COMPLETENESS_SPEC: PredicateSpec[ResolutionCompletenessFacts] = PredicateSpec(
    lambda c: c.statuses <= {"resolved", "unresolved", "ambiguous", "wrong_kind"},
    name="trace.resolution_inventory_complete",
)
