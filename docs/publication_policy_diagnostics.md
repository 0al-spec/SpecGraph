# Publication policy diagnostics

SG-SPEC-0069 pilot: architectural diagnostics for the publication gate.
The classification is **proposed**, authored as an engineering interpretation,
not a human approval record, canonical Intent or permission to publish.

## Decide by responsibility

Ask what changes when a condition changes:

- `policy`: eligibility, authority, trust, admitted evidence scope or transition
  semantics change. Prefer a named Specification with immutable facts.
- `mechanics`: parsing, exchange-shape recognition, I/O adaptation or enforcement
  of an already computed result changes. Procedural code is permitted.
- `variant_behavior`: dispatch selects behavior for an already prepared variant.
  Consider encapsulation in its type or Protocol when dispatch is repeated.

For example, parsing a JSON pointer is mechanics; checking that its evidence
belongs to the reviewed inventory is policy. Reading a Git blob is mechanics;
requiring a regular, immutable evidence source is a trust policy. Those
boundaries are explicit review judgments, not conclusions from CC or S/U.

## Bounded profile and evidence

`tools/publication_policy_classification.json` version 1 covers every
`require(...)` guard and `if` site in `tools/subject_publication.py`, plus three
registered PredicateSpec modules. Assert, match and conditional expressions
introduced into this inventoried module become unclassified diagnostics until
supported and classified. This does not discover equivalent rules throughout
the repository or resolve arbitrary Python dynamic imports.

Each site has a stable ID, category, rationale, diagnostic/dispatch selector,
position-independent predicate SHA256 and allowed architectural locations.
Families identify one semantic rule and its canonical definition. Specifications
have a module, symbol, factory-initializer digest and semantic family.

The analyzer parses source without executing it. It checks direct imported
PredicateSpec factories and direct `is_satisfied_by` consumers. Unknown factories,
shadowed receivers, missing sites, new sites, changed predicates and unreadable
source make extraction incomplete. A policy wrapped in additional inline
conditions remains inline. Repeated evaluation of one definition is reuse.

`completeness: complete` means all sites in this bounded profile resolved against
source. It does not mean the proposed semantic classification is approved,
application behavior is correct or the entire project was classified.

## Counters

- **Inline policies**: classified policy sites with procedural predicates instead
  of a resolved, directly applied Specification.
- **Duplicate policy definitions**: additional distinct definitions of a declared
  family beyond its canonical definition. Two callers of the same Specification
  count as one definition. Family equivalence is explicit proposed annotation;
  this is not an automatic semantic clone detector.
- **Policy boundary violations**: policy evaluations outside a site's declared
  locations and Specification definitions outside a family's declared modules.
  Correctly located inline policy still contributes to Inline policies.

Initial source at PR #761 commit `06efdb7ea0de52610211a72183d5866491e8b104`:
75 sites resolve: 53 policy sites, 19 mechanics, 3 variant dispatch.
They form 52 policy families. Four policy sites use three Specification definitions:
complete reviewed record is reused for subjects and workspace declarations.

| Diagnostic | Initial count |
| --- | ---: |
| Inline policies | 49 |
| Duplicate policy definitions | 0 |
| Policy boundary violations | 0 |

Zeros apply only to this scope and proposed family assignments. They do not
prove absence of equivalent rules or boundary problems elsewhere.

## Run and compare

```bash
make publication-policy-diagnostics
make publication-policy-diagnostics PUBLICATION_POLICY_REPORT_OUTPUT=/tmp/publication-policy.json
.venv/bin/python tools/publication_policy_diagnostics.py \
  --revision HEAD --base-ref <base-commit> --output /tmp/publication-policy.json --summary
```

Use repository Python via `PYTHON` when the worktree shares another checkout's
virtual environment. Default input is the working tree; its source hashes are
reported. `--revision` pins the classification and source to an immutable Git
commit. Baseline comparison reads the baseline's own versioned classification.
Absent historical classification means unavailable comparison, not zero.

Incomplete extraction reports `counts: null`, diagnostics and explicitly partial
`observed_counts`. Diffs require complete, compatible profiles. They list newly
introduced and removed violation IDs as well as aggregate count deltas: removing
an old violation cannot hide a newly introduced one behind a net zero. Changed
classification contracts are flagged and need interpretation during review.

## CI and next use

The Python CI publishes a run-local JSON artifact named
`publication-policy-diagnostics`. This step is informational and allows failures;
`merge_gate_enabled: false` is explicit. No new PR comment or canonical record is
created. Existing tests and quality gates retain their roles.

Next bounded refactor: extract the workspace allocation rule into its own typed
Specification, preserve its behavioral tests, update its existing family/site
bindings and measure removal of that inline violation. Only after validating
classification on changes should a separately approved policy gate be considered.
System One models may later suggest annotations for human review; they are not
an authority for blocking merge in this pilot.
