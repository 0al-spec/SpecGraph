# Explicit project ontology context

The source-checkout API `project_ontology_context.capture_project_context`
implements the bounded SG-SPEC-0072 selection contract. It accepts an explicit
workspace, project ID, selection path and operator-provided `ontologyc` executable.
It does not initialize a project, download a compiler, approve meanings or
activate a global gate. The broader 0232 migration/coverage proposal remains
separately scoped.

## Selection v1

Store a YAML selection inside the workspace. Paths are workspace-relative;
symlink/path escapes are rejected. Replace hash placeholders with the exact
lowercase 64-character SHA-256 values of the selected bytes:

```yaml
artifact_kind: specgraph_project_ontology_selection
schema_version: 1
packages:
  - id: org.0al.specgraph.core
    namespace: sgcore
    version: 0.1.0
    source: ontology/packages/specgraph-core/domain-ontology-package.yaml
    source_sha256: "<source-sha256>"
    ir: ontology/packages/specgraph-core/generated/ontology.normalized.json
    ir_sha256: "<ir-sha256>"
profiles:
  - ontologyc-structural-v1
composition:
  dependency_rule: explicit
  name_resolution_rule: qualified
```

`capture_project_context(project_root, project_id=..., selection_path=...,
ontologyc=..., compiler_sha256=...)` returns an immutable `ContextResult`.
Its `report()` includes the selected and captured package identities, checks,
context revision and compiler byte identity. The optional compiler pin is
checked against the same captured executable bytes **before execution**.
Compiler provenance remains `not_verified`; a byte hash is not origin attestation.

Selected source and saved IR hashes are checked against their captured bytes
before compiler execution, including when the compiler is unavailable. The
identity binds canonical package order, workspace-relative selected sources,
captured source/IR hashes, compiler hash, checking profiles and composition rules.
Changing an identity input changes the revision. Consumers receive captured bytes
and do not reopen saved IR. Partial results retain explicit capture diagnostics.

## Outcomes and limits

`invalid` has priority over `unavailable`; only successful required checks permit
`verified`. Missing selection, executable or unsupported checks remain unavailable.
Identity/hash mismatch and detected invalidity remain invalid. Snapshot failures
have typed outcomes; consumers do not classify them by matching error messages.
An ambiguous nonzero compiler exit, signal termination or undecodable compiler
output leaves the check unavailable: the process outcome alone does not establish
invalid input. Independently detected identity, pin and source/IR mismatches
remain invalid. See the [compiler outcome defect record](reviews/0232_project_ontology_context/compiler-outcome-defect/source.md)
for the repair and its evidence.

