# Mechanically checked specification authoring

SG-RFC-0233 records the agreed direction to connect specification authoring to
existing Ontology, native BDD, Supervisor and SIB checks. It is a draft proposal
with `deferred_until_canonicalized` runtime posture, not a new active gate.

The authoring loop is obligation -> ontology binding -> acceptance/check ->
scoped diagnostic -> bounded refinement. A large specification may remain a
leaf. Concrete missing obligations and structural complexity are reported
separately; a criterion count alone does not prove independent concerns.

## Existing mechanisms and limits

SG-SPEC-0015 supplies delegation semantics; SG-SPEC-0021 supplies the derived
metric boundary; SG-SPEC-0049 diagnoses harmful fragmentation; SG-SPEC-0070
validates native scenario declarations. A valid declaration is not execution.
Ontology package validation and explicit-reference lookup do not establish
complete specification-instance coverage. An authoring profile must explicitly
select applicable obligations instead of requiring every optional relation.

SVC retains the full declared in-scope denominator. Missing inputs and
unsupported checks remain visible; legacy weighted coverage and SIB_FULL
expected-test proxies are not silently promoted to atom-level verification.
Graph coupling distinguishes edge roles and architectural boundaries.

## Pilot and durable return path

The planned pilot uses SG-SPEC-0072 outcome precedence at
`c31b1a332ed1df2fba7d10ad0a215f230d61b97e`, from the open ontology stack when
this proposal was prepared. It is not a canonical main node at the preparation
baseline `ee8cb62f5acca18e884dcc19cf306ca6708ab7c5`.

Source excerpts, draft obligations and an existing intent/proposal registration
retain the conversation as shared project memory. The return handle is
`proposal::0233-mechanical-specification-authoring`; its existing canonical
target is SG-SPEC-0015. Review the pilot inventory/profile, then prepare one
derived report and negative sensitivity probes. At preparation those probes had
not run. The first post-merge baseline is now recorded separately below.
The authored proposal's empty `proposal_queue_status` keeps it outside derived
queue retirement; `proposal_authority_state` records its independent review state.

Registration does not execute an agent or approve canonical publication:
`runtime_profile_activation_allowed: false` and
`evidence_admission_allowed: false` remain in effect for this proposal.

## Source documents

The local scenario pilot follows the operator's lightweight authoring direction: a
SG72-MIXED model beside the spec, using a real ontologyc-generated TypeScript
SDK and explicit checks of one scenario. Its source map keeps one acceptance
criterion partially modelled and three unmodelled. Generated artifacts are
scratch outputs, and the local draft is not a new global ontology selection.
See `specs/models/SG-SPEC-0072/README.md` for the on-demand command and
`docs/reviews/0233_mechanical_specification_authoring/local-model-pilot/README.md`
for the experiment. Compilation, bounded execution and source completeness
remain separate observations; no new readiness or merge gate is activated.
The real local run passed SDK generation, TypeScript compilation, instance checks
and one production execution retaining both diagnostics. Its 43 focused tests
include 13 real-tool integrations and negative construction/linkage/source
probes. This is local evidence; the integration cases explicitly skip in Python
CI without configured ontologyc and TypeScript paths. The curated observation
records tested hashes and the compiler's unverified source provenance.

The Ontology 0.3.0 follow-up removes the local package's unused policy and state
machine declarations. A separate observation records 54 passing focused tests
without skips, including the real-tool negative cases, and unchanged core IR.
The old compiler rejects the minimal package; the new compiler runs the same
scenario successfully. Both compatibility CI jobs check the minimal package's
structure. They do not execute the full scenario. Original 0.2.0 evidence remains
historical; adapter complexity and partial acceptance coverage remain open.
See `docs/reviews/0233_mechanical_specification_authoring/local-model-pilot/ontology-030-observation.json`.

A second example, `SG72-UNSUPPORTED-CLOSURE`, uses the same runner, SDK and
instance consumer. Production capture verifies the selected package's source
and IR. Its required dependency closure check reports `unavailable`, so the
context also reports `unavailable`. The local draft adds one relation from
that closure check to the member check for the same package. Both examples
exercise part of acceptance criterion 2 (zero-based). The source maps retain
all four criteria and their coverage status.

The third example, `SG72-PINNED-FOUNDATION`, supplies the single-import foundation
profile to production capture. A typed model checks the verified member and
closure, and the report identifies the `sg:ValueObject` declaration in the
pinned upstream vocabulary. A paired CLI regression recompiles the member
with `sg:Typo` and checks for an invalid result at the same source pointer.

A pilot in a different spec, `SG-SPEC-0071`, binds the `PB-PAYLOAD` criterion
to its existing test. The core ontology supplies the requirement, criterion,
evidence and test relations. Two local types describe a manifest entry and a
payload observation. Matching and mismatching digests both type-check; the
production bundle verifier rejects the changed response bytes. The source map,
diagram and replay commands are in `specs/models/SG-SPEC-0071/README.md`.

The first executed baseline selects merged revision `a980ba6f` and confirms
the historical pilot spec bytes are unchanged. Existing acceptance-shape checks
detect evidence-only deletion but miss paired criterion/evidence deletion;
native BDD detects a dangling scenario reference. Textual outcome contradictions
remain outside those declaration checks. Supervisor reports no graph-health
signals for the leaf; this does not establish authoring completeness. Twenty
existing context tests passed with fixture compiler inputs. Required ontology
bindings, stale authoring evidence and a frozen outcome inventory remain the
next profile work. No readiness gate or canonical status changed.

- `docs/reviews/0233_mechanical_specification_authoring/baseline/README.md`
- `docs/proposals/0233_mechanical_specification_authoring.md`
- `docs/proposals/0233_mechanical_specification_authoring.intent.yaml`
- `docs/archive/proposal_sources/0233_mechanical_specification_authoring.md`
- `docs/reviews/0233_mechanical_specification_authoring/README.md`
