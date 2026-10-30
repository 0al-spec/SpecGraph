# Mechanically checked specification authoring

RFC: SG-RFC-0233
Version: 0.1.0

## Status and source

Draft proposal; planning contract only. Runtime realization is
`deferred_until_canonicalized`. The human agreed with this direction and asked
to retain it in the shared graph. This change records that request; it does not
activate a readiness policy, change existing thresholds or refine canonical
specification nodes.

[Source excerpts and interpretation](../archive/proposal_sources/0233_mechanical_specification_authoring.md),
[declared draft obligations](0233_mechanical_specification_authoring.intent.yaml)
and the [graph return path](../reviews/0233_mechanical_specification_authoring/README.md)
preserve the conversation as durable project memory.

```yaml
canonical_mutations_allowed: false
runtime_profile_activation_allowed: false
evidence_admission_allowed: false
```

## Problem and intended result

An author should be able to see which declared obligations, ontology bindings,
acceptance cases and dependencies remain incomplete while writing a spec.
The result must be mechanically reproducible from selected inputs. An LLM may
help author those inputs, but its opinion cannot replace a validator result.

Large specifications may be finished leaf nodes. Text length, criterion count,
node count or one aggregate score cannot establish a need for children. The
author needs separate observations of contract gaps, structural complexity and
the ability to verify the contract. Implementation success in one agent pass
remains an empirical executor property, not a compiler guarantee.

