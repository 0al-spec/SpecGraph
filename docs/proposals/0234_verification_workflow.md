# Composable verification workflow

RFC: SG-RFC-0234
Version: 0.1.0

## Status and intent

Draft proposal; planning contract only. Runtime realization is
`deferred_until_canonicalized`. The operator requested this proposal, not
activation of a new canonical transition or admission policy.

The intended experience is one operation: **verify this specification**.
The system composes source selection, test execution, evidence collection and
reporting; the agent does not reconstruct a verification ritual each time.
Missing inputs remain visible gaps. Draft authoring stays available.

[Attributed source](../archive/proposal_sources/0234_verification_workflow.md),
[draft obligations](0234_verification_workflow.intent.yaml) and
[graph return path](../reviews/0234_verification_workflow/README.md) preserve the
request. The planning target is SG-SPEC-0009, the existing single-run steering
contract; registration does not claim it already specifies this workflow.

```yaml
canonical_mutations_allowed: false
runtime_profile_activation_allowed: false
evidence_admission_allowed: false
```

## Existing behavior and ownership

| Existing contract | Reuse | Boundary |
| --- | --- | --- |
| [0224](0224_compositional_test_context_and_evidence_binding.md) | Producer context, criterion bindings and attempt lineage | Draft contract, not a general workflow implementation |
| [0226 C2c](0226_traceability_evidence_providers_and_svc.md) | EvidenceRegistry, retained Cucumber provider, complete criterion inventory, JSON/HTML | Collection does not execute tests or attest a new run |
| [0225](0225_tests_verified_evidence_admission_plan.md) | Future admission and trust boundary | No signed receipt or `tests_verified` transition here |
| SG-SPEC-0009 / native runtime | Explicit target and installed-tool/workspace separation | Existing refinement executor is not a typed test operation |

Observed source baseline: SpecGraph `002eb0691b39ea2ccdcc50d0c5c31fc84022e3bf`.
`tools/criterion_observation_report.py` returns zero when it builds a diagnostic
report, including failing observations. This is its existing contract, not a
successful verification verdict. `build_supervisor_evidence_packet` consumes a
different run format; its absence-of-validation-errors rule must not be applied
to an arbitrary criterion report. These are integration constraints, not claims
that either existing consumer has already misclassified this new workflow.

The local ExamCalc pilot executed commit
`775e0100006d98ed9ad6054e70954c54df934b39`; its evidence commit is `9e0cd21`.
Its `scripts/fresh_criterion_report.py` executes a committed snapshot and then
the installed provider. Two retained runs each report six scenarios, 69 steps
and three checked/passed criteria. A changed-measurement control fails despite
a PASSED producer step. These are prior local observations, not executions of
the workflow proposed here. Private/local source journals are not copied into
this public proposal.

ExamCalc continues to own its test command, scenario selectors, expected
measurements and producer-specific binding adapter. SpecGraph owns run
composition, source/output linkage, lifecycle and the verification verdict.
The universal completion rule uses the pinned inventory, never a hardcoded
criterion count such as three.

## First profile and external interface

First scope: one specification and a fixed versioned profile
`verify-criteria/v1`. Proposed CLI, **not implemented**:

```sh
specgraph-runtime --workspace /path/to/project verify-criteria SPEC-ID --revision COMMIT
```

The workspace selects the reviewed producer, binding template, provider and
tool pins. Local configuration supplies storage/tool locations once; callers
do not manually invent output folders or paste hashes on every invocation.
The command resolves COMMIT to a full Git revision before execution and shows
the selected scope. A run evaluates that exact snapshot; a later HEAD change
does not make it evidence for the newer snapshot.

Native CLI and an explicit Supervisor mode call the same operation. This is
an opt-in requested check, not an automatic prerequisite for every graph edit.
Invocation grants the selected producer's declared local test effects only;
it does not authorize canonical writes, publication or deployment.

```text
VerificationRequest
  -> pin: PinnedVerificationInputs
  -> execute: TestExecutionRecord + journal references
  -> collect: CriterionEvidence + TraceSnapshot
  -> report: VerificationReport + JSON/HTML
```

The definition declares typed input/output links and mandatory stages. A small
explicit operation registry pins operation ID, version, adapter identity and
allowed effects. Unknown operations, duplicate IDs, incompatible ports and
disconnected required stages are rejected before test execution. Definitions
cannot dynamically import code or turn conversational text into shell commands.
The reviewed execution adapter uses an argument vector, explicit cwd, output
root and execution limits; those choices are included in the selected profile.

The collector's input must originate from the mandatory `execute` output.
A test node in an unused branch, an optional execute stage or a direct edge
from a retained filename to a successful result does not satisfy the profile.
V1 accepts only this fixed topology; it need not solve arbitrary DAG dominance.
Arbitrary workflows, branches, retries and resume are outside this first slice.

## Request, execution and artifact linkage

The immutable request pins repository/workspace identity, declaration and
execution revisions, spec bytes and complete criterion inventory, passport,
binding template, profile/registry, producer/provider and validator identities.
Declaration and execution revisions remain separate. Their compatibility is
checked by the selected profile; equal labels do not establish compatibility.

