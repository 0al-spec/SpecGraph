# Agent Passport Adoption for Graph Agents

## Status

Draft proposal

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

## Context

SpecGraph and SpecSpace already contain agent-shaped actors:

- the SpecGraph supervisor;
- nested supervisor executor backends such as Codex CLI and future alternative
  agent CLI executors;
- graph operator assistant flows that prepare requests, drafts, diagnostics, and
  supervisor handoffs in SpecSpace or another operator surface;
- future product-workspace agents that may implement specs, run diagnostics, or
  produce evidence packets.

Today those actors are identified by local implementation names, CLI commands,
model settings, prompt profiles, or UI surfaces. That is useful operationally,
but it is not a durable identity/capability/security contract.

Agent Passport already defines the stronger external model: a human-readable and
machine-parsable declaration of agent identity, capabilities, resource
requirements, security policies, integrity checks, digital signature, issuing
authority, verification, and lifecycle.

SpecGraph should adopt Agent Passport as the authority for graph-agent
declarations rather than inventing another local passport format.

## Problem

SpecGraph is moving toward a multi-service AI software factory:

```text
SpecSpace operator surface
  -> SpecGraph supervisor
  -> executor adapter / nested agent
  -> product workspace
  -> evidence and implementation artifacts
```

Without an explicit Agent Passport boundary, several risks appear:

- executor adapters can accumulate ad hoc capability fields;
- SpecSpace can display agent state without a stable identity contract;
- product-workspace agents can run with unclear authority;
- prompt profiles, model choices, and CLI backends can be mistaken for agent
  identity;
- review and evidence surfaces cannot say which agent was authorized to do what;
- future Platform orchestration has no shared declaration to inspect.

The practical need is not immediate runtime enforcement. The first need is a
stable, external, verifiable declaration model that SpecGraph can reference and
project.

## Goals

- Adopt the external Agent Passport RFC as the authority for agent identity,
  capability, security policy, integrity, and verification concepts.
- Define which SpecGraph/SpecSpace actors count as graph agents for future
  passporting.
- Define the SpecGraph integration boundary without copying the full Agent
  Passport RFC.
- Link supervisor executor adapter backends to declared agent identities.
- Prepare read-only derived surfaces for passport inventory, verification gaps,
  and viewer-facing agent authority.
- Preserve the distinction between declared capabilities and enforced runtime
  constraints.
- Keep SpecSpace as a consumer of derived surfaces, not a parser of raw local
  executor logs or private passport material.

## Non-Goals

- Redefining the Agent Passport RFC inside SpecGraph.
- Implementing passport signing or verification in this proposal.
- Implementing `agentifyd`, `zeroald`, sandboxing, seccomp, chroot, or runtime
  enforcement.
- Replacing supervisor deterministic validation with passport declarations.
- Treating a passport as proof that an LLM agent will follow instructions.
- Publishing raw prompts, credentials, private keys, local auth paths, or
  machine-local secrets.
- Implementing SpecSpace UI.
- Requiring all existing local development tools to have operational passports
  before ordinary SpecGraph work can continue.

## Core Proposal

Introduce **Agent Passport Adoption for Graph Agents** as a governance and
observability layer:

```text
Agent Passport RFC
  -> graph-agent declaration
  -> SpecGraph passport index
  -> executor adapter / operator surface linkage
  -> verification and capability gaps
  -> viewer-facing agent authority surface
```

SpecGraph should treat Agent Passport as the external authority for agent
declaration semantics. SpecGraph should own only the integration surfaces that
connect passports to graph agents, supervisor runs, executor adapters, and
operator-facing views.

## Agent Classes

### Supervisor Agent

The SpecGraph supervisor is the graph-governance execution agent. Its passport
should eventually describe:

- identity and version of the supervisor runtime;
- allowed graph operations;
- required validation gates;
- prompt overlay boundaries;
- filesystem authority profile;
- allowed derived artifact writes;
- non-overridable invariants.

The passport does not replace SpecGraph's constitutional governance or
deterministic validation. It declares the agent's intended authority and
security posture.

### Executor Agent

A supervisor executor backend is a nested worktree-mutating agent launched
through the executor adapter gateway.

Examples:

- Codex CLI;
- future GitHub Copilot CLI backend;
- future Claude Code, Gemini CLI, or OpenCode backend.

The executor passport should eventually describe:

- command surface;
- expected non-interactive behavior;
- worktree mutation capability;
- sandbox/approval support;
- model/profile controls;
- output protocol obligations;
- local-only log boundaries.

This extends proposal `0056_supervisor_executor_adapter_gateway.md`: adapter
capability facts describe observed backend behavior, while Agent Passport
declares identity, authority, resource needs, integrity, and policy boundaries.

### Operator Assistant Agent

A SpecSpace or operator-surface assistant may help prepare graph requests,
drafts, diagnostics, preview plans, and supervisor handoffs.

Its passport should eventually describe:

- user-facing role;
- read/write authority over graph artifacts;
- allowed request preparation actions;
- forbidden direct canonical mutations;
- privacy and transcript handling;
- handoff boundaries to the supervisor.

SpecSpace should consume a derived passport/authority projection. It should not
parse raw executor logs, raw prompts, private keys, or local-only passport
material.

