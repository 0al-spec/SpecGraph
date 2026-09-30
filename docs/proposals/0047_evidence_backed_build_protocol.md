# Evidence-Backed Build Protocol

## Status

Draft proposal

## Source Material

This proposal distills the expert review captured in:

- `docs/income/runs.md`

The source review is treated as input evidence, not as canonical policy by
itself. This proposal records the SpecGraph-native interpretation.

## Context

SpecGraph has reached a stage where the supervisor can repeatedly select weak
spots, produce bounded graph mutations, validate them, and open reviewable pull
requests. That makes self-hosting credible, but it also exposes a missing
governance layer.

The raw `runs/` directory contains important operational evidence:

- why a spec node was selected;
- what candidate mutation was produced;
- what validation accepted or rejected;
- what gate decision was required;
- what changed after approval.

At the same time, `runs/` is a noisy runtime workspace. It contains timestamps,
retry attempts, local paths, intermediate failures, and generated projections.
Committing all of it as source would make review harder and would confuse raw
runtime logs with canonical graph truth.

SpecGraph needs a stricter distinction:

```text
raw runtime runs
  -> curated evidence packets
  -> implementation/build readiness
  -> code/test/runtime evidence
  -> graph update
```

## Problem

Today SpecGraph has two incomplete interpretations of supervisor evidence:

1. Treat `runs/` as local noise and rely on PR descriptions to summarize what
   happened.
2. Treat `runs/` as proof and risk committing a large, unstable log directory.

Neither is enough.

If raw runs are ignored, SpecGraph loses explainability. A reviewer cannot
fully reconstruct why a change happened, which validation failed first, whether
an auto-retry recovered safely, or whether a gate decision was justified.

If raw runs are committed wholesale, the repository becomes dominated by
generated artifacts that are not canonical product state. Reviewers must sift
through local machine paths and retry residue to find the evidence that matters.

The broader implementation problem is similar. A mature spec graph should not
jump directly from `spec -> code`. It needs a governed build protocol that
answers:

- which subgraph is ready to implement;
- which nodes are semantic leaves versus implementation leaves;
- which contracts and tests are required before coding;
- which parent compositions can be assembled safely;
- which evidence must flow back into the graph after code changes.

## Goals

- Keep raw `runs/` local by default while preserving important supervisor work
  as curated, reviewable evidence.
- Define an evidence packet concept that captures the minimal proof needed for
  a PR or self-hosting step.
- Introduce the Build Protocol as the bridge from mature spec subgraphs to
  implementation work, tests, runtime evidence, and graph feedback.
- Distinguish semantic leaves, implementation leaves, and runtime-observable
  leaves.
- Define implementation readiness as a derived signal over contracts,
  dependencies, tests, invariants, side effects, and evidence.
- Define composition contracts for parent nodes so branch assembly is more than
  summing child implementations.
- Preserve risk-based ceremony: critical governance/security nodes require more
  evidence than simple adapters or documentation updates.
- Require external anchors so graph-health optimization does not replace real
  product, runtime, security, or human-review evidence.
- Keep license and source provenance explicit when reconstructing or learning
  from external systems.

## Non-Goals

- Committing all of `runs/`.
- Making raw runtime artifacts canonical graph truth.
- Implementing the Build Protocol in this proposal.
- Starting autonomous code generation from specs.
- Replacing the Implementation Work layer proposal.
- Replacing human PR review or merge boundaries.
- Defining final JSON schemas for every future artifact.

## Core Proposal

SpecGraph should treat supervisor and build evidence as a two-layer system:

1. **Raw operational evidence** lives in generated runtime artifacts such as
   `runs/*` and remains local or CI-artifact scoped by default.
2. **Curated evidence packets** are intentionally promoted summaries that can
   be committed, cited by PRs, attached to graph nodes, or consumed by viewer
   surfaces.

The rule is:

```text
Do not commit raw runs by default.
Do commit curated evidence when it is needed for audit, review, or graph state.
```

