# Draft: native SpecGraph runtime

Review address `req.specgraph.native-runtime`; `review_pending`, `canonical: false`.
Source: [proposal 0231](../../proposals/0231_native_specgraph_runtime.md),
[intake](intake.json) and [source notes](source-notes.json).

The four draft obligations map to `tools/native_runtime.py::install`,
`extract_snapshot`, and `run`; `tests/test_native_runtime.py` checks the
destructive/error boundaries. The installed-runtime smoke must additionally
exercise two independent workspaces, existing supervisor behavior and receipt
provenance. This draft is not a canonical Requirement or an admission decision.
