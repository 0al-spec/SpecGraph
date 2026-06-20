# Source Draft: Legacy Spec Ontology Backfill Plan

Origin: operator request for the third ontology adoption slice after grouped gap
review and owner decision import v2.

Intent:

- avoid mass edits across the legacy spec corpus;
- classify specs with only report-only warnings;
- identify specs that require new-term, alias, deprecation, or relation owner
  decisions;
- identify specs that can move through small reviewed PR batches;
- keep the artifact review-first and plan-only.

Non-goals:

- no bulk rewrite of legacy specs;
- no ontology package writes;
- no ontology lockfile writes;
- no canonical spec mutation;
- no prompt-agent execution;
- no automatic owner decision import;
- no semantic-gate closure;
- no SpecSpace UI in this slice.
