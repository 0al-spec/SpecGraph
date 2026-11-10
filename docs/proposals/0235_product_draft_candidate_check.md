# Check a product draft in place

RFC SG-RFC-0235

Product authors need to check a draft before it enters the governed graph.
The GitView pilot used a disposable workspace to place a copy under
`specs/nodes/`, the documented input of `next-move --target-spec`.
[Source observation](../archive/proposal_sources/0235_product_draft_candidate_check.md)
and [draft obligations](0235_product_draft_candidate_check.intent.yaml) record the request.
This is a bounded tooling proposal adjacent to [0227](0227_git_isolated_local_workspace.md)
and [0233](0233_mechanical_specification_authoring.md). SG-SPEC-0009 supplies
the graph anchor for explicit operator selection.

## Interface

```sh
specgraph-runtime --workspace /path/to/project next-move \
  --candidate-file docs/drafts/PRODUCT-SPEC-0001.yaml
```

Select one regular YAML file under `docs/drafts/` using a workspace-relative
path. Reject absolute paths, traversal, symlinks, invalid YAML (including
duplicate keys), documents without `kind: spec`, and IDs that differ from
the filename stem. The CLI accepts either `--candidate-file` or
`--target-spec`. The native launcher binds the workspace for the operation.

On success, emit `product_workspace_candidate_check` schema 1 to stdout.
The report identifies the path, ID and SHA-256 of the bytes actually parsed.
It records authored status values and offers candidate review as the next
action. The report carries `canonical: false`. It covers source selection
and document identity. Ontology, dependencies, maturity and acceptance
criteria require their own checks.

Candidate mode reads one document and writes no files. The canonical
advisor retains its existing discovery, ranking and persisted report.
Rejected inputs exit nonzero without a successful report.

## Verification

Exercise the native entry point on the GitView draft in its original
workspace. Compare the reported hash to the actual draft and check that
the ordinary advisor still rejects that ID. In a synthetic workspace,
verify that changed bytes produce a new hash and that invalid identity,
malformed YAML and path escapes are rejected.
