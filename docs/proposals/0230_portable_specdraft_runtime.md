# Portable SpecDraft runtime

## Status

Synchronous bounded implementation slice for review. Runtime version: 0.2.0.
This packages existing note/preview behavior and a matched skill. Full
supervisor packaging, Docker, native Windows, automatic upgrades and package
index/release publication are separate work.

## Intent and source

Use SpecGraph in consumer projects while its developer checkout changes.
The operator selected an independently installed Python package containing CLI,
resources and coherent skill, and requested the SpecGraph pipeline itself.

- [Attributed source draft](../archive/proposal_sources/0230_portable_specdraft_runtime.md)
- [Tool-captured notes](../reviews/0230_portable_specdraft/source-notes.json)
- [Intake](../reviews/0230_portable_specdraft/intake.json)
- [Requirement draft and test bindings](../reviews/0230_portable_specdraft/specdraft.md)
- [Declared proposal obligations](0230_portable_specdraft_runtime.intent.yaml)
- [Installed artifact observation](../reviews/0230_portable_specdraft/verification.json)
- [Pipeline lineage observation](../reviews/0230_portable_specdraft/pipeline.json)

The source note is pre-canonical. SG-SPEC-0007 governs mediation provenance,
SG-SPEC-0050/0051 govern pre-spec meanings and promotion. Frozen governance
nodes do not acquire Python packaging details. Proposal 0228 owns live preview;
this slice preserves its implementation and prepares installation independently.

## External contract

The built wheel exposes:

```sh
specgraph --version
specgraph notes read_notes --workspace <project-sketch>
specgraph notes update_notes --workspace <project-sketch> --input <request.json>
specgraph preview --workspace <project-sketch> --port 0
specgraph skill install --destination <project-skill-directory>
```

The existing source CLIs and their note JSON/exit-code contracts remain intact.
The wheel includes `conversation_notes`, `specdraft_preview`, both source CLI
modules, static HTML/JS/CSS/SVG and a self-contained skill/reference. Notebook
data, graph sources and generated runs are not installation payloads.

The consumer explicitly selects its own workspace. Notes and history survive
runtime replacement; installed files never become the note store. The local
preview retains loopback/read-only behavior. The skill targets the installed
command and contains no developer-checkout paths. Existing differing skill
content is refused rather than overwritten; matching content is idempotent.

The first supported hosts are macOS and Linux with Python >=3.10. NotesStore's
Unix locks are retained. The pinned SpycificationCore dependency remains commit
`6113d773e78cb94c4eb0ce31e8439877fef45494`. Installation currently needs access
to Python package dependencies and that Git source; a fully offline bundle is
not claimed. Use the built wheel's actual path with pipx; do not assume this
candidate is published on PyPI.

## Verification

Five explicit obligations bind to the draft criteria and tests. Focused tests
exercise forwarding, persistence, stale revisions, skill conflict preservation
and resource-local references. The distribution smoke builds/installs the actual
artifact and runs from a synthetic consumer with PYTHONPATH/PYTHONHOME removed:

- installed module origins lie outside the developer checkout;
- fresh CLI processes restore notes/citations and reject stale writes unchanged;
- preview serves bytes matching the wheel, observes a saved update and rejects
  HTTP mutation;
- exported skill references resolve entirely inside its destination;
- runtime version and pinned dependency source match the installed distribution.

CI runs that smoke on Python 3.10/3.14 and retains the sdist, wheel and observed
receipt. Local evidence is reported separately after a real pipx installation.
HTTP observation does not establish browser rendering, canonical acceptance,
trusted receipt admission or full supervisor portability.

## Pipeline boundary

The existing notes API captured the operator quotation; the supervisor's intake
helper recorded a `captured` user intent. Proposal, draft Requirement, code and
tests keep that lineage explicit. The existing proposal-lane synchronization
helper created `proposal::0230` in `under_review`, linked to that captured intent;
the pre-spec index reports it as a queryable downstream proposal. No model refinement or frozen-spec mutation
is needed for this implementation-agnostic boundary. Running intake/index/gates
is not reported as an executor/model run or canonical materialization.