## Curated Supervisor Evidence Packet

A supervisor evidence packet should capture the smallest stable proof that a
bounded graph mutation was lawful.

Minimum fields should include:

```json
{
  "artifact_kind": "supervisor_evidence_packet",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "evidence_kind": "supervisor_run_packet",
  "run_id": "20260505T210742Z-SG-SPEC-0030-8616d24c",
  "spec_id": "SG-SPEC-0030",
  "selection": {
    "selected_because": ["graph_gap", "maturity_pressure"],
    "source_artifacts": ["runs/graph_next_moves.json"]
  },
  "mutation": {
    "changed_files": ["specs/nodes/SG-SPEC-0030.yaml"],
    "change_class": "local_refinement",
    "diff_summary": "Strengthened boundary separation evidence."
  },
  "validation": {
    "format": "passed",
    "lint": "passed",
    "tests": "passed",
    "initial_failures": [],
    "retry_recovery": null
  },
  "gate": {
    "gate_state": "none",
    "decision": "approve",
    "review_reason": "bounded local refinement"
  },
  "raw_artifact_reference": {
    "availability": "retained_ci_artifact",
    "run_path": "runs/20260505T210742Z-SG-SPEC-0030-8616d24c.json",
    "content_sha256": "sha256:example",
    "artifact_uri": "gh-artifact://0al-spec/SpecGraph/actions/runs/example",
    "retention_expires_at": "2026-06-05T00:00:00Z"
  }
}
```

The packet is stable enough for review. The raw run remains available for deep
debugging only when a durable artifact URI and content digest are recorded. If a
raw run is not retained, the packet must say so explicitly with
`availability: "summary_only"` and must not imply that deep raw-run recovery is
possible after local workspace or CI retention expiry.

## Build Protocol

SpecGraph should not wait for the entire graph to become perfect before code
exists. Instead, it should move through frontiers:

```text
specification frontier
  -> implementation frontier
  -> composition frontier
  -> runtime evidence frontier
```

The Build Protocol should define how a mature subgraph is converted into code:

1. Select an implementation-ready subgraph.
2. Freeze or identify the graph snapshot used for the build decision.
3. Generate or verify implementation contract packs for selected leaves.
4. Implement bounded leaves.
5. Run unit, contract, and integration tests.
6. Attach code/test/runtime evidence back to the graph.
7. Recompute parent composition readiness.
8. Repeat until root-level scenarios and runtime anchors are satisfied.

This is not pure bottom-up construction. The protocol should combine:

- top-down skeleton and architecture boundaries;
- bottom-up implementation of ready leaves;
- middle-out integration and composition checks.

## Leaf Taxonomy

SpecGraph should distinguish at least three leaf meanings:

- `semantic_leaf`: no further useful conceptual decomposition is currently
  modeled in the graph.
- `implementation_leaf`: bounded enough to implement as code with clear
  inputs, outputs, invariants, dependencies, and tests.
- `runtime_leaf`: observable enough to verify with runtime evidence after
  implementation.

Only implementation-ready leaves should be handed to coding agents.

## Implementation Readiness

Implementation readiness should be a derived signal, not a manual label.

Example shape:

```json
{
  "spec_id": "SG-SPEC-0123",
  "implementation_readiness": {
    "status": "ready_to_implement",
    "score": 0.91,
    "blockers": [],
    "required_artifacts": {
      "contract": "present",
      "tests": "present",
      "invariants": "present",
      "dependencies": "resolved",
      "side_effects": "declared",
      "failure_modes": "declared",
      "security_policy": "present",
      "observability": "present"
    }
  }
}
```

Blocked nodes should name why they are blocked:

- `blocked_by_missing_contract`;
- `blocked_by_missing_tests`;
- `blocked_by_unstable_parent`;
- `blocked_by_unresolved_dependency`;
- `blocked_by_undeclared_side_effects`;
- `blocked_by_missing_failure_modes`;
- `blocked_by_missing_runtime_evidence_boundary`.

