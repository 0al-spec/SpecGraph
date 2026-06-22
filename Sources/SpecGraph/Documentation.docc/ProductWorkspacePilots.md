# Product Workspace Pilots

SpecGraph can run in `product_workspace` mode when it should develop a user's
product graph instead of improving SpecGraph itself.

## First Pilot

The first real `product_idea_to_spec` pilot is Team Decision Log. It is a
small product domain, but it is not a mock or fixture: teams record decisions,
considered options, rationale, evidence, owners, review triggers,
consequences, and supersession or conflict relations.

The intended public route layout keeps one SpecSpace deployment with separate
workspaces:

```text
specgraph.space/
  -> SpecGraph bootstrap/showcase workspace

specgraph.space/team-decision-log
  -> Team Decision Log product_idea_to_spec pilot workspace
```

The Team Decision Log route should use product workspace artifacts and should
not expose SpecGraph bootstrap/self-evolution surfaces as product-domain state.

## Active Candidate Source

The next implementation slice should connect a validated Active Candidate
Source for Team Decision Log. Current public handoff artifacts can publish
`no_active_candidate` placeholders; those placeholders should become real
candidate materialization and promotion-gate artifacts only when the source is
an `active_candidate`, not fixture or demo leakage.

A valid pilot source should provide stable candidate and workspace identity,
active ontology/domain/context frame, consistent event-storming intake,
candidate graph, pre-SIB report, repair-loop state, materialization report, and
promotion gate refs.

Proposal `0155` implements the first deterministic local chain:

```bash
make team-decision-log-active-candidate
```

The target writes `runs/active_idea_to_spec_candidate.json` after building the
Team Decision Log event-storming intake, candidate graph, pre-SIB report,
repair-loop preview, candidate materialization report, and promotion gate.
Static artifact publishing keeps `no_active_candidate` placeholders unless that
active candidate source is ready.

## Authority Boundary

Team Decision Log remains non-canonical until a repository service accepts a
validated promotion request. The pilot must keep
`canonical_mutations_allowed: false` and route promotion only to
`product_spec_workspace` repository roles.

The product pilot must not:

- mutate canonical SpecGraph specs;
- write ontology packages directly;
- publish raw prompts, private operator notes, or local paths;
- use `specgraph_bootstrap` repository roles for product writes.

## Canonical Sources

The full planning contracts remain in repository Markdown:

- `docs/product_workspace_graph_versioning_roadmap.md`
- `docs/product_workspace_stable_mode_guide.md`
