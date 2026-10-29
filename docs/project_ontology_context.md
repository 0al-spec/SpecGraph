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
