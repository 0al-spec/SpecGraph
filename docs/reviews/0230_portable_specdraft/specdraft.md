# Draft Requirement: portable SpecDraft runtime

Local review address: `req.specdraft.portable-runtime`.
State: `review_pending`; authority: proposal draft; `canonical: false`.
This address is not a canonical Requirement allocation or adoption receipt.

Source: [proposal 0230](../../proposals/0230_portable_specdraft_runtime.md),
[captured notes](source-notes.json) and [intake](intake.json).

The operator can use a fixed installed SpecDraft runtime in a consumer project
while the SpecGraph checkout is developed separately.

| Criterion / obligation | Required behavior | Verification binding |
| --- | --- | --- |
| SD-DIST-CLI | Installed `specgraph` dispatches version/notes/preview with no developer PYTHONPATH dependency. | `tests/specdraft_distribution_smoke.py::observe`; `tests/test_specdraft_distribution.py::test_cli_reuses_notes_protocol` |
| SD-DIST-RESOURCES | Wheel contains/serves matching HTML, JS, CSS and SVG and runtime packages. | `tests/specdraft_distribution_smoke.py::observe` |
| SD-DIST-DATA | New processes restore the saved revision and exact quotation; stale update preserves files. | `tests/specdraft_distribution_smoke.py::observe`; `tests/test_specdraft_distribution.py::test_cli_rejects_stale_revision` |
| SD-DIST-SKILL | Exported instructions/references are local to the destination; matching installs repeat safely and differing content survives refusal. | `tests/test_specdraft_distribution.py::test_skill_is_self_contained_and_idempotent`; `test_skill_conflict_preserves_existing_content` |
| SD-DIST-COMPAT | Existing note/store tests and installed HTTP probes preserve semantics and loopback/read-only preview. | `tests/test_conversation_notes.py`; `tests/test_specdraft_preview.py`; `tests/specdraft_distribution_smoke.py::observe` |

Installed smoke observations are synthetic technical evidence, not evidence
admitted against a canonical Requirement. A successful HTTP probe does not
establish browser rendering or human acceptance. Docker, automatic installation
into arbitrary projects and full supervisor packaging remain outside this draft.