## Implementation Contract Pack

Each implementation-ready leaf should have a contract pack before code is
generated.

Minimum contract dimensions:

- target spec node;
- behavior summary;
- inputs and outputs;
- dependencies;
- invariants;
- failure modes;
- negative cases;
- side effects;
- test requirements;
- observability events or evidence expectations;
- forbidden mutations or forbidden capabilities.

The contract pack is the bounded handoff to an implementation agent. The agent
should not need authority over the whole graph to implement one leaf.

## Parent Composition Contract

A parent node is not just the sum of child implementations.

When children become implemented, the parent needs its own composition contract:

- child set being composed;
- cross-child invariants;
- integration tests;
- ordering or lifecycle expectations;
- evidence writeback rules;
- failure behavior at component boundaries.

Many important bugs occur at child boundaries. Composition contracts keep those
bugs visible as graph work rather than accidental implementation detail.

## Implementation Frontier

The first derived surface for the Build Protocol should be an implementation
frontier:

```json
{
  "artifact_kind": "implementation_frontier",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "generated_at": "2026-05-06T00:00:00Z",
  "source_snapshot": {
    "graph_ref": "main",
    "graph_digest": "sha256:example"
  },
  "frontier": [
    {
      "spec_id": "SG-SPEC-0123",
      "kind": "implementation_leaf",
      "readiness": 0.94,
      "priority": 0.88,
      "reasons": [
        "contract_complete",
        "dependencies_resolved",
        "unblocks_parent:SG-SPEC-0200",
        "deterministic_tests_available"
      ]
    }
  ],
  "blocked": [
    {
      "spec_id": "SG-SPEC-0150",
      "reasons": [
        "missing_failure_modes",
        "parent_contract_unstable"
      ]
    }
  ]
}
```

Ranking should not be pure topology. It should consider:

- readiness score;
- dependency-unblocking value;
- risk reduction;
- graph centrality;
- volatility;
- unresolved assumptions;
- security or governance sensitivity.

## SCC and Component Handling

Implementation scheduling must not assume that useful leaves always exist.

If a subgraph has cycles, the Build Protocol should:

1. detect strongly connected components;
2. collapse the SCC into a temporary implementation component;
3. define the component boundary first;
4. split implementation internally after the component boundary is stable.

This prevents the scheduler from looping forever while looking for a nonexistent
leaf.

## Risk-Based Ceremony

Evidence requirements should be proportional to risk.

High-ceremony examples:

- security boundaries;
- graph mutation semantics;
- supervisor authority;
- agent permission models;
- irreversible canonical transitions.

Lower-ceremony examples:

- documentation-only updates;
- cosmetic viewer labels;
- simple adapters with bounded tests;
- generated index projection with no canonical mutation.

No change should have zero evidence, but not every change needs the same amount
of evidence.

## External Anchors

SpecGraph must not optimize only for its own graph-health metrics.

Build and supervisor evidence should eventually anchor to:

- user scenarios;
- integration tests;
- runtime behavior;
- security properties;
- external consumer observations;
- human review;
- deployment or production telemetry when available.

These anchors keep graph maturity from becoming a self-referential score.

## Source and License Provenance

When SpecGraph reconstructs, imports, or learns from external systems, evidence
packets and future contract packs should preserve source provenance:

```json
{
  "source_type": "open_source_repository",
  "license": "MIT",
  "copied_code_used": false,
  "copied_code_policy": "not_used_without_explicit_license_review",
  "clean_room_required": false,
  "allowed_use": ["public_api_shape", "behavioral_specification"]
}
```

For proprietary or unclear sources, the default should be conservative:

```json
{
  "source_type": "proprietary_observation",
  "license": "unknown",
  "copied_code_used": false,
  "copied_code_policy": "forbidden",
  "clean_room_required": true,
  "allowed_use": ["behavioral_compatibility_notes"]
}
```

