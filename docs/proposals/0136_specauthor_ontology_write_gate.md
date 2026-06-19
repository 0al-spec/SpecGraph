# SpecAuthor Ontology Write Gate

RFC: SG-RFC-0136
Version: 0.1.0

## Status

Draft proposal

Decision scope: add a deterministic write gate for SpecAuthor-generated graph
artifacts before they can be treated as graph-ready.

## Source Material

Source draft:

- `docs/archive/proposal_sources/0136_specauthor_ontology_write_gate.md`

Roadmap:

- `docs/ontology_spec_validation_roadmap.md`

Depends on:

- `0126_specauthor_claim_calibration_prompt_contract`
- `0128_ontology_term_binding_policy`
- `0129_generated_term_binding_gate`
- `0135_spec_ontology_validation_report`

## Problem

SpecGraph now has a project-local ontology package, legacy binding reports, and
a report-only validation surface. That still leaves one risky gap: a future
SpecAuthorAgent could generate a new proposal/spec artifact that looks
graph-ready while omitting active ontology/domain/context, silently inventing
terms, or persisting weak claims as decisions.

Legacy specs should stay report-only. The stricter boundary belongs at the
point where new generated artifacts ask to enter the graph.

## Proposal

Add:

```bash
make specauthor-ontology-write-gate \
  SPECAUTHOR_ONTOLOGY_WRITE_GATE_ARTIFACT=<generated-artifact.json>
```

The command emits:

```text
runs/specauthor_ontology_write_gate_report.json
```

The gate validates typed generated artifact JSON. It does not infer semantics
from prose. The artifact must provide:

- `active_frame` with ontology refs, domain refs, context refs, target artifact,
  project, and lifecycle phase;
- `term_bindings` and/or `ontology_gaps` compatible with the existing term
  binding gate;
- `claims[]` with F/G/R calibration for strong claims, or an explicit
  `claim_inventory.strong_claims_present=false`;
- no `context_completion_request` when the artifact is presented as a final
  graph write.

## Implemented Slice

This slice adds:

- `tools/specauthor_ontology_write_gate.py`;
- `make specauthor-ontology-write-gate`;
- fixtures for clear and review-required generated artifacts;
- focused tests for active frame, term binding, claim calibration, context
  completion, and strict CLI behavior;
- proposal tracking metadata.

The gate composes with `tools/ontology_term_binding_gate.py` instead of
duplicating term authority rules.

## Acceptance

This proposal is complete when:

- a generated artifact with active frame, accepted term binding, and calibrated
  strong claim passes with `write_decision: allow_graph_write`;
- an artifact with missing active context, unbound generated terms, or low-R
  decision claims fails with `write_decision: reject_graph_write`;
- `context_completion_request` prevents final graph write;
- strict CLI mode exits non-zero for rejected artifacts;
- the report keeps ontology writes, lockfile writes, and canonical spec
  mutations disabled;
- proposal tracking gates pass.

## Out of Scope

- Running prompt agents;
- parsing arbitrary prose to discover claims;
- mutating `specs/nodes/*.yaml`;
- accepting ontology terms;
- writing Ontology packages or lockfiles;
- changing legacy spec report-only validation.
