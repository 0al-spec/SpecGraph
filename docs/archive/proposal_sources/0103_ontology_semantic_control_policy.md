# Ontology Semantic Control Policy

## Source Intent

The operator asked to continue the Ontology-SpecGraph-SpecSpace line with
productive forward work, not only text proposals. Proposal `0100` introduced
Ontology-grounded semantic control. The next bounded slice should make that
intent executable enough to guide later context-pack, lint-report, delta, and
SpecSpace work.

Proposal identifiers `0101` and `0102` are intentionally left for neighboring
worktrees. This line starts at `0103`.

## Requested Work

- Add a machine-readable semantic control policy.
- Prove the policy against the existing `0060` ontology import fixture.
- Classify a small generated-text smoke sample into accepted terms, aliases,
  unknown terms, deprecated terms, and relation conflicts.
- Preserve all existing authority boundaries: no prompt execution, no canonical
  specs, no ontology package writes, no lockfile mutation, and no SpecSpace UI.

## Follow-Up Shape

The next slices should build the real context pack, then a broader semantic lint
report, then delta/review packets, then SpecSpace or supervisor integration.
