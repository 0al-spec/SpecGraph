# 0217 Hosted Managed Public Report Publication

## Status

Implemented bounded public-safe hosted report publication.

## Problem

Hosted Platform workers write authoritative managed-operation reports to the
private VPS artifact root. SpecSpace production reads a static product workspace
bundle. A successful queue receipt therefore remained visible as transport
state while the Product Workspace lifecycle could not observe the authoritative
review result until an operator manually copied and republished files.

Publishing the authoritative file verbatim is unsafe: it may contain command
arguments, command output, and local worker paths. Giving the hosted worker SFTP
credentials would also widen its deployment authority.

## Decision

Platform emits a bounded
`platform.hosted-managed.public-report-publication.v1` packet containing exactly
one sanitized report projection. The only accepted logical refs are:

- `runs/product_candidate_promotion_review_object_evidence.json`;
- `runs/product_candidate_promotion_review_status_report.json`.

The packet is sent through authenticated `workflow_dispatch`. SpecGraph
validates packet identity, report kind, SHA-256, privacy, authority, GitHub
review identity, bounded size, and exact workspace scope before atomically
overlaying the tracked `runs/hosted-operation-canary` source. Invalid input does
not overwrite an existing artifact.

The workflow regenerates the scoped Idea Maturity report, validation report, and
Candidate Overview after a successful overlay. The ordinary Hosted Operation
Canary bundle build then includes the report and lifecycle projections derived
from it.
Proposal `0215` remains the transport implementation: checksum comparison stages
only changed payloads, metadata is finalized last, and HTTPS digest verification
is required.

Review-status publication requires a completed bounded worker window with one
`review_status_execute`, initial attempt `0`, terminal attempt `1`, a drained
queue, and one digest-pinned authoritative report. Review-object publication
requires fresh open-PR evidence pinned to the selected non-dry-run promotion
execution report.

## Authority Boundary

This proposal does not:

- expose worker commands, command output, request payloads, secrets, or local paths;
- give the hosted worker SFTP credentials;
- accept arbitrary workspaces, reports, repositories, workflows, or output paths;
- execute managed operations;
- mutate canonical specs or Ontology packages;
- create, merge, or approve Git reviews;
- publish read models;
- turn a queue receipt into lifecycle completion.

The static SpecGraph workflow remains the publication authority. Platform
authoritative reports remain the execution authority.

## Acceptance Criteria

- A valid review-object or review-status packet overlays exactly one allowlisted
  Hosted Operation Canary report.
- Digest drift, foreign workspace identity, local paths, private fields, and
  authority expansion fail closed.
- Invalid packets preserve any previously tracked report.
- The overlay runs only for an explicit non-empty workflow-dispatch input and
  precedes scoped lifecycle projection refresh and the Hosted Operation Canary
  bundle build.
- Ordinary push, pull-request, and empty manual builds remain unchanged.
- Existing checksum-aware incremental deployment stages and verifies the new
  report without a full static mirror.
