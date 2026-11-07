# Commit-time ontology advice: source and scope

The operator's standing direction, recorded here as locally attributed
conversation text, was:

> Ложные предупреждения нужно проводить как дефекты тоже через граф со всеми вытекающими процедурами

On 2026-11-07, a SpecGraph commit containing the valid draft
`SG-SPEC-0053/intent-to-proposal` ontology at
[SpecGraph revision f48d26a2](https://github.com/0al-spec/SpecGraph/blob/f48d26a26d68b834347c1e3685be8f11db24e56d/specs/models/SG-SPEC-0053/intent-to-proposal/domain-ontology-package.yaml)
produced seven advisory errors about
`ref` and action-relationship fields. The same source passes the
Ontology 0.8.0 compiler pinned by SpecGraph PR #890. The configured local Git
hook pointed to a different, older compiler binary; it remained non-blocking.
This observation concerns that installation and commit-time advisory. It does
not establish a defect in the 0.8.0 compiler or an invalid ontology package.

The repository's selected release and the local hook executable are independent
inputs. [SG-SPEC-0072](../../../../specs/nodes/SG-SPEC-0072.yaml) distinguishes the
selected compiler identity from the ontology package identity for project
context selection. Its scope does **not** prescribe Git hook implementation.
The Ontology project's
[advisory documentation](https://github.com/0al-spec/Ontology/blob/0.8.0/SPECS/ontology/ontologyc.md#commit-time-package-advice)
describes a local, non-blocking hook and a separate strict `ontologyc check`.

The local hook was switched to a verified 0.8.0 release binary after an isolated
staged-index reproduction. The previous binary and a local configuration backup
were retained. A real Git configured hook was then exercised in an isolated
repository: the valid model was quiet and a missing target was reported.
This repairs the observed workstation configuration, not automatic alignment
of every workstation or future release upgrade.

The [defect record](defect.json), [operator packet](operator-request.json), and
[verification record](verification.json) connect this observation to the
existing intent and proposal lanes. The prepared regression runs the selected
compiler against both valid and deliberately invalid staged packages. It must
pass CI and review before the tracked change can be considered delivered.
Automatic detection or updating of an outdated installed hook remains a
follow-up, not a claimed part of this repair.
