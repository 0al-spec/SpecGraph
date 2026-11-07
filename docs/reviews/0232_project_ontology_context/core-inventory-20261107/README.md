# SpecGraph core ontology: source-grounded inventory

This is a **review-only inventory**, not an approved replacement ontology.
It records the operator's request to improve and clarify the whole ontology
graph, examines every declaration in the selected core package, and identifies
bounded follow-up slices. No semantic acceptance, policy change or canonical
mutation is inferred from this inventory.

## Source and reproducibility

- Repository revision: `f48d26a26d68b834347c1e3685be8f11db24e56d`.
- [Core source](../../../../ontology/packages/specgraph-core/domain-ontology-package.yaml):
  `org.0al.specgraph.core@0.1.0`, approval status `draft`, SHA-256
  `5bfa2ff40b6174def589546ab2fea2501e1f256c4f1446f36c45c7f3fffcd929`.
- Normalized IR SHA-256:
  `7a9d1cb640f154c32a2a15a4ec8868349bee04be30a0b5da886422c0d3eb638f`.
- The `specs/nodes` Git tree is `ba90a085628322fa5a2dfacd590153986c4b4b1b`
  and contains 72 `SG-SPEC-*.yaml` files.
- [Machine-readable inventory](declaration-inventory.json) lists all 14 classes,
  16 relations, one policy and one state machine from that core source.
  [Verification](verification.json) records the bounded source and graph-overlay
  checks. Both are snapshots, not a guarantee that later revisions are covered.

The existing `make spec-ontology-bindings` report over those 72 specs returned
296 structural bindings, 143 relation candidates and 287 occurrences labelled
`legacy_unknown_term` (274 distinct exact term strings). Its
`ontology_verification.status` was `not_verified`. These are lexical and
structural review leads: the tool's `accepted_bindings` name does not mean
human acceptance, and neither an unknown word nor a count proves a missing
concept. The separate `make ontology-package-gaps` result is based on its
configured fixture and reports `sgcore:ClaimCalibration`; it is not a
whole-project completeness scan.

At the pinned revision, the legacy count can be reproduced with the repository
Python environment:

```sh
make spec-ontology-bindings
.venv/bin/python - <<'PY'
import json
from pathlib import Path
report = json.loads(Path("runs/spec_ontology_binding_index.json").read_bytes())
gaps = [gap for entry in report["entries"] for gap in entry["gaps"]]
print(report["summary"], report["ontology_verification"])
print("gap occurrences", len(gaps), "distinct exact terms", len({g["term"] for g in gaps}))
PY
```

A read-only Supervisor graph-health observation rooted at SG-SPEC-0001 covered
68 active subtree specs and listed four historical descendants; it reported no
graph-health signals for that run. This is a structural observation of the
specification subtree, not a semantic assessment of ontology completeness.

## Current declarations by concern

The groupings below partition the **existing** declarations; they do not assert
that each class is already semantically complete.

| Concern | Classes | Relations | Primary sources for the next review |
| --- | --- | --- | --- |
| Graph identity and containment | `SpecGraph`, `Node`, `Edge` | `containsNode`, `containsEdge`, `containsSpec`, `nodeConnectedByEdge`, `edgeRelatesNode` | SG-SPEC-0001, SG-SPEC-0014, SG-SPEC-0023 |
| Intent and specifications | `Intent`, `Spec` | `refinesIntent` | SG-SPEC-0001, SG-SPEC-0050, SG-SPEC-0053 |
| Obligations and governance | `Requirement`, `AcceptanceCriterion`, `Decision`, `Constraint`, `Invariant` | `definesRequirement`, `hasAcceptanceCriterion`, `requirementValidatedByCriterion`, `decisionConstrainsSpec`, `constraintAppliesToNode`, `invariantGovernsSpecGraph` | SG-SPEC-0001, SG-SPEC-0010, SG-SPEC-0051, SG-SPEC-0070 |
| Realization and evidence | `CodeSurface`, `Test`, `Evidence`, `Release` | `codeSurfaceImplementsSpec`, `testValidatesRequirement`, `releasePackagesCodeSurface`, `evidenceSupportsCriterion` | SG-SPEC-0017, SG-SPEC-0020, SG-SPEC-0061, SG-SPEC-0071 |

`DraftAuthorityBoundary` is a manual policy. `SpecReviewState` currently
declares `draft → reviewed` with `Decision` as its command. These are
included in the source inventory rather than treated as proof of runtime
enforcement.

## Review questions, not automatic defects

1. **Pre-spec meaning.** SG-SPEC-0053 distinguishes raw input,
   `IntentFragment`, `IntentDraft`, `Hypothesis` and `Proposal`; core
   declares `Intent` and `Spec`. The project-local draft from #891 and
   [follow-up #893](https://github.com/0al-spec/SpecGraph/pull/893) explore
   these missing declarations without yet adding them to core. Review which
   belong in core or a composed package and retain pre-canonical authority.
2. **Decision and action.** Core describes `Decision` as a chosen direction
   but extends `sg:Command` and uses it as a transition command. SG-SPEC-0001
   also describes a decision record with rationale. Determine whether these
   are intentionally the same concept, different roles or a type mismatch;
   do not silently replace the existing type.
3. **Lifecycle scope.** Core's two-state review machine and SG-SPEC-0001's
   seven node statuses may model different scopes. Establish their mapping and
   whether the `Spec` attachment implies more than intended before changing
   either state model.
4. **Relations and direction.** SG-SPEC-0014 and SG-SPEC-0023 define
   `refines`, `depends_on` and other typed edges with specific directions.
   Core's `refinesIntent` is only one narrower shape. Likewise
   `testValidatesRequirement` and SG-SPEC-0023's `tested_by` point in
   opposite directions; an inverse mapping needs an explicit contract rather
   than an assumed equivalence. Separately distinguish an Edge record from the
   relation type it represents.
5. **Evidence and authority.** SG-SPEC-0017 distinguishes
   `ObservabilityContract`, `Campaign` and `Attestation`, including
   provenance and claim disposition. Review how these relate to core
   `Evidence`; a declaration or provider report is not automatically an
   admitted or trusted observation.
6. **Completeness and change.** Review semantics and provenance for each
   existing declaration before deciding whether a missing source term deserves
   a class, relation, property, alias, separate package or no ontology entry.
   Preserve identity, versioning and compatibility; do not optimize for the
   number of nodes or for a particular viewer layout.

## Bounded continuation

Start with the pre-spec candidate, then review promotion and transition records
against SG-SPEC-0051, edge kinds against SG-SPEC-0023, and evidence against
SG-SPEC-0017 in separate source-bound slices. Investigate lifecycle and Decision
typing as explicit review questions. For each selected change, retain its
source, candidate model, compatibility effect and compiler/projection checks;
connect actual execution evidence only when it exists. Publish a revised core
or composed selection only after its actual review and update downstream pins
and viewer artifacts from that accepted source.

The [operator packet](operator-request.json) and
[proposal-lane record](graph-links.json)
provide a return route through the existing graph. They do not start an
executor or authorize canonical writes.
