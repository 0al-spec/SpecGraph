# Observability identity declarations: proposed opt-in profile

## Status and source

Proposal 0047 **contract preparation only**; runtime realization is
`deferred_until_canonicalized`. This is the bounded response to
[ZST-04](reviews/zeusus_second_pass_feedback_triage_20261022.md), with
[0224](proposals/0224_compositional_test_context_and_evidence_binding.md)
remaining responsible for the proposed execution-context propagation seam.

The [source-intent and requirement packet](reviews/0047_authored_traceability/README.md)
now separates retained user intent, six proposed local requirements and seven
engineering choices. It links all sixteen acceptance cases, but remains review
preparation: neither the mediated intent capture nor the manual candidate is
canonical adoption. The initial Supervisor attempt failed before model execution;
the corrected retry with CLI 0.163.0 / Sol 6.1 Medium completed and remains
`review_pending`, with diagnostic findings retained. See the packet's separate
historical and retry evidence. SG-SPEC-0020 is boundary context,
not a canonical derivation of this profile's required fields.

The portable [profile definition](contracts/observability_identity_profile_v1.json)
is proposed data, not a loaded runtime policy or JSON Schema. Current
`tools/implementation_contract_pack.py` preserves additional observability fields
but **does not enforce `identity_profile`**. Adding the field today does not
activate validation. No CLI flag, validator, canonical node, product amendment,
test adapter, evidence admission or new approval boundary is introduced here.

```yaml
canonical_mutations_allowed: false
runtime_code_mutations_allowed: false
evidence_admission_allowed: false
```

## 1. Selection and compatibility

The proposed profile ID is `observability_identity_declarations_v1`. It augments
the existing `explicit_node_observability_v1` projection; it does not replace that
profile or change legacy CLI exit codes.

After implementation, an explicit authoring request may select this profile in
immutable request context, and a node declares the same ID at
`/specification/observability/identity_profile`. Selection is local to the target
node; there is no implicit parent, sibling, environment or workspace inheritance.
The selected definition's exact bytes are SHA-256 pinned in the request and the
derived diagnostic report. Changing those bytes invalidates an earlier report.

| Request selection | Node declaration | Proposed result |
| --- | --- | --- |
| Absent | Absent | Legacy behavior; identity check `not_requested`. |
| Absent | Known ID | Explicit node opt-in; validate and record the resolved definition digest. |
| Known ID | Same ID | Validate under the pinned request profile. |
| Known ID | Missing or different | `identity_profile_mismatch`; validate available obligations under the request profile but prevent successful contract handoff/review capture. |
| Unknown ID/version, invalid type, empty or null in either supplied selector | Any | Invalid selection; no fallback to legacy. |
| Known ID with unavailable or mismatched definition digest | Any | Invalid selection; no substitution of a newer definition. |

Presence of the key with null is not absence. IDs and attribute names are exact,
case-sensitive strings; no whitespace trimming, case folding or semantic alias
inference is applied. A node-only opt-in is useful for projection, but authoring
prevention requires retaining the request selection outside executor-editable
YAML. A retry or candidate that deletes its selector cannot clear that selection.
Legacy requests do not acquire a profile by heuristic inspection of field names.

## 2. Per-obligation declaration rule

Every obligation in the selected node must declare all five attribute names:

| Name | Intended binding; not verified by this check |
| --- | --- |
| `specification_id` | Specification addressed by the observation. |
| `rule_id` | Domain rule addressed by this obligation. |
| `component_id` | Product component emitting the observation. |
| `implementation_id` | Implementation element connected to the rule. |
| `scenario_id_if_tagged` | Conditional binding from an actually tagged test harness. |

The check compares the required set against **each** obligation's `attributes`.
A union across obligations, a root-level list, or one complete sibling cannot
cover a missing declaration. Additional attributes are allowed and preserved.
Existing duplicate-key, unique-ID, string-list, excluded-attribute and local
scenario-reference checks still apply. Invalid shapes are input errors, not
evidence of conformity. A required name also listed in `excluded_attributes` is
an explicit conflict; neither constraint silently wins.

`scenario_id_if_tagged` is always a required **declaration name** in this profile.
At execution, an actual scenario binding may be absent without a tagged harness;
no placeholder scenario ID is invented. An observation's declared
`scenario_ids` are specification/test references, not proof that a harness ran or
emitted a scenario binding.

The accepted alias map in v1 is empty. For example, `implementation_element_id`
does not satisfy `implementation_id`, and `specification_core_policy_id` does
not satisfy `rule_id`. These remain ordinary additional attributes; if the
canonical name is absent, the finding reports that missing canonical name.
There is no fuzzy "unknown alias" rejection of legitimate product attributes.
A later alias policy requires a new reviewed profile version; input is never
silently rewritten. This checks declarations only: actual values, stable
identity resolution, one-to-many bindings, provenance and runtime propagation
need the separate execution-binding contract.

## 3. Proposed example (not an activation instruction)

