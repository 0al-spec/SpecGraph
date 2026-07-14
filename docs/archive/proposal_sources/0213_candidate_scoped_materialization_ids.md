# 0213 Candidate-Scoped Materialization IDs

## Status

Implemented bounded review-materialization correction.

## Summary

Candidate spec materialization previously derived every review YAML id and
filename from only the candidate node id. Different product candidates reuse
structural node ids such as `candidate-spec.product-boundary`, so promotion
reviews could produce the same `CANDIDATE-CANDIDATE-SPEC-*` paths and overwrite
or ambiguously review another product's files.

## Decision

Materialized review specs now include a deterministic candidate namespace:

- product candidates derive the namespace from the validated
  `product://<candidate-id>/...` source ref on the authoritative candidate
  graph;
- non-product review fixtures derive a non-reversible namespace from the
  SHA-256 digest of their source ref;
- missing source provenance and malformed product source refs block
  materialization;
- ids, filenames, `depends_on`, allowed paths, outputs, and promotion paths all
  use the same namespace;
- the materialization report publishes the namespace derivation and source-ref
  digest without exposing non-product source text.

The repaired graph preview may carry a local rerun source ref. It does not
replace the authoritative candidate graph provenance used for namespacing.

## Authority and Compatibility Boundary

This proposal changes review YAML ids and promotion paths, so existing approval
decisions for old generic paths must be rebuilt. It does not change canonical
candidate node ids, graph edge refs, canonical specs, ontology terms, or
workspace bindings. It does not create branches, commits, or pull requests.

## Acceptance Criteria

- Two product candidates with identical node ids produce disjoint review ids
  and filenames.
- Materialized dependencies refer to the scoped ids from the same candidate.
- Product scope is derived from candidate graph provenance, not output paths or
  run directories.
- Invalid or missing candidate provenance fails closed.
- Repaired materialization, promotion-gate, and active-candidate consumers
  continue to accept the generated scoped paths.
