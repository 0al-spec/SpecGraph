# External project ID rejected by the advisory operation

## Source and affected contract

Reported by the GitView motivation-composition pilot, GitView commit
`2ed5bb1`, using SpecGraph runtime `8e39d784`.
The source report is GitView's
`ontology/pilots/motivation-composition/README.md`, section
“Ограничение для будущих спецификаций GitView”.
The local intake receipt is
`20261101T065125Z-review-note-advisory-ontology-target-rejects-supported-external-project-spec-ids.md`.

Return anchors are SG-SPEC-0072 and
[proposal 0232](../../../proposals/0232_verified_project_ontology_context.md).
This records an implementation defect in the existing project-workspace
advisory operation. It introduces no canonical node kind or terminology decision.

## Reproduction and consequence

GitView selects `GITVIEW-SPEC` in `.specgraph/spec-id-policy.json`.
For a synthetic `specs/nodes/GITVIEW-SPEC-0001.yaml` containing that exact ID:

```sh
python /path/to/SpecGraph/tools/supervisor.py \
  --build-project-ontology-context-check \
  --target-spec GITVIEW-SPEC-0001 \
  --ontology-context-project-id gitview
```

The old CLI returns 2 with `--target-spec must be SG-SPEC-NNNN` before
attempting target/context capture. With no selected context the expected
outcome is instead `unavailable`, exit 1, retaining the captured target ID.
With a usable single-member context it can reach `checked`.
The defect is separate from the unsupported multi-member spec inventory.

A baseline test executed before the repair produced two failures for
GITVIEW and ACME-UI namespaces and one success for SG. It did not modify
the actual GitView workspace.

## Root cause, repair and prevention

Both `project_ontology_supervisor_cli.py` and
`project_ontology_supervisor_check.py` independently hardcoded
`SG-SPEC-[0-9]{4}`. The main Supervisor already supports product ID
namespaces. The duplicate narrower syntax prevented a portable advisory
operation from reaching an otherwise valid product specification.

Both advisory entry points now use `is_target_spec_id`: a safe uppercase
namespace followed by `-SPEC-` and an ASCII decimal suffix. This is mechanical
filename/input syntax validation. Allocation policy, canonical refinement and
alias resolution retain their existing owners and are not changed here.
An advisory request addresses the exact requested filename and YAML ID.
It does not require an allocation-policy file or silently follow its aliases.

Regressions in `tests/test_project_ontology_supervisor_cli.py` and
`tests/test_project_ontology_supervisor_check.py` cover product and legacy
IDs, checked and unavailable contexts, previous-report freshness, malformed
names, traversal, Unicode digits, symlink escape and mismatching YAML IDs.
The original target and project policy remain untouched. Existing output-owner
and path collision checks stay active.

## Status

The focused advisory/context/freshness/native-runtime suite passed 75 tests.
Python quality, DocC sync and proposal tracking passed.
[The retained observation](verification.json) records a source-checkout replay
against a separate TB5 copy of the real GitView composition pilot. The synthetic
GITVIEW target was captured, the composition was verified, and the operation
returned unavailable specifically for the unsupported joint inventory.
Original pilot file hashes were unchanged. Full reports remain on TB5.

Repair prepared on a PR branch; merge and distributed runtime availability
are separate events. The actual GitView project and its terms were not changed.
