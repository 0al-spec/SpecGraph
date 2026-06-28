# 0179 Product Flow Idea Maturity Artifacts

Status: implemented.

## Source Draft

The product idea-to-spec lane already has a Metrics RFC-aligned report producer
from proposal `0178`, and SpecSpace has a Product Workspace panel that can read
that report. The remaining gap is operational: after a normal product repair or
repaired promotion handoff run, the metrics report can still be missing unless
the operator invokes the metrics target separately.

Add lifecycle wiring so product review paths leave dashboard-ready maturity
artifacts by default:

- `make product-workspace-idea-maturity`
  - runs `make idea-maturity-metrics`;
  - runs `make idea-maturity-metrics-validate`.
- `make product-workspace-decision-backed-repair-chain`
  - keeps its existing repair chain;
  - ends by running `product-workspace-idea-maturity`.
- `make product-workspace-repaired-promotion-handoff`
  - keeps its repaired handoff builder;
  - ends by running `product-workspace-idea-maturity`.

Do not widen authority. This must not execute prompt agents, mutate candidate
or canonical spec artifacts, write Ontology packages, accept ontology terms,
approve candidates, create Git branches or pull requests, merge pull requests,
publish read models, or add SpecSpace write authority. Metrics remains the
owner of the RFC/schema/validator; SpecGraph only invokes the configured
Metrics CLI and publishes the resulting validation evidence.
