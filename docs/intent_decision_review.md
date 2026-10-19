# Intent decision review

Contract: `specgraph.intent-decision-review/v1`.

For every added, removed or modified Intent Atom, record how the obligation is
represented in code: a new Specification, reuse of an existing one, demonstrated
mechanics, contract-only work, retirement, or explicit `needs_review`. This is a
mandatory engineering **coverage** check in the existing blocking `python-quality`
PR job. It does not approve semantics, authenticate a reviewer, accept evidence,
change S/U or require increasing S. No LLM or network request is made.

## Trigger and scope

The gate consumes the unchanged `specgraph-intent-atoms-v1` analyzer/profile at
exact Git base/head revisions. Added, removed and modified records all matter;
a net-zero count can still require review. An incomplete snapshot is `invalid`,
including a missing tracked specification root; it is never interpreted as zero.

The profile covers `acceptance[]`, `spec.acceptance[]` and explicit intent arrays.
It does not discover every normative sentence, nested requirement or code-only
policy change. Existing SpecificationCore review rules still apply when no atom
changes. `not_required` means only that this trigger did not fire.

## Record and binding

Add a single field to the PR description:

```text
Intent-Decision-Review: tools/intent_decision_reviews/my-change.json
```

The selected JSON must be a regular tracked Git blob at the PR head. The gate
checks its schema, exact base revision, intent-delta digest, PR-description digest
and changed-source scope digest. The report preserves actual base/head SHAs,
the review blob's SHA-256 and full PR title/body/URL as author-provided context,
not approval or instructions to execute. Changed description, intent, base or
source files invalidate the old record.

There is no circular head-commit reference: the record binds the complete
changed-path inventory with each head Git object ID/mode/type (including deletions),
excluding only the selected record itself. The report separately binds that
record and the actual final head commit. Reused files are pinned by the exact
base and complete changed-path inventory. Hashes are integrity evidence, not
signatures or authenticated reviewer identity.

Each decision names an exact `change_sha256`, a disposition, a nonempty rationale,
`implementation_refs` and `specification_refs`. Missing records stay `needs_review`;
duplicate or unknown change references are invalid. JSON duplicate keys are
rejected. A blanket statement that the file is an adapter does not cover atoms.

| Disposition | Required structural evidence |
| --- | --- |
| `new_specification` | Python implementation declaration and recognized Specification definition absent at base |
| `reuse_specification` | Python implementation declaration and recognized Specification definition already at base |
| `mechanics` | Python implementation declaration and a concrete non-extraction rationale |
| `contract_only` | Explicit rationale, with no production Python/Rust/Swift/shell source changes in the PR |
| `retired` | Removed atom and explicit retirement rationale |
| `needs_review` | Unresolved interpretation; fails the coverage gate until addressed |

References use `{"path":"tools/rules.py","symbol":"RuleSpec"}`. Paths must be
repository-relative, declarations must exist in regular Git blobs and source is
parsed without executing it. V1 recognizes direct `Specification` subclasses
and directly imported `PredicateSpec` / `FirstMatch` factory declarations.
Unknown wrappers, inherited aliases and other languages need a qualified future
adapter; do not relabel them as mechanics to bypass the check. Boolean composition
can cite its existing component definitions without creating a wrapper Spec.

The gate validates source references and coverage, **not** whether the cited
caller applies the rule correctly, whether a mechanics rationale is true, or
whether two decisions are semantically equivalent. These remain review duties.
`covered` is not `approved`; `semantic_approval` remains false.

The gate itself uses named Specifications: invalid/unresolved/not-required route
rules plus `ImplementationTraceSpec`, `SpecificationOriginSpec`,
`IntentDispositionSpec` and `ContractOnlyScopeSpec` for record obligations. Each
is in its own module and consumes immutable facts. Git/JSON/AST adapters prepare
those facts; valid records preserve their rule traces in the report.

## Local workflow

Prepare the exact PR description in a file, including the review-path field.
Commit the implementation/spec changes first so Git objects exist, then draft:

```sh
.venv/bin/python -B tools/intent_decision_review_gate.py \
  --base-ref BASE_SHA --head-ref HEAD \
  --review-path tools/intent_decision_reviews/my-change.json \
  --pr-body-file /tmp/pr-description.txt --draft \
  --output tools/intent_decision_reviews/my-change.json
```

Draft generation marks every row `needs_review`. Inspect source/intent and fill
references/rationales; commit the completed record. Validate the final snapshot:

```sh
make intent-decision-review SPEC_EVIDENCE_BASE_REF=BASE_SHA \
  INTENT_DECISION_REVIEW_ARGS='--pr-body-file /tmp/pr-description.txt'
```

`--draft` is preparation, never successful review. Exit codes for validation:
0 = `covered` / `not_required`; 1 = `needs_review`; 2 = `invalid` or unavailable
inputs. Use `--output` for a machine-readable report; otherwise JSON goes to
stdout. Refresh the draft and re-review after bound source or description changes.

## CI integration and rollout

`tools/python_quality.py` invokes the gate on `GITHUB_EVENT_NAME=pull_request`,
after its existing checks, using `GITHUB_EVENT_PATH`. The existing job installs
project dependencies and fetches full Git history. Missing/malformed event data
fails rather than silently skipping; event mode cannot override the selected
base, description or review path. This requires no extra token permissions,
provider key or workflow YAML changes. Local/push quality runs retain their
existing behavior; use the Make target to request a local comparison explicitly.

Enforcement becomes available once this integration lands and a PR contains the
gate. It is not a retroactive check on older heads lacking it, and does not
replace GitHub branch protection or current-head code review. Existing informational
Intent Atoms / S/U comments keep their original contracts.

## PR773 regression and lesson

PR773 at `94be344c061f214cca6db250d08e7d64658b0b09` added three top-level acceptance
atoms to SG-SPEC-0071: criterion/test binding, identity preservation and explicit
missing/failed observation states. It added procedural evidence decisions while
the bounded publication classifier inventoried another module. Existing counters
detected change but did not require joining intent to a disposition in code.

The test fixture preserves that exact node and the `acceptance_signal` excerpt
with commit/path/digest provenance. Its three changes require review despite zero
new Specification definitions. This is a bounded single-node regression, not a
recreation of whole-project totals or a claim that all three require new classes.
Tests also preserve failure on missing roots, stale source/description, malformed
records and ordinary functions falsely referenced as Specifications.
