# Zeusus second-pass feedback triage — 2026-10-22

Status: **triaged; follow-ups proposed, no runtime fix or product adoption**.
SpecGraph source pin: `c46d58ad7918e992d77a854302338afc0aa72221`.

The four collector entries are owned by `specgraph`. Their bytes match all four
SHA-256 receipts. The [curated evidence](zeusus_second_pass_feedback_triage_20261022.json)
records source locators/digests, direct candidate observations and proposal links.
Raw Zeusus specs, executor transcripts and machine-local paths are not published.
Local source locators identify retained inputs; they are not remote delivery receipts.

## Disposition and proposal routing

Priorities order follow-up work; they do not assert production incidents.

| Record | Classification | Primary proposal | Related proposal | Disposition |
| --- | --- | --- | --- | --- |
| ZST-01 | P3 executor instruction/output-format friction; protocol rejection worked | [0056 Executor Adapter Gateway](../proposals/0056_supervisor_executor_adapter_gateway.md) | [0048 Stalled Run Salvage](../proposals/0048_supervisor_stalled_run_salvage_protocol.md), preservation only | Keep strict final-message authority; clarify plain-line instructions. A typed result envelope requires a separate compatibility decision. This run was not a stall. |
| ZST-02 | P2 recurring authoring validation gap: reference validity is weaker than complete coverage | [0047 Evidence-Backed Build Protocol](../proposals/0047_evidence_backed_build_protocol.md), explicit contract pack follow-up | [0226 Evidence Providers](../proposals/0226_traceability_evidence_providers_and_svc.md), [0223 BDD](../proposals/0223_bdd_scenario_contract_and_gherkin_exchange.md) | Propose declared rule scope and completeness checks, alongside exact mapping-reference checks. Product-side correction does not close the engine gap. |
| ZST-03 | P3 operator seed-filter error, corrected before refinement; continuation tooling gap remains | [0054 Product Workspace Initialization](../proposals/0054_product_workspace_initialization.md), related follow-up scope | [0193 Session Continuation](../proposals/0193_real_idea_smoke_session_continuation.md), precedent only | Preserve source provenance and unknown semantic fields. Native continuation of an unadopted YAML candidate is not covered by those existing flows; it needs a bounded contract before implementation. |
| ZST-04 | P2 recurring authoring validation gap: required identity context and spelling drift | [0047 Evidence-Backed Build Protocol](../proposals/0047_evidence_backed_build_protocol.md), explicit contract pack follow-up | [0224 Test Context](../proposals/0224_compositional_test_context_and_evidence_binding.md) | Propose an explicitly selected, versioned identity profile checked on every obligation before review capture. SDK/runtime propagation is a separate 0224 concern. |

These are extensions or related follow-ups, not claims that the proposals already
implement the requested prevention. No new proposal ID or canonical node is allocated.

## Verified observations

### ZST-01 — Markdown markers

Run `20261022T201612Z-ZEU-SPEC-0020-91f5daa9` returned child exit 0 but ended with
`**RUN_OUTCOME: done**` and `**BLOCKER: none**`. The run report contains both
missing-marker errors, `outcome: blocked`, `completion_status: failed` and
`accepted_canonical_diff: false`. All eight general validator results were true;
they did not override the independent protocol failure.

`tools/supervisor.py` already tells the executor to end with two machine-readable
lines. `parse_executor_protocol` matches plain marker lines in the final response.
The existing final-message boundary must remain authoritative: stripping Markdown
or borrowing a success marker from the diagnostic transcript is not an approved fix.

Small follow-up: state explicitly that the final marker lines have no bold,
backticks or other decoration, then characterize bold rejection, plain-line
acceptance and transcript decoys. Fence/duplicate/trailing-prose behavior needs
an explicit compatibility decision before strengthening parser semantics.
Keep the rejected candidate and failure record; a retry does not rewrite history.

### ZST-02 — Mapping validity and coverage

Run `20261022T202045Z-ZEU-SPEC-0023-3a0616f9` had eight true validator results and
`done / review_pending`. Direct set comparison on its saved candidate found
15 declared rules, 10 mapped rule IDs and exactly these omissions:

- `DUR-BOUNDS`
- `DUR-FORMAT`
- `DUR-IDENTITY`
- `DUR-MIGRATION`
- `DUR-RESET`

Follow-up `20261022T202429Z-ZEU-SPEC-0023-f364250a` maps all 15, but its identity
attributes still have the separate ZST-04 gaps. This recurs from collector entry
`20261021T214838Z-review-note-history-mappings-need-resolved-reference-validation.md`:
the earlier case concerned unresolved/custom references; this case additionally
demonstrates missing coverage. They belong to one follow-up family, with distinct checks.

