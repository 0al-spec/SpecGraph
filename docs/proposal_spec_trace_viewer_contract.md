# Proposal Spec Trace Viewer Contract

## Status

Draft viewer contract for proposal-to-spec trace visibility.

## Context

ContextBuilder needs to show how proposal material relates to canonical
SpecGraph nodes without turning weak textual references into authoritative
trace edges.

SpecGraph currently exposes proposal/spec relations through multiple surfaces
with different authority levels:

- proposal markdown in `docs/proposals/*.md`;
- `runs/proposal_promotion_index.json`;
- `runs/proposal_lane_overlay.json`.

These sources must stay visually and semantically distinct. SpecGraph also emits
a unified proposal/spec trace index for consumers that want one normalized
read-only surface.

## Source Artifacts

| Artifact | Current Role | Authority |
| --- | --- | --- |
| `docs/proposals/*.md` | Human-readable proposal body; may mention `SG-SPEC-*` IDs. | `textual_reference` |
| `runs/proposal_promotion_index.json` | Derived promotion/provenance state for proposal markdown. | `promotion_trace` |
| `runs/proposal_lane_overlay.json` | Derived proposal-lane entries targeting canonical regions. | `lane_overlay` |

The normalized runtime surface is:

| Artifact | Role | Authority |
| --- | --- | --- |
| `runs/proposal_spec_trace_index.json` | Unified derived proposal-to-spec trace projection. | mixed, per relation |

## Viewer Rule

Do not collapse all proposal/spec relations into one edge type.

Render three separate groups:

- `Mentioned specs`: `SG-SPEC-*` IDs found in proposal markdown.
- `Promotion trace`: proposal promotion/provenance records.
- `Lane targets`: proposal-lane entries targeting canonical specs.

The viewer may show all three groups together in one panel, but it should label
their authority and confidence separately.

## Relation Vocabulary

Recommended relation shape:

```json
{
  "proposal_id": "0045",
  "proposal_path": "docs/proposals/0045_conversation_memory_exploration_vault.md",
  "spec_id": "SG-SPEC-0008",
  "relation_kind": "mentions",
  "authority": "textual_reference",
  "trace_status": "inferred",
  "next_gap": "attach_promotion_trace",
  "source_refs": [
    "docs/proposals/0045_conversation_memory_exploration_vault.md"
  ]
}
```

Known `relation_kind` values:

- `mentions`
- `motivates`
- `refines`
- `promotes_to`
- `targets`
- `supersedes`

Known `authority` values:

- `textual_reference`
- `promotion_trace`
- `lane_overlay`
- `canonical_metadata`

Known `trace_status` values:

- `missing_trace`
- `inferred`
- `declared`
- `bounded`
- `incomplete`
- `invalid`
- `ambiguous`

Render `missing_trace`, `incomplete`, `invalid`, and `ambiguous` as warning or
review-needed states. Unknown future values should render as neutral chips, not
as errors.

## Mentioned Specs

Mentioned specs are weak relations inferred from proposal markdown.

Minimum extraction rule:

- scan `docs/proposals/*.md`;
- find canonical IDs matching `SG-SPEC-[0-9]{4}`;
- group by parsed proposal id from the proposal filename prefix;
- mark every relation as:
  - `relation_kind: "mentions"`;
  - `authority: "textual_reference"`;
  - `trace_status: "inferred"`.

Mentioned specs are useful as navigation hints. They are not promotion
provenance.

## Promotion Trace

Promotion trace should be read from `runs/proposal_promotion_index.json`.

Viewer guidance:

- treat `promotion_traceability.status` as the primary trace state when present;
- show `missing_trace` as a gap, not as a broken graph edge;
- show `incomplete` and `invalid` as actionable promotion-provenance gaps;
- show `source_refs` and provenance links when available;
- do not treat `runs/proposal_promotion_index.json` itself as a proposal-to-spec
  edge source, because it currently reports proposal promotion provenance rather
  than a canonical spec target field;
- do not infer a target `SG-SPEC-*` from prose when promotion provenance is
  missing or incomplete.

Promotion trace is stronger than textual references because it is a derived
SpecGraph surface tied to proposal promotion policy.

## Lane Targets

Lane targets should be read from `runs/proposal_lane_overlay.json`.

Viewer guidance:

- use `proposal_handle` as the lane proposal identity;
- use `target_region.target_reference` when it is an `SG-SPEC-*` id and
  `target_region.target_kind` marks a canonical node;
- mark the relation as:
  - `relation_kind: "targets"`;
  - `authority: "lane_overlay"`;
  - `trace_status: "declared"` only when `query_contract.status` is
    `queryable` and the target is canonical;
  - `trace_status: "ambiguous"` when `query_contract.findings` shows the lane
    target is invalid, incomplete, or otherwise requires review before it can
    be treated as canonical trace;
  - `trace_status: "missing_trace"` when `query_contract.findings` shows that
    no canonical target can be resolved from the lane entry.

Show `proposal_authority_state` as lane/governance state, but do not treat it as
a substitute for `trace_status`.

Lane targets are not the same namespace as markdown proposal ids. Do not merge
`proposal_handle` and `proposal_id` without an explicit bridge.

## Recommended Panel

For a proposal detail panel, show:

- `Mentioned specs`: weak navigation links from markdown references.
- `Promotion trace`: declared provenance and `next_gap`.
- `Lane targets`: proposal-lane targets, if any.

For each relation, show:

- `Mentioned specs`:
  - `spec_id`;
  - `relation_kind`;
  - `authority`;
  - `trace_status`;
  - `source_refs`.
- `Promotion trace`:
  - `proposal_id` or `proposal_path`;
  - `authority`;
  - `promotion_traceability.status`;
  - `next_gap`;
  - `source_refs`.
- `Lane targets`:
  - `spec_id`;
  - `relation_kind`;
  - `authority`;
  - `trace_status`;
  - `proposal_authority_state`;
  - `source_refs`.

`spec_id` is optional at the panel level and should only be shown for relation
groups that currently emit or derive a canonical spec reference.

Recommended visual treatment:

- textual references: subtle/neutral;
- promotion trace: primary trace chip;
- lane targets: lane/governance chip;
- `missing_trace`: warning chip;
- `incomplete`: warning chip;
- `invalid`: warning chip;
- `ambiguous`: warning chip requiring review.

## Guardrails

- ContextBuilder should remain a read-only consumer of these surfaces.
- Textual mentions must not create canonical trace edges.
- Missing promotion trace should be shown as work to do, not silently repaired by
  viewer inference.
- Lane proposal handles and markdown proposal ids are separate identifiers until
  SpecGraph emits an explicit bridge.

## Backend Surface

SpecGraph builds:

```text
runs/proposal_spec_trace_index.json
```

Use either:

```bash
make proposal-spec-trace
python3 tools/supervisor.py --build-proposal-spec-trace-index
```

The artifact normalizes:

- markdown proposal ids;
- textual spec mentions;
- promotion trace records;
- proposal-lane targets;
- authority and status vocabulary;
- `next_gap` values for missing or ambiguous trace.

It is also included in `make viewer-surfaces`. The artifact is derived-only:
`canonical_mutations_allowed` and `tracked_artifacts_written` must both remain
`false`.
