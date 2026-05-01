# Proposal Spec Trace Semantics

## Status

Draft proposal

## Context

SpecGraph already has several proposal-facing surfaces:

- markdown proposals in `docs/proposals/*.md`;
- proposal promotion provenance in `runs/proposal_promotion_index.json`;
- proposal-lane overlays in `runs/proposal_lane_overlay.json`;
- proposal runtime realization in `runs/proposal_runtime_index.json`.

ContextBuilder can inspect these surfaces, but proposal-to-spec relation
semantics are not yet explicit enough. A proposal markdown file can mention a
canonical `SG-SPEC-*` id, a promotion record can report traceability status, and
a proposal-lane node can target a canonical spec region. These are different
relation types with different authority.

If viewers flatten them into one edge, weak textual references start looking
like canonical promotion trace.

## Problem

Proposal/spec relations currently exist at three strengths:

- textual references inside proposal prose;
- derived promotion trace from proposal-promotion policy;
- proposal-lane targets pointing at canonical spec regions.

These are useful together, but they answer different questions:

- "Which specs does this proposal mention?"
- "Which canonical spec did this proposal promote into or derive from?"
- "Which canonical region does this proposal-lane item target?"

Without explicit semantics:

- viewer implementations may infer authoritative trace from markdown mentions;
- `proposal_id` and `proposal_handle` namespaces can be conflated;
- missing promotion trace can be hidden by weak textual links;
- downstream consumers cannot tell whether a relation is inferred, declared,
  bounded, or ambiguous;
- future automation may treat viewer inference as graph truth.

## Goals

- Define proposal-to-spec trace semantics for SpecGraph.
- Separate textual mentions, promotion trace, and lane targets.
- Give ContextBuilder stable consumer guidance for current artifacts.
- Prepare a later derived artifact that normalizes these relations.
- Preserve review-first promotion boundaries.
- Make missing or ambiguous proposal trace visible as graph work, not viewer
  guesswork.

## Non-Goals

- Creating the runtime `proposal_spec_trace_index.json` in this proposal.
- Mutating canonical specs based on proposal markdown references.
- Backfilling all missing proposal promotion trace.
- Merging markdown proposal ids with proposal-lane handles.
- Changing proposal promotion policy.
- Adding ContextBuilder write actions.

## Relation Layers

### 1. Textual Reference

A textual reference is an `SG-SPEC-*` id mentioned in proposal markdown.

It is useful for navigation and review, but it is weak evidence:

- `authority: textual_reference`;
- `relation_kind: mentions`;
- `trace_status: inferred`.

Textual references must not be treated as promotion provenance.

### 2. Promotion Trace

Promotion trace is derived from the proposal-promotion registry, policy, and
promotion index.

It is the authoritative surface for proposal promotion/provenance state when
present:

- `authority: promotion_trace`;
- relation kind may be `promotes_to`, `motivates`, `refines`, or `supersedes`;
- `trace_status` should reflect the derived promotion state, such as
  `missing_trace`, `declared`, or `bounded`.

When promotion trace is missing, a viewer should show a trace gap rather than
silently substituting markdown mentions.

### 3. Lane Target

A lane target is a proposal-lane node targeting a canonical spec region.

It lives in the proposal-lane namespace:

- identity: `proposal_handle`;
- target: `target_region.target_reference`;
- `authority: lane_overlay`;
- `relation_kind: targets`.

Lane targets can point to `SG-SPEC-*` ids, but they are not the same identity as
markdown proposals in `docs/proposals/*.md`.

## Vocabulary

Initial relation kinds:

- `mentions`;
- `motivates`;
- `refines`;
- `promotes_to`;
- `targets`;
- `supersedes`.

Initial authority values:

- `textual_reference`;
- `promotion_trace`;
- `lane_overlay`;
- `canonical_metadata`.

Initial trace statuses:

- `missing_trace`;
- `inferred`;
- `declared`;
- `bounded`;
- `ambiguous`.

Unknown future values should remain renderable as neutral values by consumers.

## Viewer Contract

The first slice is documented by:

```text
docs/proposal_spec_trace_viewer_contract.md
```

ContextBuilder should show proposal-to-spec relations in three groups:

- `Mentioned specs`;
- `Promotion trace`;
- `Lane targets`.

It should label each relation by authority and status. It should not collapse
all relations into one proposal/spec edge.

## Planned Derived Artifact

The next runtime slice should introduce:

```text
runs/proposal_spec_trace_index.json
```

The artifact should normalize current sources into entries shaped around:

- `proposal_id`;
- `proposal_path`;
- `spec_refs[]`;
- `lane_refs[]`;
- `relation_kind`;
- `authority`;
- `trace_status`;
- `next_gap`;
- `source_refs`;
- provenance back to source artifacts.

This artifact should be derived-only. It should not create canonical specs,
proposal-lane nodes, or promotion records.

## Acceptance Criteria

- Proposal-to-spec relation strengths are explicit.
- Textual mentions are documented as inferred navigation hints.
- Promotion trace remains the authoritative promotion/provenance source.
- Proposal-lane targets remain separate from markdown proposal ids.
- ContextBuilder has a current viewer contract before the unified runtime
  artifact exists.
- The next runtime slice is clearly scoped to
  `runs/proposal_spec_trace_index.json`.
