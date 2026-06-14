# Ontologyc Adapter Report

SpecGraph consumes `ontologyc validate-specgraph` output through an
`ontologyc_adapter_report` boundary. The report is evidence for read-only
ontology import surfaces, not canonical graph authority.

## Contract

The repository contract source is:

```text
docs/ontologyc_adapter_report_contract.md
```

The machine-readable policy is:

```text
tools/ontology_import_policy.json
```

The accepted adapter report records source/version/digest identity for the
Ontology package, points to `concept-refs.yaml`, `ontology.lock.yaml`, and
`ontology-gaps.yaml`, and preserves `canonical_mutations_allowed: false`.

`ontology.lock.yaml` from the adapter output is a non-canonical report artifact.
SpecGraph still needs proposal review before any accepted import lock, semantic
binding, or canonical node mutation exists.

## Smoke Surface

`tools/ontology_imports.py --write` validates the checked-in report fixture and
emits:

```text
runs/ontologyc_adapter_report_smoke.json
```

The smoke requires matching package id, namespace, version, source URI, source
ref, and digest. The digest must match the normalized IR `sourceDigest`.

The smoke also verifies that output refs resolve under the fixture directory and
that report counts match the resolved concept refs and ontology gaps.

## Semantic Review Surfaces

The same ontology import command consumes:

```text
tools/ontology_semantic_control_policy.json
```

and emits deterministic review-only semantic artifacts under `runs/`:

```text
runs/ontology_semantic_context_pack.json
runs/ontology_prompt_invocation_index.json
runs/ontology_semantic_lint_input.json
runs/ontology_semantic_lint_report.json
runs/ontology_delta_candidate_review_packet.json
runs/ontology_semantic_review_surface.json
runs/ontology_supervisor_semantic_gate.json
runs/ontology_delta_draft_intake.json
runs/ontology_closed_loop_evidence.json
runs/ontology_review_dashboard.json
runs/ontology_owner_decision_report.json
runs/ontology_decision_import_preview.json
runs/ontology_semantic_lint_smoke.json
```

`runs/ontology_semantic_lint_input.json` is the source-backed lint input. It
extracts declared ontology terms from tracked proposal or supervisor output
sources, records source digests and spans, and stays read-only.

`runs/ontology_prompt_invocation_index.json` is the typed prompt-agent context boundary.
It carries package refs, accepted terms, aliases, deprecated terms,
relation conflicts, unresolved gaps, governance evidence, prompt input/output
refs, and failure modes as context-only grounding. It does not execute prompt
agents, persist raw prompts or responses, write Ontology packages, update
lockfiles, or mutate canonical specs.

`runs/ontology_semantic_review_surface.json` is the SpecSpace/supervisor-facing
surface for grounding summary, blocking findings, review-required findings,
delta candidates, and non-mutating review actions. It is derived evidence only;
it is not canonical Ontology authority.

`runs/ontology_supervisor_semantic_gate.json` is the supervisor-facing gate
artifact derived from the review surface. It maps blocking ontology findings to
`blocked`, review-required findings or candidates to `review_pending`, and clean
surfaces to `clear`. It carries required human action and evidence refs without
executing prompt agents or mutating canonical specs.

Use `tools/supervisor.py --build-ontology-supervisor-semantic-gate` when the
operator wants the supervisor entrypoint to refresh these surfaces and print the
compact gate report without starting an ordinary targeted refinement run.

Ordinary targeted supervisor runs read the existing semantic gate artifact as
soft run evidence. A `clear` gate leaves approval behavior unchanged. A
`blocked` or `review_pending` gate does not stop executor invocation, but it
suppresses silent `--auto-approve` canonical sync and routes the candidate
through the existing `review_pending` path with preserved ontology evidence.
Missing or malformed gate artifacts are recorded as unavailable evidence rather
than hard runtime blockers in this MVP wiring slice.

`runs/ontology_delta_draft_intake.json` is the Ontology owner handoff surface
for candidate draft requests. It preserves candidate payloads and required human
action, but a blocked semantic gate keeps requests in
`blocked_by_semantic_gate`; it does not write Ontology packages or accept
candidate terms.

`runs/ontology_closed_loop_evidence.json` is the SpecGraph-facing evidence
surface for those intake requests. It reports blocked or pending owner-decision
states and preserves empty Ontology decision refs until real owner evidence is
available; it does not close semantic gates or mutate canonical specs.

`runs/ontology_review_dashboard.json` is the richer SpecGraph/SpecSpace
projection over semantic review, gate, intake, and closed-loop evidence. It is
read-only review material and does not import owner decisions.

`runs/ontology_owner_decision_report.json` carries typed Ontology owner decision
evidence only when those decisions match pending closed-loop owner-review
evidence. Blocked, stale, or unmatched owner-decision inputs remain ignored
diagnostics instead of becoming importable evidence.

`runs/ontology_decision_import_preview.json` joins the review dashboard with the
owner decision report. It shows no-decision, blocked, ready, rejected,
clarification, or unmatched preview states, preserves ignored owner-decision
diagnostics, and does not apply imports or mutate canonical specs.

## Boundary

The adapter report must not:

- update canonical `ontology.lock.yaml`;
- mutate `specs/nodes/*.yaml`;
- close ontology gaps automatically;
- execute prompt agents;
- redefine Ontology package schema inside SpecGraph.
