# SpecGraph

[![Coverage](https://img.shields.io/badge/coverage-pytest--cov-2ea44f)](https://pytest-cov.readthedocs.io/)
[![Ruff](https://img.shields.io/badge/lint-ruff-46aef7?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

**SpecGraph is the executable product ontology for Intent-Driven Development.**

It turns product intent into a structured, governed, and execution-ready graph that is:

- machine-verifiable
- human-readable
- semantically structured
- execution-connected

SpecGraph makes it possible to move from intent to implementation through specifications that remain understandable to humans, verifiable by machines, and traceable across the full software lifecycle.

## Native SpecGraph runtime

Proposal 0231 adds a separately installed snapshot of the full tracked SpecGraph
source and a Python environment. It uses a full Git SHA and a new destination:

```sh
# Select a trusted full commit SHA that includes tools/native_runtime.py.
REVISION=<full-commit-sha>
curl -fsSL "https://raw.githubusercontent.com/0al-spec/SpecGraph/$REVISION/tools/native_runtime.py" \
  -o /tmp/specgraph-native-install.py
python3 /tmp/specgraph-native-install.py install \
  --source https://github.com/0al-spec/SpecGraph.git \
  --revision "$REVISION" --destination <new-runtime-directory>
<new-runtime-directory>/specgraph-runtime --workspace <project-workspace> \
  init -- --project-id <project-id>
<new-runtime-directory>/specgraph-runtime --workspace <project-workspace> \
  supervisor -- --target-spec <spec-id> --dry-run
```

The selected revision must include the installer. Python 3.10+, Git and network
access for Python dependencies are required. The installer reports its Python
executable and version and rejects older interpreters before creating the
destination. Existing project history, agent
executor setup and workspace initialization are separate from installation.
See [proposal 0231](docs/proposals/0231_native_specgraph_runtime.md) for
supported operations and limitations.

## Installed SpecDraft

Proposal 0230 provides a separate Python runtime for notes and local preview.
Install a reviewed release wheel into pipx; the candidate is not yet published
on a package index:

```sh
pipx install /path/to/specgraph-0.2.0-py3-none-any.whl
specgraph --version
specgraph skill install --destination .codex/skills/specgraph-conversation-notes
specgraph notes read_notes --workspace conversation_memory/sketches/session
specgraph preview --workspace conversation_memory/sketches/session --port 0
```

The preview requires a workspace already created by `update_notes`. Runtime,
bundled resources and skill are versioned together; project notes remain in
the explicitly selected consumer workspace. Add private sketches to the consumer's
`.gitignore` when appropriate. The installed runtime does not depend on a developer
checkout and can remain fixed while SpecGraph is developed separately.

This slice supports macOS/Linux with Python >=3.10; it does not package the full
supervisor or provide native Windows support. See the
[distribution contract](docs/proposals/0230_portable_specdraft_runtime.md) and
[installed CLI/skill guide](src/specgraph/resources/skills/specgraph-conversation-notes/references/usage.md).

## Python Environment

SpecGraph tooling requires Python 3.10 or newer. CI currently runs Python 3.10,
and `pyproject.toml` declares `requires-python = ">=3.10"`.

On macOS, `python3` may still point to the Xcode/system Python 3.9 runtime. The
Makefile automatically prefers `.venv/bin/python` when that local virtual
environment exists, so the usual setup is:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

make test
make test-supervisor
```

For non-standard interpreter locations, pass `PYTHON=/path/to/python3.10` (or
newer) explicitly.

The Makefile runs `make check-python` before Python-backed targets and fails
fast with a clear message when the selected interpreter is too old.

## Model Layers

SpecGraph is built on four foundational layers:

- **Intent** as the source of truth
- **Specifications** as governed artifacts
- **Graph** as operational memory
- **Code** as the derived and executable layer

## Intent

In SpecGraph, intent is not a vague description.  
It is a precise, governed representation of what a product must be, how it must behave, and how its implementation can be validated.

Intent is defined by:

- completeness
- correctness
- contradiction resistance
- traceability
- bounded execution cost
- human legibility