This keeps reverse specification from becoming hidden implementation copying.
`copied_code_used` is always a boolean fact. `copied_code_policy` is the
enum-like policy field that explains whether copying is forbidden, deferred to
license review, or otherwise constrained.

## Proposed Runtime Slices

### Slice 1: Supervisor Evidence Packet Proposal

- Add a policy for curated supervisor evidence packets.
- Add a command that can distill one raw run into a stable evidence packet.
- Keep raw `runs/*` ignored by default.
- Write reviewable packets to a stable curated location such as
  `docs/evidence/supervisor-runs/<run_id>.json` until a future dedicated
  evidence store exists.
- Let PR descriptions cite the curated packet path and run id.

### Slice 2: Implementation Readiness Projection

- Add a derived artifact that classifies candidate nodes as
  `ready_to_implement`, blocked, or not applicable.
- Start with conservative rule-based blockers.
- Do not create code tasks yet.

### Slice 3: Implementation Frontier Viewer Contract

- Document the viewer-facing contract for frontier rows, blockers, risk, and
  next action.
- Keep this read-only.

### Slice 4: Contract Pack Preview

- Emit reviewable implementation contract-pack previews for selected ready
  leaves.
- Do not write code.

#### First bounded realization: explicit-node observability

The Zeusus pilot exposed a missing handoff: runtime tracing was implemented from
operator conversation while the product spec only described route composition.
Existing implementation must be recorded as prior work, never retroactively
described as generated by the new specification.

`make implementation-contract-pack` now projects one explicitly selected node
through the `explicit_node_observability_v1` profile. The input is a structured
`specification.observability` declaration with obligations, stable obligation IDs,
event boundaries, attributes, expected outcomes, scenario references,
non-interference guarantees, and excluded attributes. Each scenario reference
must resolve within that node. This profile is opt-in; it does not require
observability fields on every SpecGraph node or change canonical YAML ontology.

The derived `implementation_contract_pack_preview` pins the exact source SHA-256,
carries the full target specification and acceptance criteria, and provides an
`implementation_work_preview` using the existing Implementation Work vocabulary:
`affected_spec_ids`, `required_tests`, and `expected_evidence`. It is not inserted
into the implementation backlog or dispatched to a coding agent automatically.
The operator can hand the reviewed pack to a bounded implementation task.

Missing obligations or an unresolved source gate produce `blocked`; a structurally
valid pack remains `review_required`. Neither state is implementation readiness,
runtime verification, human approval, nor permission to mutate code or specs.
Malformed declarations fail validation. Consumers must regenerate and compare
the source digest before using a retained preview after any source change.

Output is scoped to `runs/implementation-contract-packs/<spec-id>.json` in the
explicit workspace. The producer does not infer requirements from source code,
conversation history, parent nodes, or Feature Passport. Parent references remain
visible with inheritance `not_evaluated`; source hierarchy and policy propagation
are a future slice. A product binding can map obligations to SpecificationCore
objects, call sites, tests, and independent evidence providers without creating
a Feature Passport dependency on SpecGraph.

The pilot also found a Codex executor transport failure: final protocol markers
were present in the diagnostic transcript but absent from captured stdout.
Nested refinement now reads the run-local `--output-last-message` artifact and
joins both stream readers before cleanup. Missing/empty final messages still fail
the existing protocol gate; transcript text cannot authorize a candidate.

This realizes only the observability part of Slice 4. Generic readiness scoring,
complete contract-pack dimensions, inherited-policy resolution, automatic task
dispatch, Feature Passport observation ingestion, and production storage remain
unimplemented by this slice. See [the operator contract](../implementation_contract_pack.md).

### Slice 5: Composition Readiness

- Project parent composition readiness from child implementation evidence and
  cross-child invariants.

## Relationship To Existing Proposals

- `0037_implementation_work_layer.md` defines Layer 2 as the bridge from specs
  to implementation work. This proposal defines evidence and readiness rules
  that make that bridge safer.