Each invocation creates a unique workflow run ID and new run-local directory.
The runner records each mandatory stage and the input references it consumed.
The execution adapter records source snapshot identity, command/profile,
start/completion, process outcome and produced paths/hashes. Collection accepts
outputs registered by that execution stage in this run, not arbitrary paths or
an externally supplied claim of successful execution. Matching content hashes
alone do not confer ownership by the current run.

The producer binding adapter selects new run/case/step IDs using committed
scenario selectors. Expected measurements are fixed before execution and must
not be inferred from observed values. Selection drift, such as a changed feature
invalidating positional selectors, remains an explicit review gap.

The final record is written atomically after required stages finish. A missing
terminal record is incomplete even if report files exist. On failure, collect
available diagnostics without falling back to a previous journal. An aborted,
timed-out, skipped or nonzero producer cannot be compensated by a green
collector result. An uncatchable termination leaves an incomplete run rather
than synthesizing completion. Unexecuted dependent stages remain `not_run`.

Re-execution creates a new run. Reading a retained run is separately labelled
replay and cannot fulfill the fresh-execution obligation. Changes to pinned
criteria, snapshot, template, profile or tools require a new verification;
historical results remain addressable. Inputs used by the run are checked for
mutation before finalization. V1 has no late-event reopening protocol; conflicting
later observations require an explicit new evaluation and cannot silently
rewrite a completed result.

## Result semantics

| Field | Meaning |
| --- | --- |
| `workflow_outcome` | `completed`, `rejected`, `failed`, `aborted` or `incomplete`: execution lifecycle |
| `verification_outcome` | `passed`, `failed`, `incomplete` or `not_applicable`: verification result |
| criterion `binding_integrity` / `observed_outcome` | Existing C2c values, preserved without reinterpretation |
| `admission` / `receipt` | `not_evaluated` / `null` |

A fully collected negative test can have workflow `completed` and verification
`failed`; process/infrastructure failure is reflected in lifecycle as well.
`passed` requires successful fresh execution, every mandatory stage completed,
an intact current-run output chain, complete nonempty inventory, no unresolved
bindings/conflicts and every required criterion checked/passed. Empty inventory
is `not_applicable`, not vacuous success. Missing information is `incomplete`.
Gaps, failure and inapplicability stay visible in the complete criterion report.

Proposed CLI exit contract: 0 only for verification `passed`; 1 for a finalized
non-passing/incomplete diagnostic result; 2 for rejected invocation/profile or
an inability to produce a valid result. Preserve normal process signal behavior
on unhandled termination; any nonzero exit or missing completion is non-success.
Existing diagnostic collector CLI semantics remain unchanged.

Evidence remains `local_test` with `producer_declared` execution provenance.
The run record is local bookkeeping, not a FeaturePassport receipt authority.
This prevents bypass through the conforming workflow path; it does not prevent
a hostile operator from rewriting the runtime, producer and files on the host.
Independent attestation and trusted admission belong to later work under 0225.

## Module and representation boundaries

Keep workflow behavior behind thin CLI/Supervisor facades, separate from the
legacy refinement loop. Roots, clock, storage, source snapshot and execution
adapter are explicit inputs. Immutable typed facts and named SpecificationCore
policies express profile validity, run/input compatibility and completion.
Parsing, Git, subprocesses and filesystem operations remain edge adapters.
The existing EvidenceRegistry/provider owns criterion interpretation.

The first definition can be a small JSON/YAML document validated against this
fixed profile, with reviewed in-process operations. Hypercode is a future
authored representation of the same operation graph; equivalence must be
checked before substituting it. No existing Hypercode compiler support for
executing this workflow is claimed. Terminology bindings to the selected
ontology should be reviewed during implementation; this proposal creates no
new ontology package or canonical type by naming its conceptual records.

## Acceptance and implementation slices

| Control | Required observation |
| --- | --- |
| Producer deleted, optional or disconnected; direct retained-file bypass | Preflight rejection before any test command starts |
| Complete green report from a previous run, even at the same commit | Current-run ownership mismatch; verification is not passed |
| Execution record names another commit, even with identical feature/spec | Source compatibility failure; verification is not passed |
| Missing criterion, attachment, step completion or run completion | Full inventory retained with gaps; verification is not passed |
| Aborted, nonzero or unterminated producer with a good-looking journal | Explicit failed/aborted/incomplete result; no inherited success |
| Diagnostic collector exits zero with failing criteria | Verification remains non-passing |
| Empty inventory or changed inputs | Not applicable or invalidated selection; never passed |
| One valid invocation | Producer invoked exactly once; new output chain; all required criteria checked/passed |
| Installed runtime in an external workspace | Same contract and results as source checkout; project roots preserved |

These cases plan future verification; none has been executed by this proposal.

1. Review fixed-profile contracts and source-attributed obligations. Add a
   narrow workflow core with preflight and lifecycle fixtures, preserving C2c.
2. Connect native CLI and explicit Supervisor entrypoints to that operation;
   exercise a fixture producer with the bypass cases above and installed smoke.
3. Move reusable orchestration out of the ExamCalc pilot, preserving its
   selectors/expectations. Run two independent invocations and show their
   distinct identities and identical expected outcomes in Supervisor.

Resume through `proposal::0234-verification-workflow`. The next action is
contract review, followed by the first bounded implementation PR. This proposal
does not alter SG-SPEC-0009, other canonical nodes, thresholds or admission.
