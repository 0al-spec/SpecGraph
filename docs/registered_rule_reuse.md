# Registered Specification rule reuse

The Python CI `registered-rule-reuse` job detects new procedural copies of the
reviewed `subject_publication.workspace_allocation` rule with
`check-rule-reuse` from SpecificationMetrics. This is separate from the
informational publication policy classification and the primary S/U counters.

## Catalog authority

`tools/rule_reuse_catalog.toml` registers the canonical
`WORKSPACE_ALLOCATION_SPEC`, its declaration digest, the `subject_publication`
bounded context, the `tools/` source scope and the historical six-condition
workspace binding predicate at PR #762's exact commit. Tests and examples outside
`tools/` are not analyzed. A reviewed template is a narrow reuse contract;
source field names alone do not establish semantic equivalence.

CI pins analyzer commit `797dc648e62a14a208cf058af32a996de44cdc91` and builds it
with `cargo build --locked`. The adapter `tools/check_rule_reuse.sh` extracts the
catalog from the PR **base** revision. Before comparison it independently
validates the effective head catalog against that same effective head commit
(`head → head`), including TOML schema, templates and canonical declaration
digests. An invalid proposed catalog cannot land and poison subsequent PRs.
The base catalog still governs the current comparison. A deleted effective head
catalog fails. Catalog or canonical rule changes
require an explicit reviewed migration; a stale canonical digest fails closed
under the base catalog, even when the head updates its own digest.

For first-time activation, the base has no catalog. The job validates and reports
using the head catalog, labels its mode **bootstrap**, and does not enforce new
copy counts. After the catalog lands in the base, mode **enforcing** passes
`--strict`. Bootstrap still rejects incomplete/missing evidence and reports for other base/head revisions. An artifact's
presence alone does not establish readiness.

## Merge snapshot selection

CI checks out `${{ github.sha }}`, the GitHub PR merge commit, and passes it
through `tools/check_rule_reuse_merge.sh`. Its first parent must equal the event
base SHA and its second parent must equal the event PR head SHA. Mismatches fail
before analysis. The analyzer compares base to this **merge result**; it does not
interpret changes already made on the base as deletions by an older PR branch.
A genuine catalog deletion in the merge result still fails.

`comparison.json` records base, original PR head and merge revisions. The report's
`head_revision` is the effective merge revision. These identities are distinct;
its report must match the exact selected base/merge revisions. For a local CI
reproduction, create a merge commit with base and PR head in that order and run
`tools/check_rule_reuse_merge.sh ROOT ANALYZER BASE PR_HEAD MERGE OUTPUT_DIRECTORY`.
The direct snapshot adapter remains available for intentional local comparisons.

## What blocks

In enforcing mode, `new_reimplementations > 0`, incomplete parsing, invalid
catalogs, changed canonical digests or unreadable Git snapshots fail the job.
New near matches are review-only. A whole-file historical total cannot hide a new
copy in another file. Existing copies are a baseline, not a mandate to refactor
all code in the PR. Git-detected renames and local registered-binder renaming do
not create new copies.

Python v1 visits predicates in `if`, `elif`, `while`, `assert`, `require` first
arguments and lambda bodies. It preserves constants, calls and operator order;
reordered or compound conditions are near matches. Arbitrary boolean assignments,
comprehensions, match guards and generated code are not covered. `complete`
means the declared scope parsed successfully, not a project-wide semantic proof.
The canonical declaration itself is excluded. Direct/aliased explicit imports
and direct `.is_satisfied_by(...)` calls are static reuse observations; this
adapter does not prove runtime identity or resolve module aliases/re-exports.

## Reports and history

The run-local `registered-rule-reuse` artifact contains `report.json`, selected
catalog, head catalog, `head-catalog-validation.json`, `comparison.json` in CI,
`mode.txt`, `summary.md` when successful and
`history.sqlite`. The SQLite `rule_reuse_snapshots` table is separate from S/U
history; each snapshot records revisions, catalog digest and analyzer version.
Artifacts are retained per Actions retention, not a permanent cross-run database.
Download retained SQLite files for local history; long-term retention is a
separate operational choice.

```bash
bash tools/check_rule_reuse.sh /path/to/SpecGraph \
  /path/to/specification-metrics BASE_SHA HEAD_SHA /tmp/unique-rule-reuse-run
specification-metrics rule-reuse-history --store /tmp/unique-rule-reuse-run/history.sqlite
```

The job summary reports changed-file copies, new exact/near matches and static
spec uses. Existing publication diagnostics remain `merge_gate_enabled: false`.
This new job supplies a separate gate; it does not replace their counts or add
LLM authority. Whether it is a branch-protection required check is controlled by
GitHub settings, independently of workflow failure.

## Evidence and optional semantic review

The real historical pilot `9b285a2e018331460c1a6bee46a697b24a26d3fb` →
`5ddd1c0b62241681c2ced4073a3402a68c10e385` reports procedural copies **1 → 0**, one
static spec use, four changed scoped files and no new exact or near matches.
This verifies the selected extraction, not every existing policy in SpecGraph.

Near-match JSON includes bounded `semantic_review_requests` containing the
candidate and registered declaration. Local optional Jev classification uses
`same_rule / different_rule / needs_review`, with model/prompt/input provenance.
It requires explicit hosted-source opt-in. CI makes no Jev calls and needs no
API key. A semantic suggestion never changes the blocking count.


## Enforcing CI smoke

Before analyzing the PR, `tools/rule_reuse_ci_smoke.py` exercises the pinned
analyzer against committed, isolated Git fixtures in **enforcing** mode. It
copies the selected committed Python snapshot and reviewed catalog without
executing application source. The intentional historical copy lives only in
`tests/fixtures/rule_reuse/workspace_allocation_copy.py` and a temporary fixture
repository, never production tooling.

Three cases are required:

| Case | New exact | New near | Expected exit |
| --- | ---: | ---: | --- |
| clean | 0 | 0 | success |
| exact_copy | 1 | 0 | failure from the registered-copy gate |
| changed_authority | 0 | 1 | success; review suggestion |

A nonzero exit alone is insufficient proof of a blocked copy: reports must be
complete, bind the exact fixture revisions and identify the registered rule.
The smoke summary starts `incomplete` and becomes `complete` only after all cases
pass. Unexpected failures fail the CI job; expected rejection of the exact copy
is a passing smoke case. No Jev calls or keys are used.

CI uploads fixture evidence separately as `registered-rule-reuse-smoke`.
Its `summary.json` has `production_metrics: false`; these counts must not enter
production metric history. The ordinary `registered-rule-reuse` artifact remains
the authoritative PR comparison with no fixture reports mixed into it.

```bash
python tools/rule_reuse_ci_smoke.py --root /path/to/SpecGraph \
  --analyzer /path/to/specification-metrics --output /tmp/new-unique-smoke-directory
```

The output directory must be new. Keep `execution.json`, reports, selected
catalogs and SQLite evidence scoped to that run. Expanding the registered catalog
requires reviewing smoke coverage and the expected outcomes, not silently
relaxing its assertions.
