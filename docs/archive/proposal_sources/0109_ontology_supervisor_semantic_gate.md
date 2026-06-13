# Ontology Supervisor Semantic Gate

## Source Intent

After `0108`, SpecGraph has a single ontology semantic review surface that
SpecSpace can display and the supervisor can treat as evidence. The next
bounded step is to turn that surface into a typed supervisor gate artifact
without letting generated ontology material become canonical authority.

## Requested Work

- Build `ontology_supervisor_semantic_gate` from
  `runs/ontology_semantic_review_surface.json`.
- Map blocking findings to `gate_state: blocked`.
- Map review-required findings or ontology delta candidates to
  `gate_state: review_pending` when no blocker exists.
- Preserve source artifact refs, review item ids, required human action, and
  non-mutating failure modes.
- Keep prompt-agent execution, Ontology package writes, lockfile updates,
  candidate acceptance, and canonical spec mutation explicitly forbidden.
- Keep the output deterministic and local under `runs/`.

## Follow-Up Shape

The following slice should wire this artifact into targeted supervisor runs so
semantic gate evidence can route generation attempts before and after prompt
agent invocation. That follow-up should still avoid automatic Ontology package
drafting or canonical spec mutation.
