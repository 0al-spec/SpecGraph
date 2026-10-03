"""Only a recorded approval with project-author authority satisfies this policy."""

from specification_core import PredicateSpec

from subject_publication_context import HumanApprovalContext

HUMAN_APPROVAL_SPEC: PredicateSpec[HumanApprovalContext] = PredicateSpec(
    lambda context: (
        context.reviewer_authority == "human_project_author" and context.outcome == "approved"
    ),
    name="subject_publication.human_approval",
)
