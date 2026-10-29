# Project ontology context: Supervisor review packet

Status: **review candidate**, not canonical adoption or runtime implementation.
The implementation must follow a reviewed specification contract; proposal 0232
alone was not used as permission to bypass this step.

## Actual Supervisor cycle

1. Targeted SG-SPEC-0064 under proposal 0232 using the standard profile
   (Sol 6.1 Medium), without auto-approval. Run
   `20261029T182812Z-SG-SPEC-0064-40f74cb3` returned `split_required` and named
   a dedicated project ontology context child.
2. Preserved the intermediate parent candidate and restored the parent source.
   Its environment error was a false positive from quoted examples in
   CONTRIBUTING.md; the original error remains in `selection-run.json`.
   `executor_environment.primary_failure` was false. This packet does not fix
   the classifier or rewrite historical run outcomes.
3. Invoked one `materialize_one_child` pass on the same parent using the
   materialize profile (Sol 6.1 Medium). Run
   `20261029T183152Z-SG-SPEC-0064-356a72ac` returned `done`,
   `completion_status: ok`, `gate_state: review_pending`, zero validation errors,
   and `accepted_canonical_diff: false`.
4. Exported the two exact candidate files and restored the main checkout's
   canonical parent. The candidate child is not installed under `specs/nodes`.

## Proposed contract and topology

- [SG-SPEC-0072 candidate](candidates/SG-SPEC-0072.yaml): explicit project
  selection of one package or a compatible set; immutable context identity;
  scoped `verified`, `unavailable` and `invalid` outcomes; separate authority.
- [SG-SPEC-0064 candidate](candidates/SG-SPEC-0064.yaml): dependency and member
  reconciliation only. Detailed selection rules stay in the child.
- [Child run observation](child-run.json): original outcomes, validator results,
  original run digest and exact candidate inventory.
- [First run observation](selection-run.json): retained diagnostic and the
  intermediate refinement, superseded by the dedicated-child candidate for
  design review. It is not an additional accepted contract.

The four child acceptance entries are specification obligations, not four
passing behavioral tests. The future package-selection/runtime checks have not
been executed because no implementation is included. The original Supervisor
checked outputs, allowed paths, reconciliation, atomicity, transition and
refinement acceptance. Reconciliation found no cycles; work dependencies were
not ready for lifecycle progression.

## Gate and review scope

The run's existing soft ontology gate reported example `ExamPolicy` and related
findings. This artifact's relevance and freshness for project context selection
are not established by the run. It suppressed auto-approval and was not cleared
or used as proof of a current defect in the proposed contract. The run's required
human action still says `resolve_blocking_ontology_semantic_findings`.

Review the two candidate definitions and their topology against the attributed
0232 source. The proposed `verified` outcome concerns declared structural checks;
it cannot approve meanings, complete terminology coverage or implementation.
No compiler/storage/CLI/UI code, package changes or global policy activation
belong to this candidate.

The main parent has been restored, so do not call `--resolve-gate ... approve`
against it and assume these exported files were adopted. A subsequent approved
adoption must reconstruct the reviewed candidate/gate through the supported
Supervisor path, verify current base and candidate hashes and recheck allocation
of proposed ID SG-SPEC-0072 before applying the parent and child together.
Do not interpret merging this review packet as that approval. A changed
candidate requires a new reviewed inventory.

After contract review/adoption, the first implementation slice selects the
minimal project configuration shape and connects the existing snapshot-backed
binding reports. Other 0232 coverage, freshness, migration and UI obligations
remain separately scoped follow-ups.

## Worktree disposition

Both temporary run worktrees are retired. The second candidate remains on its
local run branch at the commit recorded in `child-run.json`, and exact parent/child
copies are retained in this packet. Bytes were compared before retirement; the
run tree had no ignored data and its staged YAML format/lint hooks passed.
Historical run JSON and transcripts remain under the primary checkout's ignored
`runs/`; curated outcomes and their original artifact digests are retained here.
