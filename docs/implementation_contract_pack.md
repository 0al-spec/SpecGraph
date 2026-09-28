# Implementation Contract Pack preview

Proposal `0047`, Slice 4 starts with the `explicit_node_observability_v1` profile.
It produces an `implementation_contract_pack_preview` from one explicitly
selected workspace node. It does not infer observation requirements from code.

```sh
make implementation-contract-pack PYTHON=.venv/bin/python \
  CONTRACT_WORKSPACE_ROOT=/path/to/product-workspace \
  CONTRACT_TARGET_SPEC=ZEU-SPEC-0016
```

Input: `specs/nodes/<id>.yaml`, with `specification.observability`:

```yaml
observability:
  non_interference:
  - observation_does_not_change_authoritative_state
  excluded_attributes: [user_id]
  obligations:
  - id: ROUTE-OBS-001
    event: route_completed
    boundary: composition_return
    attributes: [operation_id, sequence]
    expected_outcomes: [selected, no_path]
    scenario_ids: [ROUTE-SCENARIO-001]
```

Scenario IDs resolve against the same node's `specification.bdd_scenarios`.
The input node also supplies ID, kind, title, status, gate state and acceptance.
Product-defined additional contract fields are retained. Attribute exclusion
validation compares exact names; semantic categories still require review.

Output: `runs/implementation-contract-packs/<id>.json` inside the selected
workspace, written atomically. It pins source SHA-256 and retains the full
specification, acceptance, observability obligations and explicit parent references.
The `implementation_work_preview` uses existing Implementation Work field names
but is not inserted into its backlog. `evidence_status` is `not_evaluated`.

Exit codes:

- `0`: a valid `review_required` preview was written; this does not approve work.
- `2`: a `blocked` preview was written, for missing observability or a source
  status/gate unsuitable for handoff.
- `1`: input or output error; no new valid preview is claimed. A prior output
  may remain and must not be mistaken for this invocation's result.

Only `linked`, `reviewed`, or `frozen` source nodes with gate `none` avoid source
blockers. This is a conservative profile check, not independent review evidence.
Every preview sets `canonical_mutations_allowed: false` and
`runtime_code_mutations_allowed: false`. It does not resolve any review gate.
There is no automatic inheritance: the context reports `not_evaluated`.

For an implementation handoff, review the exact source and digest, bind obligation
IDs to implementation objects/call sites/scenario tests, and record actual checks
separately. Regenerate after source changes. Existing code is prior implementation;
the preview cannot make it retrospectively spec-generated or produce an evidence
receipt. Feature Passport remains independent and may consume provider-neutral
bindings through an adapter.

Validation: `make test-implementation-contract-pack PYTHON=.venv/bin/python`.
