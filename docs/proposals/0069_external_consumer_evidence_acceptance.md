# External Consumer Evidence Acceptance

## Status

Draft proposal

## Source Material

This proposal captures the follow-up after the SpecGraph -> SpecSpace handoff
became ready and SpecSpace implemented the agent surface visibility panel.

Source draft:

- `docs/archive/proposal_sources/0069_external_consumer_evidence_acceptance.md`

## Context

The external consumer loop is now active:

```text
SpecGraph handoff packet
  -> SpecSpace implementation PR
  -> SpecSpace/Platform validation
  -> SpecGraph evidence acceptance
```

Proposals `0065`, `0066`, `0067`, and `0068` established the SpecSpace handoff
contract and stabilized the producer artifacts:

- `runs/supervisor_executor_adapter_index.json`
- `runs/agent_surface_index.json`
- `runs/agent_verification_gap_index.json`
- `runs/external_consumer_handoff_packets.json`

SpecSpace PR `0al-spec/SpecSpace#225` implemented the consumer surface for this
handoff and Platform published the resulting Timeweb deploy branch.

## Problem

SpecGraph has a report-only `evidence_contract` shape in the handoff packet, but
there is no derived surface that accepts downstream consumer implementation
evidence back into the graph.

Without that acceptance surface:

- SpecGraph can emit `ready_for_handoff`, but cannot show that the downstream
  consumer implemented it;
- SpecSpace CI and Platform publish runs remain outside the graph-visible loop;
- reviewers must manually connect PR links, smoke runs, and handoff ids;
- the handoff loop remains conceptually complete but operationally open.

## Goals

- Add a tracked external consumer evidence registry.
- Add a derived `runs/external_consumer_evidence_index.json`.
- Validate evidence entries against the current handoff packet evidence
  contract.
- Record SpecSpace PR #225 and Platform Timeweb publish evidence for
  `external_consumer_handoff::specspace`.
- Preserve the privacy boundary: no machine-local paths or raw logs in accepted
  evidence.
- Keep evidence acceptance report-only.

## Non-Goals

- Mutating SpecSpace.
- Re-running SpecSpace CI.
- Polling GitHub live from the builder.
- Implementing screenshots or browser verification capture.
- Closing Agent Passport verification gaps.
- Making evidence acceptance a canonical spec mutation.

## Runtime Realization

This proposal introduces:

```text
tools/external_consumer_evidence_registry.json
runs/external_consumer_evidence_index.json
make external-consumer-evidence
tools/supervisor.py --build-external-consumer-evidence
```

The registry stores operator-curated evidence records. The derived index
normalizes those records against the current handoff packet:

- handoff existence;
- handoff readiness;
- required evidence fields;
- accepted evidence kinds;
- result value;
- consumed producer artifacts;
- local-only path leakage.

## Acceptance Model

The index uses these acceptance statuses:

- `accepted`
- `blocked`
- `deferred`
- `contract_mismatch`
- `handoff_missing`

For the initial SpecSpace evidence, acceptance requires:

- `handoff_id: external_consumer_handoff::specspace`;
- `implementation_ref` pointing to
  `https://github.com/0al-spec/SpecSpace/pull/225`;
- consumed artifacts matching the stable producer artifact contract;
- evidence items for PR merge, SpecSpace CI/smoke, and Platform Timeweb publish;
- result `implemented`;
- no local-only paths.

## Initial Evidence

The first evidence record binds:

- SpecSpace PR: <https://github.com/0al-spec/SpecSpace/pull/225>
- SpecSpace CI run: <https://github.com/0al-spec/SpecSpace/actions/runs/27067315048>
- Platform Timeweb Publish run:
  <https://github.com/0al-spec/Platform/actions/runs/27067340747>

This proves consumer implementation and deploy publication for the first
SpecSpace agent/executor/passport visibility handoff without claiming that
Agent Passport verification gaps or runtime enforcement are closed.
