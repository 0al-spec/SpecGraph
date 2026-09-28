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
python3 tools/intent_atoms.py snapshot --repo . --revision HEAD \
  --output runs/intent_atoms_snapshot.json
python3 tools/intent_atoms.py snapshot --repo . --revision <commit> \
  --spec-root specs/nodes --output runs/intent_atoms_snapshot.json
```

The analyzer reads Git tree entries and blob contents directly. Archive
attributes such as `export-ignore` and `export-subst` therefore cannot omit or
rewrite evidence. A missing or non-directory `--spec-root` produces an
incomplete snapshot with a diagnostic; this is expected for historical commits
that predate the specification tree. The root is passed as a literal Git
pathspec, so option-like names cannot alter the Git command.

The `specgraph_intent_atoms_snapshot` artifact records the commit SHA, analyzer
and profile versions, profile digest, node kind, lifecycle status, provenance,
atom counts, source field and path for each atom, and diagnostics. The profile
digest is calculated from canonical JSON, so whitespace and key ordering do not
change it. Atom text normalizes CRLF and CR to LF and trims outer whitespace.
It reports `completeness: incomplete`
when malformed or ambiguous input prevents a trustworthy full count. A partial
subtotal must not be treated as the project's full `N_spec`.

The selected fields define v1 coverage. Specs with no supported declaration are
reported as zero-atom nodes with mode `absent`; this is a coverage fact, not a
claim that the node expresses no intent. Other semantic fields remain outside
the v1 count.

## Diff and history replay

Compare revisions using the same current analyzer and profile:

```sh
python3 tools/intent_atoms.py diff --repo . --base <base-commit> --head <head-commit>
python3 tools/intent_atoms.py replay --repo . --revision main --count 30 \
  --output-dir runs/intent_atoms_replay_example
```

Diffs match explicit atoms by node ID and atom ID. Acceptance entries and
explicit atoms without IDs match by node ID, origin, and normalized text;
changed acceptance text appears as a removal and an addition. Cross-node moves
and semantic rewrites are not inferred. A change between acceptance and
explicit-atom modes is called out in `diagnostics.mode_transitions` so source
representation changes are distinguishable from ordinary edits. Incomplete
input remains visible in the diff's completeness state and diagnostics.

Replay records the resolved tip SHA and the oldest-to-newest SHA list for up to
30 first-parent commits, including commits without spec changes. It writes one
snapshot per commit, one diff per adjacent pair, and a manifest into an empty
output directory. The manifest pins the exact history window, profile digest,
and analyzer source digest. To reproduce the window, use its recorded tip SHA
and commit count with the analyzer version recorded in the manifest. Its summary
includes accumulated additions, removals, modifications, and source-mode
transitions as well as the net atom-count change.

The metric-pack adapter advertises the versioned snapshot as an optional source.
A consumer may use it only when its completeness is `complete`, its `spec_root`
is `specs/nodes`, its analyzer and profile digests are present, and its commit
SHA matches the measured revision. The pre-existing `acceptance[]` binding
remains labeled as a `legacy proxy` for compatibility.
