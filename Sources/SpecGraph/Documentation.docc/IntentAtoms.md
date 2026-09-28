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
