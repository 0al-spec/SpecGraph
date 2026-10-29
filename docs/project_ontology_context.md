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

The initial structural profile can verify a single package with no imports.
Imported/composed dependency closure is not implemented. In particular, the
current specgraph-core source imports specgraph.foundation, so compiling its
root alone leaves the required closure guarantee unavailable. Capturing those
bytes does not approve the package or ground all specifications. Missing context
does not prevent conversation capture or draft authoring.

Each domain outcome policy lives in its own Specification module with immutable
facts. Parsing, paths, subprocess adaptation and serialization remain at the edge.

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
does not certify a specification. Multi-member resolution is unsupported in this
profile. A single captured member may supply local advisory candidates while
overall dependency closure remains unavailable. Foreign workspace, malformed
input and duplicate identities remain explicit failures.

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
selection. Previous freshness is a separate observation; the current report is
recomputed from current captured inputs. Producer source digests are attributed
input identity, not execution attestation.

Exit status is 0 for `checked`, 1 for `unavailable`, and 2 for invalid/input
errors. `checked` is only this structural advisory operation; prose stays
unassessed and semantic approval remains absent. Imported closure can leave the
context unavailable even when local advisory reports exist. Missing selection
does not invoke refinement or prevent draft capture. Combining this mode with
refinement, loop or approval options is rejected; legacy modes remain unchanged.
