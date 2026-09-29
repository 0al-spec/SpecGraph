"""Named candidate approval fields backed by readiness specifications."""

from __future__ import annotations

from tools.candidate_approval_next_artifact_spec import candidate_approval_next_artifact
from tools.candidate_approval_readiness_context import ApprovalReadinessContext
from tools.candidate_approval_review_state_spec import candidate_approval_review_state
from tools.idea_to_spec_decision_set import SpecField, SpecSet

CANDIDATE_APPROVAL_FIELDS = SpecSet[ApprovalReadinessContext](
    fields=(
        SpecField("review_state", candidate_approval_review_state),
        SpecField("next_artifact", candidate_approval_next_artifact),
    )
)