- `0039_review_feedback_learning_loop.md` already treats review comments as
  process evidence. This proposal extends the same principle to supervisor and
  build evidence.
- `0041_graph_next_moves_game_master_surface.md` can consume implementation
  frontier signals as future next moves.
- `0045_conversation_memory_exploration_vault.md` covers pre-canonical source
  memory. This proposal covers post-spec build and evidence feedback.

## Acceptance Criteria

- Raw `runs/*` remain local by default.
- The proposal defines why curated evidence packets are different from raw run
  logs.
- The proposal defines implementation readiness as a derived signal.
- The proposal distinguishes semantic, implementation, and runtime leaves.
- The proposal defines parent composition contracts.
- The proposal includes risk-based evidence ceremony.
- The proposal preserves external anchors and source/license provenance.


### Bounded evidence admission follow-up — 2026-09-28

The Zeusus owner requested deterministic admission for implementation claims,
separate from specification maturity. `tools/evidence_claim_gate.py` now consumes
live Feature Passport pinned source resolution under a digest-pinned local
adapter policy. Optional canonical `evidence_claims` declare requirements only;
Supervisor and YAML lint reject self-authored verdicts in that surface.

`source_anchored` remains limited to pinned syntactic source identity. A bounded
`runtime_verified_v1` path now freshly invokes Feature Passport `verify-decision`
for one explicitly mapped claim. The request pins the CLI, claim policy, bundle,
decision, trust stores, and raw referenced pair files; the gate snapshots and
checks inputs around execution. Admission requires exit zero, strict trusted JSON,
an accepted decision, and exact signed identity/digest/profile/authority/key
matches. A trusted `not_satisfied` result remains unknown. Test/effect/outcome
claims remain unknown without their own evaluators. Source review gates still
block aggregate admission. No lifecycle state is mutated, no cross-spec inheritance
is inferred, and no upstream runtime receipt contract is fabricated. This bounded
slice precedes the full build/review/acceptance protocol described above.
See [evidence claim admission](../evidence_claim_admission.md) for trust boundaries,
CLI, failure modes, and the external provider contract.


### Cross-repository receipt issuance handoff — 2026-09-30

**Status: `proposal_only`.** This follow-up owns coordination under proposal
0047, not an implemented issuer, adopted trust configuration, or lifecycle
permission. The earlier source-only follow-up is historical: the current bounded
SpecGraph consumer also verifies externally supplied signed aggregate decisions
through `runtime_verified_v1`. Issuance remains a separate gap.

The Zeusus pilot captured two real headless route calculations at producer
commit `28b3710857cd4fdc76e14a69ea924418dc19b9bb`. Six observations matched the
FeaturePassport CLI built from `7e8ced31775b10c7274c47a66c3098cdde5335e4`;
four source anchors resolved. The retained report is
`Zeusus/docs/evidence/route-observation-capture/run-28b3710/report.json`.
Its result is `matched_untrusted`, receipt `none`, admission `not_attempted`.
These are motivating observations, not retrospective issuance or runtime proof.

#### Ownership and dependency direction

| Owner | Owned change | Boundary |
| --- | --- | --- |
| Zeusus | Product specs, SpecificationCore objects, product passport, probes, trace adapter, pilot capture and fixtures | Emits observations; does not grant itself SpecGraph admission |
| SpecificationCore | Generic specification evaluation and diagnostic tracing | No game, receipt policy, or SpecGraph schema dependency |
| FeaturePassport | Provider-neutral observation/receipt contracts, generic issuer API/CLI, signer abstraction, verification and aggregate evaluation | Must work without SpecGraph IDs, service or schemas |
| SpecGraph | Evidence requirements, implementation handoff, provider adapter, canonical claim mapping and admission policy | Consumes verified artifacts; does not implement another receipt schema or signer |
| SpecSpace | Read-only visualization of requirements, evidence and gate reasons | Does not issue receipts or decide trust |
| Explicit runner/CI configuration | Operated authority, capture execution, signer access, selected policy and artifact publication | A role; this proposal creates no additional repository or hosted service |

