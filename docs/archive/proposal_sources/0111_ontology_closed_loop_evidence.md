# Ontology Closed-Loop Evidence

## Source Intent

After `0110`, SpecGraph can prepare review-only Ontology delta draft intake
requests. The next bounded step is to expose a SpecGraph-facing evidence surface
that reports whether those requests are blocked, pending owner decision, or
ready for later review without pretending that Ontology has accepted anything.

## Requested Work

- Build `ontology_closed_loop_evidence` from
  `runs/ontology_delta_draft_intake.json`.
- Preserve candidate id, intake id, intake state, required human action,
  blocking refs, and source artifacts.
- Mark entries blocked when the intake is blocked by the semantic gate.
- Leave Ontology decision refs empty until real owner decisions exist.
- Keep the output deterministic and local under `runs/`.
- Do not mutate canonical specs, close semantic gates, accept candidates, write
  Ontology packages, update lockfiles, or invoke prompt agents.

## Follow-Up Shape

The following slice should wire this evidence surface into SpecGraph review
surfaces or dashboard/backlog projections. Actual closure should require
Ontology owner evidence and a non-blocked semantic gate.
