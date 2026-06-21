# Product Workspace Graph Versioning Roadmap

## Purpose

This roadmap defines how product workspaces should version and publish
SpecGraph graph state in production.

Git is the preferred canonical version substrate for product graphs, but the
application must not behave as a direct UI over an arbitrary local folder with
`git init`. Product graph writes need a managed repository boundary that can
validate candidate state, create branches and commits, and publish read models
for SpecSpace.

## Target Shape

```text
SpecSpace UI
  -> Graph Repository Service
  -> Git-backed canonical store
  -> validated specs/nodes, docs/proposals, runs
  -> public-safe read model / artifact bundle
```

The write path and read path stay separate:

- canonical graph history lives in Git;
- draft and generated graph content lives in candidate workspaces until gates
  pass;
- SpecSpace reads published artifacts and read models;
- writes go through a service or CLI contract that owns validation, branch
  creation, commit creation, review, merge, and publication.

## Authority Boundary

The Graph Repository Service may prepare canonical changes, but it must not
silently mutate canonical graph truth.

Allowed first:

- create a candidate workspace;
- materialize a candidate graph;
- run ontology, SpecAuthor, pre-SIB, and structural consistency checks;
- create a branch or PR with validated changes;
- publish read-only artifacts for SpecSpace.

Not allowed in the MVP:

- browser-to-filesystem direct writes into `specs/nodes/*.yaml`;
- direct writes from SpecSpace into Ontology packages;
- direct writes from generated artifacts into canonical specs;
- merge to `main` without a repository policy decision;
- treating candidate graph state as accepted specification truth.

## Roadmap

### 1. Event-Storming Intake Artifact

Status: implemented in proposal `0149`.

Capture raw product intent as structured pre-canonical input:

- actors;
- domain events;
- commands;
- policies;
- external systems;
- constraints;
- vocabulary questions;
- open risks and assumptions.

This artifact should feed the existing SpecAuthor authoring flow and ontology
context resolution without creating canonical specs.

### 2. Candidate Spec Graph Contract

Status: implemented in proposal `0150`.

Define a full candidate graph artifact that can contain proposed specs, edges,
requirements, acceptance criteria, claims, ontology refs, and unresolved gaps.

The candidate graph must declare:

- `canonical_mutations_allowed: false`;
- source intent refs and digests;
- active ontology/domain/context frame;
- ontology layer refs and model applicability refs when available;
- generated node and edge provenance;
- materialization intent limited to review or branch preparation.

### 3. Pre-SIB And Coherence Metrics

Status: implemented in proposal `0151`.

Add a pre-implementation metric layer that scores whether the candidate graph is
ready for canonical review.

Initial signals:

- missing ontology/domain/context refs;
- unsupported strong claims;
- low-reliability decisions;
- orphan nodes;
- unresolved dependencies;
- contradictory requirements;
- duplicated or ambiguous terms;
- acceptance criteria coverage;
- implementation-readiness warnings.

The metrics are review and repair inputs, not product-quality guarantees.

### 4. Autonomous Candidate Repair Loop

Status: implemented in proposal `0152`.

Let the agent repair candidate graph state before human review:

```text
candidate graph
  -> validation reports
  -> repair plan
  -> revised candidate graph
  -> metric delta
```

The loop may update candidate artifacts, but it must not update canonical specs
or Ontology packages directly.

### 5. Graph Repository Service Contract

Status: Platform contract and report-only promotion request handoff are
implemented; SpecGraph materialized candidate spec previews are implemented in
proposal `0153`, and the final idea-to-spec promotion gate is implemented in
proposal `0154`.

Define the first service/CLI boundary over Git:

- `create_workspace`;
- `create_candidate_workspace`;
- `validate_candidate_graph`;
- `prepare_branch`;
- `create_commit`;
- `open_review`;
- `publish_read_model`.

The first implementation can be local and CLI-backed. Production deployments can
later replace the storage backend with a hosted Git provider, object storage,
queue-backed workers, or a workspace manager without changing the authority
model.

SpecGraph owns the candidate materialization preview before Platform creates a
branch. `0153` writes review-only YAML previews under
`runs/materialized_candidate_specs/` plus
`runs/candidate_spec_materialization_report.json`; Platform consumes the
reported paths through `graph-repository promotion-request` before any executor
step creates a branch, commit, or pull request.

`0154` adds `runs/idea_to_spec_promotion_gate.json` as the final read-only
handoff check. It aggregates pre-SIB metrics, repair-loop context requirements,
materialization readiness, and promotion paths so the autonomous idea-to-spec
flow has one explicit go/no-go surface before Platform promotion.

### 6. SpecSpace Review And Publish Surface

SpecSpace should show:

- active workspace and graph version;
- candidate graph preview;
- pre-SIB/coherence status;
- validation findings;
- repair loop history;
- branch/PR/review status;
- published read model status.

SpecSpace remains a consumer of the repository service contract. It should not
mount a writable checkout and commit files itself.

## Success Criteria

- A user can start with a product idea and receive a coherent candidate graph.
- The candidate graph reaches configured pre-SIB/coherence thresholds without a
  human reviewing every generated node.
- Canonical graph writes happen only through branch/commit/review boundaries.
- SpecSpace can show both the latest canonical graph version and candidate
  graph state without confusing them.
- Published read models remain reproducible from a Git commit and validated
  artifact bundle.

## Related Documents

- `docs/product_workspace_stable_mode_guide.md`
- `docs/product_workspace_initialization_viewer_contract.md`
- `docs/proposals/0062_proto_graph_recursive_refinement.md`
- `docs/proposals/0146_specauthor_prompt_side_authoring_flow.md`
- `docs/ontology_spec_validation_roadmap.md`
