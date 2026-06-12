# Public Proposal Doc Materialization Policy

## Context

`0099` added a local-only deterministic materializer that can write one reviewed
proposal source draft under:

```text
docs/archive/proposal_sources/
```

That source draft is still not a public proposal document. The next boundary is
the policy that decides whether a valid source materialization report may become
input to a future deterministic materializer for:

```text
docs/proposals/
```

## Motivation

The executor/materializer chain now has enough local evidence to move from
executor report to source draft, but publishing a public proposal document is a
stronger act than writing archival source material. It creates reviewable
proposal-lane surface area and consumes a stable proposal id. That step needs a
separate explicit policy before any writer exists.

## Proposal

Add `public_proposal_doc_materialization_policy` as a policy-only surface.

The policy accepts a request only when:

- the source artifact is
  `runs/local_operator_executor_proposal_materialization_report.json`;
- the source report is a valid
  `proposal_source_draft_materialization_report`;
- the source report status is `materialized_source_draft`;
- the source report records `source_draft_written: true`;
- the target is under `docs/proposals/`;
- the target filename matches the source draft filename;
- the target proposal id matches the source report proposal id;
- the target proposal id is still the current deterministic `make proposal-id`;
- explicit human authorization approves public proposal doc materialization.

## Authority Boundary

The source report and source draft remain input evidence. They do not become
proposal-lane authority by themselves.

The policy rejects:

- canonical spec mutation;
- patch application;
- gap closure;
- proposal status mutation;
- proposal registry mutation;
- executor invocation;
- static publication of local-only materialization state;
- source report as authority;
- direct source-draft-to-canonical apply.

## Non-Goals

- Writing `docs/proposals/...`.
- Updating proposal registries.
- Updating proposal status.
- Mutating canonical specs.
- Applying patches.
- Closing gaps.
- Running an executor.
- Adding SpecSpace or Platform behavior.

## Next Gap

```text
build_public_proposal_doc_materializer
```