The actual parser is `tools/implementation_contract_pack.py`, proposal 0047,
profile `explicit_node_observability_v1`. `validate_observability` validates
obligation IDs, string-list shapes, excluded attributes and local scenario refs.
It does not inspect `materialization.rule_to_obligation_mapping` or enumerate the
expected rule set. This file is byte-identical at `92ee71cf` and `c46d58ad`.
The eight supervisor validators are not eight independent mapping/identity checks.

Proposed follow-up: declare the expected local rule scope and whether coverage
is full or partial. Resolve exact rule/obligation/scenario IDs and declared
SpecificationCore target strings; report missing, unknown and duplicate mappings
separately. Many rules may share an obligation, and one rule may have several
observations. For full coverage compare ID sets, not row counts. Root composition
delegation must not invent local copies of participant rules. Authored target
existence remains different from a resolved source-code declaration or execution.
The packet also uses two explicit mapping locations: `materialization` for most
participants and `composition` for economy 0021. A selected mapping contract
must declare its location rather than recursively treating every similarly named
field as authoritative or assuming one path covers the entire packet.

0226's implemented resolver/provider cohort is SG-SPEC-0071 publication only.
Its synthetic mapping tests did not activate a generic Zeusus authoring gate.
Reuse suitable resolver concepts without presenting that cohort as this fix.

### ZST-03 — Provenance preservation

The collector attributes the initial omission to the operator's manual whitelist,
not to a SpecGraph transform. The restored seed lineage includes `provenance`
for applicable source nodes, records correction commit `e20bdc0`, and the product
packet reports semantic-field equality before refinement. No final input
provenance loss or product adoption is claimed. Sources that never had provenance
must not receive fabricated history just to satisfy a field checklist.

Native candidate continuation remains a design follow-up. Proposal 0054 covers
workspace initialization; 0193 covers intake-session continuation, not resuming
a review-pending legacy node. Neither proves an existing candidate-reset API.
A bounded continuation contract should retain source digest, provenance, semantic
content and historical lifecycle; distinguish a fresh unadopted authoring copy
from the pending candidate; and list the operational fields it may reset.
Dropping `gate_state` is not permission to approve or overwrite the original.
Unknown source fields require classification rather than silent whitelist loss.

### ZST-04 — Per-obligation identity

Candidate `b7f23348` uses `implementation_element_id` on all eight application
obligations despite the requested `implementation_id`. Candidate `f364250a`
has complete rule coverage but all six durability obligations still lack at
least one requested common field; some use `specification_core_policy_id`
without `rule_id`. These are directly observed spelling/membership facts,
not a claim that the identifiers are semantically unrelated.

The requested Zeusus contract declares these attributes on each obligation:
`specification_id`, `rule_id`, `component_id`, `implementation_id`,
`scenario_id_if_tagged`. The current parser only checks that `attributes` is a
string list; it has no required-set or alias contract.

Proposed follow-up: select the identity profile explicitly in authoring context
and make the same deterministic check available before review capture and at
contract projection. Preserve legacy profile behavior unless a stricter profile
is selected. Missing names and unrecognized aliases must produce attributed
findings, not silent rewrites. Do not impose this pilot's spelling on every
project or invent runtime field values. The scenario attribute describes a
conditional harness binding: an actual scenario ID is absent without a tagged
harness. Attribute declarations do not prove propagation or executed observations.

## Current product packet and evidence limits

Read-only inspection of the final six saved snapshots confirms 100 BDD scenarios
and 37 obligations; all 37 declare the requested five attribute names. Participant
mapping covers 49/49 local rules, including 15/15 durability rules. Root 0018
delegates participant rules. These checks do not execute any BDD/game tests or
prove semantic sufficiency. The product verification report additionally records
preserved gameplay/acceptance/provenance, which is retained as its reported result.

All final candidates remain `review_pending`; no aggregate adoption receipt,
runtime implementation permission, trusted evidence or `tests_verified` result
is created by this triage. The latest local workaround is not evidence that
SpecGraph's general validators acquired these checks.

## Recommended implementation order

1. **0047 identity-profile preparation:** define the opt-in authored-observation
   contract and attributed missing/alias findings; use the saved 0020/0023 gaps
   to derive small public synthetic regressions. No product-private YAML copies.
2. **0047 complete mapping scope:** add expected-rule scope plus exact reference
   and coverage checks. Include a resolvable-but-incomplete 10/15 case, a full
   15/15 case and delegated/root scope. Reference resolution alone is insufficient.
3. **0056 format friction:** clarify plain final markers and characterize the
   authority boundary. Consider a typed backend result only as a separate contract.
4. **0054 continuation preparation:** specify provenance-preserving fresh copies
   and pending-candidate retention before introducing a normalization command.

The first two checks must actually be wired into the selected authoring/review
boundary; a new report or standalone validator alone must not be described as
preventing green-but-incomplete candidates. No additional model execution,
gameplay changes, metric thresholds or blanket acceptance gates are introduced here.
