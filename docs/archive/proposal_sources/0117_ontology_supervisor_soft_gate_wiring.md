# Ontology Supervisor Soft Gate Wiring

## Source Intent

After `0116`, SpecGraph has a source-backed semantic lint input and the
existing `0109` supervisor semantic gate can report clear, review-pending, or
blocked ontology evidence. The next bounded step is to make ordinary targeted
supervisor runs aware of that gate without turning the gate into hidden prompt
execution or automatic ontology mutation.

## Requested Work

- Read `runs/ontology_supervisor_semantic_gate.json` during ordinary supervisor
  runs as soft review evidence.
- Preserve the source gate state, outcome, required human action, blocking item
  ids, review-required item ids, and candidate item ids in run artifacts.
- Do not invoke prompt agents, rebuild ontology surfaces, write Ontology
  packages, update ontology locks, or mutate canonical specs as part of this
  wiring.
- If the semantic gate is `blocked` or `review_pending`, prevent silent
  `--auto-approve` canonical sync and route the run through the existing
  `review_pending` path.
- If the semantic gate artifact is missing or malformed, continue the run and
  record unavailable evidence rather than failing closed in the first MVP
  wiring slice.

## Follow-Up Shape

The next slice should define the prompt-agent ontology context artifact used
before drafting. That artifact should carry accepted terms, aliases,
deprecated terms, relation conflicts, unresolved gaps, package refs, versions,
digests, prompt input/output refs, and failure modes without granting write
authority over Ontology packages or canonical SpecGraph specs.