```yaml
specification:
  observability:
    identity_profile: observability_identity_declarations_v1
    non_interference: [observation_does_not_change_authoritative_state]
    excluded_attributes: [user_id]
    obligations:
      - id: ROUTE-OBS-001
        event: route_completed
        boundary: composition_return
        attributes:
          - specification_id
          - rule_id
          - component_id
          - implementation_id
          - scenario_id_if_tagged
          - operation_id
        expected_outcomes: [selected, no_path]
        scenario_ids: [ROUTE-SCENARIO-001]
```

The owning node must separately define `ROUTE-SCENARIO-001` and satisfy all other
contract-pack prerequisites. The example does not supply runtime field values.

## 4. Diagnostics and enforcement seam

The future shared, pure check receives parsed declarations, immutable request
selection and resolved profile definition. It performs no I/O or source mutation.
Adapters supply exact node bytes and source SHA-256. The same check is called
before authoring review capture and during explicit contract projection;
prompt guidance or a standalone report alone does not close ZST-04.

The proposed diagnostic projection has status `not_requested`, `invalid_input`,
`nonconformant` or `conformant`. It retains source spec ID, source path and exact
SHA-256; request selection/digest when present; effective profile ID/digest;
and attributed findings. Each missing-name finding carries:

```json
{
  "code": "missing_identity_attribute",
  "obligation_id": "ROUTE-OBS-001",
  "pointer": "/specification/observability/obligations/0/attributes",
  "required_attribute": "implementation_id"
}
```

Selection findings use `identity_profile_mismatch`, `unknown_identity_profile`,
`invalid_identity_profile` or `identity_profile_definition_unavailable`, with
the selector pointer and supplied/expected values where available; they are
node/request-level findings and do not invent an obligation ID. A digest
mismatch uses `identity_profile_definition_mismatch`. Existing input errors
remain attributed input errors; affected invalid obligations cannot be marked
conformant. For structurally valid input, collect all missing-name findings in
source obligation order, then required-name order from the definition.

Selection/input errors take status precedence over nonconformity. Valid
selection with any missing name is `nonconformant`; only a complete check with
no errors is `conformant`. `not_requested` makes no statement about identity.
Selection errors never downgrade to `not_requested`.

After integration, invalid selection/input follows existing CLI exit 1; valid
but nonconformant declarations follow blocked preview/exit 2. Conformant input
retains existing source gates/status checks and at best `review_required`/exit 0.
Authoring findings prevent successful review capture for the selected request;
they do not erase prior accepted material or authorize automatic repairs.
Current CLI output has no identity diagnostic projection; its exact serialization
and authoring adapter locations must be characterized in the implementation PR.

A retained diagnostic is current only for the exact source, profile definition
and request selection that produced it. Missing/stale reports or an unavailable
checker cannot be treated as a successful opt-in check. A conformant declaration
proves neither verified tests, runtime emission, canonical adoption nor mapping
completeness. No existing lifecycle or evidence gate is cleared by the result.

## 5. Acceptance matrix for the implementation PR

These are **future checks, not executed runtime tests** of this proposal.

| ID | Fixture / expected result |
| --- | --- |
| IDP-01 | Both selectors absent: existing legacy pack and exit behavior unchanged. |
| IDP-02 | Node-only opt-in with all five names in every obligation: conformant; additional attributes preserved. |
| IDP-03 | One sibling complete and another missing two names: two findings attributed to the incomplete obligation; no union-based pass. |
| IDP-04 | `implementation_element_id` replaces `implementation_id`: missing canonical-name finding, original list preserved. |
| IDP-05 | `specification_core_policy_id` replaces `rule_id`: missing rule declaration; policy identity not equated with domain-rule identity. |
| IDP-06 | `Implementation_id` or padded names replace a required name: exact-name failure. |
| IDP-07 | Unknown version, null, empty, list or mapping selector: invalid input, no legacy fallback. |
| IDP-08 | Request opts in; candidate removes/changes selector: mismatch; request profile retained across retry. |
| IDP-09 | Required attribute excluded: input conflict; no silent removal or grant. |
| IDP-10 | No tagged harness: declaration may conform, no runtime scenario ID or verified execution fabricated. |
| IDP-11 | Duplicate obligation IDs, duplicate attributes or malformed list: existing input checks preserved, no conformant diagnostic. |
| IDP-12 | Source/profile bytes or request selection change: previous diagnostic cannot satisfy the current check. |
| IDP-13 | Same candidate/request passed through authoring and projection: same identity findings and stable ordering. |
| IDP-14 | Identity conformant but source review pending: existing source blocker remains. |
| IDP-15 | Missing pinned profile, digest mismatch or checker failure: explicit error, no opt-in success. |
| IDP-16 | Additional alias-looking attribute alongside all required names: conformant; no speculative semantic rejection. |

## Next bounded slices

1. Review this contract; prepare/adopt the bounded canonical requirement through
   the existing SpecGraph workflow before runtime realization. No new proposal
   number or global identity requirement is needed.
2. Characterize the two consumer seams; implement the shared declaration check
   and its adapter wiring with the acceptance matrix. Publish exactly which
   boundaries enforce it, preserving legacy behavior and authority.
3. Separately define mapping scope/location and full/partial coverage for ZST-02.
   Compare declared rule ID sets; allow many-to-many mappings. Do not confuse
   identity-name conformity with coverage or evidence admission.
