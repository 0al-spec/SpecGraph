# Source: SpecAuthor Ontology Write Gate

Operator intent:

- new agent-generated specs/proposals should not enter the graph as free prose;
- generated artifacts must resolve active ontology/domain/context before graph
  persistence;
- accepted ontology entities are treated as canonical type symbols;
- unknown generated terms become ontology gaps, not silent vocabulary drift;
- strong claims carry F/G/R calibration and low-R claims do not become
  decisions;
- existing legacy specs remain report-only and are not bulk rewritten by this
  gate.

Bounded slice:

- add a deterministic SpecAuthor write gate over typed generated artifact JSON;
- compose with the existing ontology term binding gate;
- emit a `runs/` report and strict CLI exit for future authoring workflows;
- keep ontology package writes, lockfile writes, and canonical spec mutations
  disabled.
