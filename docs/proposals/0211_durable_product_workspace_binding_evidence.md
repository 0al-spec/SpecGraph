# 0211 Durable Product Workspace Binding Evidence

## Status

Draft / bounded product workspace initialization evidence slice.

## Summary

Platform already records routing and execution fields for an initialized product
workspace, but downstream operations can still derive run directories, state
namespaces, or artifact routes from a workspace slug or shared local defaults.
SpecGraph's initialization receipt proves that a workspace layout is valid, but
it does not yet expose a compact digest-bound descriptor that Platform can pin
when it creates the durable cross-repository binding.

This slice adds that SpecGraph-owned evidence without making SpecGraph the owner
of Platform paths, SpecSpace state, deployment URLs, or Git execution.

## Decision

`runs/product_workspace_initialization.json` carries
`workspace_binding_evidence` with:

- stable workspace identity and product-workspace governance;
- workspace-relative layout refs for config, specs, proposals, runs, and
  supervisor state;
- the `specgraph.project.yaml` digest;
- repository/worktree identity hints that do not create a worktree;
- a stable evidence digest over the public-safe descriptor;
- closed privacy and authority boundaries.

Platform may validate and pin the whole initialization report plus this evidence
when it creates its durable workspace binding. SpecSpace may render a sanitized
projection but must not infer local paths from the route.

## Authority Boundary

This slice does not:

- select Platform artifact base URLs or local execution roots;
- allocate SpecSpace mutable-state storage;
- execute Platform, SpecGraph managed flows, or Git Service;
- create a repository, worktree, branch, commit, or pull request;
- mutate canonical specs;
- write Ontology packages or accept Ontology terms;
- publish raw root intent or local absolute paths.

## Acceptance Criteria

- Ready initialization reports include versioned workspace binding evidence.
- Evidence uses workspace-relative refs and a stable content digest.
- The project config digest is available on first initialization and idempotent
  reruns.
- Blocked initialization reports mark binding evidence blocked.
- No absolute input path or raw root intent appears in the evidence.
- Platform can pin the initialization report and evidence without re-deriving
  SpecGraph layout semantics.

