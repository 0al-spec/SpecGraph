# 0180 Idea Maturity Readiness Explainers

Status: implemented.

## Problem

Proposal `0178` added the Metrics RFC-aligned
`runs/idea_maturity_metrics_report.json`, and proposal `0179` made normal
product review targets emit that report by default. The report already exposes
counts, lifecycle state, findings, and validation evidence, but downstream
operators still need to infer why a candidate is not ready by reading several
separate artifacts.

That can make the Idea Maturity surface look like a score or dashboard rather
than a diagnostic layer. Product workspaces should explain readiness with typed
conditions: Pre-SIB findings, repair-session blockers, promotion-gate blockers,
stale refs, policy failures, and invariant failures.

## Proposal

Extend `idea_maturity_metrics_report` with a public-safe, read-only
`readiness_explainers` array.

Each explainer is compact and typed:

```json
{
  "id": "readiness-explainer.pre-sib-ontology-coverage-gap",
  "proposal_id": "0180",
  "kind": "pre_sib_finding",
  "source": "pre_sib",
  "severity": "high",
  "blocks": ["pre_sib_review", "candidate_approval"],
  "message": "Ontology coverage is incomplete for the candidate graph.",
  "next_action": "Inspect Pre-SIB coherence findings and close the referenced candidate graph condition.",
  "evidence_refs": [
    "runs/pre_sib_coherence_report.json#findings.pre-sib-ontology-coverage-gap"
  ],
  "evidence": {
    "finding_id": "pre_sib_ontology_coverage_gap",
    "review_state": "pre_sib_review_required"
  }
}
```

SpecGraph chooses the current lifecycle surface conservatively. Repaired
artifacts supersede their original counterparts when present, so an old Pre-SIB
blocker does not keep the maturity report blocked after the repaired Pre-SIB
surface is ready.

## Authority Boundary

This slice is observability-only:

- no Metrics schema ownership transfer from Metrics to SpecGraph;
- no prompt-agent execution;
- no candidate approval decision;
- no Git branch, commit, PR, merge, or read-model publication;
- no canonical spec mutation;
- no Ontology package writes;
- no ontology term acceptance;
- no SpecSpace mutation authority.

The explainers are not gates. They help SpecSpace and Platform explain existing
gate state, while the concrete repair, approval, promotion, and Git Service
artifacts remain authoritative.

## Acceptance Criteria

- `runs/idea_maturity_metrics_report.json` includes `readiness_explainers`.
- Pre-SIB findings become typed explainers with `next_action` and
  `evidence_refs`.
- Repair-session blockers explain candidate approval and Platform promotion
  blockers.
- Promotion-gate blockers explain Platform promotion blockers.
- Source-ref and invariant findings become stale-ref or invariant explainers.
- Repaired Pre-SIB artifacts supersede original Pre-SIB blockers when present.
- Metrics validation still passes for the report.

## Validation

- `tests/test_idea_maturity_metrics_report.py`
- `make python-quality`
- `make proposal-tracking-gate`
- `make docc-sync`
- `make publish-bundle`
