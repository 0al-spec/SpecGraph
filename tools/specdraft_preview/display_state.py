"""SDPV-01/05: ordered display policy; callers own reading and rendering."""

from specification_core import FirstMatch, TraceRecorder

from .context import DisplayFacts, DisplayState
from .empty_snapshot_spec import EMPTY_SNAPSHOT_SPEC
from .stale_snapshot_spec import STALE_SNAPSHOT_SPEC
from .unavailable_snapshot_spec import UNAVAILABLE_SNAPSHOT_SPEC

DISPLAY_STATE_SPEC = FirstMatch.with_fallback(
    (
        (STALE_SNAPSHOT_SPEC, DisplayState.STALE),
        (UNAVAILABLE_SNAPSHOT_SPEC, DisplayState.UNAVAILABLE),
        (EMPTY_SNAPSHOT_SPEC, DisplayState.EMPTY),
    ),
    DisplayState.CURRENT,
    name="specdraft_preview.display_state",
)


def display_state(facts: DisplayFacts, *, recorder: TraceRecorder | None = None) -> DisplayState:
    decision = DISPLAY_STATE_SPEC.decide(facts, recorder=recorder)
    assert decision.value is not None
    return decision.value
