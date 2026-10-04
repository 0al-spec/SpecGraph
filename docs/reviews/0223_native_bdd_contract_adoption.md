# RFC 0223: native BDD contract adoption and loader evidence

## Human decision

On 2026-10-03 the owner replied **“ок / делай”** to the next steps: merge #757,
accept the native BDD contract, then implement the shared loader. This records the
actual conversation authorization; a green CI or merge is not its substitute.

The reviewed candidate is pinned by SHA-256 in
[SG-SPEC-0070](../../specs/nodes/SG-SPEC-0070.yaml). Independent Astra Max rechecked
`dff02dbb28c5fc571f66b24bb4d33cb3eecfa478`: all three findings resolved, no new
contradictions, 75 compatibility tests passed and nine hashes matched. Rebase to
`70aa9cb9` retained semantic content; its only conflict combined independent DocC
registry entries. #757 merged as `a5ab64363d054bae759b81441da6b79dbd4a9e86`.
The historical preparation, raw result, observation hashes and pending historical
gate remain unchanged. This is a new adoption record, not a rewrite of old evidence.

## Allocation and bounded authority

SG-SPEC-0070 refines SG-SPEC-0062. Before allocation, read-only discovery searched
1,067 refs (598 unique tip commits), 97 worktrees, run/proposal reservations and
open PR metadata/diffs for the exact ID and node path: no claims found. Historical
commits outside ref tips were not exhaustively scanned. No new node kind, edge
kind or Requirement/criterion ID is created.

Native contract approval authorizes the explicit read-only `load_native_bdd` API. It does
not activate consumer defaults, migrate sources, execute BDD steps, choose
normalized digest bytes, implement Gherkin or admit trusted evidence. Six RFC rule
references remain stable and are mapped to SG-SPEC-0070 policy objects; they are
not substituted for durable Requirement/criterion identities.

## TDD and current evidence

Observed Red: collection of `tests/test_native_bdd_loader.py` failed with
`ModuleNotFoundError: native_bdd`. Minimal Green: all initial 26 tests passed.
Refactor replaced type-based policy dispatch with policy-owned transitions.
Additional regression cases bring the strict suite to 34 passing tests; those
additional cases do not carry separate observed Red evidence.

A separate privacy regression observed Red when an unsupported profile supplied
a path leaked into events; Green records only a policy-classified safe profile
label. The original selection remains in the result for diagnosis. The API
requires explicit `profile="bdd_scenarios_v1"` selection.

The existing consumer remains unchanged and its 75 compatibility tests continue
to be checked separately. Historical future scenarios are declarations; this
slice exercises their native semantics, not Zeusus gameplay or trusted evidence.

| Object | Module | Scenario coverage |
| --- | --- | --- |
| BDDProfileSelectionSpec | tools/native_bdd/profile_spec.py | BDD-NATIVE-UNKNOWN-PROFILE |
| BDDContainerPresenceSpec | tools/native_bdd/presence_spec.py | BDD-NATIVE-ABSENT, EMPTY, ALTERNATE, AMBIGUOUS |
| BDDScenarioFieldsSpec | tools/native_bdd/fields_spec.py | BDD-NATIVE-UNKNOWN-FIELD, COMBINED-ERROR, TIMESTAMP title |
| BDDScenarioValuesSpec | tools/native_bdd/values_spec.py | BDD-NATIVE-EXACT-STEPS, TIMESTAMP, COMBINED-ERROR |
| BDDScenarioIDsSpec | tools/native_bdd/ids_spec.py | duplicate local IDs and prerequisite skips |
| BDDScenarioReferencesSpec | tools/native_bdd/references_spec.py | BDD-NATIVE-LOCAL-REFERENCE, TIMESTAMP reference |

`BDD-NATIVE-DUPLICATE-KEY` is the strict YAML edge, checked before domain maps.
`BDD-NATIVE-NO-AUTHORITY` is verified through result flags and privacy-safe events.
`BDD-NATIVE-COMPATIBILITY` is the unchanged 75-case consumer suite, not a new
compatibility coercion mode inside the strict loader. The composed call site is
`tools/native_bdd/composition.py:evaluate`; each eligible rule uses
`SpecificationCore.is_satisfied_by`. Source SHA-256 pins UTF-8 input bytes; no
normalized scenario digest is generated. Events contain classification and
policy outcomes, not titles, steps or absolute paths. Durations never affect results.

## Next integration

Integrate an explicitly selected strict profile into one consumer, with existing
compatibility mode preserved and tests for profile provenance and failed handoff.
Source migration, Gherkin and evidence admission follow separately.


## Review fixes on PR #759

Four threads identified: include implementation artifacts in node outputs/allowed
paths; preserve the selected safe profile on YAML boundary failures; use a supported
proposal posture; and register strict tests plus actual post-implementation
observation. Focused regressions reproduced both code defects before fixes.
The proposal runtime index now intentionally reports runtime `partial`, validation
`covered`, observation `covered`, and `next_gap: runtime_realization` because the
legacy implementation-contract consumer has not yet been integrated. See the
loader observation JSON for the generated index evidence.
