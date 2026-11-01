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
are emitted. The first CLI is checkout tooling, not yet an installed runtime
command or an automatic SpecDraft update hook.

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

HC/HCS input paths and their source bindings are workspace-relative. A relative
output directory is resolved from the caller's current directory. Tools are
operator-selected executables, never downloaded or built by this command.
Their digests identify bytes, not publisher authenticity. The observed compiler
combination is Hypercode IR v2 (`0.6.0-dev`) and ontologyc `0.5.0`.

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
