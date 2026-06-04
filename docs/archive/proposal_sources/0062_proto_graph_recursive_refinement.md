# Proto-Graph Recursive Refinement Source Draft

## Operator Intent

SpecGraph should support two complementary modes:

- recursive, fractal refinement of specifications node-by-node and
  layer-by-layer;
- fast generation of a reviewable proto-graph from a user's first raw intent.

The proto-graph should be a semi-empty but legible product graph. For example,
when a user asks for a calculator, SpecGraph should quickly seed placeholder
nodes with clear names and shallow descriptions derived from a draft product
ontology. The graph should then become richer over time as more LLM compute,
agent work, user attention, and new user intent are applied.

## Motivation

The current SpecGraph workflow is strong at bounded refinement once a target
node exists. It is weaker at the earliest product moment, where a user expects
the system to turn a small idea into a visible map of the future product before
all details are known.

The Ontology layer was separated partly to support this: ontology should provide
the semantic basis for quick scaffold generation without forcing mature
canonical specs too early.

## Desired Shape

```text
raw user intent
  -> ontology seed / product concept basis
  -> proto-graph placeholder nodes
  -> recursive refinement queue
  -> node-by-node enrichment
  -> reviewed proposals/specs/evidence
```

## Boundary

Proto-graph nodes are not mature canonical specifications. They are reviewable
seed material. They may suggest future specs, proposals, questions, assumptions,
and refinement work, but they should not silently mutate canonical graph truth.

## Example

```text
Intent: "Build a GUI calculator for iOS/macOS."

Fast proto-graph:
  - Calculator Product
  - Numeric Input
  - Operation Model
  - Result Display
  - Platform UI Shell
  - Error Handling
  - Testing and Verification
  - Runtime Packaging

Each node starts shallow. Later passes refine one node at a time and attach
details, links, evidence, acceptance criteria, and implementation work.
```

## Open Questions

- Which artifact should represent proto-graph previews?
- How much ontology induction is allowed before human review?
- How should compute and attention budgets be represented?
- When does a placeholder become eligible for canonical promotion?
- How should SpecSpace show proto-graph material without confusing it with
  accepted specs?
