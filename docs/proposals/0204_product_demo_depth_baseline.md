# 0204 Product Demo Depth Baseline

## Status

Draft / product demo quality slice.

## Summary

Add a first-class depth baseline for UI-started product demo runs.

The product demo harness already proves that SpecSpace can collect a raw idea,
hand it off through Platform, and receive a SpecGraph candidate. That is not
enough for a convincing demo: a shallow candidate with zero actors, events,
workflow topology, or Idea Maturity can still look "generated" while failing to
show meaningful idea-to-spec understanding.

This proposal adds a deterministic report:

```text
runs/<demo-run>/product_demo_depth_report.json
```

The report checks whether a product demo run has enough event-storming and
candidate evidence to be presented as a meaningful story.

## Decision

SpecGraph should expose a `real-idea-smoke-depth-baseline` target for local
UI-started demo runs.

The target:

1. builds Idea Maturity for the selected real-idea smoke run directory;
2. builds `candidate_overview.json` for the same run directory;
3. emits `product_demo_depth_report.json`;
4. fails in strict mode when required depth evidence is missing.

The baseline requires:

- at least one actor;
- at least one command;
- at least one domain event;
- at least one policy;
- at least one constraint;
- at least one review-only workflow topology edge;
- at least one candidate node;
- requirements and acceptance criteria;
- `candidate_overview.json`;
- non-missing Idea Maturity.

## Authority Boundary

This slice is report-only.

It does not:

- execute prompt agents;
- infer product semantics with an LLM;
- mutate candidate artifacts outside the selected smoke run directory;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidates;
- create Git branches, commits, or pull requests;
- publish read models.

## Downstream Contract

SpecSpace can use the report as a Playwright demo assertion surface. A demo
run should not pass merely because an active candidate exists; it should pass
only when the published run artifacts contain enough event-storming structure,
candidate requirements, candidate overview, and Idea Maturity to explain the
product.

Platform remains downstream. It does not gate promotion on this report; the
report is a demo/readiness diagnostic for product presentation quality.

## Acceptance Criteria

- `make real-idea-smoke-depth-baseline` emits
  `product_demo_depth_report.json`.
- Strict mode fails for shallow demo runs.
- The report includes public-safe source refs and explicit read-only authority
  and privacy boundaries.
- SpecSpace product demo harness can publish and assert the report from the
  same workspace-scoped run directory it shows in the browser.
- Deprecated `tasks.md` remains untouched; durable tracking uses proposals,
  registries, roadmaps, and DocC.
