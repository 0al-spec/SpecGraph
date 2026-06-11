# Executor Report Consumption Policy

## Status

Draft proposal

## Source Material

This proposal defines the consumption policy for valid local executor reports
after `0091`.

Source draft:

- `docs/archive/proposal_sources/0092_executor_report_consumption_policy.md`

## Context

`0090` defined a generic executor/producer report contract. `0091` then proved
that a local executor can return a contract-valid
`runs/local_operator_executor_report.json` without canonical mutation or unsafe
payload persistence.

The next bounded step is not proposal generation. The next bounded step is to
define who may consume that report and what effects are allowed.

The central invariant is:

```text
executor report is admissible input/evidence, not authority
```

## Goals

- Add `executor_report_consumption_policy` to the supervisor executor adapter
  policy.
- Define allowed consumers:

  ```text
  supervisor_report_validator
  human_review_packet_builder
  proposal_draft_builder
  implementation_planning_surface
  external_consumer_handoff_builder
  ```

- Define allowed transformations:

  ```text
  report_to_review_packet
  report_to_proposal_draft_candidate
  report_to_implementation_planning_input
  report_to_evidence_reference
  report_to_external_consumer_handoff
  ```

- Define allowed effects:

  ```text
  review_packet_candidate
  proposal_draft_candidate
  implementation_planning_input
  evidence_reference
  external_consumer_handoff_packet
  ```

- Define forbidden effects:

  ```text
  canonical_spec_mutation
  patch_application
  gap_closure
  proposal_status_mutation
  static_publish_of_local_report
  canonical_fact_assertion
  ```

- Add validation helpers that reject unknown consumers, unknown
  transformations, forbidden effects, authority-boundary expansion, unsafe
  source report references, and invalid source reports.

## Non-Goals

- Running a new Codex/Pi/SpecHarvester task.
- Creating a proposal draft from a report.
- Applying a patch.
- Mutating canonical specs.
- Closing gaps from report findings.
- Changing proposal status from report findings.
- Publishing local executor reports to `specgraph.tech`.
- Adding SpecSpace UI or Platform deploy behavior.

## Policy Contract

The policy is report-only and consumption-only:

```json
{
  "executor_report_consumption_policy": {
    "artifact_kind": "executor_report_consumption_policy",
    "schema_version": 1,
    "source_report_artifact": "runs/local_operator_executor_report.json",
    "allowed_consumers": [
      "supervisor_report_validator",
      "human_review_packet_builder",
      "proposal_draft_builder",
      "implementation_planning_surface",
      "external_consumer_handoff_builder"
    ],
    "allowed_transformations": [
      "report_to_review_packet",
      "report_to_proposal_draft_candidate",
      "report_to_implementation_planning_input",
      "report_to_evidence_reference",
      "report_to_external_consumer_handoff"
    ],
    "allowed_effects": [
      "review_packet_candidate",
      "proposal_draft_candidate",
      "implementation_planning_input",
      "evidence_reference",
      "external_consumer_handoff_packet"
    ],
    "forbidden_effects": [
      "canonical_spec_mutation",
      "patch_application",
      "gap_closure",
      "proposal_status_mutation",
      "static_publish_of_local_report",
      "canonical_fact_assertion"
    ],
    "authority_boundary": {
      "report_is_authority": false,
      "human_or_supervisor_review_required": true,
      "canonical_mutations_allowed": false,
      "proposal_status_mutations_allowed": false,
      "gap_closure_allowed": false,
      "static_publish_of_local_report_allowed": false
    },
    "next_gap": "build_executor_report_review_packet"
  }
}
```

## Consumption Semantics

`valid` consumption means only that a consumer request may treat a valid local
report as input to a reviewable downstream artifact.

It does not mean:

- report findings are canonical facts;
- proposals are created automatically;
- patches are applied;
- gaps are closed;
- proposal lifecycle status changes;
- local-only reports become public static artifacts.

## Acceptance

This slice is complete when:

- proposal `0092` is tracked;
- the policy declares allowed consumers, transformations, effects, forbidden
  effects, and authority boundary;
- supervisor validators accept allowed review/proposal candidate consumption;
- supervisor validators reject unknown consumers and transformations;
- supervisor validators reject forbidden effects such as canonical mutation,
  patch application, and gap closure;
- supervisor validators reject authority-boundary expansion;
- supervisor validators reject invalid source reports;
- no new executor runtime is added;
- existing executor report smoke behavior remains unchanged;
- proposal gates, focused consumption tests, publish-bundle, and the full Python
  suite pass.
