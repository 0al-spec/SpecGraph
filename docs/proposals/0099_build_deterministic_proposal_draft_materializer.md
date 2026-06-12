# Build Deterministic Proposal Draft Materializer

## Status

Draft proposal

## Source Material

This proposal implements the local materializer boundary defined in `0098`.

Source draft:

- `docs/archive/proposal_sources/0099_build_deterministic_proposal_draft_materializer.md`

## Context

`0098` added `deterministic_proposal_draft_materialization_policy`, which
validates whether a ready local promotion packet may become input to a future
deterministic source draft materializer. That policy intentionally did not
write proposal source files.

The next bounded step is to implement only that materializer, while preserving
the same authority boundary: executor output and promotion packets remain
review inputs, not canonical or proposal-lane authority.

## Goals

- Add a local-only materialization report:

  ```text
  runs/local_operator_executor_proposal_materialization_report.json
  ```

- Add a local operator command:

  ```bash
  make executor-proposal-source-materialize
  ```

- Consume:

  ```text
  runs/local_operator_executor_proposal_promotion_packet.json
  ```

- Validate the request with:

  ```text
  deterministic_proposal_draft_materialization_policy
  ```

- Write exactly one source draft under:

  ```text
  docs/archive/proposal_sources/
  ```

- Record source packet validation, request validation, target path, checks, and
  mutation guard status in the local-only report.

## Non-Goals

- Writing `docs/proposals/...`.
- Updating `tools/proposal_promotion_registry.json`.
- Updating `tools/proposal_runtime_registry.json` from generated output.
- Changing proposal status.
- Mutating canonical specs.
- Applying patches.
- Closing gaps.
- Invoking an executor.
- Publishing local materialization state.
- Adding SpecSpace or Platform behavior.

## Runtime Contract

The materializer writes a report shaped around:

```json
{
  "artifact_kind": "proposal_source_draft_materialization_report",
  "schema_version": 1,
  "local_only": true,
  "source_promotion_packet_artifact": "runs/local_operator_executor_proposal_promotion_packet.json",
  "summary": {
    "status": "materialized_source_draft",
    "proposal_id": "0100",
    "target_path": "docs/archive/proposal_sources/0100_executor_report_proposal_draft_materialization.md",
    "source_draft_written": true,
    "next_gap": "define_public_proposal_doc_materialization_policy"
  }
}
```

The shown `proposal_id` is illustrative. The validator still checks the live
deterministic proposal allocator.

## Checks

The report records:

```text
source_promotion_packet_present
source_promotion_packet_valid
materialization_policy_allows_source_draft
target_path_available
source_draft_written
mutation_scope_limited
materialization_report_contract_valid
```

## Safety Boundary

The materializer is allowed to create only the requested source draft path. It
uses a git status mutation guard and fails closed when the changed path set
cannot be proven. The local report does not persist raw logs, raw executor
responses, absolute executable paths, secrets, or public static publish state.

## Acceptance

This slice is complete when:

- `make executor-proposal-source-materialize` exists;
- a valid promotion packet can produce a local source draft and local report;
- missing or invalid promotion packets are blocked;
- existing targets are blocked;
- mutation guard failures are blocked;
- report validation rejects local paths and unsafe payloads;
- local materialization report is excluded from public static bundle;
- proposal `0099` is tracked in promotion/runtime registries;
- focused tests, proposal gates, `publish-bundle`, `docc-sync`, and full Python
  suite pass.

## Next Gap

```text
define_public_proposal_doc_materialization_policy
```
