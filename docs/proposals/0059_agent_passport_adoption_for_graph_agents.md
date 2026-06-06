# Agent Passport Adoption for Graph Agents

RFC: SG-RFC-0059
Version: 0.1.0

## Status

Draft proposal

Decision scope: adoption path and graph integration contract.

This document does not define Agent Passport itself, signing, verification,
sandboxing, SpecSpace UI, hosted registry behavior, or runtime enforcement.

## Source Material

This proposal captures the operator request to adopt Agent Passport for the
agents that already exist around SpecGraph and SpecSpace.

Source draft:

- `docs/archive/proposal_sources/0059_agent_passport_adoption_for_graph_agents.md`

External Agent Passport authority:

- Agent Passport repository: <https://github.com/0al-spec/agent-passport>
- Agent Passport RFC:
  <https://github.com/0al-spec/agent-passport/blob/12b1fbd9cabd91adaea1989e3958f5cf90e2e449/drafts/agent-passport.md>
- RFC status at referenced commit: Experimental RFC.

## Summary

SpecGraph and SpecSpace already expose graph-facing agent surfaces:
supervisors, executor adapters, nested CLI agents, and operator assistant flows.
These surfaces need stable identity, capability, security-policy, integrity, and
verification semantics.

This proposal adopts Agent Passport as the external authority for graph-facing
agent declarations. SpecGraph does not duplicate the Agent Passport RFC.
SpecGraph stores graph-specific references, derived indexes, verification
summaries, and gaps. SpecSpace consumes safe derived surfaces instead of parsing
raw executor logs, prompts, private passport material, or local-only files.

## Motivation

SpecGraph is moving toward a multi-service AI software factory:

```text
SpecSpace operator surface
  -> SpecGraph supervisor
  -> executor adapter / nested agent
  -> product workspace
  -> evidence and implementation artifacts
```

Today those actors are identified by local implementation names, CLI commands,
model settings, prompt profiles, or UI surfaces. That is useful operationally,
but it is not a durable identity/capability/security contract.

Without an explicit Agent Passport boundary:

- executor adapters can accumulate ad hoc capability fields;
- SpecSpace can display agent state without a stable identity contract;
- product-workspace agents can run with unclear authority;
- prompt profiles, model choices, and CLI backends can be mistaken for agent
  identity;
- review and evidence surfaces cannot say which agent was authorized to do what;
- future Platform orchestration has no shared declaration to inspect.

The first need is not immediate runtime enforcement. The first need is a stable,
external, verifiable declaration model that SpecGraph can reference, index, and
project.

## Architecture Decision

SpecGraph and SpecSpace must not define ad hoc agent identity, capability, or
authority fields as canonical truth.

Agent Passport is adopted as the canonical external authority for:

- agent identity;
- declared capabilities;
- resource requirements;
- security policies;
- integrity metadata;
- issuer and signature metadata;
- verification and lifecycle state.

SpecGraph may store references, indexes, snapshots, verification states, and
graph-specific usage relationships derived from Agent Passports. It may cache
derived fields for search and inspection, but Agent Passport remains the source
of truth.

This prevents authority drift such as:

```text
Agent Passport says: executor has read-only filesystem authority.
SpecGraph says: executor can write arbitrary workspace files.
SpecSpace says: operator assistant can hand off unrestricted shell work.
```

Such drift is incompatible with the zero-trust agent model.

## Goals

- Adopt the external Agent Passport RFC as the authority for agent identity,
  capability, security policy, integrity, and verification concepts.
- Define which SpecGraph/SpecSpace actors count as graph agents for future
  passporting.
- Define a minimal graph-side `GraphAgentPassportRef` binding instead of copying
  passports into SpecGraph.
- Define read-only derived indexes for known passports, verification gaps, and
  agent surfaces.
- Preserve the distinction between declared authority, verified identity,
  runtime enforcement, and observed execution.
- Link supervisor executor adapter backends to declared agent identities.
- Consume executor-side Agent Passport CLI discovery diagnostics from `0056`
  instead of adding a second direct validator discovery path.
- Keep SpecSpace as a consumer of safe derived surfaces, not raw local executor
  logs or private passport material.

## Non-Goals

This proposal does not define:

- the Agent Passport schema;
- passport signing;
- passport verification implementation;
- key management;
- sandboxing;
- seccomp, chroot, or capability enforcement;
- `zeroald` or `agentifyd` runtime behavior;
- supervisor executor enforcement;
- SpecSpace UI implementation;
- hosted passport registry behavior;
- policy engine implementation;
- replacement of supervisor deterministic validation or human review;
- proof that an LLM-backed agent will obey instructions.

## Canonical Authority

The Agent Passport RFC is the source of truth for:

