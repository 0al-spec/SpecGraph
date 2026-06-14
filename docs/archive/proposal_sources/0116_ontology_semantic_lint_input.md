# Ontology Semantic Lint Input

## Operator Intent

The ontology semantic lint line should move beyond fixture-only terms without
turning into a strict ontology type system. For MVP, SpecGraph needs a
source-backed input artifact that records which terms were extracted from real
proposal or supervisor output and where those terms appeared.

## Bounded Slice

Add a deterministic `ontology_semantic_lint_input` artifact under `runs/`.

The artifact should:

- read tracked proposal or supervisor output sources;
- verify declared term anchors are present in the source text;
- record source id, source kind, repository path, digest, and span;
- feed the existing semantic lint report classifier;
- preserve all current no-mutation and no-authority boundaries.

## Non-Goals

- Arbitrary natural-language parsing.
- Prompt-agent execution.
- Canonical SpecGraph mutation.
- Ontology package writes.
- Lockfile updates.
- SpecSpace mutation UI.

## Next Gap

```text
wire_supervisor_semantic_gate_into_targeted_runs
```
