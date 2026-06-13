# Ontology Owner Decision Contract

Source artifact class: working draft

## Motivating concern

SpecGraph can display closed-loop Ontology evidence, but it does not yet have a
typed report contract for the accepted/rejected decisions that Ontology owners
will return for reviewed delta candidates.

## Bounded scope

Add a deterministic `ontology_owner_decision_report` artifact under `runs/` that
models Ontology owner decisions as read-only evidence. The report carries
decision ids, candidate ids, intake ids, decision state, Ontology decision refs,
decision actor/time, accepted/rejected state, matched closed-loop evidence
state, and explicit false SpecGraph import, gate-close, and canonical mutation
flags. Decisions that do not match pending Ontology owner closed-loop evidence
are ignored with diagnostics rather than emitted as valid decision evidence.

This slice must not import decisions into SpecGraph, mark candidates accepted,
close semantic gates, write Ontology packages, update ontology lockfiles, mutate
canonical specs, invoke prompt agents, parse arbitrary text, or run ontologyc.

## Acceptance sketch

- Declare the owner decision report layout and contract in
  `tools/ontology_semantic_control_policy.json`.
- Build `runs/ontology_owner_decision_report.json` from a typed owner-decision
  fixture and existing closed-loop evidence source refs.
- Validate accepted/rejected/clarification states against pending closed-loop
  evidence and reject import authority.
- Cover artifact shape, write path, authority rejection, and `make
  ontology-imports` output in focused tests.
- Register proposal `0114` in promotion and runtime registries.

## Next gap

```text
build_ontology_decision_import_preview
```