The first pilot is the outcome precedence in SG-SPEC-0072, Project Ontology
Context Selection, at frozen revision
`c31b1a332ed1df2fba7d10ad0a215f230d61b97e` from the open ontology stack:
[pilot source](https://github.com/0al-spec/SpecGraph/blob/c31b1a332ed1df2fba7d10ad0a215f230d61b97e/specs/nodes/SG-SPEC-0072.yaml).
At proposal preparation, main is `ee8cb62f5acca18e884dcc19cf306ca6708ab7c5`;
SG-SPEC-0072 is not yet a canonical file on main. This proposal targets existing
SG-SPEC-0015 and can be reviewed independently of that stack. Rebase or merge
of the stack requires explicitly selecting the pilot revision again.

## Reuse and responsibility

| Existing contract or tool | Reused responsibility | Remaining boundary |
| --- | --- | --- |
| SG-SPEC-0015 | Bounded concern and independent delegation | Numeric atomicity limits are not proof of independent concerns |
| SG-SPEC-0016 and SG-SPEC-0055 | Declared dependency linkage and reconciliation | Linked state does not prove implementation completion |
| SG-SPEC-0021 | Derived verifiability and metric family | Measurements do not change canonical status themselves |
| SG-SPEC-0049 | Shape pressure and lower-boundary handoff | Over-atomization and bookkeeping chains can argue against another child |
| SG-SPEC-0070 / native BDD | Exact scenario declarations and local references | Declaration validation is not step execution or behavioral coverage |
| Ontology compiler / SG-RFC-0232 | Selected vocabulary and supported structural checks | A valid package does not prove a specification instance is complete |
| SIB_FULL / SG-RFC-0226 | Verifiability, complexity, stability and trace inputs | Preserve measured facts, proxies and unavailable quantities separately |
| Existing intent/proposal lanes | Durable source, proposal and return route | Registration is neither execution nor canonical adoption |

Related proposals: [0222](0222_workspace_structural_limits.md),
[0226](0226_traceability_evidence_providers_and_svc.md),
[0232](0232_verified_project_ontology_context.md). This authoring method does not
extend SG-SPEC-0072 into terminology inventory, freshness or Supervisor
readiness: those concerns are explicitly outside that node's scope.

## Proposed authoring cycle

### 1. Preserve source obligations and selected scope

Start from the existing source-bound Intent Atoms or Requirement identities.
Record which obligations the spec addresses, including partial coverage,
delegation, deferral and unresolved mappings. Keep source obligation identity
separate from scenario identity and from an agent's implementation task.

For proposal 0232, `ONT-CONTEXT` is only partly addressed by selection semantics;
whole-spec terminology grounding remains separate. `ONT-INPUTS` supplies the
operation-capture obligation. `ONT-COVERAGE` and `ONT-FRESHNESS` must remain
visible outside SG-SPEC-0072 rather than being counted as covered by its name.

Compute missing mappings against the declared expected inventory, not against
only the rows that happened to resolve. Deleting a criterion does not delete
its source obligation. A deliberate removal or scope change is an explicit
reviewable disposition and appears in the before/after inventory. Partial
source mappings must not count as full discharge of the parent obligation.
This is coverage of a bounded declared inventory, not discovery of every
possible unstated human expectation.

### 2. Bind applicable concepts and relations

Use the project's explicitly selected versioned ontology context. Bind domain
uses to qualified definitions and source locations, reusing existing binding
formats where possible. New meanings remain source-attributed ontology gaps.

A versioned authoring profile specifies the applicable required bindings and
checks for this stage and spec kind. Optional relations stay optional. The
current specgraph-core package declares `definesRequirement`,
`hasAcceptanceCriterion` and `requirementValidatedByCriterion` with minimum
cardinality zero; absence is not automatically a compiler error. This proposal
does not globally change those cardinalities.

Distinguish a missing ontology definition, a missing usage binding, an
incomplete requirement, and an unsupported check. Resolve the first through
the existing ontology review path, the next two through authoring, and the
last through a tool follow-up. Draft capture remains available in all cases.

### 3. Declare verification while writing acceptance

Give applicable criteria explicit verification links and local scenario IDs.
Reuse native `bdd_scenarios` and `observability.obligations[*].scenario_ids`
where appropriate. The pilot's six prose `acceptance_cases` are not already
native BDD coverage and must not be relabelled as executed checks.

Keep three observations separate: a valid declaration, an available method
for checking the expected result, and an actual execution result. A BDD step
string is not an executable assertion. Reuse existing verification adapters;
add a small explicit adapter only for unsupported machine-readable conditions.

For the bounded outcome pilot, specify a valid selected context and the
applicable required-check inventory before applying outcome precedence:

| Detected invalidity | Required check unavailable | Expected outcome |
| --- | --- | --- |
| No | No | verified, only when all required checks actually succeeded |
| No | Yes | unavailable |
| Yes | No | invalid |
| Yes | Yes | invalid, retaining both diagnostics |

An absent selection, unsupported profile or incomplete capture cannot gain
verified status from an empty check list. The check inventory and expectations
come from the contract, not solely from the implementation under test. Identity
stability and dependency closure are later checks; they are not claimed covered
by this four-row precedence example.

### 4. Observe gaps and complexity on one input snapshot

Bind observations to the spec/source revision, selected ontology inputs,
binding inventory and checking/metric profile. Recompute affected observations
after changes; no current success may be inferred from stale or partial data.
Reuse selected artifacts explicitly, without an implicit latest-report search.

Keep concrete violations and unsupported checks separate from SIB diagnostics:

- SVC uses all declared in-scope atoms as its denominator and a named
  verifiability predicate, not only successfully mapped records. Missing criteria
  remain visible; declaration coverage and execution success are separate.
- PVC requires an explicit premise inventory and applicable check evidence.
- Expected implementation potential I* requires recorded boundaries, modes,
  external dependencies and exceptions; missing inputs remain unavailable.
- Graph degree, dependency closure and impact radius identify their projection,
  edge roles and architectural boundary. Refinement and vocabulary links are
  not silently penalized as blocking dependencies.
- Stability uses a declared historical window; one snapshot cannot establish it.

An empty or incomplete inventory cannot yield an unexplained 100 percent.
Existing SIB_FULL proxies retain their own names and derivation. No new weights,
universal cutoff, automatic split rule or numerical merge gate is introduced.

### 5. Route one bounded next move

Supervisor presents the exact obligation, definition, relation or check needing
attention. Refine the same node when the gap clarifies its bounded concern;
propose delegation when independently advancing concerns justify it under
SG-SPEC-0015. Treat missing tool support as such, not as a reason to manufacture
another canonical spec. Use SG-SPEC-0049 to notice unproductive fragmentation.

A proposed implementation handoff requires the selected authoring checks to be
satisfied, required mappings resolved and unsupported mandatory guarantees made
explicit. Complexity informs execution planning. It does not alone require a
child. Runtime readiness, human acceptance and canonical publication remain
separate existing decisions. The precise handoff policy requires review before
activation; current Supervisor behavior is unchanged by this document.

## Current implementation limits observed during preparation

- `validate-specgraph` resolves explicitly represented namespace references;
  it does not detect every omitted binding or interpret normative prose.
- `validate-golden-intent` checks declared expectations against an ontology
  package, not the completeness of an arbitrary SpecGraph specification.
- The current Ontology instance validator supports specific EventCore profiles;
  it is not a general SG-SPEC-0072 instance checker.
- `LegacyVerifiabilityMetric` skips `not_defined`; acceptance mapping uses a
  token-overlap heuristic. Neither is atom-level SVC under this proposed profile.
- `sib_eff_star` uses an expected-test/work-item proxy, not all I* components.
- `validate_atomicity` enforces counts; the default five-criterion limit must be
  reviewed against SG-SPEC-0015 before this profile changes any handoff behavior.

These are bounded source observations, not fresh compiler or test-run evidence.
The [review packet](../reviews/0233_mechanical_specification_authoring/README.md)
records how to resume the work and the source locations to recheck.

## Pilot, verification and return task

1. Review the applicable obligation inventory and authoring profile for the
   selected SG-SPEC-0072 revision; reuse existing ontology and check contracts.
2. Prepare explicit links and native scenario declarations for outcome
   precedence. Keep unsupported behavioral checks visible.
3. Produce one derived authoring report without changing canonical status.
4. Probe sensitivity on copies: remove a required binding, remove a required
   case, introduce conflicting outcomes, and use a stale input binding.
5. Confirm unrelated optional relations and a large closed leaf do not cause
   mandatory refinement; confirm missing compiler/check support remains unknown.

These cases plan future verification; none has been executed by this proposal.
Success means a reproducible report identifies each deliberately introduced
gap and its source, preserves the expected inventory and recommends the right
bounded follow-up. Report generation alone is not success. This pilot does not
claim universal completeness or one-pass implementation reliability.

Resume through `proposal::0233-mechanical-specification-authoring`, targeting
SG-SPEC-0015. The first pending action is review of this bounded pilot profile,
then preparation of its inventory/check bindings. No agent run, automatic
schedule, canonical refinement or runtime gate is authorized by registration.
