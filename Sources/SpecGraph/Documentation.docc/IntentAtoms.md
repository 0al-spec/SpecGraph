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
`c4d95427875d28870085c847852f7357859d164f`. The trusted counter parses source
data and does not execute PR-authored code. One informational comment reports
S, U, S/U, dead and unknown Specifications, and supplementary Python SLOC,
Cyclomatic Complexity (CC), Cognitive Complexity (Cog), and clone deltas.
Supplementary tools are pinned to Radon 6.0.1, complexipy 8.0.1, and jscpd 5.0.11.
Failed tools or unknown liveness remain explicit diagnostics; the
comment does not gate merge readiness.
