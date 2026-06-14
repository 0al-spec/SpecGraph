# Source Draft: SpecAuthor Claim Calibration Prompt Contract

This source draft records the operator-provided proposal intent for
SG-RFC-0126.

## Operator Intent

The operator proposed a SpecGraph proposal named:

```text
SG-PROP-AGENT-SPEC-CLAIM-CALIBRATION-v0.1
Epistemic & Ontological Prompt Contract for SpecAuthorAgent
```

The main intent is:

```text
SpecAuthorAgent should not write specifications in free style. Before
generation it must determine the active ontology, domain, context, and target
artifact, reuse existing SpecGraph terms and relations, and attach F/G/R
calibration to every nontrivial architectural, product, security, behavioral,
or runtime claim.
```

The operator explicitly wanted this to reduce:

- hallucinated terminology;
- misunderstanding of accepted terms;
- use of the wrong domain vocabulary;
- unsupported claims entering the graph as stable truths;
- overbroad architectural or security statements.

## Requested Checklist

The requested proposal checklist was:

- place the proposal in `Application.AgentLayer.SpecificationAuthoring`;
- change the system prompt or prompt policy for `SpecAuthorAgent`;
- add a mandatory resolution step:

  ```text
  ontology -> domain -> context -> target artifact
  ```

- introduce `{F,G,R}` for strong claims;
- forbid universal claims without scope;
- add a validator or gate before writing to SpecGraph;
- optionally reflect the policy in Agent Passport through an extension field.

## Requested Roadmap

The requested roadmap was:

| Stage | Work | Check |
| --- | --- | --- |
| 1 | Add prompt contract to SpecAuthorAgent | Agent emits active ontology/domain/context |
| 2 | Add FGR claim records | Strong claims get F, G, and R |
| 3 | Add SpecGraph validator | Spec without ontology/context/FGR fails |
| 4 | Add regression prompts | Compare overclaim rate before and after |
| 5 | Link to Agent Passport | `compose_specification` carries behavioral policy |

## Key Policy Rules

The operator recommended starting with a soft but enforceable version:

```text
No ontology/context -> no final spec.
No FGR on strong claim -> no graph write.
Low R -> not a decision.
Broad G without evidence -> narrow the claim.
```

Mandatory rules:

- resolve ontology/domain/context;
- attach FGR to strong claims;
- downgrade low-R decisions.

Recommended rules:

- use mechanism-oriented language;
- avoid vague label-like formulations;
- emit machine-ingestable claim records where possible.

Optional future rule:

- add a special `mechanism_language` reasoning mode for decision analysis,
  security policy, architecture tradeoff, and governance claims.

## FGR Model

The operator proposed:

```yaml
fgr:
  F:
    type: "ordinal"
    scale:
      F0: "raw idea / intuition"
      F1: "informal note"
      F2: "structured narrative"
      F3: "explicit model with assumptions"
      F4: "typed/spec-level constraints"
      F5: "machine-checkable invariant/test/proof artifact"
  G:
    type: "scope_object"
    fields:
      applies_to:
        - "domain"
        - "subsystem"
        - "agent_type"
        - "runtime"
        - "lifecycle_phase"
      excludes:
        - "out_of_scope_domain"
        - "unsupported_runtime"
      assumptions:
        - "contextual_precondition"
  R:
    type: "ordinal_or_scalar"
    scale:
      R0: "unsupported"
      R1: "intuition only"
      R2: "internal reasoning"
      R3: "internal evidence or small experiment"
      R4: "replicated internal evidence / production telemetry"
      R5: "external replication / strong source quality"
```

The operator explicitly recommended that `G` should not be stored as a number
in SpecGraph. It should be a structured scope object.

## Candidate Claim Record

The operator proposed machine-ingestable claim records shaped like:

```yaml
claims:
  - id: "claim.<slug>"
    statement: "..."
    type: "hypothesis | decision | constraint | invariant | risk | observation"
    ontology_refs: []
    domain_refs: []
    context_refs: []
    evidence_refs: []
    calibration:
      F: "F0..F5"
      G:
        applies_to: []
        excludes: []
        assumptions: []
      R: "R0..R5"
    required_validation: []
```

## Candidate Validator

The requested write gate should reject graph-ready generated specs when:

- a strong claim lacks F/G/R calibration;
- claim scope is empty;
- an `R0`, `R1`, or `R2` claim is persisted as a decision;
- new terms lack ontology bindings or a context completion request;
- the artifact lacks active context refs.

The operator also suggested warnings for broad terms such as `always`,
`universal`, `any agent`, and `all systems`.

## Agent Passport Alignment

The operator proposed a future experimental Agent Passport behavior extension:

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

The operator emphasized that this semantic/specification policy is not a
replacement for runtime security controls such as sandboxing, chroot, seccomp,
network restrictions, or capability enforcement.
