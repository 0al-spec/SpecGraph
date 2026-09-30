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

Repository methodology is contract-first: preserve documented CLI behavior,
artifact shapes, viewer surfaces, and Makefile targets while extracting clearer
package boundaries behind stable façades. `AGENTS.md` and `CONTRIBUTING.md`
define the source-of-truth engineering method, code style, and review heuristics
for artifact readiness, producer lifecycle states, and gate behavior. New
supervisor package code under `src/specgraph/supervisor/` is guarded by the
`architecture-style` gate, while `architecture-metrics` provides report-only
code-shape and EO-inspired trend metrics. The long-running supervisor refactor
roadmap is tracked in `docs/supervisor_refactor_roadmap.md` as engineering
governance rather than a SpecGraph semantic specification.

The lifecycle pilot also has a versioned state-classification contract. Its PR
report checks import direction and cycles, identifies unclassified lifecycle
modules, and measures branch structure in declared state classifiers, including
`PredicateSpec` lambdas. The approval decision is an operator action; the
classifier projects resulting evidence into lifecycle state. Artifact
producers create the evidence, and publication validation has a separate
responsibility. Repeated selector matches are review candidates, not automatic
failures; the AST branch-point proxy is not C901 or Cognitive Complexity.

The `LAC007` rule fails the gate when it finds literal reads of
policy-protected raw context inputs by sibling state classifiers. It excludes
the input's classifier module, report adapters, and modules with other roles.
Classifier modules use the first positional `PredicateSpec` argument as the
context predicate, and function parameters annotated `LifecycleStateContext`
are also context roots. The gate follows simple local aliases and direct calls
to named helpers in the same module when a context name is passed positionally
or by keyword. Computed artifact names, indirect or cross-module helper calls,
starred arguments, attribute dispatch, returned callables, and nested lambda
bodies, including immediately invoked nested lambdas, are outside its syntax
scope. A finding blocks the gate for the declared input boundary, but does not
prove that the read duplicates the classifier's semantics.

The ontology decision-state counts pilot centralizes three exact counting
predicates in `ontology_decision_state_spec.py`, with no approval or import
authority. CLI behavior and report fields are preserved. The conventional
extraction control gives the same local complexity reduction; SpecificationCore
additionally gives the predicates explicit names. The source experiment at
`docs/experiments/ontology_decision_counts.md` records the behavior matrix,
pinned benchmark tools, absolute clone counts, and change-footprint limits.

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
- `docs/supervisor_refactor_roadmap.md`
- `docs/product_workspace_graph_versioning_roadmap.md`
- `docs/product_workspace_stable_mode_guide.md`
- `docs/proposals/*.md`
- `tools/README.md`

## Topics

### Start Here

- <doc:GettingStarted>
- <doc:ArtifactPublishing>
- <doc:ExecutorAdapterGateway>
- <doc:OntologyCAdapterReport>
- <doc:ProposalsAndRuntime>
- <doc:ImplementationContractPack>
- <doc:ProductWorkspacePilots>

### Proposed composition comparison

- <doc:CompositionObservation>
