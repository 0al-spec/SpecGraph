# Executor diagnostic defect: graph-tracked repair

Defect `EXECUTOR-DIAGNOSTIC-20261029` is a confirmed false-warning case, linked
through the existing intent and proposal lanes. Its source is
[the operator direction and run observation](source.md); the bounded record is
[defect.json](defect.json). This is an engineering defect observation, not a new
canonical graph kind or acceptance of earlier ontology candidates.

## Lifecycle and trace

The retained operator packet supplies the native `user_intent` and
`operator_request`. A native proposal-lane node links those handles to
SG-SPEC-0003, the defect artifact, implementation and regression evidence.
The actual record paths and overlay checks are listed in `verification.json`.
The graph is the work return path; the earlier `.0al` entry is coordination.

The defect is confirmed by the original run and a minimal classifier probe.
The proposed repair separates runtime diagnostics from agent/tool transcript
data while preserving authoritative final-message parsing and actual failures.
Verification must exercise both absence of false findings and preservation of
true state, usage, transport and timeout diagnostics. Native error events on
stdout must not disappear merely because ordinary tool events are excluded.

The repair remains prepared/review-pending until merged. Passing regressions
do not themselves close the defect, approve previous candidates or authenticate
the original observation. An actual merged revision and its review/check status
are the closure evidence. The raw historical run stays unchanged; any later
reclassification must identify its new classifier and source scope as a replay.

## Operational boundary

Graph nodes are materialized through existing Supervisor builders; its overlay
commands validate graph visibility. The stored operator packet is a routing
declaration, not a claim that a nested spec-refinement executor ran for this
bug fix. The delegated agent handled source diagnosis and code/tests; the main
agent owns defect registration, integration and publication. No canonical spec
was rewritten to justify an existing parser-contract repair.
