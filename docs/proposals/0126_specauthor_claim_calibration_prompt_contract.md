# SpecAuthor Claim Calibration Prompt Contract

RFC: SG-RFC-0126
Version: 0.1.0

## Status

Draft proposal

Decision scope: prompt and validation contract for SpecAuthorAgent output before
any generated specification, proposal, ADR, Agent Passport draft, or
Hypercode-related artifact can be treated as graph-ready.

This document defines a prompt and validation contract only. It does not change
the active supervisor prompt, execute prompt agents, add a write gate, mutate
canonical specs, accept ontology terms, write Ontology packages or lockfiles,
change Agent Passport runtime policy, or add SpecSpace UI.

## Source Material

This proposal captures the operator intent that SpecAuthorAgent should reduce
hallucinated terminology, unsupported decisions, and scope leakage by resolving
active ontology, domain, and context before writing, then calibrating strong
claims with a structured F/G/R record.

Source draft:

- `docs/archive/proposal_sources/0126_specauthor_claim_calibration_prompt_contract.md`

Related proposal context:

- `0001_vocabulary`
- `0011_pre_spec_semantic_layer`
- `0013_default_deny_write_authority`
- `0059_agent_passport_adoption_for_graph_agents`
- `0070_agent_passport_reference_declaration`
- `0100_ontology_grounded_semantic_control`
- `0116_ontology_semantic_lint_input`
- `0117_ontology_supervisor_soft_gate_wiring`
- `0118_ontology_prompt_agent_context_artifact`
- `0119_ontology_canonicalization_backlog`

## Summary

SpecAuthorAgent should not write persistent graph specifications in free prose.
Before authoring graph-facing text, it should resolve the active frame:

```yaml
active_frame:
  project: "SpecGraph"
  subsystem: "Application.AgentLayer.SpecificationAuthoring"
  agent_layer: "SpecificationAuthoring"
  domain_refs: []
  ontology_refs: []
  context_refs: []
  target_artifact: "Proposal | ADR | RFCSection | AgentPassportDraft | HypercodeSpec"
  lifecycle_phase: "draft | review | accepted | implementation"
  constraints: []
```

The agent should reuse accepted SpecGraph and Ontology terms when available,
declare missing context instead of pretending the frame is known, and attach
F/G/R calibration to every nontrivial architectural, product, security,
runtime, behavioral, or cross-domain claim.

The short rule is:

```text
No ontology/context -> no final spec.
No FGR on strong claim -> no graph write.
Low R -> not a decision.
Broad G without evidence -> narrow the claim.
```

## Problem

SpecGraph artifacts are not ordinary prose. Once accepted, they become graph
nodes and evidence that downstream agents may use for implementation,
validation, review, policy generation, and runtime behavior.

The current ontology line gives SpecGraph source-backed semantic context,
semantic lint input, supervisor soft gates, and prompt-agent ontology context.
That reduces terminology drift, but it does not yet define how a spec-authoring
agent must express epistemic strength.

Without an explicit authoring contract, SpecAuthorAgent can still:

- invent new terms when accepted ontology nodes already exist;
- generalize outside the active product, security, runtime, or platform domain;
- ignore active lifecycle phase, subsystem, or operator constraints;
- present hypotheses as architectural decisions;
- produce plausible text that lacks evidence, scope, and reliability
  boundaries.

This creates systemic risk because unsupported claims can look canonical after
they enter the graph.

## Proposal

Introduce `specgraph.prompt-contract.claim-calibration.v0.1` as a mandatory
contract for SpecAuthorAgent and future graph-facing spec-authoring agents.

The contract changes the authoring boundary from:

```text
Write a good specification from the user's intent.
```

to:

```text
Resolve the active SpecGraph ontology, domain, context, and target artifact
first. Reuse existing graph concepts. For every strong claim, attach a bounded
F/G/R calibration record. If evidence or scope is missing, downgrade the claim
to a hypothesis, proposal, risk, observation, or ContextCompletionRequest.
```

## Required Behavior

Before writing a graph-facing artifact, SpecAuthorAgent must resolve or emit a
completion request for:

- project;
- subsystem;
- agent layer;
- domain refs;
- ontology refs;
- context refs;
- target artifact;
- lifecycle phase;
- audience;
- constraints.

