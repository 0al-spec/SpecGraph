# Source: 0226 criterion observation report

## Operator intent and authorization

The operator requested that the local ExamCalc experiment lead to a proposal in
SpecGraph, rather than treating an ExamCalc proposal as the tooling change.
The final bounded exchange was:

> Agent: Следующий шаг — закрепить этот целевой результат в proposal SpecGraph,
> используя ExamCalc как проверочный пример.

> Human: Да, звучит хорошо, давай делать.

The earlier agreed division was 0224 + FeaturePassport + 0226, with admission
separate under 0225. These are agent-attributed excerpts from the current
conversation; no authenticated speaker identity or original message timestamp
is claimed. Authorization covers preparing this proposal amendment and PR,
not canonical adoption, a receipt authority or automatic runtime activation.

## Pinned observations

SpecGraph source/runtime: `92cb1f4eb4b96e39598edfb9b2671d9d4903a313`.
FeaturePassport source: `0fe35e9edb1461744ffa89161ec64cc86d44f728`.
ExamCalc is a local-only project; no remote repository is asserted or created.

| Local ExamCalc commit | Artifact path within that repository | Observed scope |
| --- | --- | --- |
| `39c2e44` | `docs/evidence/specgraph-aggregation/README.md` and `results.json` | Native trace index sees 0/3 mappings; exact Russian declarations produce 1/3; deleting JSON does not change that; English diagnostic declarations produce 3/3 without JSON |
| `6b1c9a4` | `docs/proposals/0004-joint-criterion-evidence-pilot.md` | Local pilot proposal; not the SpecGraph tooling proposal |
| `6b1c9a4` | `evidence/feature-passport/tablet-return.passport.json` and `bindings.json` | Draft passport plus an explicitly ExamCalc-owned experimental binding format |
| `6b1c9a4` | `docs/evidence/feature-passport-pilot/report.json` | Three local-observation rows, exact original journal joins, producer-declared execution-source provenance, no receipt or admission |
| `6b1c9a4` | `tests/test_evidence_pilot.py` | Nine locally executed adapter controls; not native SpecGraph tests |
| `6b1c9a4` | `docs/evidence/feature-passport-pilot/passport-validation.json` | Native FeaturePassport accepts the draft and rejects unknown criterion / wrong test role |

These paths are locators for the operator's local evidence, not public links or
bundled test fixtures. This PR publishes the curated design and bounded result
summary only; it does not copy the local notebook, journals, application code or
test artifacts. Public reviewers can inspect the repository contracts below;
replaying the consumer observation requires access to its local inputs.

The native `derive_acceptance_coverage` compares textual declarations, not
execution artifacts. `SEMANTIC_WORD_RE` at the pinned source is ASCII-only:
the first Russian criterion contains `unknown`; the others have no matching
tokens. This explains the 1/3 observation but is not fixed by this proposal.
The evidence-plane registry is surface-level; no consumer registry was supplied.
Thus `untracked` was not interpreted as loss of the existing observations.

## Existing implementation inspected

- `tools/traceability/evidence.py`: explicit immutable `EvidenceScope`,
  `EvidenceRequest`, provider identity and source evidence.
- `tools/traceability/providers.py`: explicit registered providers, not dynamic
  imports or plugin discovery.
- `tools/traceability/publication_execution_provider.py`: retained publication
  reports, not a generic Cucumber reader.
- `docs/evidence_provider.md`: source-pinned, derived, conservative collection.
- Proposals 0224 and 0225: producer bindings and separate trusted admission.
- FeaturePassport v1 schema/validator at the revision above: envelope and local
  reference validation. The source resolver supports Swift; TypeScript anchors
  in the pilot were not claimed as resolved by it.

The new C2c contract is author synthesis of these observations and the operator's
request. No fresh autonomous refinement run or independent review is claimed.
No canonical SG-SPEC-0021 criteria or lifecycle state are changed.
