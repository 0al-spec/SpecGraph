# Readable ontology overview export

This bounded realization of proposal 0232 exports a reviewable HC/HCS pair from
an **authored composition**, using SG-SPEC-0072 as the first example. The operator
approved the three-role outline and its source bindings in the
[prototype discussion](reviews/0232_project_ontology_context/hypercode-overview/source-notes.md).

## Contract

- Input: an explicitly authored HC tree and its HCS bindings. Use `overview_name`
  to select a short role name; otherwise the HC type is used. Every occurrence
  has a distinct `role_id` or HC `#id`, and a fully qualified `ontology_ref`.
- One root and unambiguous sibling names are required. Hierarchy and order are
  preserved; relations are never traversed to invent children. Technical HC IDs
  become HCS identities, while the readable HC contains only short role names.
- The root selects `ontology_source`; a role may explicitly select another
  workspace-relative package. References must exist in that exact package's
  compiler-produced IR. A supplied source hash must match. This checks local
  declarations, not import closure, relation applicability or semantic approval.
- Optional Python production bindings require `production_path`,
  `production_symbol` and `production_anchor` together. The function must be a
  unique top-level definition and the anchor must occur once inside it. Source
  modules are read and parsed with AST; they are never imported or executed.
- Output: `context.hc` and `context.hcs` in a new directory. HCS records role/type
  identity, selected composition relation, exact source and compiler digests,
  original HC/HCS digests and checked production locations. Absolute temporary
  paths, timestamps and inferred relations are excluded. Fixed input/tool bytes
  yield identical output bytes. Existing output directories are not overwritten.
- All selected mappings and generated Hypercode are checked before creating the
  destination. Exit 0 means `exported`; exit 1 means a required tool is
  `unavailable`; exit 2 means invalid input or an export failure. Processing
  reports are JSON on stdout (success) or stderr (failure); argument usage errors
  use ordinary argparse diagnostics. No canonical graph writes, runtime
  invocation evidence, term acceptance or new merge gate are implied.

The only input formats are existing HC/HCS. This is not a reverse importer or a
lossless export of every HCS property. Extra source attributes and ontology
relations remain in the original inputs; only the documented projection fields
are emitted. The CLI is available from the source checkout and the native
runtime's `ontology-overview` operation. It is independent of SpecDraft note
capture; there is no automatic notebook-conversion hook.

## Run the first example

The [selection HC](reviews/0232_project_ontology_context/hypercode-overview/selection.hc)
declares the existing case and its two check IDs. Its
[selection HCS](reviews/0232_project_ontology_context/hypercode-overview/selection.hcs)
chooses the three short names and explicit bindings. No separate JSON/YAML
composition or mapping schema is introduced.

From the SpecGraph checkout, with explicitly selected reference tools:

```sh
.venv/bin/python tools/ontology_overview_cli.py \
  --workspace-root . \
  --hc docs/reviews/0232_project_ontology_context/hypercode-overview/selection.hc \
  --hcs docs/reviews/0232_project_ontology_context/hypercode-overview/selection.hcs \
  --hypercode /path/to/hypercode --ontologyc /path/to/ontologyc \
  --output-dir /path/to/new-review-directory
```

In the source CLI, HC/HCS input paths and their source bindings are
workspace-relative. Relative `--output-dir`, `--hypercode` and `--ontologyc`
paths resolve from the caller's current directory; `--workspace-root` does not
change that directory. Tools are operator-selected executables, never downloaded
or built by this command.
Their digests identify bytes, not publisher authenticity. The observed compiler
combination is Hypercode IR v2 (`0.6.0-dev`) and ontologyc `0.5.0`.

## Use an installed native runtime

Install a reviewed SpecGraph revision containing this operation and inspect its
help before use. The installed snapshot provides the exporter and its Python
environment, while the project owns its ontology, selections and review files:

```sh
specgraph-runtime --workspace /absolute/product/project ontology-overview -- \
  --hc ontology/views/publication.selection.hc \
  --hcs ontology/views/publication.selection.hcs \
  --hypercode /absolute/path/to/hypercode --ontologyc /absolute/path/to/ontologyc \
  --output-dir docs/reviews/publication-new
```

Choose the root containing the selected ontology sources and any bound
production files. This can be the product project even when its SpecGraph
knowledge workspace is elsewhere. Export needs no initializer, project
configuration or developer checkout. The runtime rejects forwarded
`--workspace-root` overrides; the exporter also disables argument abbreviation.
Inputs and source bindings resolve within the selected root. A relative output
directory resolves there too; an explicit absolute output directory retains the
exporter's existing semantics. Existing destinations are never overwritten.
Pass the chosen compiler executables explicitly, preferably with absolute paths.
Relative `--hypercode` and `--ontologyc` values resolve from the selected
workspace in native mode, not from the directory where the launcher was called.
The launcher does not install or select those tools.

