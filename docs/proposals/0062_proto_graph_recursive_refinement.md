# Proto-Graph Recursive Refinement

RFC: SG-RFC-0062
Version: 0.1.0

## Status

Draft proposal

Decision scope: ontology-backed proto-graph generation and recursive refinement protocol for turning raw product intent into reviewable graph seed material.

This document does not implement a generator, mutate canonical specs, define a
complete Ontology package schema, build SpecSpace UI, or execute implementation
work.

## Source Material

This proposal captures the operator request to make SpecGraph support fast
proto-graph generation from an initial user intent while preserving the
node-by-node recursive refinement model.

Source draft:

- `docs/archive/proposal_sources/0062_proto_graph_recursive_refinement.md`

## Summary

SpecGraph should support a **Proto-Graph Recursive Refinement** flow:

```text
raw user intent
  -> ontology-backed seed concepts
  -> reviewable proto-graph placeholder nodes
  -> recursive refinement queue
  -> bounded node-by-node enrichment
  -> proposals, canonical specs, implementation work, evidence
```

The proto-graph is a fast, shallow, non-canonical graph scaffold. It gives the
operator and Graph Operator Surface something visible to inspect immediately,
while preserving SpecGraph's proposal-first and review-before-materialization
discipline.

The key design point is that ontology-backed generation is useful as a
semantic scaffold, not as automatic truth. A generated placeholder node can be
named and explained, but it remains a seed until reviewed, refined, and
promoted through existing graph governance.

## Problem

SpecGraph is already effective when it has a concrete target node to refine.
However, early product exploration still has a gap:

```text
small raw intent
  -> no graph yet
  -> operator or agent must manually invent the first structure
```

For a user who asks for "a GUI calculator for iOS/macOS", the system should not
need to wait for a fully mature specification before showing structure. It
should quickly produce a legible proto-graph such as:

- Calculator Product
- Numeric Input
- Operation Model
- Result Display
- Platform UI Shell
- Error Handling
- Testing and Verification
- Runtime Packaging

The risk is that fast generation can overclaim. If generated nodes look like
canonical specs, the system may confuse a plausible scaffold with accepted
graph truth.

## Goals

- Define a fast proto-graph seed layer for initial product intent.
- Use Ontology as the lower semantic basis for scaffold generation.
- Preserve recursive, fractal refinement as the normal way graph detail grows.
- Represent placeholder nodes explicitly rather than pretending they are mature
  specs.
- Keep proto-graph output reviewable and non-canonical by default.
- Make compute budget and human attention budget explicit concepts.
- Provide a bridge from Exploration Preview and Product Workspace
  Initialization toward first graph materialization.
- Give future SpecSpace and supervisor tooling a stable vocabulary for proto
  graph preview, seed plans, and refinement queues.

## Non-Goals

- Implementing `--build-proto-graph-preview` in this proposal.
- Implementing ontology induction or `ontologyc` invocation.
- Creating canonical `specs/nodes/*.yaml` from raw intent automatically.
- Replacing `runs/exploration_preview.json`.
- Replacing the External Ontology Import Plane.
- Replacing Conversation Memory or Pre-Spec Semantic Layer semantics.
- Implementing SpecSpace UI.
- Generating product runtime code.
- Treating proto-graph placeholders as accepted requirements.

## Layer Model

Proto-graph generation should sit between raw exploration and canonical spec
materialization:

```text
Layer 0a: Raw user intent / conversation source
Layer 0b: Structured exploration memory and intent fragments
Layer 0c: Ontology-backed proto-graph seed
Layer 0d: Recursive refinement queue
Layer 1: Canonical specifications
Layer 2: Implementation work
Layer 3: Runtime, evidence, metrics, and deployment observation
```

The proto-graph layer is deliberately pre-canonical. It may produce pressure
toward proposals and specs, but it does not become canonical merely because it
was generated.

## Responsibilities

### SpecGraph

SpecGraph owns:

- proto-graph artifact contracts;
- placeholder lifecycle vocabulary;
- recursive refinement queue semantics;
- promotion and review boundaries;
- deterministic validation and derived backlog surfaces;
- connection to proposals, specs, trace, evidence, and implementation work.

### Ontology

Ontology owns:

- reusable ontology package semantics;
- product/domain concept induction contracts;
- ontology package validation;
- external concept authority, version, digest, and governance evidence.

SpecGraph may reference ontology concepts, packages, and induction reports, but
it should not copy ontology package authority into canonical graph truth.

### Graph Operator Surface

The Graph Operator Surface owns:

- collecting the first raw product intent from a human;
- showing proto-graph previews;
- letting the operator approve, reject, rename, or defer placeholder regions;
- preparing bounded operator requests for later refinement.

It must not treat proto-graph previews as accepted canonical specs.

### Supervisor / Agents

The supervisor or agent runtime may:

- produce a proto-graph seed plan;
- suggest placeholder nodes and shallow edges;
- recommend the next refinement target;
- enrich one node at a time under a bounded request.

They must not bypass review barriers or silently promote generated placeholders
into canonical specs.

## Core Concepts

### Proto-Graph

A proto-graph is a reviewable, shallow graph scaffold derived from an initial
intent and optional ontology seed.

Candidate artifact:

```text
runs/proto_graph_preview.json
```

Candidate fields:

