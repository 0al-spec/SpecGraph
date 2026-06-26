# 0174 SpecSpace Repair Rerun Request Gate

## Status

Implemented

## Summary

SpecSpace can now store repair draft answers and a separate operator intent to
prepare a repair-draft rerun. Proposal `0174` lets SpecGraph consume that
SpecSpace-owned request artifact as a typed handoff before running the existing
proposal `0173` rerun chain.

This proposal adds:

```bash
make specspace-repair-rerun-request-gate
make product-workspace-requested-repair-draft-rerun
```

The gate reads:

```text
runs/idea_to_spec_repair_rerun_requests.json
runs/specspace_repair_draft_import_preview.json
runs/idea_to_spec_repair_session.json
```

and writes:

```text
runs/specspace_repair_rerun_request_gate.json
```

If the request is valid, `make product-workspace-requested-repair-draft-rerun`
then runs the existing review-only rerun builder and produces the standard
proposal `0173` outputs. If the request is invalid, strict mode stops before
rerun artifacts are written.

## Motivation

Proposal `0172` validates SpecSpace-owned repair drafts through an import
preview. Proposal `0173` turns a ready import preview into the standard
clarification answer, ontology decision, rerun input, preview, materialization,
and repair-session artifacts.

The missing boundary was the operator request itself. SpecSpace should be able
to say "the operator requested a repair rerun", but that request must not grant
SpecSpace authority to run Make targets, mutate SpecGraph artifacts, accept
ontology terms, or promote through Git Service. SpecGraph needs a small gate
that treats the request as evidence and intent, not as execution authority.

## Implementation

The implemented surface is:

- `tools/specspace_repair_rerun_request_gate.py`;
- `make specspace-repair-rerun-request-gate`;
- `make product-workspace-requested-repair-draft-rerun`;
- `runs/specspace_repair_rerun_request_gate.json`;
- focused regression coverage in
  `tests/test_specspace_repair_rerun_request_gate.py`;
- registry, roadmap, and DocC tracking for proposal `0174`.

The gate validates that the request artifact:

- uses artifact kind `specspace_idea_to_spec_repair_rerun_request_state`;
- is owned by `SpecSpace`;
- contains exactly one active `prepare_repair_draft_rerun` request for the
  selected workspace;
- keeps `may_execute_specgraph`, `may_run_make_target`, canonical mutation,
  ontology write, ontology term acceptance, branch, PR, and Git Service flags
  false;
- points to the selected import preview and repair-session inputs;
- matches the active candidate and repair-session identity.

The gate also validates that the import preview and repair-session journal are
ready and review-only.

## Contract

The gate report artifact kind is:

```text
specspace_repair_rerun_request_gate
```

The contract ref is:

```text
specgraph.idea-to-spec.specspace-repair-rerun-request-gate.v0.1
```

The default output is:

```text
runs/specspace_repair_rerun_request_gate.json
```

The report records:

- selected request id, workspace id, candidate id, and source artifact refs;
- source refs and digests for the SpecSpace request, import preview, and
  repair-session journal;
- recommended operator invocation;
- readiness status and blocking findings;
- an explicit read-only authority boundary.

Custom paths can be threaded through:

- `SPECSPACE_REPAIR_RERUN_REQUEST_STATE`;
- `SPECSPACE_REPAIR_RERUN_REQUEST_IMPORT_PREVIEW`;
- `SPECSPACE_REPAIR_RERUN_REQUEST_REPAIR_SESSION`;
- `SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID`;
- `SPECSPACE_REPAIR_RERUN_REQUEST_OUTPUT`.

## Authority Boundary

This proposal does not grant write or execution authority to SpecSpace.

It does not:

- execute prompt agents;
- trust `operator_command` from the request artifact;
- treat `may_run_make_target` as acceptable;
- apply SpecSpace drafts to source artifacts;
- apply answers or ontology decisions to source artifacts;
- mutate candidate source artifacts;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- mark candidate graphs accepted;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation authority.

The request remains an explicit operator intent. The operator or controlled
automation still owns the actual Make invocation.

## Acceptance Criteria

- A valid SpecSpace rerun request produces a ready
  `specspace_repair_rerun_request_gate` report.
- Requests claiming Make, SpecGraph execution, ontology, Git, or canonical
  mutation authority are rejected.
- Request import-preview and repair-session refs must match the selected
  SpecGraph inputs.
- `product-workspace-requested-repair-draft-rerun` refreshes the import preview,
  validates the request in strict mode, then runs the existing proposal `0173`
  rerun artifacts builder.
- On invalid request state, strict mode exits non-zero before rerun artifacts are
  written.
