# RFC 0226: recovered SG-SPEC-0021 candidate review

Prepared on 27 October 2026 against SpecGraph
`8e1a261b021ecc6c50b9d352f11a1543340f8988`. This review closes the analysis
return point WTR-0021 from the worktree recovery. It recommends a revised
semantic candidate; it does not adopt that candidate or activate atom SVC.

```yaml
status: review_only
canonical_mutations_allowed: false
runtime_profile_activation_allowed: false
evidence_admission_allowed: false
```

## Source and disposition

The original [proposal 0226 source](../archive/proposal_sources/0226_traceability_evidence_providers_and_svc.md)
records the operator's request for replaceable evidence sources and a bounded
self-improvement cycle. Its completed Supervisor run was
`20261021T193422Z-SG-SPEC-0021-6ca26a10`; the separate earlier protocol failures
are retained in [the cycle record](0226_supervisor_cycle.json).

The [original curated candidate](0226_metric_verifiability_candidate.patch)
remains unchanged, with SHA-256
`f99cb0d9fdac91b17d4d73af3444f0d9338ab5216cc7e8aab89eb90313aa80db`.
Recovery additionally retained the raw local salvage patch under run ID
`worktree-recovery-20261026t2150z-sg-spec-0021`, SHA-256
`5402411db9e681bae025a5e85f50a6ebbabbd381e772d8457db4eab6b035e599`.
The latter contains historical escalation/protocol metadata as well as the
semantic edits. Its archived worktree path is no longer a live execution target.

Do not replay that raw file or clear a historical gate. At the inspected
revision, [canonical SG-SPEC-0021](../../specs/nodes/SG-SPEC-0021.yaml) has
`gate_state: none`. The [revised review-only patch](0226_metric_verifiability_candidate_v2.patch)
is an author-curated successor, not a new Supervisor verdict or human approval.

## What to retain and tighten

| Original clarification | Source-grounded disposition |
| --- | --- |
| Declared link, resolved declaration, execution observation and result are distinct facts within existing input classes | Retain the distinctions; restrict the wording to authored evidence records and the derived facts they cite. Both permitted classes for Specification Verifiability are canonical. Merely naming a runtime observation cannot admit a new derived input class. |
| A claim of execution needs a run and a result; failure differs from absence | Retain, with the selected profile and recorded scope explicit. Optional missing execution does not invalidate a declaration-only assessment. A completed failure may support inspectability while still reporting failed fulfillment. |
| Missing, stale, unknown or incomplete inputs must not yield a complete zero | Retain the unknown/negative distinction, but preserve legitimate negative results from complete required inputs. A future profile may define a known zero; this family boundary does not define its formula. |
| Historical reviews do not establish current execution or later acceptance | Retain. Reusing a link requires resolution at the selected revision. Revision/run binding alone proves neither wall-clock freshness nor independent authenticity. |

SG-SPEC-0021's `metric_input_class_ontology` permits
`acceptance_criteria_and_evidence` and `trace_dependency_links` for this family.
It reserves `runtime_observability_entities` and `run_artifacts` for Process
Observability. Its `relationship_policy` requires explicitly declared input
classes. The revised wording therefore distinguishes a canonical record citing
an observation from admitting that observation as a new computational input.
Direct use of derived execution reports in a future Specification Verifiability
profile still needs an explicit reviewed input-boundary decision.

## What the implementation already covers

The [EvidenceProvider contract](../evidence_provider.md) describes implemented
C1 and C2a boundaries; [proposal 0226](../proposals/0226_traceability_evidence_providers_and_svc.md)
separately retains the future SVC qualification proposal.

| Boundary | Existing implementation and regression evidence |
| --- | --- |
| Resolution is not execution | C1 returns `execution: not_collected`. `test_single_collection_serves_legacy_facade_and_provider` and `test_independent_snapshot_cli` in `tests/test_evidence_provider.py` characterize the declaration snapshot. |
| Completeness is not success | `RESOLUTION_COMPLETENESS_SPEC` accepts conclusive negative resolution. `test_resolution_completeness_is_not_resolution_success`, `test_required_source_failure_remains_incomplete` and `test_missing_target_keeps_complete_atom_inventory` keep absence and independent completeness visible. |
| Retained outcomes require matching bindings | C2a keeps `producer_result` separate from `evaluated_result`. `test_wrong_source_is_retained_but_not_bound`, `test_wrong_report_run_is_not_bound` and `test_existing_suite_policy_preserves_failures_and_missing` in `tests/test_publication_execution_provider.py` cover the distinction. |
| Execution must not inflate inventory | `test_composition_preserves_declarations_and_uses_separate_profile` preserves C1 inventory while adding C2a reports; execution-only providers contribute no atom inventory. |
| Provenance binding is narrower than trust | Execution reports explicitly retain `provider_reported_not_attested` and `selected_revision_and_run_only`. C2a does not authenticate the producer, prove recency or reread original JUnit/HTTP bytes. |
| Historical review reuse | The proposal preserves base/head scope and requires resolution for another snapshot. C1/C2a do not implement a historical PR-review provider; that remains a future integration concern. |

These implementations provide relevant evidence for the proposed distinctions.
They do not make the proposed family semantics canonical, implement atom-level
SVC, or demonstrate that a resolved test sufficiently verifies an obligation.
The separate [claim-admission contract](../evidence_claim_admission.md) still
leaves `tests_verified` as `unknown / evidence_evaluator_unavailable`.

## Revised candidate and bounded next step

The v2 patch changes only Specification Verifiability boundary notes and the
existing acceptance-evidence explanation of that boundary. It preserves all
acceptance criteria, family names/roles, subjects, admissible input lists,
ontology entries, invariant IDs, lifecycle fields and runtime behavior.
It grants no canonical publication authority and selects no SVC formula.

The next semantic decision is whether to adopt those clarified meanings in
SG-SPEC-0021. If approved, apply only the v2 semantic delta in a focused
canonical-spec PR against its then-current base; perform the existing spec,
intent-decision and documentation checks. Do not invoke gate resolution for
the archived run. If the base changes, regenerate and review the delta rather
than treating a formerly applicable patch as current authority.

## Verification of this review slice

The v2 patch SHA-256 is
`df8f1bc4037a698ddf4fb57630b5b2ee6bbf4409a768577ba1797fde34c37728`.
It passed `git apply --check --whitespace=error`, application to a temporary
copy of the pinned canonical file, YAML parsing and a parsed-field comparison.
The only changed paths were `acceptance_evidence[2].evidence` and
`specification.metric_family_catalog[2].boundary_notes`. The actual canonical
file and original curated patch retained their hashes.

The existing `tests/test_evidence_provider.py` and
`tests/test_publication_execution_provider.py` suites passed all 82 cases.
`make docc-sync proposal-tracking-gate` also passed. These checks characterize
the existing provider boundaries and the candidate's shape; they do not enact
the proposed semantics or test an atom-SVC implementation.

## Following realization

After that decision, RFC 0226 C2b can separately propose the atom-to-check
qualification profile and any required derived-input admission. Existing
providers can be reused; another provider framework is not needed for this
candidate. SVC activation, `tests_verified` evaluation and signed admission
remain separate work with separate evidence requirements.
