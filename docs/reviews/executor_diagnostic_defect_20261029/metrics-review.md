# PR #828: diagnostic metric review

## Measured scope

The [initial report](https://github.com/0al-spec/SpecGraph/pull/828#issuecomment-6506530681)
compares base `1c586346751cb1fd6fb065f6902ef691d37c76e0` with head
`7cff1a2310486d62e17243ec25fa23be905074fe`. Both collections are complete,
non-provisional, without primary diagnostics. Counting rule is v9; collection
contract is `943b09cbbe201297fd4dd2818bb574be357e277e62f4532a0fc23ec7a7e11d74`.
The reports use the same scope manifest. Tests are outside application scope.

The [retained six-file artifact](https://github.com/0al-spec/SpecGraph/actions/runs/40941342416/artifacts/12927616309)
was downloaded and its provenance checked against the repository, PR, exact
base/head and collection run. Analyzer is
`4650728d33d79e75e1eaa2470ec26ec9b0338e5a`. The downloaded ZIP SHA-256 is
`1c3a34c6e188d9a2b27fa1b7fcbaf0f331ddb13b7e3296a5d0f410a86385897a`.
GitHub artifact access and retention limits still apply.

| Observation | Measured change | Interpretation |
| --- | --- | --- |
| S | 126 → 126 | No new counted Specification in the initial implementation. |
| U | 10,374 → 10,378 | Four additional uncovered syntactic opportunities. |
| CC sum / Cog sum | +9 / +15 | Entire deltas are the new `codex_json_error_diagnostics` function. |
| CC max / Cog max | 0 / 0 delta | Existing project maxima did not increase. |
| SLOC | +26 | New application parsing/projection code. |
| Clone pairs / duplicate lines / tokens | 0 / 0 / 0 delta | No measured duplication improvement or regression. |

The aggregate candidate count rises by four while covered candidates remain
24. Four added `if`/`elif` branches in the parser structurally explain this,
but the report does not provide individual U locations. `run_codex` and
`classify_executor_environment` retain their previous function complexity.

## Decision and correction

JSON decoding, exception handling, shape checks, field mapping and whitespace
normalization are adapter mechanics. They remain procedural. The initial claim
that all new logic was parsing mechanics was too broad: **admitting native
`error`/`turn.failed` as diagnostic evidence while excluding agent/tool content
is a policy about evidence origin**.

The correction extracts one Boolean Specification,
`EXECUTOR_DIAGNOSTIC_EVIDENCE_SPEC`, into
`tools/executor_diagnostic_evidence_spec.py`. Its immutable context contains the
adapter-supplied origin and event kind. The policy admits only the Codex native
event origin with `error` or `turn.failed`; it does not parse JSON, inspect text,
read files, mutate state or execute an effect. The adapter consumes that result
before projecting event fields. Tests cover permitted/denied origins and kinds,
the stable trace name, actual adapter invocation, malformed shapes, retained
true failures and excluded agent/tool decoys.

The benefit is an explicit, independently testable trust boundary, not four
classes to match four branches. A small lazy sibling loader preserves direct
CLI and file-based import behavior without relying on another test's sys.path.
That compatibility code is additional mechanical overhead, included in the
same measurement scope. Behavioral verification is in `verification.json`.

## Measurement boundary

These numbers describe the initial head only. Measurements for the corrected
head are pending; do not reuse them as validation of the new implementation.
Extraction can add module/function overhead and does not guarantee lower total
CC, Cog or U. Scope roles and the counting contract remain unchanged. Review
the complete adapter/policy/loader family when the next report arrives and
update the PR response for its exact revisions.

The reusable review steps are in CONTRIBUTING.md, "Responding to
SpecificationMetrics". Local verification does not close the graph defect or
establish merge readiness.
