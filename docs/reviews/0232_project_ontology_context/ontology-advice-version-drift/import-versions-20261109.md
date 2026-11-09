# Commit-time advice: matching versions of imported packages

Status: **observed; automatic import selection not implemented**.

While preparing the `GraphInvariant` migration, the configured SpecGraph Git
advice hook passed only `specgraph-core@0.3.0` to `ontologyc advise-staged`.
The new Intent-to-Proposal draft imports `specgraph-core@0.4.0`; the hook
reported `class.field.target.unresolved` for `candidateDraft` and
`candidateProposal`. Checking the same staged draft against 0.4.0 succeeds.
These two diagnostics were false for this valid model. The hook remains
advisory and the observation does not establish that either ontology is invalid.

This is a separate input mismatch from the previously recorded stale **compiler**
binary: a current compiler still needs the matching **package** version.
The standing user instruction to track false warnings through the graph and
the existing `ontology-advice-version-drift` intent and proposal apply here.

## Reproduction and boundaries

The isolated Git index contained the old and new models together, with the
0.3.0 and 0.4.0 core packages committed as indexed imports. The configured
compiler's SHA-256 was
`ed6db089372b7ac4ad97eff89bb6f6e0825fbb6e5fea79d9181d75179850864e`.
The 0.5.0-draft.1 source SHA-256 was
`20a985790334aab3693c0bb4621f64a5f5d46652ca9601879f807b2cb82c83ac`.

- Supplying only core 0.3.0 reported unresolved fields in the new model.
- Supplying both exact core versions produced no diagnostics for either model.
- Supplying an import path absent from the index made **both** models
  report that they could not be checked, including the one with a valid import.
- With both supplied, a deliberately nonexistent `Ref` target in the new
  model was still reported. The advisory command returned zero, as designed.

`tests/test_ontology_advice_release.py` preserves this staged-index regression
when `ONTOLOGYC_BINARY_PATH` identifies a suitable compiler. It tests a means
to provide the imports; it does not implement automatic selection.

The local hook configuration is shared by worktrees. Hard-coding a second
path globally would leave older branches, whose indexes do not contain that
path, unable to check their packages. A durable fix should select matching
available inputs from the active index, identify unavailable or ambiguous
imports explicitly, and retain actual diagnostics. The implementation and
its review remain open. No local shared hook configuration was changed here.
