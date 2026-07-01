# 0190 Real Idea Smoke Run Directory

Status: implemented.

## Problem

Real idea smoke runs require many output-path overrides when operators want to
avoid touching default `runs/*.json` artifacts. This made staged debugging
verbose and error-prone, especially when demonstrating a new idea from intake
through active candidate generation.

## Proposal

Add a run-dir convenience target:

```bash
make real-idea-smoke REAL_IDEA_SMOKE_RUN_DIR=runs/<id>
```

The target routes the existing real-intake active-candidate chain into the
selected run directory:

```text
real idea intake
  -> candidate source bridge
  -> event-storming seed
  -> product-workspace-active-candidate
  -> real_idea_smoke_summary
```

It also writes a compact summary artifact:

```text
runs/<id>/real_idea_smoke_summary.json
```

The summary is public-safe telemetry over the run artifacts. It does not include
raw idea text, and artifact `summary` blocks are copied through a safe-field
whitelist instead of being embedded wholesale.

The run directory and summary output must resolve inside the SpecGraph
repository. Repository-local absolute paths are normalized to repository-relative
artifact refs, external absolute paths are rejected, and ambient
active-candidate config variables are cleared for the smoke child invocation.

## Authority Boundary

This proposal only sequences existing review-only targets and summarizes their
outputs.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models.

## Acceptance Criteria

- `make real-idea-smoke REAL_IDEA_SMOKE_RUN_DIR=<dir>` writes all active-candidate
  outputs under `<dir>`.
- The target writes `<dir>/real_idea_smoke_summary.json`.
- Blocked intake runs still emit the smoke summary and preserve the failing exit
  status.
- Upstream artifact summary blocks are sanitized through a whitelist so raw idea
  text/debug payloads cannot contradict the privacy boundary.
- The summary reports the active candidate status, candidate id, route, artifact
  presence, and authority/privacy boundaries.
- Under-specified ideas remain blocked by the existing intake/bridge gates.
- Raw idea text remains outside the summary.

## Validation

- `tests/test_idea_intake_clarification_rerun.py`
- `tools/real_idea_smoke_summary.py`
