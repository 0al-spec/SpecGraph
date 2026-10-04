"""Deliberate historical copy for isolated gate tests; never production code."""

import hashlib


def copied_workspace_allocation(allocation, request):
    if (
        allocation["workspace_identity"] == request.topology.workspace_identity
        and allocation["source_ref"] == request.source_ref
        and allocation["expected_commit"] == request.expected_commit
        and allocation["identity_allocation_authorized"] is True
        and allocation["source_ref_initialization_authorized"] is True
        and allocation["declaration_sha256"]
        == hashlib.sha256(request.workspace_declaration_yaml.encode()).hexdigest()
    ):
        return True
    return False
