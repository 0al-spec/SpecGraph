# Exact Publication Trace Links

RFC 0226 resolution prerequisite for SG-SPEC-0071.
Profile: `specgraph.publication-exact-links/v1`.

Run `tools/publication_trace_links.py --repository-root . --revision <commit>`
with the repository Python environment. The required revision is resolved to a
full Git SHA. Regular Git blobs supply the existing publication spec, passport,
bindings and direct Python declarations. Measured code is never imported or
executed, and working-tree edits cannot replace source from the selected commit.

The `publication_trace_links` report preserves each declared link, exact
candidate locations, input digests, analyzer source digests and a deterministic
`content_sha256`. `REFERENCE_STATUS_SPEC` distinguishes `unsupported`,
`unavailable`, `unresolved`, `ambiguous`, `wrong_kind` and `resolved`, in that
order. Report status is `needs_review` when a link or inventory/mapping check
fails. Exit 0 means a diagnostic was computed, not readiness. Invalid required
inputs exit 1 with no JSON report.

Mapping completeness is owned by `POLICY_ATOM_BINDINGS_SPEC` and `ATOM_ROLES_SPEC`
in separate modules, with immutable `PolicyAtomBindingsFacts` and `AtomRolesFacts`.
The Git adapter prepares facts and serializes the returned outcomes. Focused
policy tables and adapter-integration tests preserve the original findings,
including duplicate, missing, extra, empty and overlapping-role cases.

The inventory joins atom `verifiable_by`, criterion/atom links, passport and
bound criteria, policy atom bindings and implementation declarations. Duplicate
IDs remain visible; empty/repeated atom channels and mismatched bound tests are
diagnostics. `atom_inventory.complete` concerns atom enumeration, while
`resolution_counts` counts links, not distinct covered atoms.

This bounded profile supports direct top-level Python functions and single-name
assignments, with `tests/**/test_*.py::test_*` for pytest channels. It does not
resolve imports, aliases, class methods, dynamic exports or parameter-instance
selectors. Declaration presence does not establish runtime value type,
Specification semantics or execution. Local IDs resolve exactly within one node
inventory. Range strings never expand to lists of scenarios.

`source_lifecycle` retains the selected YAML state. A formal run's review state
requires its own source-bound projection. The report retains
`execution: not_collected`, `fulfillment: not_evaluated`, `admission: not_evaluated`,
`readiness: not_evaluated` and `canonical_mutations_allowed: false`.

This is a prerequisite for EvidenceProvider and TraceSnapshot integration; no
atom SVC profile or trusted evidence admission is activated. The legacy metric
proxy and S/U remain unchanged.

See `docs/publication_trace_links.md` for the full contract and
`docs/evidence/0226_publication_link_resolution.json` for the pinned observation.
Synthetic Zeusus negative cases exercise the common ID resolver without claiming
whole-package validation or executed gameplay scenarios.
