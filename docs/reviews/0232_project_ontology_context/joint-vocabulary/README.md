# Joint vocabulary for the selected motivation composition

## Source and return path

This is a tooling realization under SG-SPEC-0072 and
[proposal 0232](../../../proposals/0232_verified_project_ontology_context.md).
The source observation is GitView's
`ontology/pilots/motivation-composition/README.md`, commit `4b32515`, reporting a
synthetic `GITVIEW-SPEC-0001` retest with SpecGraph runtime `710c4f60`.
The operator approved the bounded joint-vocabulary follow-up in conversation.
The local coordination receipt is
`20261101T082013Z-task-implement-joint-advisory-vocabulary-for-the-supported-motivation-composition.md`.
This does not accept GitView's candidate terms or create a real GitView spec.

The preceding [external-ID repair](../external-target-id/README.md) allows the
request to reach the context check. At this baseline, the supported motivation
composition verifies, but two independent guards return unavailable: explicit
inventory and the binding/validation bundle each require one member.

## Bounded realization

`tools/project_ontology_context/vocabulary.py` captures a lossless advisory
vocabulary from the existing immutable member snapshots. The supported
motivation composition requires verified context and complete captures; it
adds classes from the existing pinned foundation export catalog. It never
pretends the composition is one compiler-produced IR. Source/IR files are not
reopened, and missing members cannot yield a partial successful joint result.

The inventory and composed binding/validation reports consume that vocabulary.
Qualified references are exact. Unqualified spellings and aliases preserve
all matching declarations. Ambiguity is a gap/finding, rather than a winner
chosen by package order. Each candidate retains its package, version, concept
URI and captured hashes; dependency source URIs are retained where captured.
Foundation provenance explicitly identifies a hash-checked export catalog,
without an invented compiler or IR digest.

Composed reports have a distinct analysis profile and a member capture inventory.
Freshness covers every dependency and catalog input. The producer source binding
also includes the new vocabulary implementation and its composition/foundation
dependencies. Old producer/report bindings cannot silently validate changed code.
Previous inventory freshness stays unassessed; current inventory is recomputed.

Single-member binding extraction keeps its existing profile. The shared capture
adapter preserves local analysis for a single verified member whose full closure
is unavailable. Protocol/policy inventories, arbitrary package resolution and
natural-language interpretation are outside this slice. The legacy
`accepted_bindings` field and report-only structural mappings confer no acceptance.

## Before/after replay

An independent TB5 workspace copies GitView's existing composition inputs and
the exact synthetic target bytes from its retained retest. The original GitView
workspace is never written. The baseline source is archived from SpecGraph
`710c4f602a6c9c129aa665ccb844d6336d00bcf3`; the same copied target is then checked
with the changed source checkout and the same release `ontologyc` 0.5.0 bytes.

| Observation | Baseline | Changed source |
| --- | --- | --- |
| Context | `verified` | `verified` |
| Binding/validation bundle | `unavailable` | `analyzed` |
| Explicit inventory | `unavailable` | `analyzed` |
| Target operation / exit | `unavailable` / 1 | `checked` / 0 |

The target SHA-256 is identical in both runs. It contains only an ID and kind:
its successful empty inventory is not evidence of terminology coverage or
grounding. A separate synthetic extension explicitly mentions `motivcore:Motive`,
`sg:ValueObject` and unknown names. It reaches `checked`, retains the two resolved
origins and still reports unknown terms. A completed structural advisory operation
can have visible review gaps; it is not a semantic-readiness gate.

[The retained local observation](verification.json) records the target hash,
compiler hash, outcomes and original-pilot preservation check. Full derived
reports remain in the local TB5 task artifact directory. This packet does not
claim an independent rerun of GitView's Git-backup restoration or note history.

## Regression and policy review

`tests/test_project_ontology_joint_reports.py` exercises exact qualified names,
cross-package short-name and Unicode-alias ambiguity, attributable origins,
order invariance, source/IR non-reopening, partial/foreign capture rejection,
catalog loss/corruption and dependency-sensitive freshness. The baseline run
before implementation had four failures and five passes.

`tests/test_project_ontology_composition.py` also runs the real release compiler
and the actual Supervisor CLI for `GITVIEW-SPEC-0001`. Both macOS and Linux
release-compatibility jobs include these joint-vocabulary regressions.

This change implements input capture, namespace matching and report projection.
It reuses the existing invalid/unavailable outcome policies and freshness
Specification; it introduces no new approval, authority or lifecycle policy.
Mechanical parsing/matching is deliberately kept in adapters rather than adding
Specification classes to change adoption counters. Canonical specs and proposal
intent atoms are unchanged. Tests and byte bindings provide structural evidence,
not semantic approval, execution attestation or a global terminology guarantee.

## Delivery status

Prepared and locally verified on a PR branch. Hosted CI, review, merge and an
installed runtime update are separate events. The next product-level observation
is checking a separately authored real GitView specification against this same
explicit selection; that authoring is not part of this synthetic pilot.
