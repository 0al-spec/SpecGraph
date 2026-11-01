# One selected motivation composition

This realizes the composed-context case of SG-SPEC-0072 under proposal 0232.
The existing specification and its acceptance criteria are unchanged.

## Operator source and bounded decision

The operator reported that the current profile supports selected foundation
but cannot compose the existing motivation package, and chose to retain Motive
as a reuse candidate rather than duplicate it. The agent proposed:
“Следующий срез — поддержать одну явно закреплённую композицию этих пакетов.”
The operator replied to that proposal: “Хорошо, делай сейчас”. This authorizes
the bounded implementation, not acceptance of the packages' meanings.

The return record is the local intake task
`20261101T053425Z-task-resolve-one-pinned-multi-package-ontology-context-without-duplicating-motive.md`.
Its abbreviated proposal path is corrected by the following local note.
The canonical return anchors are SG-SPEC-0072 and
[proposal 0232](../../../proposals/0232_verified_project_ontology_context.md).

## Realization

The opt-in profile `ontologyc-motivation-composition-v1` captures three selected
packages and resolves project -> motivation-core -> events-core -> foundation.
Each selected source and saved compiler IR has an explicit SHA-256.
The foundation remains the existing release-pinned export catalog.

The project declares a relation to `motivcore:Motive`. The fixture adds no
local Motive definition. Release package bytes are retained under
`tests/fixtures/motivation_composition` with source URLs, hashes and their MIT
license. In Ontology 0.5.0 the required events-core 0.2.0 is under
`versions/0.2.0`; the unversioned path still contains 0.1.0.

## Checks and limits

`tests/test_project_ontology_composition.py` exercises the actual CLI with the
released compiler, positive closure, unknown and unqualified names, direct
versus transitive visibility, wrong symbol role, missing dependencies, pin and
namespace conflicts, duplicate imports, cycle attempts, absent source/IR/compiler,
digest mismatches, outcome precedence and selection-order stability.
The compiler's normalized import order is compared independently of source order,
with duplicate multiplicity preserved.

Existing Invalid and Unavailable Specifications retain decision precedence.
Parsing, exact identity matching and linking structural slots remain mechanical
adapters; they do not decide acceptance, readiness for publication or semantic fit.
No additional policy Specification is introduced merely to change S/U.

Supervisor preparation used the repository-local skill's targeted dry-run for
SG-SPEC-0072. It selected the existing node, with no gate and no canonical writes.
The plain refinement lane only permits spec changes, so implementation stays in
the separate tooling lane anchored here.

Joint spec term inventory/advisory analysis remains unsupported. A verified
composed package context is not a verified multi-member terminology inventory.
No GitView ontology, semantic approval, canonical term or active gate is created.

## Local observation

[The retained summary](verification.json) records three captured members and
158 checked structural reference occurrences, including the existing Motive URI.
The full report and workspace remain on TB5. These are attributed local results,
not execution attestation or a signed compiler-origin receipt.

The focused context/snapshot/report/Supervisor suite passed 131 tests without
skips using the Ontology 0.5.0 executable. Python quality, DocC sync and proposal
tracking passed. Hosted macOS/Linux execution is checked separately by the PR.