The agent must not invent new domain terms when an existing ontology term,
alias, relation, domain node, or context node can be reused.

If a required frame element is unavailable, the agent should emit:

```yaml
context_completion_request:
  kind: "ontology | domain | context"
  proposed_name: ""
  reason: ""
  status: "requires_human_confirmation"
  canonical_mutations_allowed: false
```

## FGR Claim Calibration

F/G/R is a structured claim calibration model:

```yaml
claim_calibration:
  F: "F0..F5"
  G:
    applies_to: []
    excludes: []
    assumptions: []
  R: "R0..R5"
```

`F` records formality and rigor:

```text
F0 raw idea or intuition
F1 informal note
F2 structured narrative
F3 explicit model with assumptions
F4 typed/spec-level constraints
F5 machine-checkable invariant, test, or proof artifact
```

`G` is not a number. It is a scope object that names where the claim applies,
where it does not apply, and which assumptions bound the claim.

`R` records reliability:

```text
R0 unsupported
R1 intuition only
R2 internal reasoning
R3 internal evidence or small experiment
R4 replicated internal evidence or production telemetry
R5 external replication or strong source quality
```

No evidence should cap reliability at `R2`. Low-reliability claims must not be
persisted as decisions.

## Claim Record Shape

When possible, generated output should include machine-ingestable claims:

```yaml
claims:
  - id: "claim.specauthor.fgr_reduces_overclaiming"
    statement: >
      Requiring SpecAuthorAgent to attach F/G/R calibration to strong
      architectural claims should reduce overbroad and unsupported
      specification claims.
    type: "hypothesis"
    ontology_refs:
      - "ontology.specgraph.claim"
      - "ontology.specgraph.evidence"
    domain_refs:
      - "domain.specification_authoring"
    context_refs:
      - "context.specgraph.agent_layer"
    evidence_refs: []
    calibration:
      F: "F3"
      G:
        applies_to:
          - "SpecGraph-like workflows"
          - "LLM agents that generate proposals, ADRs, RFCs, Agent Passport fragments, or Hypercode specs"
        excludes:
          - "pure chat UX with no persistent specification graph"
          - "fully formal verification workflows unless F is upgraded"
        assumptions:
          - "SpecGraph contains reusable ontologies, domains, and contexts"
          - "Generated specs are validated before graph persistence"
      R: "R2"
    required_validation:
      - "Measure unsupported claim density"
      - "Measure scope leakage rate"
      - "Measure human edit distance before acceptance"
```

`R2` is intentional for the example. At proposal time this is a plausible
design hypothesis, not a validated production fact.

## Mechanism-Oriented Language

The contract should prefer mechanism-oriented phrasing in decision rationale:

- actions over labels;
- constraints over vague qualities;
- dependencies and effects over ungrounded adjectives;
- flows and enforcement mechanisms over broad claims.

This is a prompt-level guideline for the first slice, not a hard lexical
validator. A later review mode may make it stricter for security, governance,
or architecture tradeoff analysis.

## Proposed Node And Edge Vocabulary

Candidate node types:

```yaml
node_types:
  SpecAuthoringPolicy:
    description: "Behavioral policy controlling how spec-authoring agents generate specifications."
  ClaimCalibration:
    description: "F/G/R tuple attached to a graph-facing claim."
  ContextCompletionRequest:
    description: "Request emitted when required ontology, domain, or context cannot be resolved."
  OntologyBinding:
    description: "Mapping between generated terms and existing ontology nodes."
  PromptContract:
    description: "Versioned prompt fragment with validation semantics."
  MechanismLanguageConstraint:
    description: "Prompt-level constraint requiring operational and mechanistic phrasing."
```

Candidate edge types:

```yaml
edge_types:
  USES_ONTOLOGY:
    from: "SpecArtifact"
    to: "Ontology"
  IN_DOMAIN:
    from: "Claim"
    to: "Domain"
  VALID_IN_CONTEXT:
    from: "Claim"
    to: "Context"
  CALIBRATED_BY:
    from: "Claim"
    to: "ClaimCalibration"
  SUPPORTED_BY:
    from: "Claim"
    to: "Evidence"
  REQUIRES_VALIDATION:
    from: "Claim"
    to: "ValidationTask"
  GOVERNED_BY:
    from: "SpecAuthorAgent"
    to: "SpecAuthoringPolicy"
  GENERATED_UNDER:
    from: "SpecArtifact"
    to: "PromptContract"
```

