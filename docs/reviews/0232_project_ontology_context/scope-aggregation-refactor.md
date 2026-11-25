# Shared aggregation of requested ontology scopes

This behavior-preserving implementation slice of proposal 0232 centralizes the
outcome selection used by `build_context_reports.finish` and the schema-2
saved-report `_shape` check. Schema-3 meta freshness continues to reuse the
schema-2 domain check through its existing projection.

## Decision table

| Prepared scope facts | Aggregate outcome |
| --- | --- |
| Any requested outcome is invalid | invalid |
| A nonempty request has exactly one analyzed outcome for every scope | analyzed |
| No requested scope, missing result, or another incomplete result | unavailable |

The producer and saved-report consumer previously used different expressions
of this rule. They agree for validated saved-report inputs: requested scopes
cannot claim `not_requested`, unknown statuses are rejected, and each requested
scope has one assessment. Those adapter guards remain before aggregation.
The policy itself operates on immutable `ScopeFacts`, not report dictionaries.

`project_ontology_scope_aggregation_spec.py` composes the new invalidity
Specification and the existing `REQUESTED_SCOPES_ANALYZED_SPEC` in `FirstMatch`.
Each Specification remains in its own module. The fallback is explicitly
`unavailable`, including empty requests. This differs from context-capture
failure precedence, so the two decisions are not merged into a generic policy.

The producer retains diagnostics and completed findings for each scope. The
consumer still compares the claimed aggregate against the computed result and
preserves its exact inconsistency diagnostic. No schemas, CLI behavior,
semantic approval or supported metamodel capabilities change. Producer source
identity includes the two new policy modules so later rule edits affect freshness.

## Verification and limits

Before extraction, the existing scope/freshness/Supervisor suite passed 106
tests. Additional characterization tests passed on the original implementation:
79 scope and saved-report tests cover both-scope combinations, mixed failures,
empty requests and all three claimed aggregate labels. Literal expected tables
are independent of the shared Specification. Metamodel outcomes in the
producer aggregation matrix are controlled test doubles, not compiler evidence.

Policy tests cover completion cardinality, permutations, unknown raw statuses
and named selected/skipped trace branches. Existing integration tests retain
the structural rejection of unsupported schema-2 metamodel success, scope
identity mismatches, document capture and authority boundaries.
After extraction, 212 scope, freshness, Supervisor, joint-report and metamodel
tests passed; another 28 report-consumer and metamodel-integration tests passed.
Python quality, DocC sync, proposal tracking and materialization packet integrity
checks also passed. These focused tests do not establish a new real-compiler
verification or a hosted deployment.

Evaluate complexity across the producer, consumer and both new modules, using
the PR's existing SpecificationMetrics collection. This extraction centralizes
two policy expressions; it does not by itself establish a reduction in detected
clone pairs or future defects.
