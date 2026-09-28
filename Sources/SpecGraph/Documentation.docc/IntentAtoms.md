# Intent Atoms and SIB snapshots

SpecGraph's `specgraph-intent-atoms-v1` profile provides one explicit choice
for counting Intent Atoms in the SIB framework. It counts structured
acceptance criteria and explicitly declared `atoms.intents[]` while keeping
the broader SIB definition open to other implementations.

The `specgraph_intent_atoms_snapshot` artifact is read-only evidence for one
Git commit. Its profile digest, provenance, source locations, completeness state, and
diagnostics make the count reproducible. A zero-atom node means that the
supported fields contain no countable declaration; it does not prove that the
node has no intent. The count is sensitive to how authors split and combine
YAML entries.

The analyzer reads Git tree entries and blob contents directly, so archive
attributes cannot omit or rewrite tracked specifications. A missing or
non-directory specification root produces an incomplete snapshot. Profile
digests use canonical JSON, and atom text normalizes line endings before
counting and comparison.

An atom is not evidence of human authorship, review, approval, or
verifiability. The profile does not define a SIB threshold or change canonical
specification authority. See the [repository contract](https://github.com/0al-spec/SpecGraph/blob/main/docs/intent_atoms.md)
for counting rules and CLI usage.
