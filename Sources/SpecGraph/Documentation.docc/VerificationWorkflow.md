# Verification workflow proposal

SG-RFC-0234 proposes `verify-criteria/v1`: pin criteria and source, execute
tests, collect observations through the existing EvidenceProvider, and show
the outcome in Supervisor. A native command and Supervisor mode use the same
operation. Neither entrypoint exists for this profile yet.

Status: `deferred_until_canonicalized`. The graph return path is
`proposal::0234-verification-workflow`, with SG-SPEC-0009 as the planning
target. Registration is not canonical adoption or runtime activation.

The fixed profile rejects missing or disconnected mandatory execution.
Collection consumes the current run's execution outputs. Successful report
generation alone does not establish verification success. Full criterion
inventory, expected measurements, source revisions and tool pins remain
explicit. Retained replay cannot stand in for a new execution.

Failed or incomplete runs preserve diagnostics. Local paths and tool locations
are configured once; the runner allocates isolated outputs automatically.
The first slice has no general DAG engine, retry/resume or Hypercode executor.
Hypercode can later represent the same checked operation graph.

The design reuses proposals 0224 and 0226; proposal 0225 owns the separate
admission boundary. Results remain `producer_declared`, `admission:
not_evaluated`, `receipt: null`, without a `tests_verified` transition.
Local run records do not attest a host whose producer/runtime can be rewritten.

The local ExamCalc pilot exercised the execution adapter with Cucumber and
native FeaturePassport validation. The two fresh runs verified all three
criteria. A process that copied the first journal exited zero and was rejected
before collection. Testing the workflow through an installed native command
remains a follow-up.

## Consistency core available

`tools/verification_workflow/` now provides immutable request and stage records
with separate SpecificationCore policies for topology, pinned scope, linkage,
collection consistency, lifecycle and verdict. The scope carries FeaturePassport
identity, feature and criterion/contract/binding references, file hash and
schema/validator pins. C2c continues to interpret criterion observations.

The 65 focused pure-core tests cover missing execution, foreign-run records,
revision/passport drift, incomplete inventory and conflicting nested step facts.
Independent review reproduced two false-success cases involving individual
versus aggregate statuses and lost observation conflicts/retry state; both are
fixed with regression tests and confirmed by re-review. A valid observation
remains `completed/passed`, and a consistent negative test `completed/failed`.

The execution adapter creates a separate run directory, snapshots the pinned
Git commit and launches the test producer in a POSIX process group. The
producer emits a challenge from the current invocation inside each selected
test case. The adapter checks this marker before handing the original journal
to C2c. It writes the terminal record atomically after integrity checks.
The installed CLI and Supervisor mode remain pending.

Collection checks are partitioned into selection identity, journal provenance,
criterion binding/projection and observation consistency. Two immutable contexts
carry facts between those named policies. The public collection interface and
C2c outcome ownership remain unchanged. Independent review and the unchanged
65-test core suite confirm the refactor's bounded behavior; aggregate metric
changes require a fresh report and are not inferred from smaller functions.

- `docs/proposals/0234_verification_workflow.md`
- `docs/proposals/0234_verification_workflow.intent.yaml`
- `docs/archive/proposal_sources/0234_verification_workflow.md`
- `docs/reviews/0234_verification_workflow/README.md`
- `docs/reviews/0234_verification_workflow/execution-replay-defect.json`
