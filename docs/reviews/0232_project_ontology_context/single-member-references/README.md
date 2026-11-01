# Single-member explicit references omitted by binding and validation

## Source and affected contract

GitView's motivation-composition pilot, local commit `b388aa3`, reports that
its precanonical `docs/drafts/GITVIEW-SPEC-0001.yaml` reaches `checked` on runtime
`54db6fb9`. With the default single-member selection, inventory marks the explicit
`motivcore:Motive` reference unknown, but the binding index and validation report
omit it. A composed-context negative control appears in all three views.
The source is `ontology/pilots/motivation-composition/README.md`, section
“Наблюдение для SpecGraph”. The local intake receipt is
`20261101T091245Z-review-note-single-member-ontology-binding-drops-explicit-references-seen-by-inventory.md`.

This defect follows the existing SG-SPEC-0072 / [proposal 0232](../../../proposals/0232_verified_project_ontology_context.md)
tooling-realization lane. The private draft text and ontology packages are not
copied into this packet. No terms or canonical graph nodes are accepted here.

## Root cause and consequence

The #857 implementation deliberately retained the legacy snapshot-only builder
path for one member. The context wrapper constructed a common vocabulary, but
only passed it to the builders for compositions. Explicit `ontology_refs`
extraction was already implemented in the vocabulary path; the legacy path
only considered terminology keys and its historical structural mappings.
Consequently, unknown explicit references could disappear when inspecting the
single-member binding or validation view independently.

Before repair, focused regressions produced eight failures and thirteen passes.
They reproduced omitted known/unknown qualified references, alias ambiguity
disagreement and the need to version the changed local interpretation.

## Repair and compatibility

All context-bound reports now use the already captured vocabulary. Root and
nested explicit reference lists, exact qualified names and unqualified
spelling/alias candidates therefore use the same resolver as inventory.
Unknown references become attributable gaps/findings; ambiguity never selects
a winner by normalized spelling or package order. A selected local package
does not gain access to a dependency merely because a qualified name was written.

The local analysis profile becomes `specgraph-local-symbol-advisory-v2`.
Historical v1 bundles are stale against v2 even with unchanged input files;
the existing freshness policy checks the profile and complete report payloads.
The composed profile is unchanged. Single-member source/IR/compiler evidence
is explicitly restored from its snapshot, retaining `compiler_checked` rather
than losing it when the builders no longer receive the snapshot argument.
Local scope, `verified_closure: false`, report-only authority, existing structural
`sgcore:*` mappings and unavailable-closure handling remain unchanged.
Legacy no-context builder defaults remain on their original path.

This is adapter routing and source-bound projection, not a new approval or
lifecycle decision. Existing outcome/freshness Specifications retain their
responsibility. No new Specification class or global quality gate is introduced.

## Replay on the real draft

An isolated TB5 workspace copies the existing GitView selection/packages and
the actual precanonical draft, preserving its bytes. The baseline tools are
archived from SpecGraph `54db6fb97c1b66754ddf1d0e63882c30c3841319`.
The old and changed source entry points use the same copied default context
and pinned release `ontologyc` 0.5.0. The changed source also checks the selected
motivation composition as a control. The original GitView inputs are not written.

| View of `motivcore:Motive` | Baseline default | Changed default | Composition control |
| --- | --- | --- | --- |
| Inventory | unknown | unknown | structurally resolved candidate |
| Binding gaps | 0 | 1 | 0 |
| Validation findings | 0 | 1 | 0 |
| Total warnings | 4 | 5 | 4 |
| Operation / exit | checked / 0 | checked / 0 | checked / 0 |

The additional warning exposes the omitted reference. It does not indicate
that the repair introduced a new ontology term or accepted an import. The three
historical structural `sgcore` warnings and `Activity` review gap are not resolved
by this change. Their applicability is a separate follow-up.
`checked` remains completion of the advisory operation, not absence of gaps,
semantic approval, or full-spec conformance.

[The retained observation](verification.json) binds the source/draft hash,
before/after outcomes, local compiler evidence and preservation check.
Full reports remain in the local TB5 task artifact directory. The private draft
was inspected on a copy; neither publication into GitView's canonical graph nor
the user's reported note-history/backup restoration was performed here.

## Prevention and delivery state

Regressions cover root/nested known and unknown references, namespace/case,
unique/ambiguous aliases, malformed lists, structural mappings, preserved compiler
evidence and v1-to-v2 staleness. Composed and native/runtime suites remain part
of the focused check. CONTRIBUTING and DocC record the lesson: test the same
positive and negative explicit field across default and specialized paths.

Prepared on a PR branch. Hosted CI/review, merge and an installed runtime update
are separate events. The independent read-only implementation review reported no
blocking findings; it did not execute tests or approve terminology.