- passport document shape;
- agent identity concepts;
- capability declarations;
- resource requirements;
- security policies;
- agent integrity;
- signature and verification;
- issuing authority;
- lifecycle and revocation;
- trust-chain terminology.

SpecGraph is responsible for:

- referencing known agent passport sources;
- linking passports to graph-agent roles;
- building read-only derived indexes and summaries;
- surfacing missing, stale, unverifiable, or unenforceable passports as gaps;
- preserving local-only secrecy boundaries;
- refusing to treat a passport declaration as runtime success.

## Graph Agent Surfaces

The following graph-facing surfaces eventually require Agent Passports:

| Surface | Description | Passport Priority |
| --- | --- | --- |
| `specgraph.supervisor` | Bounded graph work planner and coordinator | required |
| `specgraph.supervisor.executor_adapter` | Adapter that launches nested executors | required |
| `specgraph.executor.codex` | Codex-style CLI executor launched from supervisor | required |
| `specgraph.executor.copilot` | Future Copilot-style executor | required before production |
| `specgraph.executor.claude` | Future Claude-style executor | required before production |
| `specgraph.executor.gemini` | Future Gemini-style executor | required before production |
| `specspace.operator_assistant` | Assistant flow preparing operator requests and handoffs | required |
| `specspace.diagnostics_assistant` | Assistant flow preparing diagnostics or reports | recommended |
| `product_workspace.implementation_agent` | Future implementation agent acting in a product workspace | required before production |
| `product_workspace.evidence_agent` | Future agent emitting product evidence packets | required before production |

## Staged Adoption

Adoption should be staged rather than all-or-nothing:

| Tier | Status | Meaning |
| --- | --- | --- |
| Tier 0 | `known_unpassportized` | Agent surface is known, but no passport reference exists. |
| Tier 1 | `passport_referenced` | SpecGraph knows a passport URI/digest but does not fully verify it. |
| Tier 2 | `passport_verified` | Schema, signature, issuer, lifecycle, and revocation checks pass. |
| Tier 3 | `runtime_enforceable` | Declared policies can be mapped to an enforcement target. |
| Tier 4 | `runtime_enforced_observed` | Future state: runtime enforcement is observed and evidenced. |

Tier 4 is future work. This proposal stops at adoption and graph integration.

## Agent Passport Reference Model

SpecGraph should not copy Agent Passports as canonical source data. It should
store graph-side references and derived summaries.

Candidate graph-side binding:

```yaml
artifact_kind: graph_agent_passport_ref
schema_version: 1
metadata:
  ref_id: "gapref_specgraph_supervisor_v1"
  agent_surface: "specgraph.supervisor"
  owner: "specgraph-core"
  created_at: "2026-05-26T00:00:00Z"
spec:
  agent_passport:
    uri: "agent-passport://specgraph/supervisor/0.1.0"
    digest: "sha256:..."
    api_version: "agent-passport.io/v1alpha1"
    metadata_name: "specgraph-supervisor"
    metadata_uid: "did:0al:agent:specgraph-supervisor"
    metadata_version: "0.1.0"
  graph_binding:
    graph_roles:
      - "supervisor"
      - "bounded_graph_worker"
    surfaces:
      - "SpecGraph supervisor"
    allowed_invocation_contexts:
      - "operator_requested_graph_work"
      - "supervisor_bounded_handoff"
  verification:
    expected_minimum_state: "V4_signature_verified"
    required_for_merge: false
    required_for_production: true
```

`GraphAgentPassportRef` is not a passport. It is the graph-side binding between
SpecGraph surfaces and an external Agent Passport.

## Derived Indexes

Future bounded implementation slices may introduce:

```text
tools/agent_passport_adoption_policy.json
runs/known_agent_passport_index.json
runs/agent_verification_gap_index.json
runs/agent_surface_index.json
```

### KnownAgentPassportIndex

Shows every agent surface known to SpecGraph or SpecSpace and its current
passport reference state.

```json
{
  "artifact_kind": "known_agent_passport_index",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "agents": [
    {
      "agent_surface": "specgraph.supervisor",
      "passport_ref": "agent-passport://specgraph/supervisor/0.1.0",
      "verification_state": "V4_signature_verified",
      "last_checked_at": "2026-05-26T00:00:00Z"
    },
    {
      "agent_surface": "specgraph.executor.codex",
      "passport_ref": null,
      "verification_state": "V1_known_surface",
      "last_checked_at": null
    }
  ]
}
```

### AgentVerificationGapIndex

Shows where an agent surface exists but passport reference, verification, or
policy mapping is incomplete.