With `profiles: [ontologyc-structural-v1]`, imported packages have unavailable
closure. Ontology 0.5.0 requires at least one import. The [earlier compatibility
probe](reviews/0233_mechanical_specification_authoring/local-model-pilot/README.md#single-package-verified-probe-31-october-2026)
records this combination.

### One pinned foundation import

Set `profiles: [ontologyc-foundation-v1]` in the existing selection file.
Select one package whose only import is
`{id: specgraph.foundation, namespace: sg, version: 0.1.0}`.
Run the workspace CLI shown below with the same source, IR and compiler pins.

The profile pins the [foundation export catalog from Ontology 0.5.0](https://github.com/0al-spec/Ontology/blob/0fcc94469d971aaf39fcc182bc5c6b8acff37fd2/SPECS/ontology/foundation/0.1.0/exports.json). Release compatibility CI compares the vendored bytes with `ontologyc export-foundation` on both platforms. The profile checks the SHA-256 of those bytes before linking verified references to their URIs.

SpecGraph runs `ontologyc check --format json` on private copies of the selected compiler and the pinned source. A compiler rejection can identify an invalid foundation reference before there is any generated IR. The report binds the compiler's code and field to the value at that location in the captured source. A valid source with missing IR remains unavailable. A process failure or an unreadable diagnostic response is also unavailable.

For `Entry.extends: sg:ValueObject`, the report includes the declaration's
JSON pointer and `ontology://specgraph.foundation/0.1.0/classes/ValueObject`.
For `sg:Typo` at that site the outcome is `invalid`. The reference includes the pointer and the source value. The `compiler_diagnostic` records `class.extends.unresolved` and the SHA-256 of the checked source and executable. A rejected package has no verified snapshot or context revision.
The `resolved_imports` entry identifies the content actually consulted and
participates in the context revision. An unavailable catalog or an unsupported
import set produces `unavailable`; a catalog digest mismatch produces `invalid`.
Verification covers structural name resolution in this profile. Package approval
and prose coverage retain their separate review processes.

Each domain outcome policy lives in its own Specification module with immutable
facts. Parsing, paths, subprocess adaptation and serialization remain at the edge.


### One selected motivation composition

Use the opt-in profile `ontologyc-motivation-composition-v1` in the same
selection format and CLI. Select three packages with exact source and IR hashes:

| Selected member | Namespace | Version |
| --- | --- | --- |
| Your project package | Your unique project namespace | An exact project version |
| `org.0al.motivation.core` | `motivcore` | `0.1.0` |
| `org.0al.events.core` | `eventcore` | `0.2.0` |

Foundation is the existing pinned `specgraph.foundation@0.1.0` catalog and is
not an additional selected member. The project must explicitly import
motivation-core and may also import the selected events-core and foundation.
Motivation imports exactly events-core and foundation; events imports only
foundation. This bounds the supported graph; a different package set needs a
separate profile. Each dependency source is supplied explicitly in the workspace,
not downloaded or chosen by a remote version solver.

For example, a project relation may use `range: motivcore:Motive` without
declaring its own Motive class. Imports and references resolve by exact package
ID, namespace, version and symbol role. An imported name must be qualified and
visible through a direct import; a transitive dependency is not implicitly visible.
Every resolved concept includes its source pointer and an `ontology://` URI.

The CLI returns 0 for verified closure, 1 for unavailable checks and 2 for
detected invalidity. Missing selected dependencies, incompatible import pins,
namespace conflicts, cycle attempts and unknown qualified names are invalid.
Absent source, IR or compiler stays unavailable unless another independently
detected error makes the result invalid. Independently compiling each package
cannot establish closure.

`resolved_imports` records the selected dependency source paths and SHA-256
alongside the foundation pin. Captured source/IR, compiler and profile inputs
participate in the context revision. Reordering selection members preserves that
revision. Package hashes pin the selected bytes; they do not attest publisher
identity or accept package meanings.

[The source-bound realization](reviews/0232_project_ontology_context/motivation-composition/README.md)
and `tests/fixtures/motivation_composition` retain a runnable synthetic project
and the actual dependency packages from Ontology 0.5.0. The events-core 0.2.0
source is under `SPECS/ontology/packages/events-core/versions/0.2.0/`.

This profile checks package composition and structural reference slots.
The explicit term inventory and advisory reports also support this one verified
composition, as described below. Other multi-member profiles remain unavailable.
A composed context does not establish natural-language coverage or semantic
approval.

## Workspace CLI and native runtime

From the source checkout, inspect help with
`python tools/project_ontology_context_cli.py --help`. A capture command selects
an existing workspace and caller-provided executable:

```sh
python tools/project_ontology_context_cli.py \
  --workspace-root /path/to/project --project-id example \
  --selection ontology/context.yaml --ontologyc /path/to/ontologyc \
  --compiler-sha256 <executable-sha256> --output runs/ontology-context.json
```

An installed native source runtime exposes the same operation:

```sh
specgraph-runtime --workspace /path/to/project ontology-context -- \
  --project-id example --selection ontology/context.yaml \
  --ontologyc /path/to/ontologyc --output runs/ontology-context.json
```

The CLI may read `project_id` and an optional `ontology_context.selection` pointer
from `specgraph.project.yaml`; explicit arguments take precedence. It does not
rewrite configuration or run init. JSON stays on stdout; exit codes are 0 for
verified, 1 for unavailable, and 2 for invalid/input errors. Optional output is
atomically replaced only inside the selected workspace, without overwriting
project configuration, ontology inputs or unrelated existing files.

Native routing preserves the wrapper-selected workspace and rejects forwarded
workspace overrides. Argument abbreviation is disabled, including forms such as
`--workspace-r`. Existing init, next-move, supervisor and draft routes remain.
This is a native source-runtime route, not a new command in the standalone
SpecDraft wheel CLI.

## Context-bound advisory reports

`spec_ontology_context_reports.build_context_reports(context,
workspace_root=..., specs_root=..., documents=None)` connects the existing
binding index and validation report to the captured context. It reads the
selected `SG-SPEC-*.yaml` corpus once, or accepts explicit workspace-relative
captured `(path, bytes)` documents. Both views consume the same snapshot and
parsed specifications; validation consumes the same built binding index.

Inputs retain each specification path/hash and the profile
`specgraph-local-symbol-advisory-v1`. Report metadata records project/workspace,
context revision/outcome, member/source/IR/compiler identities and the
`single_member_local_symbols` scope. The legacy field name `accepted_bindings`
still describes structural extraction, not accepted meaning.

One successfully captured member may supply advisory local-symbol analysis
while imported closure is unavailable. This does not claim verified context
closure. Invalid context, foreign workspace, mismatched capture, duplicate spec
IDs or unsupported joint multi-member analysis return diagnostics without
falling back to mutable saved IR. Ordinary no-context report APIs remain
backward-compatible. These profiles do not assess all natural-language prose.

## Explicit report freshness assessment

At creation, `bind_report_bundle(bundle, producer_identity=...)` produces an
immutable `ReportInputBinding`. Save its `report()` alongside that exact advisory
bundle. `assess_report_freshness(saved_bundle, input_binding=..., context=...,
workspace_root=..., specs_root=..., producer_identity=..., documents=None)`
compares it with explicitly supplied current inputs and a rebuilt advisory view.
No directory is searched for a latest result, and no cache is selected implicitly.

The binding records canonical-JSON bundle/binding digests and caller-supplied
producer identity. It is integrity/attribution data, not a signature, trusted
producer attestation, FeaturePassport receipt or evidence admission. Creating
a binding later cannot establish who produced historical data.

`fresh` means compatible declared advisory inputs: project/workspace, context,
captured member/source/IR/compiler, exact specification paths/hashes, binding and
validation payloads, analysis profile and producer identity. Changed known inputs
are stale, inconsistent saved content is invalid, and missing/partial identity
or original binding remains unavailable. Missing data cannot become fresh by
reconstructing a historical binding during assessment. A named Specification
evaluates immutable comparison facts; it does not approve meanings or activate
a new Supervisor/merge gate.

## Explicit term inventory

`build_term_inventory(context, workspace_root=..., specs_root=...,
documents=None)` assesses the `specgraph-explicit-terms-v1` profile:
`specification.terminology` mapping keys and string references in root or
`specification.ontology_refs`. It records spec/path, exact field path, source
hash, YAML line/column and character span, and captured context identity.
Source marks are one-based line/column with exclusive end; byte and Unicode
character offsets are not interchangeable. YAML aliases are rejected rather
than presenting an anchor's location as an occurrence location.

Qualified matches are structural candidates; spelling/alias matches remain
candidates and unknown/ambiguous terms become attributable gaps. No match is a
human review or meaning approval. Gap records retain existing report vocabulary
where applicable. Captured documents may be shared with the advisory reports;
the inventory never reopens saved ontology IR or changes source specifications.

Free prose remains `unassessed`, `grounded` remains false, and an empty inventory
does not certify a specification. A single captured member may supply local advisory candidates while
overall dependency closure remains unavailable. Foreign workspace, malformed
input and duplicate identities remain explicit failures.

### Joint vocabulary for the selected motivation composition

For a verified `ontologyc-motivation-composition-v1` context, inventory and the
binding/validation bundle share the captured-vocabulary implementation. It
reads classes, relations and aliases from all three immutable selected IR
snapshots, plus classes from the hash-checked pinned foundation catalog.
It does not merge packages into a fictional compiler IR or reopen saved source/IR
files. Protocol/policy inventories and arbitrary package compositions are outside
this slice. An incomplete or unverified composition cannot fall back to the
symbols of whichever packages happen to be available.

Qualified names such as `motivcore:Motive` require an exact reference match.
Unqualified spellings and aliases search the selected vocabulary as a whole:
one match is a candidate, multiple declarations remain ambiguous, no match is
unknown. This is a specification-wide advisory vocabulary, not the direct-import
visibility rule for references inside an individual ontology package.
The existing package compiler/closure check still owns that separate rule.

Each inventory candidate and composed binding/gap has `candidate_origins`:
package ID/namespace/version, concept URI, captured source/IR/compiler hashes and
the captured import source URI where available. Foundation entries are explicitly
`pinned_export_catalog`, with no fabricated IR/compiler digest. The bundle records
`selected_composition_symbols` and `specgraph-composed-symbol-advisory-v1`, an
ordered `members` capture inventory and `foundation_catalog`. It has no invented
single `selected_member` or aggregate source/IR hash. `verified_closure: true`
refers only to the already verified selected dependency closure.

The composed binding index resolves both terminology keys and explicit
`ontology_refs` through that vocabulary. It keeps the legacy `accepted_bindings`
field name for compatibility; the field remains structural advisory data.
Ambiguity creates gaps/findings rather than allowing package order to select a
winner. Existing legacy structural mappings and warnings remain report-only.
Single-member binding extraction retains its existing profile and behavior.

Freshness binding includes every member capture and catalog identity. A changed
dependency cannot stay fresh just because the project package is unchanged.
Changing only member selection order does not change the results. Previous
inventory freshness remains `not_assessed`; current inventory is recomputed.
See the [source-bound GitView replay](reviews/0232_project_ontology_context/joint-vocabulary/README.md).

## Target-scoped Supervisor operation

The optional operation inspects one existing specification and saves a separate
derived report. It does not refine the target or modify approval gates:

```sh
python tools/supervisor.py --build-project-ontology-context-check \
  --target-spec SG-SPEC-0072 --ontology-context-project-id specgraph \
  --ontology-context-selection runs/ontology-context-pilot/selection.yaml \
  --ontologyc /path/to/ontologyc --ontologyc-sha256 <executable-sha256>
```

The command shares one captured context and target byte sequence across reports,
inventory and explicit comparison. It saves
`runs/project_ontology_context/SG-SPEC-0072.json` inside the selected workspace,
with atomic replacement restricted to the same report/target/project kind.
Compact JSON goes to stdout; `--output-mode full` prints the full report.
The same command can be forwarded through native runtime `supervisor -- ...`.

Pass `--ontology-context-previous-report <workspace-relative-path>` to assess
an explicitly chosen previous target report. There is no automatic latest-report
selection. `previous_freshness_scope` is `binding_validation_bundle`: only the
binding/validation bundle is compared, while `inventory_freshness` stays
`not_assessed`. A fresh bundle never certifies a previous inventory. The current
report is recomputed from current captured inputs. Producer source digests are attributed
input identity, not execution attestation.

Targets may use a product namespace such as `GITVIEW-SPEC-0001`, as well
as legacy `SG-SPEC-0001`. Both advisory entry points share the safe uppercase
`PREFIX-SPEC-number` syntax with an ASCII decimal suffix. The operation reads
the exact `specs/nodes/<target-id>.yaml` and requires its YAML ID to match.
It does not allocate IDs, rename nodes or follow allocation-policy aliases.
Workspace, symlink and report ownership restrictions remain enforced.
See the [source-bound defect and regression record](reviews/0232_project_ontology_context/external-target-id/README.md).

Exit status is 0 for `checked`, 1 for `unavailable`, and 2 for invalid/input
errors. `checked` is only this structural advisory operation; prose stays
unassessed and semantic approval remains absent. Imported closure can leave the
context unavailable even when local advisory reports exist. Missing selection
does not invoke refinement or prevent draft capture. Combining this mode with
refinement, loop or approval options is rejected; legacy modes remain unchanged.