```json
{
  "artifact_kind": "proto_graph_preview",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "root_intent_ref": {
    "source_kind": "product_workspace_root_intent",
    "content_sha256": "..."
  },
  "ontology_seed": {
    "status": "draft|imported|unavailable",
    "package_ref": "ontology://...",
    "concept_count": 8
  },
  "summary": {
    "placeholder_node_count": 8,
    "edge_count": 10,
    "review_state": "review_required",
    "next_gap": "human_review_before_seed_materialization"
  },
  "nodes": [],
  "edges": []
}
```

### Placeholder Node

A placeholder node is an intentionally shallow graph candidate.

It should have:

- stable preview ID;
- human-readable label;
- short shallow description;
- placeholder kind;
- ontology concept references, when available;
- confidence or assumption notes;
- review state;
- next refinement gap.

It should not have:

- mature acceptance criteria unless explicitly refined;
- implementation work claims;
- evidence claims;
- canonical spec ID unless promoted through review.

### Recursive Refinement Queue

The refinement queue turns a broad proto-graph into bounded work:

```text
proto node
  -> inspect shallow description
  -> ask missing questions
  -> refine one node
  -> add links/evidence/proposals/specs
  -> update queue
```

Candidate artifact:

```text
runs/proto_graph_refinement_queue.json
```

Queue entries should include:

- `subject_id`;
- `subject_label`;
- `layer`;
- `readiness`;
- `next_gap`;
- `suggested_run_mode`;
- `compute_budget_hint`;
- `attention_budget_hint`;
- `blocking_questions[]`;
- `source_artifacts[]`.

### Fractal Refinement

Refinement is fractal when the same pattern can recur at each level:

```text
product
  -> subsystem
  -> capability
  -> behavior
  -> acceptance criterion
  -> implementation work
  -> runtime evidence
```

At each level, the node should remain bounded enough for one reviewable next
step. When it becomes too broad, it should emit split pressure or child
materialization pressure through existing graph mechanisms.

### Compute and Attention Budgets

The proto-graph flow should distinguish two scarce resources:

- `compute_budget`: how much LLM/agent work may be spent refining generated
  material;
- `attention_budget`: how much human review effort is expected before
  promotion.

A generated proto-graph may be cheap and broad. Mature specs require targeted
compute and human attention.

## Relationship To Existing Surfaces

### Exploration Preview

`runs/exploration_preview.json` is a minimal review-only placeholder graph for
early exploration. Proto-graph preview is a richer follow-up concept that may
use ontology seed material and produce a recursive refinement queue.

Exploration Preview remains useful for very early assumption/hypothesis/proposal
scaffolding. Proto-graph generation is product-structure oriented.

### Product Workspace Initialization

Product Workspace Initialization captures the root intent safely and creates a
workspace shell. Proto-graph generation is the next step after that capture:

```text
workspace initialized
  -> root intent captured
  -> proto-graph preview
  -> review
  -> first materialization/refinement request
```

### External Ontology Import Plane

Proposal `0060` defines how external ontology packages enter SpecGraph through a
review-first import boundary. This proposal uses that boundary as a semantic
basis for seed generation. It does not replace ontology import governance.

### Conversation Memory and Pre-Spec Semantics

Conversation Memory and Pre-Spec Semantic Layer preserve raw and structured
intent before canonical promotion. Proto-graph generation may consume those
surfaces as sources, but should project a distinct product-structure seed graph
instead of copying conversation memory directly into specs.

### Proposal Debt

If this proposal is accepted without immediate runtime implementation, the
future runtime work should appear in proposal debt surfaces rather than staying
implicit.

## Promotion Boundary

Proto-graph material may be promoted only through explicit review steps.

Allowed transitions:

```text
placeholder_node -> proposal_candidate
placeholder_node -> pre_spec_draft
placeholder_node -> operator_question
placeholder_node -> refinement_queue_entry
reviewed placeholder -> canonical spec candidate
```

Disallowed transitions:

```text
raw intent -> canonical spec
ontology draft -> canonical spec
placeholder_node -> implementation work
placeholder_node -> evidence claim
assistant answer -> accepted graph truth
```

## Future Runtime Slices

Likely bounded implementation slices:

1. Add `tools/proto_graph_generation_policy.json`.
2. Add `--build-proto-graph-preview`.
3. Emit `runs/proto_graph_preview.json`.
4. Emit `runs/proto_graph_refinement_queue.json`.
5. Include proto-graph surfaces in `make viewer-surfaces`.
6. Add SpecSpace viewer contract for proto-graph preview and queue browsing.
7. Connect accepted queue entries to existing supervisor targeted refinement
   requests.

## Acceptance Criteria

- Proto-graph output is explicitly non-canonical.
- Placeholder nodes are clearly marked as shallow and review-required.
- Ontology references are source/version/digest aware when present.
- Missing ontology seed produces an observation gap, not a hard failure.
- Compute and attention budget hints are represented in the queue.
- No raw prompt text, private paths, API keys, or provider secrets appear in
  viewer-facing artifacts.
- SpecSpace can render proto-graph previews without reading raw run logs.
- Promotion into canonical specs requires explicit review.

## Risks

- Fast proto-graph generation may create plausible but misleading structure.
  The UI and artifacts must label it as preview-only.
- If placeholder nodes become too numerous, the graph may feel complete while
  lacking real specification depth. The queue should surface shallow-node debt.
- If ontology seed generation is overtrusted, external draft semantics may
  bypass SpecGraph governance. Use ontology import references and review gates.
- If recursive refinement lacks budget controls, it may spend compute on broad
  scaffolding rather than high-value unresolved nodes.