```json
{
  "artifact_kind": "agent_verification_gap_index",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "gaps": [
    {
      "agent_surface": "specgraph.executor.codex",
      "gap": "missing_passport",
      "severity": "high",
      "reason": "Executor adapter launches nested CLI agent without passport reference."
    },
    {
      "agent_surface": "specspace.operator_assistant",
      "gap": "unsigned_passport",
      "severity": "medium",
      "reason": "Passport draft exists but signature verification is not available."
    },
    {
      "agent_surface": "specgraph.executor.codex",
      "gap": "verification_tool_unavailable",
      "severity": "medium",
      "reason": "Executor adapter gateway did not find an Agent Passport validator CLI."
    }
  ]
}
```

### AgentSurfaceIndex

Shows where agents appear in the graph and whether a passport is expected.

```json
{
  "artifact_kind": "agent_surface_index",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "surfaces": [
    {
      "surface_id": "specgraph.supervisor",
      "surface_type": "graph_runtime",
      "launches_agents": true,
      "requires_passport": true
    },
    {
      "surface_id": "specspace.operator_assistant",
      "surface_type": "operator_ui_flow",
      "launches_agents": false,
      "prepares_handoffs": true,
      "requires_passport": true
    }
  ]
}
```

These artifacts are read-only derived surfaces. They must not grant new
authority by themselves.

## Verification State Model

SpecGraph should present verification state as a ladder, not a boolean:

| State | Meaning |
| --- | --- |
| `V0_unknown` | SpecGraph has no reliable information about this agent. |
| `V1_known_surface` | SpecGraph knows this agent surface exists. |
| `V2_passport_referenced` | A passport URI or digest is known. |
| `V3_schema_valid` | Passport parses and conforms to Agent Passport schema. |
| `V4_signature_verified` | Passport signature and issuer chain are verified. |
| `V5_lifecycle_valid` | Passport is not expired or revoked. |
| `V6_integrity_declared` | Passport contains `agentIntegrity` data when applicable. |
| `V7_policies_mappable` | Declared policies can be mapped to an enforcement target. |
| `V8_runtime_enforcement_observed` | Future state: runtime enforcement is evidenced. |

This proposal uses `V0` through `V7` for adoption. `V8` is future work because
runtime enforcement is outside this proposal.

## Declaration vs Runtime Enforcement Boundary

Agent Passport declares identity, capabilities, resources, security policies,
integrity metadata, issuer, signature, and lifecycle.

SpecGraph adoption records whether a graph-facing agent has a passport, where it
is referenced, and what verification state is known.

This proposal does not claim that declared policies are enforced at runtime.
Runtime enforcement is the responsibility of compatible runtimes, executor
adapters, policy engines, `zeroald`, `agentifyd`, sandboxing layers, or future
SpecGraph supervisor enforcement components.

Observed executor capabilities and verified passport claims must remain
separate:

```text
observed capability: Codex CLI edited a temp worktree during smoke.
passport claim: specgraph.executor.codex declares bounded workspace writes.
runtime enforcement: external sandbox actually constrained writes.
```

Only the third line is enforcement. This proposal does not implement it.

## SpecGraph Agent Record

SpecGraph may cache derived fields for search, viewer display, and diagnostics:

```yaml
agent_surface: "specgraph.executor.codex"
passport_ref:
  uri: "agent-passport://executors/codex-cli/0.1.0"
  digest: "sha256:..."
verification:
  state: "V4_signature_verified"
  checked_at: "2026-05-26T00:00:00Z"
  verifier: "specgraph-passport-indexer"
derived:
  declared_capability_names:
    - "codex.execute"
    - "codex.patch"
  declared_policy_summary:
    filesystem: "workspace-bounded"
    network: "deny-by-default"
    shell: "bounded"
gaps:
  - "integrity_metadata_missing"
  - "runtime_enforcement_unknown"
```

This record is a derived cache. It must not become a parallel canonical passport
model.

## Relationship To Existing Proposals

- `0056_supervisor_executor_adapter_gateway.md` defines the launch-and-observe
  boundary for nested executor agents. It is also the owner of Agent Passport
  CLI discovery diagnostics for executor backends; this proposal consumes those
  diagnostics as verification gaps rather than rediscovering validator tooling.
- `0057_graph_operator_surface_request_preparation.md` defines the operator
  surface preparation boundary where assistant agents may appear.
- `0052_product_workspace_governance_profile.md` and
  `0053_product_workspace_stable_mode_enforcement.md` define why product
  workspaces need stable authority boundaries.
- `0058_feature_runtime_evidence_layer.md` delegates product-feature evidence to
  Feature Passport. This proposal delegates agent identity/capability/security
  to Agent Passport.

Feature Passport answers "what feature evidence must be proven?" Agent Passport
answers "which agent was authorized to act, with what declared capabilities and
constraints?"

## Viewer Model

