"""The reviewed allocation must bind the exact workspace bootstrap."""

from specification_core import PredicateSpec

from subject_publication_context import WorkspaceAllocationContext

WORKSPACE_ALLOCATION_SPEC: PredicateSpec[WorkspaceAllocationContext] = PredicateSpec(
    lambda context: (
        context.allocation_workspace_identity == context.requested_workspace_identity
        and context.allocation_source_ref == context.requested_source_ref
        and context.allocation_expected_commit == context.requested_expected_commit
        and context.identity_allocation_authorized is True
        and context.source_ref_initialization_authorized is True
        and context.allocation_declaration_sha256 == context.requested_declaration_sha256
    ),
    name="subject_publication.workspace_allocation",
)