### Product Workspace Agent

Future product-workspace agents may implement specs, run tests, generate
evidence, or prepare pull requests for product codebases.

Their passports should eventually describe:

- product workspace scope;
- allowed repositories and paths;
- build/test authority;
- network and credential boundaries;
- evidence packet emission authority;
- handoff obligations back to SpecGraph.

This class is especially important for stable product workspaces where SpecGraph
must not self-evolve while working on a customer's software.

## External Contract Boundary

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
- projecting passport verification state into derived artifacts;
- surfacing missing or stale passports as gaps;
- preserving local-only secrecy boundaries;
- refusing to treat a passport declaration as runtime success.

## Proposed SpecGraph Artifacts

Future bounded implementation slices may introduce:

```text
tools/agent_passport_adoption_policy.json
runs/agent_passport_index.json
runs/agent_authority_surface.json
```

Suggested responsibilities:

- `agent_passport_adoption_policy`: configured passport sources, recognized
  graph-agent roles, required fields, local-only redaction rules, and allowed
  authority states.
- `agent_passport_index`: discovered passports, linked graph-agent roles,
  RFC/source revision, verification status, freshness, and gaps.
- `agent_authority_surface`: viewer-facing summary of which agents exist, what
  they claim authority to do, whether verification is available, and what is
  missing before operational trust.

These artifacts should be read-only derived surfaces. They must not grant new
authority by themselves.

## Authority States

Suggested viewer-facing authority states:

- `declared`: passport exists but is not verified.
- `verified`: signature/integrity/lifecycle checks passed.
- `stale`: passport exists but version, validity, or source revision is stale.
- `missing`: expected agent has no known passport.
- `unsupported`: passport exists but declares requirements SpecGraph cannot
  inspect or enforce.
- `local_only`: passport is intentionally local and must not be published.

Authority state is not the same as run success. A verified passport can still
produce a failed supervisor or executor run.

## Relationship To Existing Proposals

- `0056_supervisor_executor_adapter_gateway.md` defines the launch-and-observe
  boundary for nested executor agents.
- `0057_graph_operator_surface_request_preparation.md` defines the operator
  surface preparation boundary where assistant agents may appear.
- `0052_product_workspace_governance_profile.md` and
  `0053_product_workspace_stable_mode_enforcement.md` define why product
  workspaces need stable authority boundaries.
- `0058_feature_runtime_evidence_layer.md` delegates product-feature evidence to
  Feature Passport. This proposal delegates agent identity/capability/security
  to Agent Passport.

Together, Feature Passport answers "what feature evidence must be proven?"
Agent Passport answers "which agent was authorized to act, with what declared
capabilities and constraints?"

## Viewer Surface

SpecSpace or another Graph Operator Surface should eventually show an agent
authority panel:

```text
Agent: specgraph.supervisor
Role: supervisor
Passport: declared / verified / missing
Issuer: local project authority
Authority: graph refinement, derived artifacts, proposal preparation
Gaps: signature verification not configured

Agent: specgraph.executor.codex
Role: executor
Passport: declared
Authority: bounded worktree mutation through adapter gateway
Gaps: sandbox support is observed, not passport-verified
```

The viewer must distinguish:

- passport missing;
- passport declared but unverified;
- passport verified;
- declared capability versus observed capability;
- passport authority versus runtime success;
- local-only information versus publishable summary.

## Implementation Plan

Suggested bounded slices:

1. Agent Passport adoption policy and viewer contract.
2. Read-only agent passport index builder for configured sources.
3. Link executor adapter index entries to agent passport identities.
4. Link supervisor run provenance to supervisor/executor passport identities.
5. Project agent authority summary into viewer-facing surfaces.
6. Add optional verification checks for signature, validity, integrity hashes,
   and stale passport source revisions.
7. Coordinate with SpecSpace for an agent authority panel after artifacts are
   stable.

## Acceptance Criteria

- SpecGraph references the external Agent Passport RFC instead of duplicating
  its full schema.
- The proposal identifies supervisor, executor, operator assistant, and product
  workspace agents as future passport subjects.
- The proposal defines read-only SpecGraph artifacts for passport inventory and
  authority projection.
- The proposal states that passports declare authority but do not replace
  runtime validation or human review.
- The proposal names relationships to existing executor adapter and operator
  surface proposals.
- The proposal keeps this PR documentation-only.

## Risks

- Treating a passport as proof of safe behavior rather than a declared contract.
- Duplicating Agent Passport semantics inside SpecGraph and creating drift.
- Publishing local-only auth, prompts, paths, or secrets.
- Blocking ordinary local development before operational passport tooling
  exists.
- Confusing observed executor capabilities with verified passport claims.
- Making SpecSpace parse raw passport material instead of derived safe surfaces.

## Open Questions

- Should initial graph-agent passports live in the SpecGraph repo, Platform repo,
  product workspaces, or the Agent Passport repo?
- Should Platform become the issuing authority for local factory agents?
- Which passport fields are safe to publish into `specgraph-public` bundles?
- What is the minimum useful unsigned local passport for bootstrap development?
- How should passport revocation interact with already-created supervisor
  evidence packets?
