# Source: Idea Maturity Readiness Explainers

This source proposal tracks implementation proposal `0180`.

Idea Maturity should not become a single quality score. It should explain why a
candidate is or is not ready by listing the concrete lifecycle conditions that
remain: Pre-SIB findings, unresolved repair-session blockers, promotion-gate
blockers, stale refs, policy failures, and invariant failures.

The implementation adds a typed `readiness_explainers` array to the existing
`idea_maturity_metrics_report`. The array is public-safe, read-only, and
report-only. It does not change Metrics ownership of the RFC/schema/validator,
does not mutate candidate or canonical artifacts, does not write Ontology
packages, does not accept ontology terms, and does not run Git Service
promotion.
