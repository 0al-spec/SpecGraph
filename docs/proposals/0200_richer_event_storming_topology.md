# 0200 Richer Event-Storming Topology

Status: implemented.

## Problem

Proposal `0191` made real idea candidate graphs connected by adding conservative
`decomposes_to` edges from `candidate-spec.product-boundary` to each generated
candidate node. That removed false topology-empty Pre-SIB failures, but the
candidate graph still did not expose useful event-storming workflow semantics.

Operators need to see how actors, commands, events, policies, and constraints
relate without treating those derived relations as canonical specs or global
ontology facts.

## Proposal

Extend the ontology-bound candidate graph seed with additive workflow topology
edges derived from the event-storming intake:

```text
actor -> command
command -> event
event -> policy
constraint -> command
policy -> command
```

The concrete candidate graph still uses candidate node endpoints so the existing
candidate graph validator and Pre-SIB report remain compatible. Event-storming
refs are carried as edge evidence:

```json
{
  "relation": "actor_triggers_command",
  "source_event_refs": ["actor.support-agent", "command.record-triage-note"],
  "actor_ref": "actor.support-agent",
  "command_ref": "command.record-triage-note"
}
```

The existing `decomposes_to` edges remain as structural fallback. New relation
counts appear in `source_generation.summary.topology_relation_counts`.

The seed generation report also includes a non-blocking `topology_quality`
section. It surfaces review warnings for incomplete event-storming topology,
such as actors without commands, commands without events, events without
commands, or constraints/policies without targets. These warnings do not block
candidate readiness; they are diagnostic signals for downstream overview,
repair, and maturity surfaces.

## Authority Boundary

This slice does not:

- execute prompt agents;
- infer missing domain semantics with an LLM;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept Ontology terms;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models.

Workflow edges are review-only evidence derived from already approved
event-storming intake.

## Acceptance Criteria

- Existing `decomposes_to` topology remains present for Pre-SIB connectivity.
- Command nodes gain actor-trigger and command-event relation evidence when the
  intake provides `actor_refs` and `produces_event_refs`.
- Policy and constraint nodes gain relation evidence when the intake provides
  `trigger_event_refs` or `command_refs`.
- Candidate graph validation still requires known candidate node endpoints.
- Relation counts are summarized for downstream overview/UI surfaces.
- Incomplete event-storming topology is reported as non-blocking
  `topology_quality` warnings.
- No raw idea text or private operator notes are published through topology
  edges.

## Validation

- `tests/test_ontology_bound_candidate_graph_seed.py`
- `tests/test_candidate_spec_graph.py`
- `tests/test_pre_sib_coherence_report.py`
- `make proposal-tracking-gate`
- `make docc-sync`
