# Local scenario pilot

The operator chose lightweight, optional formalization alongside specifications;
[source excerpts](source.md) retain that direction separately from the earlier
norm-package discussion. This slice continues
`proposal::0233-mechanical-specification-authoring` and the
[executed baseline](../baseline/README.md).

The editable [SG72-MIXED model](../../../../specs/models/SG-SPEC-0072/README.md)
combines two check results. It reuses project-local `specgraph-core` and a small
local draft extension, generating TypeScript through ontologyc on demand. It
neither expands the global selected ontology nor activates an authoring gate.

## What this experiment must demonstrate

1. Compile the draft and instantiate actual generated SDK types.
2. Link the readable scenario and exact spec clauses to the model.
3. Check the expected invalid outcome and preservation of both diagnostics
   against one bounded execution of the current implementation.
4. Reject intentional construction and relationship mistakes, and expose
   deleted mappings instead of silently reducing the modelled scope.

Structural compilation, scenario checks, execution observations and completeness
are separate results. The four acceptance rows remain visible; only a fragment
of the third is modelled. The earlier baseline and original approval/registration
records are not rewritten by this run.

## Executed result — 2026-10-30

The [curated observation](observation.json) records real ontologyc SDK generation,
TypeScript 6.0.3 compilation, the local instance checks and an execution of
`capture_project_context`. All four layers passed for the authored model. The
implementation returned `invalid`, retaining the selection-invalid and
compiler-unavailable diagnostics. Other diagnostics remain in the observation;
the scenario does not claim there were only two checks overall.

| Intentional change in a disposable copy | Observed boundary |
| --- | --- |
| Remove a required SDK field or use an unknown type/relation | TypeScript diagnostic |
| Connect a check edge to a Requirement instead | Model domain/range diagnostic |
| Remove the spec-to-requirement edge, a check or its diagnostic | Model diagnostic |
| Declare a different overall result | Source/model expectation mismatch |
| Keep a well-formed but incorrect diagnostic expectation | Execution comparison mismatch |
| Remove a source clause/coverage row, change the source ID or use a stale hash | Source-binding diagnostic |
| Reuse a nonempty output directory | Refusal; previous report preserved |

The focused test run passed **43 tests**, comprising 9 source-mapping cases,
13 real-tool integration cases, and 21 existing baseline/context regressions.
No integration cases were skipped locally. Ordinary Python CI runs the pure
cases and skips the real-tool cases unless both tool environment variables are
configured; the local result does not claim hosted toolchain execution.

Independent review found and fixed a source-node ID mismatch that could survive
an updated source hash. An initial negative test also caught literal-type
narrowing in the consumer that hid the intended missing-link diagnostic behind
a TypeScript error. Both now have regressions. Repository Python quality,
DocC synchronization and proposal tracking checks passed.

Input and generated-output digests bind this observation to the tested bytes.
The receipt records the compiler binary hash with `provenance: not_verified`;
it does not attest a binary-to-source build or approve the model's interpretation.
Source clauses were selected and reviewed explicitly. The compiler cannot prove
that arbitrary prose or unmodelled criteria have been represented faithfully.

## Tooling friction to retain

The authored instance is 34 TypeScript lines; its local vocabulary adds 50 YAML
lines. The one-off runner and consumer add 482 Python/TypeScript lines, excluding
tests, the source map and documentation. These physical line counts describe
the prototype's footprint, not quality. This experiment establishes feasibility,
not low adoption cost: copying that adapter per specification would defeat the
operator's lightweight-authoring goal. A second case should establish reusable
parts before this becomes an authoring convention or distributable tool.

The compiler currently requires package policies and a state-machine section
even for a small local model. Package metadata must not be mistaken for an
executed lifecycle or a new project review policy. Generated primitive string
fields do not constrain outcomes to the three domain values, and generated
relations do not validate instance edges by themselves. The bounded consumer
supplies the relevant checks. This is useful feedback for improving authoring
ergonomics, not a reason to formalize every surrounding concept.

The future SpecSpace view can render the same model and diagnostics; a viewer
or editor is not implemented in this slice.

## Return task

Resume through `proposal::0233-mechanical-specification-authoring`. Try a second
bounded case with different relations before generalizing this consumer; measure
how much authoring and adapter code it reuses. Preserve the compiler's mandatory
policy/state-machine boilerplate and missing generic instance checks as concrete
Ontology ergonomics feedback. Global enforcement remains outside this pilot.
