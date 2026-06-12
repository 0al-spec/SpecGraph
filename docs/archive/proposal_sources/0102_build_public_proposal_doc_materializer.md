# Build Public Proposal Doc Materializer

## Context

`0101` defined `public_proposal_doc_materialization_policy`, which validates
whether a reviewed local source draft materialization report may become input to
a future `docs/proposals/...` materializer.

## Motivation

The executor/materializer chain can now produce reviewed proposal source drafts,
but the next step still needs deterministic write behavior before any broader
proposal-lane automation exists. The materializer must write exactly one public
proposal document and prove that no proposal registry, proposal status,
canonical spec, patch, gap, executor, or static publish authority was added.

## Proposal

Add a local-only materializer command:

```bash
make executor-public-proposal-doc-materialize
```

It consumes:

```text
runs/local_operator_executor_proposal_materialization_report.json
```

It validates the `public_proposal_doc_materialization_policy`, reads the source
draft named by the source report, writes exactly one matching
`docs/proposals/...` file, and records:

```text
runs/local_operator_executor_public_proposal_materialization_report.json
```

## Boundary

The materializer may only write the requested public proposal document. It must
not:

- update proposal runtime or promotion registries;
- update proposal status;
- mutate canonical specs;
- apply patches;
- close gaps;
- invoke an executor;
- publish local-only materialization state.

## Next Gap

```text
define_public_proposal_tracking_update_policy
```
