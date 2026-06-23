# Product Workspace Pilots

SpecGraph can run in `product_workspace` mode when it should develop a user's
product graph instead of improving SpecGraph itself.

## First Pilot

The first real `product_idea_to_spec` pilot is Team Decision Log. It is a
small product domain, but it is not a mock or fixture: teams record decisions,
considered options, rationale, evidence, owners, review triggers,
consequences, and supersession or conflict relations.

Team Decision Log is product data, not a system-mode name. SpecGraph scripts,
Make targets, promotion gates, and SpecSpace consumers should stay generic for
`product_idea_to_spec`; a later product idea should be able to replace the
pilot payload without adding a product-specific flow.

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

Proposal `0155` implements the first deterministic local chain through the
generic product workspace target:

```bash
make product-workspace-active-candidate
```

The target writes `runs/active_idea_to_spec_candidate.json` after building the
Team Decision Log event-storming intake, candidate graph, pre-SIB report,
repair-loop preview, candidate materialization report, and promotion gate.
Static artifact publishing keeps `no_active_candidate` placeholders unless that
active candidate source is ready. Team Decision Log is the default fixture data
for the target, not a separate system-level flow.

## CLI Candidate Approval Flow

Proposal `0156` defines the next approval boundary for CLI and agent-mediated
product workspace operation. A ready candidate may be recommended by the agent,
but it should not move toward Git Service promotion without an explicit
operator decision.

The proposed approval surface is `runs/candidate_approval_decision.json`. It
should record public-safe refs, digests, decision state, and authority metadata
for the transition from `candidate_review_requested` to
`promotion_request_approved`. It must not create branches, commits, pull
requests, merges, read models, canonical spec mutations, or Ontology writes.

Proposal `0157` implements the first deterministic local approval artifact:

```bash
make candidate-approval-decision
```

The target writes `runs/candidate_approval_decision.json`. Its default decision
state is `needs_context`; approval requires an explicit
`CANDIDATE_APPROVAL_DECISION_STATE=approved` and ready upstream candidate/gate
artifacts.

## Review And Promotion Chain

SpecSpace can now route the product workspace separately from the SpecGraph
showcase and read the candidate graph, pre-SIB report, repair loop, promotion
gate, Platform promotion request, and Git Service execution report without
granting write authority.

Proposal `0158` adds the generic idea intake entry point. A
`user_idea_intake_source` now becomes `runs/idea_event_storming_seed.json` and
then the existing `runs/idea_event_storming_intake.json` through
`make generic-idea-intake`. Team Decision Log stays data; another product idea
can replace it at the intake-source boundary without new product-specific
scripts.

The next product workspace slice is generic candidate graph seed generation
from approved intake data. Git Service post-review status and read-model
publication remain service operations outside SpecSpace write authority.

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

## Current Execution Order

1. Generic candidate graph seed generation from approved intake data.
2. Extend Platform Git Service orchestration through review status and
   read-model publication.
3. Refine product workspace workflow lane metrics and blocker copy.
4. Refine ontology applicability and layer-aware review as compiler support
   matures.

## Canonical Sources

The full planning contracts remain in repository Markdown:

- `docs/product_workspace_graph_versioning_roadmap.md`
- `docs/product_workspace_stable_mode_guide.md`
