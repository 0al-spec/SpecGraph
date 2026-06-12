# Build Public Proposal Doc Materializer

## Status

Draft proposal

## Source Material

This proposal implements the local public proposal document materializer
boundary defined in `0101`.

Source draft:

- `docs/archive/proposal_sources/0102_build_public_proposal_doc_materializer.md`

## Context

`0101` added `public_proposal_doc_materialization_policy`, which validates
whether a reviewed source materialization report may become input to a future
public proposal document materializer. That policy intentionally did not write
`docs/proposals/...`.

The next bounded step is to implement only that materializer, while preserving
the same authority boundary: source reports and source drafts remain review
inputs, not proposal registry/status/canonical authority.

## Goals

- Add a local-only materialization report:

  ```text
  runs/local_operator_executor_public_proposal_materialization_report.json
  ```

- Add a local operator command:

  ```bash
  make executor-public-proposal-doc-materialize
  ```

- Consume:

  ```text
  runs/local_operator_executor_proposal_materialization_report.json
  ```

- Validate the request with:

  ```text
  public_proposal_doc_materialization_policy
  ```

- Read the reviewed source draft from:

  ```text
  docs/archive/proposal_sources/
  ```

- Write exactly one matching public proposal document under:

  ```text
  docs/proposals/
  ```

- Record source report validation, request validation, source/target paths,
  checks, and mutation guard status in the local-only report.

## Non-Goals

- Updating `tools/proposal_promotion_registry.json`.
- Updating `tools/proposal_runtime_registry.json` from generated output.
- Changing proposal status.
- Mutating canonical specs.
- Applying patches.
- Closing gaps.
- Running an executor.
- Publishing local materialization state.
- Adding SpecSpace or Platform behavior.

## Runtime Contract

The materializer writes a report shaped around:

```json
{
  "artifact_kind": "public_proposal_doc_materialization_report",
  "schema_version": 1,
  "local_only": true,
  "source_materialization_report_artifact": "runs/local_operator_executor_proposal_materialization_report.json",
  "summary": {
    "status": "materialized_public_proposal_doc",
    "proposal_id": "0103",
    "source_path": "docs/archive/proposal_sources/0103_executor_report_proposal_draft_materialization.md",
    "target_path": "docs/proposals/0103_executor_report_proposal_draft_materialization.md",
    "public_proposal_doc_written": true,
    "next_gap": "define_public_proposal_tracking_update_policy"
  }
}
```

The shown `proposal_id` is illustrative. The validator still checks the live
deterministic proposal allocator through the `0101` policy.

## Checks

The report records:

```text
source_materialization_report_present
source_materialization_report_valid
public_proposal_doc_policy_allows_materialization
source_draft_available
source_draft_safe_for_public_materialization
target_path_available
public_proposal_doc_written
mutation_scope_limited
public_proposal_doc_materialization_report_contract_valid
```

## Safety Boundary

The materializer is allowed to create only the requested `docs/proposals/...`
path. It uses a git status mutation guard and fails closed when the changed
path set cannot be proven. The local report does not persist source draft text,
raw logs, raw executor responses, absolute executable paths, secrets, or public
static publish state.

## Acceptance

This slice is complete when:

- `make executor-public-proposal-doc-materialize` exists;
- a valid source materialization report can produce a public proposal doc and
  local report;
- missing or invalid source reports are blocked;
- missing source drafts are blocked;
- existing targets are blocked;
- source draft privacy failures are blocked;
- mutation guard failures are blocked;
- report validation rejects local paths and unsafe payloads;
- local public proposal materialization report is excluded from public static
  bundle;
- proposal `0102` is tracked in promotion/runtime registries;
- focused tests, proposal gates, `publish-bundle`, `docc-sync`, and full Python
  suite pass.

## Next Gap

```text
define_public_proposal_tracking_update_policy
```
