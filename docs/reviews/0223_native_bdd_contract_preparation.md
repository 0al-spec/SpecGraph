# RFC 0223: native BDD contract preparation

## Status and bounded scope

PR [#753](https://github.com/0al-spec/SpecGraph/pull/753) merged the proposal
at `0a08e38a23fbbe5ad7450c0d31ed48cec84a094e`. This follow-up prepares **one
review-only native declaration contract** and characterizes the existing 0047
consumer. It does not adopt a canonical spec, implement the shared strict loader,
activate a profile, migrate sources, run gameplay scenarios or admit evidence.

The proposed canonical parent is **SG-SPEC-0062**, the Canonical Record Semantics
Cluster. The concern is record-local scenario fields, validation and references,
without a new Scenario node kind. Proposal 0047 owns downstream implementation
handoff, 0006/0021 own validation architecture, and 0221 owns requirement identity.
Proposal numbers are not canonical spec IDs; SG-SPEC-0047 is not proposal 0047.

The [candidate](0223_native_bdd_supervisor_candidate.yaml) keeps the temporary
`DRAFT-SPEC-0223` identity outside `specs/nodes`. It has **five acceptance criteria
and thirteen future BDD cases**, with `review_pending`. A canonical ID is not
allocated or reserved by this document. `CONSTITUTION.md` requires explicit
human approval before proposed policy becomes authoritative.

## Supervisor preparation and curation

Following the temporary draft pattern used for RFC 0221, a seeded draft in an
isolated worktree received one targeted Supervisor pass:

```text
target: DRAFT-SPEC-0223
model: gpt-6-luna
execution profile: materialize (medium)
run: 20261002T170949Z-DRAFT-SPEC-0223-c1fbfbe7
executor exit: 0
completion: ok
outcome: done
gate: review_pending
proposed status: specified
final status: outlined
```

The only changed path in the run was the temporary draft. The raw candidate
contains nine BDD cases and a proposed maturity of 0.35. Its acceptance-evidence
entries describe structural coverage in the candidate; they are not executable
test evidence or implementation conformance.

The author curated the result by proposing the field policy, naming policy
objects, defining unknown-profile and invalid-count behavior, adding two future
BDD cases and specifying read-only observability. The tracked review copy's gate
is explicitly pending; the historical Supervisor gate was not resolved.

Independent GPT 6 Astra / Max audited head `13ed5d0` and reported one P2 and two
P3 findings, with no P1. The author follow-up adds timestamp compatibility tests,
original-type strict validation, explicit composition aggregation/skips, two
additional future cases and narrower diagnostic claims. These corrections are
separate from the original independent verdict; see the [audit record](0223_astra_native_contract_audit.md).

Input, raw result, curated result and exact byte hashes are retained in
[preparation evidence](0223_native_bdd_preparation_evidence.json). The raw result
and curated result are different evidence artifacts. The original Zeusus pilot
observation and its source hashes remain unchanged.

A read-only 0047 preview of the curated candidate resolves all thirteen local
scenario references, then reports `blocked` on `review_pending` and `outlined`.
It retains `evidence_status: not_evaluated` and denies code/canonical mutations.
This checks declaration structure and handoff boundaries, not scenario execution.

## Proposed contract for review

| Concern | Proposed native v1 rule |
| --- | --- |
| Representation | `specification.bdd_scenarios`; each item has `id`, optional `scenario`, and `steps`. |
| Field policy | Allow exactly `id`, `scenario`, `steps`; reject unknown fields. V1 has no extension field. |
| Values | Validate original decoded YAML types before legacy timestamp normalization. IDs, supplied titles, steps and references must be strings; date/datetime scalars are invalid. Retain meaningful strings exactly. |
| Steps | Nonempty ordered list; repetition is allowed. Do not infer executable grammar. |
| Presence | Distinguish `absent`, `explicit_empty`, `present`, `invalid`. Absence and explicit empty imply no coverage. |
| Alternate container | Recognized `scenarios`, including `[]`, is unsupported; two recognized containers are ambiguous. Neither wins. |
| YAML keys | Reject duplicate keys before ordinary map construction. |
| Identity and references | Exact IDs are unique within the owning node. Obligations resolve only in that node, without parent/sibling fallback. |
| Invalid result | Return typed findings; successful extracted count is unavailable, not a misleading zero. Diagnostic counts remain separate. |
| Profile | Explicit supported strict selection; unknown version fails without silent compatibility fallback. |
| Authority | Valid declarations do not grant readiness, execution, implementation authorization or evidence admission. |

The allowlist is an **author proposal for this candidate**, not an activated
schema. A future extension profile must define typed namespaced fields before
accepting them. Existing 0047 compatibility preserves its current behavior until
a separately reviewed consumer integration.

The legacy consumer recursively applies `normalize_yaml_scalars` before BDD
validation: YAML date/datetime becomes an ISO string in IDs, titles, steps and
references. A timestamp ID can collide with its quoted ISO string. Strict v1
checks the original decoded types first; quoted strings stay strings. Generic
metadata normalization must not silently make a strict declaration valid.

Normalized scenario digests remain outside this slice. Exact source-byte
SHA-256 is available for provenance, but normalized pins require the separately
reviewed canonical byte contract from RFC 0223. A shared declaration loader must
not manufacture a private serializer or declare digest equivalence.

## SpecificationCore materialization plan

These are proposed object bindings, not implemented classes or canonical subject
identities. Each policy belongs in its own module, with immutable typed context
and a composed decision path. File/YAML handling stays at boundaries.

| Proposed object | Proposed rule reference |
| --- | --- |
| `BDDContainerPresenceSpec` | `SG-RFC-0223.native.container-presence` |
| `BDDScenarioFieldsSpec` | `SG-RFC-0223.native.scenario-fields` |
| `BDDScenarioValuesSpec` | `SG-RFC-0223.native.scenario-values` |
| `BDDScenarioIDsSpec` | `SG-RFC-0223.native.node-local-ids` |
| `BDDScenarioReferencesSpec` | `SG-RFC-0223.native.node-local-references` |
| `BDDProfileSelectionSpec` | `SG-RFC-0223.native.profile-selection` |

After adoption, bind the objects to the canonical subjects explicitly. A named
RFC reference declares intended obligations; it does not prove conformance or
replace durable requirement identity. FeaturePassport retains generic bindings
and does not acquire a dependency on SpecGraph.

The candidate's observability contract links two future events to its own BDD
IDs: declaration classification and policy attribution. Traces exclude step
text, titles and absolute paths. They cannot write source, change decisions,
activate a profile or supply trusted admission receipts.

Composition accumulates findings from eligible checks instead of globally
stopping at the first error. Prerequisite failures produce explicit `skipped`
reasons: invalid YAML/profile/container prevents dependent checks; invalid or
duplicate IDs prevent reference resolution. Unknown fields, invalid steps or
titles do not suppress otherwise eligible ID checks. Empty/absent declarations
still validate supplied references against an empty inventory. Findings follow
policy order and source indices, with explicit field order in each policy;
steps and findings are not deduplicated.

For `{id: A, steps: [], extra: true}`, the future composition reports
`unsupported_field` for `extra`, then `invalid_value` for `steps`; Fields and
Values are unsatisfied and eligible ID checks run. Final presence is invalid
and successful extracted count is unavailable. This is a future case, not an
executed SpecificationCore implementation.

## Current compatibility evidence

`make test-native-bdd-characterization` runs the new characterization file and
existing implementation-contract tests: **75 passed, 0 failed**. The new file
adds 54 cases; the existing suite supplies 21. These tests call the current
consumer and preserve its behavior; they are not Red/Green evidence for the
future strict profile.

| Input | Observed 0047 behavior | Proposed strict behavior |
| --- | --- | --- |
| Native absent or `[]` | No required tests; missing observability remains a blocker. | Typed absent/explicit empty; readiness remains separate. |
| Only alternate `scenarios` | Preserved in returned specification, but not consumed. | Unsupported container finding. |
| Native plus alternate | Only native IDs can satisfy obligations. | Ambiguous container finding, even with empty lists. |
| Malformed supplied title | Ignored by validation and retained in output. | Invalid value finding. |
| Bad native container/ID/steps | Rejected by the consumer. | Typed invalid finding. |
| Repeated steps or meaningful whitespace | Retained exactly; IDs use exact equality. | Preserve the same values and ordering. |
| Sibling/parent/other-workspace reference | Cannot satisfy a local obligation. | Preserve the local boundary with typed findings. |
| Same local ID in another node | No workspace inventory is scanned. | Explicit inventory scope is separate; no full-workspace uniqueness claim. |
| YAML date/datetime in BDD fields/references | Converted to ISO strings before validation; IDs may collide with matching strings. | Validate original types; timestamp scalars are invalid, quoted strings remain exact. |

The [bounded corpus audit](0223_native_bdd_corpus_audit.json) pins all inspected
source bytes. It covers 69 canonical SpecGraph files (no scenario containers)
and six normalized historical Zeusus files (100 scenarios). Every inspected
Zeusus scenario uses exactly `id`, `scenario`, `steps`; all supplied titles are
nonempty strings. This supports the candidate allowlist in the pilot, without
proving compatibility across every workspace or producer.

## Runtime diagnostic observation

The run recorded `state_runtime_failure` despite successful executor completion
and a structurally valid candidate. The pinned [excerpt](0223_executor_diagnostic_excerpt.txt)
contains backticked diagnostics from `CONTRIBUTING.md`; that excerpt alone
reproducibly triggers the classifier. This establishes a false-positive trigger,
not the absence of every real diagnostic in the historical run.

The historical assessment that its matches were quoted text is an author
observation. The packet does not preserve a full pinned transcript or complete
match inventory. Since classifier evidence is truncated to three lines, repeated
quoted examples can hide a subsequent genuine error in that projection. The
author reproduced this ambiguity as well; historical completeness remains
unproved and the gate stays pending.

PR #746 removed the earlier match on ordinary migration vocabulary, but the
current classifier still searches the entire transcript for literal diagnostic
fragments. Printed documentation can therefore produce a false positive.
This contract preparation records a **separate runtime follow-up**: distinguish
executor diagnostic records from quoted tool output and add classifier plus
run-artifact regressions. It does not change that classifier or clear the gate.

## Next bounded steps

1. Review this native candidate, its proposed parent, field policy and policy
   materialization map; approve canonical adoption explicitly if acceptable.
2. Allocate/materialize one canonical child through the existing graph workflow.
3. Implement the shared loader through TDD using named SpecificationCore objects;
   preserve the characterized compatibility façade and exercise strict findings.
4. Integrate consumers and profile selection in bounded reviewed slices. Source
   migration, Gherkin exchange and normalized digest binding follow separately.
