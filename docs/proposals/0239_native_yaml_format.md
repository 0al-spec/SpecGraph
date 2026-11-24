# Format selected specification YAML through the native runtime

RFC SG-RFC-0239

The [GitView observation](../archive/proposal_sources/0239_native_yaml_format.md)
identified the correction step missing from [0237](0237_native_spec_yaml_lint.md).
SG-SPEC-0009 anchors explicit operator selection.

```sh
specgraph-runtime --workspace /path/to/project format -- \
  specs/nodes/PRODUCT-SPEC-0001.yaml
```

Select one or more workspace-relative files under `specs/nodes/` or
`docs/drafts/`, using the same path restrictions as native lint.
Read and canonicalize the complete selected set before writing. A path,
read or parse failure exits 2 before changes. The formatter uses the existing
canonicalization rules, including timestamp normalization and comment removal.

Replace each changed file through a temporary file in the same directory,
preserving its permission mode. Recheck its path and original bytes before
replacement. A subsequent filesystem failure exits 1 with the completed
results, the failed path, and `not_attempted` paths. Publication is per file.

The `specgraph_yaml_format` schema 1 report names the selected files and gives
their `changed`, `unchanged` or `failed` status and SHA-256 before and after.
Exit 0 means formatting completed. Repeating the operation on canonical files
returns `unchanged`. Repeated file arguments select one file once.

When native lint finds noncanonical formatting, its JSON includes a
`format_command` argument list. Its first argument is `specgraph-runtime`;
an installation outside PATH can substitute its absolute launcher path.

Verify the lint, format, lint cycle on a captured current GitView Activity
file. Record whether it needed correction initially. Where it is already
canonical, add whitespace to a second copy to exercise correction. Check
that repeated formatting is idempotent and malformed selected input prevents
writes to the other files.