## Future Write Gate

The prompt alone is not sufficient enforcement. A later implementation should
add a `SpecGraphWriteGate.claim_calibration_required` validator before generated
artifacts can be persisted as graph-ready material.

Candidate rejection rules:

```yaml
reject_if:
  - condition: "strong claim lacks calibration"
    message: "Strong claim requires F/G/R calibration."
  - condition: "claim.calibration.G.applies_to is empty"
    message: "Claim scope must be explicit."
  - condition: "claim.calibration.R in ['R0', 'R1', 'R2'] and claim.type == 'decision'"
    message: "Low-reliability claim cannot be persisted as a decision."
  - condition: "new terms exist without ontology bindings or context completion request"
    message: "New terms require ontology binding or human confirmation."
  - condition: "artifact.context_refs is empty"
    message: "Spec artifact must declare active context."
```

## Agent Passport Alignment

This proposal starts in SpecGraph prompt policy, not runtime security. A later
Agent Passport extension may declare the behavior policy for the
`compose_specification` capability:

```yaml
x-behaviorPolicies:
  - id: "specgraph.prompt-contract.claim-calibration.v0.1"
    appliesTo:
      - "compose_specification"
    requires:
      ontologyResolution: true
      domainResolution: true
      contextResolution: true
      claimCalibration: "FGR"
      mechanismLanguage: true
    rejectsOutputWhen:
      - "missing_active_context"
      - "strong_claim_without_fgr"
      - "new_term_without_ontology_binding"
      - "decision_with_low_reliability"
```

This must not replace runtime controls such as sandboxing, seccomp, network
policy, filesystem boundaries, or signed execution identity.

## Non-Goals

- Changing the current SpecGraph supervisor prompt in this PR.
- Implementing a validator or write gate in this PR.
- Requiring F/G/R for every trivial wording or formatting change.
- Treating ontology context as proof that generated text is correct.
- Creating or accepting new ontology terms.
- Writing `specs/imports/ontology.lock.yaml`.
- Mutating `specs/nodes/*.yaml`.
- Executing prompt agents.
- Adding SpecSpace mutation UI.
- Treating Agent Passport behavior-policy extensions as runtime security
  enforcement.

## Proposed Child Proposal Sequence

### 0126-A: Prompt Contract Artifact

Add a versioned prompt-contract artifact for SpecAuthorAgent with active-frame
resolution, ontology/domain/context reuse rules, and missing-context behavior.

### 0126-B: Claim Record And FGR Schema

Define the graph-facing claim record shape, F/G/R schema, claim types, and
evidence reference rules.

### 0126-C: SpecGraph Write Gate

Add a validator that rejects graph-ready generated artifacts missing active
context, ontology bindings, claim calibration for strong claims, or downgrade
rules for low-R decisions.

### 0126-D: Regression Prompt Metrics

Measure overclaim rate, scope leakage rate, unsupported assertion density,
ontology reuse ratio, new-term justification rate, and human edit distance
before and after the contract.

### 0126-E: Agent Passport Behavior Extension

Reflect the accepted behavior policy as an experimental Agent Passport extension
for the `compose_specification` capability after SpecGraph-side semantics are
stable.

## Acceptance

This contract slice is complete when:

- proposal `0126` has source draft provenance;
- promotion registry records the bounded source and scope;
- runtime registry records this as a deferred contract slice rather than an
  implemented runtime behavior;
- proposal tracking gate passes;
- documentation sync passes;
- future child proposals can cite `0126` without using it as authority for
  canonical mutation or prompt execution.

## Authority Boundary

This proposal may be used as:

- a prompt-contract design reference;
- a parent for bounded prompt, schema, validator, metric, and Agent Passport
  follow-up proposals;
- evidence that authoring agents need active ontology/domain/context and F/G/R
  calibration before graph-ready persistence.

This proposal may not be used as:

- approval to change the active SpecAuthorAgent prompt;
- approval to execute prompt agents;
- approval to write a new validator;
- approval to reject existing graph artifacts retroactively;
- approval to create or accept ontology terms;
- approval to write Ontology packages, lockfiles, or canonical specs;
- approval to change Agent Passport runtime security posture.
