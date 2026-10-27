# Installed SpecDraft runtime

Proposal 0230 packages the existing `read_notes`, `update_notes` and local
preview interfaces into an independently installed Python runtime. It is a
`synchronous_runtime_slice`, not canonical Requirement adoption. The source
proposal and draft criteria are in `docs/proposals/0230_portable_specdraft_runtime.md`
and `docs/reviews/0230_portable_specdraft/specdraft.md`.

## Consumer setup

On macOS/Linux with Python >=3.10, install the reviewed wheel into pipx:

```sh
pipx install /path/to/specgraph-0.2.0-py3-none-any.whl
specgraph --version
specgraph skill install --destination .codex/skills/specgraph-conversation-notes
specgraph notes read_notes --workspace conversation_memory/sketches/session
specgraph notes update_notes --workspace conversation_memory/sketches/session --input request.json
specgraph preview --workspace conversation_memory/sketches/session --port 0
```

`update_notes` creates the store before preview starts. Its request retains
the existing `expected_revision`, exact source quotation and changes array.
The bundled skill contains a self-contained `references/usage.md` with a
complete JSON example. Existing differing skill files are refused, matching
files are idempotent; agent settings are not edited automatically.

The installed runtime, static resources and exported skill come from one version.
Consumer notebooks and their revision history live in the explicitly chosen
project workspace; exclude private sketches in that project's `.gitignore`.
They are not installed data and do not follow the SpecGraph developer checkout.
Notes remain pre-canonical and the preview remains read-only on loopback.

The 0.2.0 candidate is not published on PyPI. Installation resolves Python
dependencies and the pinned SpycificationCore Git commit; this is not a fully
offline bundle. Full supervisor packaging, Docker and native Windows support
remain separate follow-ups.

## Distribution verification

Source tests characterize the preserved façades, but only an installed wheel
can demonstrate that the package contains its resources. Build through the source
distribution and run `tests/specdraft_distribution_smoke.py` in an external
consumer with isolated pipx. It checks installed module origins, separate-process
note recovery, stale-write rejection, HTTP asset bytes, live snapshot updates,
HTTP mutation refusal and local skill references. CI covers Python 3.10/3.14.
HTTP observation does not prove browser rendering, canonical acceptance or
trusted evidence admission.

Historical CN-CAPTURE review packets bind the original `pyproject.toml` and
runtime sources. Their test rehearsal reads a pinned Git snapshot rather than
today's build metadata, while changes within the selected review snapshot still
fail. Packaging does not rewrite prior reviews or their digests. The repository
skill remains a source-checkout guide; portable instructions ship separately.

The five draft obligations are SD-DIST-CLI, SD-DIST-RESOURCES, SD-DIST-DATA,
SD-DIST-SKILL and SD-DIST-COMPAT. Source capture and supervisor intake preserve
their origin. No model refinement or canonical publication is claimed.
