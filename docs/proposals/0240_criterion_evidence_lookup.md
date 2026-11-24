# Look up retained evidence for one acceptance criterion

RFC: SG-RFC-0240

Status: Draft

An agent can use the [C2c provider](0226_traceability_evidence_providers_and_svc.md#c2c-criterion-observation-report)
after finding the passport, binding plan and journal. The
[ExamCalc observation](../archive/proposal_sources/0240_criterion_evidence_lookup.md)
shows the missing operation: start from the acceptance criterion and find the
retained materials relevant to that exact declaration.

The first slice is a read-only native runtime operation for one selected product
workspace, spec ID, full Git revision and acceptance JSON Pointer.
[SG-SPEC-0068](../../specs/nodes/SG-SPEC-0068.yaml) anchors exact historical
lookup. A legacy pointer such as `/acceptance/1` is revision-scoped and allocates
no criterion subject. [0234](0234_verification_workflow.md) owns execution;
[0225](0225_tests_verified_evidence_admission_plan.md) owns admission.

## Proposed behavior

- Resolve the spec inside the selected workspace at the requested commit. Check
  the file digest and criterion pointer against the retained binding. If the
  source, revision or criterion is unavailable, report that before examining
  observations. A matching pointer or text on another revision is insufficient.
- Start from the project's explicitly configured retained artifact locations.
  Resolve only declarations with matching workspace, spec, declaration
  revision, file digest and pointer. Return the local FeaturePassport, binding
  plan, journal and report references that apply, including the recorded run
  identity. If several runs match, list them separately for selection; file
  timestamps and the most favorable outcome cannot select a run. A missing
  registration is distinct from a missing file at a declared locator.
- Return the selected C2c observation with its test/execution source revision,
  binding integrity, observed outcome and admission as separate fields.
  Preserve the distinction between a readable historical report and the
  current availability of its underlying inputs. If a journal is missing,
  the report may still describe past observations with its original provenance,
  while current rechecking is unavailable. Use the existing C2c contract for
  validation and interpreted outcomes.

The lookup reads retained artifacts and can be used by a later agent or Viewer.
It neither starts tests nor changes their results or lifecycle. The first slice
uses retained run artifact references from workflow 0234.

## Native runtime slice

From the selected product Git workspace:

```sh
specgraph-runtime --workspace /path/to/product criterion-evidence -- PRODUCT-SPEC-0001 \
  --revision FULL_DECLARATION_COMMIT --criterion /acceptance/1 --runs-root /path/to/retained-runs
```

Set `--runs-root` to the workflow's local output directory. Relative paths are
relative to the selected workspace. The declaration revision supplies
`specgraph.project.yaml` and the exact `specs/nodes/<ID>.yaml` blob. The project
ID selects the run's workspace and is the default repository ID. Use
`--repository-id` when the producer records a separate repository ID.

The reader opens `terminal.json` only under immediate UUID-named run directories
of the selected root, with a limit of 1,000 directory entries. Each matching record preserves the run ID, terminal
digest, workflow outcome, verification outcome and local admission. Its
collection must match the pinned C2c report before the selected historical row
is returned. Selected artifact paths are relative to the run directory.
`recheck_inputs` describes the current availability and integrity of the
retained report, passport, binding plan and journal bytes. Rechecking C2c
observations is a separate operation.

The JSON report has status `found`, `not_found` or `incomplete` when a catalog
was read. A corrupt or unreadable run entry appears in findings. Exit 0 means
the lookup produced a report. An invalid request or unavailable required
source or catalog returns 2 with `invalid` or `unavailable`. This slice reads
`verify-criteria/v1` terminal records. Independently archived C2c reports are
outside the first slice.

## Acceptance cases for the first implementation

| Control | Expected result |
| --- | --- |
| Exact ExamCalc criterion with available, matching inputs | Select the late-return row and show its passport, plan, report and run references. The preserved local observation is `checked / passed` with admission `not_evaluated`. |
| Same declaration, missing journal | Name the missing journal and show that rechecking is unavailable, even when an older report is readable. |
| Journal exists but bytes differ | Show the integrity problem. No checked observation from those bytes. |
| Pointer reused on another spec revision | Withhold the earlier observation for the new revision. |
| Two retained runs match | Return both run identities and individual results without combining verdicts or selecting a default run. |
| No workspace artifact declarations | Report the missing configuration rather than claiming no evidence exists. |

Use synthetic retained artifacts for public regression tests. The local ExamCalc
scenario was checked on saved runs and separate local copies. See the
[pilot result](../reviews/0240_criterion_evidence_lookup/examcalc-pilot.json). Track this work through
`proposal::0240-criterion-evidence-lookup`.
