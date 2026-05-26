# Agent Passport Adoption for Graph Agents Source Draft

## Source Context

The operator observed that SpecGraph and SpecSpace already contain agents in
practice:

- SpecGraph supervisor runs bounded graph work.
- Supervisor executor adapters launch nested CLI agents such as Codex and future
  Copilot/Claude/Gemini-style executors.
- SpecSpace is expected to host graph operator assistant flows that prepare
  operator requests, drafts, diagnostics, and supervisor handoffs.

The Agent Passport repository already defines a passport model for agent
identity, capabilities, resource requirements, security policies, integrity,
signature, issuer, verification, and lifecycle.

## Operator Intent

Adopt Agent Passport as the external authority for agent identity and capability
contracts across SpecGraph and SpecSpace-facing agent surfaces.

SpecGraph should not duplicate the Agent Passport RFC. It should reference it,
define the graph-specific integration boundary, and prepare future derived
artifacts that let viewers inspect agent identity, declared authority, and
verification state.

## Desired Outcome

Define a proposal for:

- Agent Passport as the authority for graph agent declarations;
- the set of SpecGraph/SpecSpace agents that eventually need passports;
- derived indexes for known agent passports and verification gaps;
- the boundary between passport declarations and actual runtime enforcement;
- how this relates to supervisor executor adapters and SpecSpace operator
  surfaces.

## Boundary

This proposal should not implement passport signing, verification, sandboxing,
SpecSpace UI, or runtime enforcement. It should define the adoption path and
prevent ad hoc agent identity/capability fields from drifting across SpecGraph,
SpecSpace, and Platform.
