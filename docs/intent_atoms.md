# SpecGraph Intent Atoms v1

SpecGraph uses the SIB framework's freedom to choose an implementation-level
definition of an Intent Atom. The `specgraph-intent-atoms-v1` profile counts
only structured acceptance
criteria and explicitly declared `atoms.intents[]`. It is a local measurement
contract; it does not redefine SIB for other projects.

## Counting rules

- Each non-empty string in `acceptance[]` or `spec.acceptance[]` is one atom.
- Each mapping in `atoms.intents[]` or `spec.atoms.intents[]` is one atom when
  it has a non-empty `statement` string.
- If explicit intents are present, they are counted and acceptance items are
  retained as non-counted context. This prevents counting the same requirement
  twice when a spec carries both representations.
- Compound acceptance statements are not split. Repetitions are preserved;
  atoms in separate specs are not semantically deduplicated.
- Objective, scope, premises as standalone declarations, rationale, evidence,
  metadata, provenance, links, and other fields do not add atoms in v1.

The count is representation-sensitive. Splitting or merging YAML entries may
change the count without changing the underlying intent. The profile version
and digest therefore travel with every snapshot. An atom's presence says
nothing by itself about human authorship, review, approval, or verifiability.

## Snapshot CLI

Run the analyzer against an exact Git revision; it reads tracked YAML from Git
and does not check out or execute the historical revision:

```sh
python3 tools/intent_atoms.py snapshot --repo . --revision main
python3 tools/intent_atoms.py snapshot --repo . --revision <commit> \
  --spec-root specs/nodes --output runs/intent_atoms_snapshot.json
```

The `specgraph_intent_atoms_snapshot` artifact records the commit SHA, analyzer
and profile versions, profile digest, node kind, lifecycle status, provenance,
atom counts, source field and path for each atom, and diagnostics. It reports `completeness: incomplete`
when malformed or ambiguous input prevents a trustworthy full count. A partial
subtotal must not be treated as the project's full `N_spec`.

The selected fields define v1 coverage. Specs with no supported declaration are
reported as zero-atom nodes with mode `absent`; this is a coverage fact, not a
claim that the node expresses no intent. Other semantic fields remain outside
the v1 count.