SpecSpace or another Graph Operator Surface should eventually show an agent
authority panel:

```text
Agent: specgraph-supervisor
Surface: SpecGraph supervisor
Passport
  yes Referenced
  yes Schema valid
  yes Signature verified
  yes Issuer trusted
  yes Lifecycle valid
  yes Integrity metadata present
  warning Runtime enforcement not observed
Declared authority
  capabilities:
    - graph.plan
    - graph.execute_bounded
    - supervisor.handoff
  resources:
    - workspace read/write bounded by graph context
  policies:
    - no unbounded shell
    - nested executors require passport ref
Verification state: V6 / integrity declared
Gap: runtime enforcement not yet wired
```

The viewer must distinguish:

- passport missing;
- passport referenced but unverified;
- passport verified;
- declared capability versus observed capability;
- passport authority versus runtime success;
- local-only information versus publishable summary;
- runtime enforcement missing versus runtime enforcement observed.

## Minimum Viable Adoption

The first implementation should stop at read-only observation:

- define `tools/agent_passport_adoption_policy.json`;
- define expected graph-agent surfaces;
- build `runs/agent_surface_index.json`;
- build `runs/known_agent_passport_index.json`;
- build `runs/agent_verification_gap_index.json`;
- project summary fields into viewer-facing surfaces only after artifact shape is
  stable.

No passport should be required to merge ordinary SpecGraph work until the
adoption policy explicitly says so.

## Runtime Derived Surface Slice

Proposal `0067 Agent Passport Derived Surface Runtime` materializes the first
read-only runtime slice for this proposal:

```text
tools/agent_passport_adoption_policy.json
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_verification_gap_index.json
make agent-passports
```

The slice consumes Agent Passport CLI availability diagnostics from the `0056`
executor adapter index. It does not verify signatures, enforce passports,
launch agents, mutate SpecSpace, or change Platform packaging.

## Implementation Plan

Suggested bounded slices:

1. Agent Passport adoption policy and viewer contract.
2. Agent surface index builder.
3. Known passport index builder for configured references.
4. Verification gap index builder.
5. Consume `0056` executor adapter Agent Passport CLI diagnostics and normalize
   them into `agent_verification_gap_index`.
6. Link executor adapter index entries to agent passport identities.
7. Link supervisor run provenance to supervisor/executor passport identities.
8. Project agent authority summary into viewer-facing surfaces.
9. Add optional verification checks for signature, validity, integrity hashes,
   and stale passport source revisions.
10. Coordinate with SpecSpace for an agent authority panel after artifacts are
   stable.

## Acceptance Criteria

- SpecGraph references the external Agent Passport RFC instead of duplicating
  its full schema.
- The proposal includes an ADR-level architecture decision that forbids
  parallel canonical agent identity/capability models.
- The proposal defines `GraphAgentPassportRef` as a graph-side reference, not a
  passport copy.
- The proposal identifies supervisor, executor, operator assistant, and product
  workspace agents as future passport subjects.
- The proposal defines read-only SpecGraph artifacts for agent surfaces, known
  passports, and verification gaps.
- The proposal states that passports declare authority but do not replace
  runtime validation, human review, or runtime enforcement.
- The proposal names relationships to existing executor adapter and operator
  surface proposals.
- The proposal keeps this PR documentation-only.

## Risks and Mitigations

| Risk | Why It Matters | Mitigation |
| --- | --- | --- |
| Ad hoc capability drift | SpecGraph and SpecSpace could grow separate permission models. | Agent Passport is canonical authority. |
| False trust | A passport URI may be mistaken for verified identity. | Use verification state ladder. |
| Runtime gap hidden | Passport declares policy, but executor does not enforce it. | Declaration vs enforcement boundary. |
| Nested executor ambiguity | Supervisor launches Codex/Claude/Gemini without separate identity. | Passport required per executor surface. |
| UI overconfidence | Viewer may show "trusted" despite gaps. | Show verification gaps explicitly. |
| Stale passport | Agent changed while passport stayed old. | Digest, lifecycle, version, and freshness checks. |
| Secret leakage | Passport material can reveal internal endpoints or credentials. | Redacted derived surfaces and local-only states. |
| Issuer compromise | False passports can be signed. | Trust anchors, revocation, and issuer registry future work. |
| Development friction | Mandatory passports too early can block local work. | Stage adoption and keep initial artifacts read-only. |

## Open Questions

- Should initial graph-agent passports live in the SpecGraph repo, Platform repo,
  product workspaces, or the Agent Passport repo?
- Should Platform become the issuing authority for local factory agents?
- Which passport fields are safe to publish into `specgraph-public` bundles?
- What is the minimum useful unsigned local passport for bootstrap development?
- How should passport revocation interact with already-created supervisor
  evidence packets?
