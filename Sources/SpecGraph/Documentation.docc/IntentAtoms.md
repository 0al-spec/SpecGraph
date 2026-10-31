# Intent Atoms and SIB snapshots

SpecGraph's `specgraph-intent-atoms-v1` profile provides one explicit choice
for counting Intent Atoms in the SIB framework. It counts structured
acceptance criteria and explicitly declared `atoms.intents[]` while keeping
the broader SIB definition open to other implementations.

The `specgraph_intent_atoms_snapshot` artifact is read-only evidence for one
Git commit. Its profile digest, analyzer source digest, provenance, source
locations, completeness state, and diagnostics make the count reproducible. A zero-atom node means that the
supported fields contain no countable declaration; it does not prove that the
node has no intent. The count is sensitive to how authors split and combine
YAML entries.

The analyzer reads Git tree entries and blob contents directly, so archive
attributes cannot omit or rewrite tracked specifications. A missing or
non-directory specification root produces an incomplete snapshot. Profile
digests use canonical JSON, and atom text normalizes line endings before
counting and comparison.
Diffs match declared IDs or same-node normalized text and report changes in
atom source mode. Replay manifests pin the first-parent commit list and
summarize atom changes across that history window.

An atom is not evidence of human authorship, review, approval, or
verifiability. The profile does not define a SIB threshold or change canonical
specification authority. See the [repository contract](https://github.com/0al-spec/SpecGraph/blob/main/docs/intent_atoms.md)
for counting rules, the `snapshot`, `diff`, and `replay` commands, and the
optional versioned metric-pack source. Consumers use a snapshot only when its
completeness is `complete` and its commit SHA matches the measured revision.
Consumers accept the versioned snapshot only when it is complete, uses
`specs/nodes`, carries analyzer and profile digests, and matches the measured
commit SHA. The legacy `acceptance[]` binding stays available and is labeled as
a proxy.

GitHub Actions posts one informational Intent Atoms comment per pull request
after the existing `Python CI` workflow completes for a PR. Later CI runs update
that same comment. The report compares the PR's current base and head trees
using the analyzer from the trusted default branch. It resolves the PR from the
CI head SHA, fetches the target base and PR head as Git objects, and does not
consume CI artifacts or check out or execute PR-authored code while it has
permission to write comments. This also supports stacked PRs. An incomplete
comparison reports diagnostics and withholds atom counts. The comment is review
feedback, not a merge gate or the durable post-merge metric history.

## Declared Proposal Obligations

The PR report also counts explicit YAML declarations under `docs/proposals`
as a separate draft scope. A `<proposal-name>.intent.yaml` declaration carries
the proposal ID, `kind: proposal`, a descriptive status, `proposal_ref`, and
`atoms.intents[]` with stable IDs and statements. Proposal 0045 provides
the first eight agent-authored draft obligations. Its documentation-only
declaration change records individual `contract_only` dispositions and does
not attest implementation or canonical acceptance.

The unchanged v1 analyzer runs with `--spec-root docs/proposals`. Its result
is displayed separately from specification atoms and is never added to them.
Text changes with the same proposal/atom ID pair are reported as modifications.
Unannotated Markdown remains unassessed; completeness describes the declared
fields, not all intent present in the prose. The declarations do not establish
review, approval, implementation or canonical promotion.

The renderer's optional `--proposal-report` requires matching base/head
revisions, profile digest, analyzer version/digest and the proposal root.
Mismatched or incomplete proposal measurements withhold draft counts while
the specification result remains visible. The SIB snapshot adapter continues
to accept only `specs/nodes`, so draft counts cannot replace canonical N_spec.

Both scopes use tooling from the trusted default branch. The new hosted
section becomes available after the workflow lands there; verify it on a
later open PR. The detailed declaration and reporting contract is in
`docs/intent_atoms.md`.

## Specification Adoption and Code Metrics

SpecificationMetrics reports **S** (live or unknown Specification definitions
and factory sites), **U** (current control-flow opportunities outside those
definitions), and **S/U**. The ratio is not a percentage or a capped score.
Confirmed dead Specifications leave S; unresolved liveness stays in S and
makes the observation provisional. See the
[SpecificationMetrics counting contract](https://github.com/SoundBlaster/SpecificationMetrics/blob/main/docs/counting-contract.md).

SpecGraph records source roles in `.specificationmetrics.toml` and
`scopes/specificationmetrics.toml`. Application is the default role, `tests/`
is `test`, and the report renderer is `framework`. Unknown Specification
liveness remains counted because `closed_world = false`.

After successful `Python CI`, the PR workflow compares the current base and head
Git trees using SpecificationMetrics pinned to commit
`332348dc86ebd9cfc9d1db15c37afbae9c2546d0`. The trusted counter parses source
data and does not execute PR-authored code. One informational comment reports
S, U, S/U, dead and unknown Specifications, and supplementary Python SLOC,
Cyclomatic Complexity (CC), Cognitive Complexity (Cog), and clone deltas.
Supplementary tools are pinned to Radon 6.0.1, complexipy 8.0.1, and jscpd 5.0.11.
Failed tools or unknown liveness remain explicit diagnostics; the
comment does not gate merge readiness.

The pinned CLI also renders a section for changes in U. Added locations link
to the PR head and removed locations to the base, with one-based line and UTF-8
byte column. A commit link requires matching Git blob bytes. Repeated identical
conditions with a change in multiplicity appear as an ambiguous group. The
comment shows up to 20 locations within a 12 KB row budget. The full
`opportunity_changes` object is in `diff.json`.

The comment links to the actual collection run and its `specificationmetrics-pr-*`
artifact, retained for 30 days and downloadable with GitHub access. It contains
`before.json`, `after.json`, `diff.json`, `provenance.json`,
`collection-config.toml`, and `scope-manifest.toml`. Provenance records PR
base/head, collection run/attempt, upstream CI, analyzer commit, and checked-out
trusted tooling revision. Source snapshots, tools, and environment dumps are
excluded from upload.

Full JSON retains per-file/per-function complexity, clone locations,
Specification liveness entries, and parse/marker/scope diagnostics. The comment
summarizes counts and review-required flags; unavailable diagnostics are not
reported as clean. `S` includes live plus unknown Specifications, and unresolved
liveness makes the primary metric provisional.

Upload preserves available named files even if collection fails. Artifact
presence does not imply completeness: inspect report statuses and diagnostics.
A failed collection publishes no new success summary; check revision IDs in
any existing comment. Historical raw reports cannot be recovered when the old
workflow did not retain them.

Counting rule v9 recognizes statically resolved module-level Python subclasses
and class-base runtime uses. It recovers the native BDD family: on unchanged
SpecGraph `b86895c9`, S changes 100 to 106, U changes 10,093 to 10,073, and unknown
liveness changes 1 to 0. This is an analyzer correction, not a refactoring gain.
Preserve prior artifacts and start a new contract baseline; normal comparison
rejects different collection contracts. The upstream
[inheritance audit](https://github.com/SoundBlaster/SpecificationMetrics/blob/4650728d33d79e75e1eaa2470ec26ec9b0338e5a/docs/python-inheritance-counting-audit.md)
records the source snapshot, supported subset and regression coverage.

Counting rule v10 adds resolved Python `PredicateSpec[T]` factories. On the
same SpecGraph revision `4add3afe`, this analyzer change raises S from 127 to
130 with U at 10,676 under both rules. Collect both sides with the pinned v10
analyzer for each new PR comparison.

### Verify an analyzer rollout

The report workflow checks out the trusted default branch. A PR that changes
the analyzer pin can therefore still receive a report from the previous
analyzer before that PR merges. The first hosted verification must use a later
open PR after the new workflow has reached the default branch. Push-only CI and
reruns for merged PRs do not produce a new PR measurement.

For that verification, download the linked artifact and check all six named
files above. Bind `provenance.json` to the repository, PR base/head, upstream CI
run, collection run/attempt, trusted tooling revision and expected analyzer SHA.
Check counting rule v10 in both collection reports, matching collection contracts,
complete collection/supplementary statuses, and primary diagnostics. Verify that
the comment describes the same revisions and values as those JSON reports.

A documentation-only verification PR should leave application S, U and classic
metrics unchanged between its base and head. That proves collection consistency,
not business correctness. Compare counting-rule versions separately on the same snapshot and retain
the historical reports.

### Respond to the metric report

Each SpecificationMetrics report needs a substantive author response linked in
the PR conversation. Identify the reported base/head, counting contract and
collection status. Connect material deltas to the changed functions and the
whole decision family, separating parsing mechanics from domain policies.
Use the location section and full diff artifact for changed sites. For an
ambiguous group, cite its net change and inspect both revisions before
attributing the change to an occurrence.

Either defend the design with code evidence and explicit trade-offs, or identify
a real defect, repair it and cite the commit and behavioral verification. When
evidence is incomplete, state the gap and next check. A bare acknowledgement or
"informational only" does not answer the report. After a changed-head report,
update the response for those revisions; do not claim an unmeasured improvement
using an earlier report.

This is review practice, not a numerical merge gate. Do not create Specifications
to increase S, change source roles to hide complexity, or split files only to
reduce a local metric. A justified increase is acceptable; extracting a misplaced
policy can be useful without reducing total CC/U. See CONTRIBUTING.md,
"Responding to SpecificationMetrics", for the review steps.
