# Run YAML lint through the native runtime

RFC SG-RFC-0237

The [GitView observation](../archive/proposal_sources/0237_native_spec_yaml_lint.md)
records the cost of temporarily copying a canonical node for a draft-only
identity check. This proposal complements the draft identity surface in
[0235](0235_product_draft_candidate_check.md). SG-SPEC-0009 anchors explicit
operator selection.

## Interface

```sh
specgraph-runtime --workspace /path/to/product lint -- \
  specs/nodes/PRODUCT-SPEC-0001.yaml docs/drafts/PRODUCT-SPEC-0002.yaml
```

The operator explicitly selects one or more workspace-relative YAML files in
`specs/nodes/` or `docs/drafts/`. Absolute paths, traversal, symlinks, and
invalid selections such as directories are rejected. Relative paths are resolved
from the selected workspace. The command reuses the existing YAML linter.

The `specgraph_yaml_lint` schema 1 report lists each file's `checks_run` and
`issues`. A parse failure omits downstream checks. Missing or unreadable
files report a finding with no checks run. Exit 0 means all selected files
passed lint, exit 1 means the report contains findings, and exit 2 signals
invalid invocation or path selection. The command writes its report to stdout
and leaves files in place.

The report covers YAML mapping and duplicate keys, specification timestamps,
acceptance and acceptance evidence shape, evidence claim declarations, and
canonical formatting. Draft kind and ID/filename matching remain in 0235.
Semantic review, ontology and readiness have separate checks.

## Verification

Verify native invocation from outside the selected workspace, a clean
canonical file, a draft missing `updated_at`, duplicate keys, rejected
paths, and unchanged source files. Repeat on the original GitView node.
