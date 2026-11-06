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

The prior ExamCalc pilot demonstrates the underlying snapshot/test/provider
chain. The new workflow's bypass and installed-runtime tests are planned,
not executed by this documentation change.

- `docs/proposals/0234_verification_workflow.md`
- `docs/proposals/0234_verification_workflow.intent.yaml`
- `docs/archive/proposal_sources/0234_verification_workflow.md`
- `docs/reviews/0234_verification_workflow/README.md`
