# ``SpecGraph``

SpecGraph is a specification graph for evolving agent-facing contracts,
proposal traces, runtime evidence, and publication surfaces.

## Overview

SpecGraph keeps specification work auditable by connecting canonical specs,
proposal records, generated viewer surfaces, runtime evidence, and downstream
handoff artifacts.

The runtime implementation remains in the Python tooling under `tools/`. This
DocC catalog is the hosted technical documentation surface for operators and
downstream consumers.

The current public surfaces are:

- a GitHub Pages technical root;
- generated static artifacts for read-only consumers;
- proposal and runtime-evidence documentation under `docs/`;
- product landing content on the specgraph.tech static host.

Product landing and technical documentation are separate publication surfaces.
The specgraph.tech static host owns product-facing landing content. GitHub Pages
owns generated technical documentation and public artifact entrypoints.

## Source Documents

The canonical source files remain in the repository:

- `README.md`
- `CONTRIBUTING.md`
- `AGENTS.md`
- `docs/static_artifact_publish.md`
- `docs/proposals/*.md`
- `tools/README.md`

## Topics

### Start Here

- <doc:GettingStarted>
- <doc:ArtifactPublishing>
- <doc:ExecutorAdapterGateway>
- <doc:ProposalsAndRuntime>