The route preserves stdout/stderr and exit codes: 0 `exported`, 1 `unavailable`,
2 invalid/input error. Error envelopes depend on which layer rejects the request:

- Launcher validation, such as a workspace override or nonexistent workspace:
  exit 2 and JSON `{"error": "..."}`, without `status`.
- Exporter processing errors after dispatch: JSON
  `{"status": "invalid", "error": "..."}` with exit 2, or
  `{"status": "unavailable", "error": "..."}` with exit 1.
- Argument usage errors from either parser: exit 2 and ordinary argparse text.

Consumers should inspect the exit code first, read `error` for JSON failures,
and tolerate missing `status` or non-JSON usage diagnostics. The launcher keeps
its existing error contract. Exported files have the same structural/advisory
meaning as a checkout export. To put version-matched guidance in the project,
use the existing
`draft -- skill install --name specgraph-project-ontology --project ...` command.
The skill suggests this operation for a requested structure overview and useful
ontology-composition PR diffs. It does not mandate an export for every edit.

The installed-runtime smoke always checks the operation's help and unavailable
tool result from separate workspaces. Passing `--hypercode` and `--ontologyc` to
`tests/native_runtime_smoke.py` additionally checks a real export in both roots,
including byte-identical output and delivery of the updated skill. An observation
with `reference_export: not_requested` is not a successful reference export.

The [installed-runtime observation](reviews/0231_native_runtime/ontology-overview-verification.json)
records a local installation of commit `126ee3cd7155ca4914de958477b2cb94a849c17f`
with a separate venv and no engine `.git`. Both synthetic workspaces completed
real Hypercode/ontologyc exports with identical pair digests and received the
matching project ontology skill. Existing init/advisor/Supervisor/note scenarios
also passed. This is local fixture evidence; it does not update a consumer's
existing installation or establish ontology acceptance or live agent behavior.
Later skill wording clarifications are verified through source/package equality;
this observation continues to identify the skill installed at `126ee3cd`.

Version 1 accepts a single HCS sheet and the empty context. HCS imports and
context selection are not expanded by the export adapter. Generated HC removes
source classes/IDs; `source_type` and `role_id` retain type/occurrence identity in
the mapping. Other source class annotations and unmapped properties remain in
the input. Duplicate sibling labels are rejected rather than silently renamed.
Short display names use ASCII HC identifiers in this first profile. Python
bindings require UTF-8 source; malformed syntax is a structured rejection.
If a type selector would leak properties into another occurrence, resolved
output comparison rejects the export; choose unambiguous display names.

The root's `ontology_source` is the exporter profile's explicit default package
for selected roles, not implicit HCS inheritance. Every emitted role gets its
own source/IR/compiler hashes. `composition_ref` existence is checked, but its
cardinality and role compatibility are not established by this view. A scenario
source is captured by hash; the exporter does not evaluate TypeScript values or
prove that the authored role IDs appear there. `production_line` is a navigation
location in the captured file and does not replace `production_sha256`.

The [generated example](reviews/0232_project_ontology_context/hypercode-overview/generated/context.hc)
keeps the approved three-line outline. Its HCS adds identities and checked
bindings. Generation preserves the manual prototype and both source files.
Regenerate into a new directory and review the pair before replacing a tracked
example; source changes intentionally change the mapping digest.

## Verification

```sh
HYPERCODE_BIN=/path/to/hypercode ONTOLOGYC_BIN=/path/to/ontologyc \
  .venv/bin/python -m pytest -q tests/test_ontology_overview.py
```

Without those variables, compiler compatibility cases are explicitly skipped;
the always-on tests cover the selected-role contract, deterministic rendering,
source-path and AST binding checks, no-overwrite behavior and failed export
preservation. Optional cases use both real executables to reproduce the example
and reject bad mappings before destination creation. Neither suite validates
ontology meaning or observed runtime behavior.

## Second fragment: publication criteria

The [publication replay](reviews/0232_project_ontology_context/hypercode-overview/publication/README.md)
selects the existing core `Spec`, `Requirement` and `AcceptanceCriterion` types
for SG-SPEC-0071: seven roles, three levels and five distinct criterion IDs sharing
one type. A common HCS type selector supplies the shared ontology/production
binding while exact IDs choose display names and source fragments.

Real-tool controls preserve identities across renaming and tree reordering,
reject incorrect references/hashes and detect root-name selector leakage.
No exporter code change was required. This is an ontology-bound instance view;
SpecDraft capture and notebook conversion are outside this experiment. The
readable names remain proposed for human review.
