# Shared priority of ontology check outcomes

The operator requested a behavior-preserving SpecificationCore refactor of
the outcome selection shared by context capture and the target Supervisor
check. This is an implementation slice of proposal 0232.

## Decision table

| Invalid check present | Unavailable check present | Context capture | Target check |
| --- | --- | --- | --- |
| Yes | Yes | invalid | invalid |
| Yes | No | invalid | invalid |
| No | Yes | unavailable | unavailable |
| No | No | verified | checked |

The aggregate decision operates on existing immutable `ContextFacts`.
Its fallback means that neither failure predicate matched. Existing adapters
still prepare the required checks, including incomplete-capture findings and
normalization of unexpected component outcomes to unavailable. Empty checks
and unrecognized raw labels keep their existing aggregate behavior.

## Implementation

`project_ontology_context/outcome_spec.py` composes the existing
`INVALID_SPEC` and `UNAVAILABLE_SPEC` in one `FirstMatch`.
The caller supplies its success label explicitly. Both production callers
consume `context_check_outcome`; the Supervisor's `_outcome` façade remains.
The existing predicate modules retain their names and definitions.

An optional `TraceRecorder` records rule evaluation and skipped branches.
Producer source identity includes the shared decision module and its two
predicate dependencies, so changes to these rules affect report freshness.

## Verification

The original context, Supervisor and CLI focused tests passed before the
refactor. The additional decision-table test checks both success labels,
overlapping failures, permutations, repeated findings and the existing empty
and unknown-label cases. Trace tests check all branches and short-circuiting.
The existing production tests retain context identity, diagnostics, CLI
behavior and invalid-over-unavailable precedence scenarios.

The original focused suite passed 97 tests. The expanded context, Supervisor,
CLI, composition and freshness suite passed 198 tests after the change.
Its 26 real-compiler integration cases were skipped because
`ONTOLOGYC_BINARY_PATH` was unset.

The implementation centralizes the priority order in one declaration.
Whole-family complexity and duplication are assessed by the PR's existing
SpecificationMetrics collection.
