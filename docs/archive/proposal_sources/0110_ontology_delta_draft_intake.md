# Ontology Delta Draft Intake

## Source Intent

After `0109`, SpecGraph can derive a supervisor semantic gate from ontology
review evidence. The next bounded step is to prepare a typed intake artifact for
Ontology delta draft work without writing the Ontology repository or treating
candidate terms as accepted.

## Requested Work

- Build `ontology_delta_draft_intake` from the supervisor semantic gate and
  ontology delta candidate review packet.
- Preserve candidate identity, proposed draft delta payload, gate state,
  blocking item refs, required human action, and non-mutating write flags.
- When the semantic gate is blocked, mark draft requests
  `blocked_by_semantic_gate` rather than ready for package drafting.
- Keep package writes, lockfile updates, canonical spec mutations, prompt-agent
  execution, and candidate acceptance explicitly forbidden.
- Keep the output deterministic and local under `runs/`.

## Follow-Up Shape

The following slice should collect or model Ontology owner decisions for intake
requests. Materializing an Ontology package draft should remain deferred until a
candidate is owner-approved and the semantic gate is clear.
