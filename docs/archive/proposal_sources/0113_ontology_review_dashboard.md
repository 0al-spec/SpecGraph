# Ontology Review Dashboard

Source artifact class: working draft

## Motivating concern

SpecGraph can emit closed-loop Ontology evidence, but operators and SpecSpace
still have to inspect multiple artifacts separately to understand the current
semantic gate state, blocking findings, pending owner decisions, and review
actions.

## Bounded scope

Add a deterministic `ontology_review_dashboard` artifact under `runs/` that
aggregates the existing read-only Ontology semantic review surface, supervisor
semantic gate, delta draft intake, and closed-loop evidence artifacts. The
dashboard must expose status summary, gate evidence, blocking and review items,
delta candidates, draft requests, closed-loop entries, review actions, source
artifacts, and authority boundary for SpecGraph and SpecSpace consumers.

The slice must not import owner decisions, write Ontology packages, update
ontology lockfiles, mutate canonical specs, mark candidate terms accepted,
close semantic gates, execute prompt agents, parse arbitrary text, or run
ontologyc.

## Acceptance sketch

- Declare the dashboard layout and contract in
  `tools/ontology_semantic_control_policy.json`.
- Build `runs/ontology_review_dashboard.json` from existing derived Ontology
  surfaces in `tools/ontology_imports.py`.
- Validate source artifact consistency and preserve all non-authority and
  non-mutation flags.
- Cover artifact shape, custom write path, authority rejection, and `make
  ontology-imports` output in focused tests.
- Register proposal `0113` in promotion and runtime registries.

## Next gap

```text
build_specspace_rich_ontology_review_panel
```
