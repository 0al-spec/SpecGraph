# Inspect existing criterion evidence from the specification graph

On 23 November 2026, the operator asked to compare the graph queries available
across Ontology and SpecGraph on one ExamCalc scenario. After the agent proposed
a read-only criterion lookup in SpecGraph, the operator asked whether this was
a hypothetical tooling change, then instructed: “Ok, тогда проведи по процессу
самого SpecGraph”.

The bounded request is to prepare a reviewable SpecGraph proposal for retrieving
existing evidence by an exact criterion address. The proposed operation
should identify the passport, report and observation for the selected revision,
preserve admission separately and name any unavailable artifact.

The local observation is attributed to
`platform/20261123T140254Z-review-note-examcalc-criterion-answerability-probe.md`
in the 0AL inbox, SHA-256
`6c3ffed3cdbcfb211678e71286c6e609e6b204d68a9139b9928b9a0ed7afdc1e`.
Using SpecGraph `c802c181` with the historical ExamCalc journal, C2c returned
`checked / passed` for the late-return criterion. Changing the selected journal
locator to a missing file preserved the criterion and returned
`unavailable / unavailable`. Both report commands exited zero. These were
checks of the existing provider, with no new application execution. The underlying
local artifacts stay in ExamCalc.
