# Workspace structural limits: proposal 0222

## Scope and source

The Zeusus product owner requested implementation on 2026-09-30. Earlier pilot
feedback recorded workspace-level acceptance overrides on 2026-09-26. Proposal
0222 preserves repository defaults and all authority/evidence admission rules.
The proposal ID was allocated from refreshed origin/main `0d3b004` after checking
proposal files, registries, branches/worktrees and open PR740 for collisions.

## TDD observations

- Characterization: five criteria accepted; six rejected at the default five.
- Initial Red: 1 characterization passed, 16 new tests failed. A configured
  seven-criterion candidate was still rejected against the global five.
- Green: focused workspace tests verify strict types, all nine configurable
  keys, fallback defaults, workspace isolation, scoped snapshot immutability,
  exception cleanup, prompt/inspector/changed-spec agreement, source digests,
  SpecificationCore rule traces in persisted evidence and historical digest
  verification.
- SpecificationCore uses ordered `FirstMatch` classification and named
  `PredicateSpec` value rules with stable `SG-RFC-0222.structural_limits.*`
  identifiers. This is the Python package pinned by this repository.

## Real CLI smoke

A temporary workspace reused the Zeusus project-config shape with real YAML.
The installed task supervisor was invoked with that directory as cwd.

- `--build-project-environment --output-mode full`: exit 0, effective acceptance
  limit 8 and blocking-child limit 5; unspecified graph settings inherit policy.
- Changing acceptance count to YAML `true`, then `--dry-run`: exit 1 and
  `invalid structural limit atomicity_max_acceptance: True`, before executor.
- Temporary config was removed. No Zeusus configuration or specification changed.

This is runtime/config evidence, not a signed receipt or canonical adoption.
Historical logs without a recorded snapshot retain the legacy default fallback;
their original workspace settings are not reconstructed.

## Repeatable checks

```bash
make test-workspace-limits
make docc-sync proposal-tracking-gate
python -m pytest -q tests/test_supervisor.py tests/test_workspace_structural_limits.py \
  tests/test_supervisor_problem_diagnosis.py tests/test_supervisor_problem_diagnosis_policy.py \
  tests/test_docc_sync.py
ruff check tools/supervisor.py tools/supervisor_structural_limits.py \
  tests/test_workspace_structural_limits.py
git diff --check
```

Use a Python >=3.10 environment; the host's Xcode-provided Python 3.9 was
rejected by the existing interpreter check, so the repository venv was used.

## Initial implementation checks (before SpecificationCore follow-up)

- The initial implementation combined suite passed 1096 tests. This predates
  the SpecificationCore correction and is retained only as historical evidence.
- Focused suite after SpecificationCore correction: 49 passed.
- DocC sync: passed.
- Proposal tracking gate: passed; proposal 0222 has runtime, validation and
  observation markers plus an archived source draft and promotion record.
- Ruff and diff whitespace checks: passed.

## Final SpecificationCore follow-up checks

The full combined suite was rerun after adding SpecificationCore and trace
evidence. Its final result is recorded here before the PR is updated.
