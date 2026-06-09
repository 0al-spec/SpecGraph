# External Consumer Evidence Static Publish

## Status

Draft proposal

## Source Material

This proposal closes the publish gap found after merging `0085`.

Source draft:

- `docs/archive/proposal_sources/0086_external_consumer_evidence_static_publish.md`

## Context

`0085` accepted downstream evidence for SpecSpace PR `#231` in
`runs/external_consumer_evidence_index.json`. The local artifact exists and is
valid, but the public static bundle did not publish it, so
`https://specgraph.tech/runs/external_consumer_evidence_index.json` returned
`404` even after the post-merge publish workflow succeeded.

The handoff packet and Agent surface producer artifacts were already
HTTP-readable. This slice makes the evidence acceptance surface equally
publishable.

## Goals

- Include `runs/external_consumer_evidence_index.json` in the public publish
  bundle.
- Treat the evidence index as a required run surface for public static publish.
- Refresh `external-handoffs` and `external-consumer-evidence` before collecting
  bundle files.
- Keep existing safety checks for malformed JSON, local path leakage, and
  Agent Passport verification.
- Document the new published surface.

## Non-Goals

- Changing external consumer evidence acceptance semantics.
- Mutating SpecSpace.
- Mutating Platform.
- Adding a new public manifest shape.
- Claiming runtime enforcement.

## Acceptance

This slice is complete when:

- `make publish-bundle PUBLISH_BUNDLE_FLAGS=` writes
  `dist/specgraph-public/runs/external_consumer_evidence_index.json`;
- the generated bundle manifest marks
  `external_consumer_evidence_index.json` as a required present surface;
- focused static bundle tests cover both presence and missing-surface failure;
- `make docc-sync`, proposal gates, and the full Python suite pass.