For the bounded pilot, runner orchestration may remain in Zeusus. Shared issuance
code belongs in FeaturePassport. SpecGraph coordinates the work through this
proposal and consumes the results through its existing adapter. No dependency
`FeaturePassport -> SpecGraph` is introduced.

#### Policy and trust are separate inputs

- **Receipt policy:** describes exactly what the issuer checks and signs. The
  generic supported profile belongs in FeaturePassport; a reviewed exact policy
  and its deployment selection belong to the runner/authority configuration.
- **Claim policy:** states the required evidence for one bounded assertion.
  Product intent and scenarios originate in Zeusus specs; its provider-neutral
  representation uses FeaturePassport contracts, with mapping/handoff owned by
  the SpecGraph adapter. It must not invent probes or inherited requirements.
- **Admission policy:** determines whether that assertion can be admitted for
  the current canonical node. SpecGraph owns this decision and review boundary.
- **Trust stores:** explicitly owned by each verifier/consumer. SpecGraph selects
  receipt and decision authorities for its admission invocation; no issuer
  registration or valid signature automatically grants trust.
- **Private signing capability:** supplied by the authority deployment outside
  Git (for example, Keychain or CI secret custody). FeaturePassport receives an
  injected signer. This follow-up does not generate keys or edit trust stores.

The first proposed receipt policy proves acceptance of exact contract-matched
observation bytes only. It does not prove independent runtime origin, successful
execution, delivery, game completion or production operation. A local headless
run remains local headless evidence after signing. A stronger origin/execution
claim needs a separately specified capture/attestation policy.

#### Bounded work routing and review gates

1. **FeaturePassport follow-up:** propose and implement a generic receipt issuer
   compatible with `signed-observation-receipt-v1`, injected signer and explicit
   policy authorization. It must validate inputs before signing and pass the
   existing verifier. Rejected, tampered, expired or unauthorized inputs must
   fail. Existing aggregate-decision issuance can be reused within its actual
   scope; production key custody is not supplied by that library.
2. **Zeusus pilot integration:** select an explicitly reviewed local authority
   configuration, rerun capture under the issuer policy, retain exact passport,
   observations, receipt pairs and executable/source pins. Historical unsigned
   artifacts remain historical and do not become proof of issuer-controlled
   execution by being signed later. Admission trust keys are provisioned by the
   consumer, independently of the observation payload.
3. **SpecGraph admission integration:** review the exact claim-policy scope and
   canonical `feature_passport_decision` mapping, then run the existing live
   `verify-decision` admission path with explicit receipt/decision trust stores.
   A trusted `not_satisfied`, stale bytes or unresolved source gate cannot pass.
4. **SpecSpace follow-up, only when needed:** expose the existing distinctions
   between observed, matched, trusted and admitted; no viewer-owned authority.

Each implementation has its own repository PR and evidence. Their dependency
order is FeaturePassport issuer contract/implementation -> Zeusus bounded pilot
-> SpecGraph admission evidence. Proposal review does not imply that those PRs
exist, that authority/key configuration is approved, or that any spec gate is
cleared. Proposed issuance and pilot wiring have **no runtime realization in
this amendment**; existing admission tools remain unchanged.

#### Acceptance for this proposal amendment

- The ownership table routes every implementation task to one repository or
  explicitly operated deployment role.
- Receipt policy, claim policy and admission policy remain distinct; each
  consumer controls its own trust inputs.
- FeaturePassport remains provider-neutral and a passport without SpecGraph
  remains valid under its own contracts.
- The local receipt scope cannot be presented as production or game-outcome
  proof, nor can historical observations be relabeled as issuer-controlled runs.
- Source draft, promotion provenance, runtime classification and DocC remain
  aligned. Issuer implementation, keys, policy adoption and lifecycle mutation
  require subsequent bounded work and evidence.
