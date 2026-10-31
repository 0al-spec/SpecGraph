# Local scenario pilot

The operator chose lightweight, optional formalization alongside specifications;
[source excerpts](source.md) retain that direction separately from the earlier
norm-package discussion. This slice continues
`proposal::0233-mechanical-specification-authoring` and the
[executed baseline](../baseline/README.md).

The editable [SG72-MIXED model](../../../../specs/models/SG-SPEC-0072/README.md)
combines two check results. It reuses project-local `specgraph-core` and a small
local draft extension, generating TypeScript through ontologyc on demand. It
neither expands the global selected ontology nor activates an authoring gate.

## What this experiment must demonstrate

1. Compile the draft and instantiate actual generated SDK types.
2. Link the readable scenario and exact spec clauses to the model.
3. Check the expected invalid outcome and preservation of both diagnostics
   against one bounded execution of the current implementation.
4. Reject intentional construction and relationship mistakes, and expose
   deleted mappings instead of silently reducing the modelled scope.

Structural compilation, scenario checks, execution observations and completeness
are separate results. The four acceptance rows remain visible; only a fragment
of the third is modelled. The earlier baseline and original approval/registration
records are not rewritten by this run.

## Executed result — 2026-10-30

The [curated observation](observation.json) records real ontologyc SDK generation,
TypeScript 6.0.3 compilation, the local instance checks and an execution of
`capture_project_context`. All four layers passed for the authored model. The
implementation returned `invalid`, retaining the selection-invalid and
compiler-unavailable diagnostics. Other diagnostics remain in the observation;
the scenario does not claim there were only two checks overall.

| Intentional change in a disposable copy | Observed boundary |
| --- | --- |
| Remove a required SDK field or use an unknown type/relation | TypeScript diagnostic |
| Connect a check edge to a Requirement instead | Model domain/range diagnostic |
| Remove the spec-to-requirement edge, a check or its diagnostic | Model diagnostic |
| Declare a different overall result | Source/model expectation mismatch |
| Keep a well-formed but incorrect diagnostic expectation | Execution comparison mismatch |
| Remove a source clause/coverage row, change the source ID or use a stale hash | Source-binding diagnostic |
| Reuse a nonempty output directory | Refusal; previous report preserved |

The focused test run passed **43 tests**, comprising 9 source-mapping cases,
13 real-tool integration cases, and 21 existing baseline/context regressions.
No integration cases were skipped locally. Ordinary Python CI runs the pure
cases and skips the real-tool cases unless both tool environment variables are
configured; the local result does not claim hosted toolchain execution.

Independent review found and fixed a source-node ID mismatch that could survive
an updated source hash. An initial negative test also caught literal-type
narrowing in the consumer that hid the intended missing-link diagnostic behind
a TypeScript error. Both now have regressions. Repository Python quality,
DocC synchronization and proposal tracking checks passed.

Input and generated-output digests bind this observation to the tested bytes.
The receipt records the compiler binary hash with `provenance: not_verified`;
it does not attest a binary-to-source build or approve the model's interpretation.
Source clauses were selected and reviewed explicitly. The compiler cannot prove
that arbitrary prose or unmodelled criteria have been represented faithfully.

## Tooling friction to retain

The authored instance is 34 TypeScript lines; its local vocabulary adds 50 YAML
lines. The one-off runner and consumer add 482 Python/TypeScript lines, excluding
tests, the source map and documentation. These physical line counts describe
the prototype's footprint, not quality. This experiment establishes feasibility,
not low adoption cost: copying that adapter per specification would defeat the
operator's lightweight-authoring goal. A second case should establish reusable
parts before this becomes an authoring convention or distributable tool.

The compiler currently requires package policies and a state-machine section
even for a small local model. Package metadata must not be mistaken for an
executed lifecycle or a new project review policy. Generated primitive string
fields do not constrain outcomes to the three domain values, and generated
relations do not validate instance edges by themselves. The bounded consumer
supplies the relevant checks. This is useful feedback for improving authoring
ergonomics, not a reason to formalize every surrounding concept.

The future SpecSpace view can render the same model and diagnostics; a viewer
or editor is not implemented in this slice.

## Return task

Resume through `proposal::0233-mechanical-specification-authoring`. Try a second
bounded case with different relations before generalizing this consumer; measure
how much authoring and adapter code it reuses. Preserve the compiler's mandatory
policy/state-machine boilerplate and missing generic instance checks as concrete
Ontology ergonomics feedback. Global enforcement remains outside this pilot.

## Ontology 0.3.0 follow-up

The observations above describe the original 0.2.0 experiment; its receipt and
hashes remain unchanged. [Ontology 0.3.0](https://github.com/0al-spec/Ontology/releases/tag/0.3.0),
commit `d831e25b46095dfea5e17befbc88c5fdcd03e031`, addresses the package-format
friction through Ontology PR #78. The current local package omits both unused
sections instead of declaring a manual policy and an unbound state machine.
Its classes, relations, model and selected source obligations are unchanged.

The [new observation](ontology-030-observation.json) records a separate run:
the old compiler rejects this minimal source; the new compiler passes SDK
generation, TypeScript, instance checks and the same production behavior probe.
All 54 focused tests passed without skips, including the real-tool negative
cases and release-smoke boundary tests. The existing specgraph-core IR remains
byte-identical, with seven resolved refs and the same ClaimCalibration gap.
The compiler hash identifies the tested binary without authenticating its source.

CI checks the minimal package on macOS and Linux in addition to the existing
release compatibility smoke. This is a package check, not hosted execution of
the full scenario. The Python/TypeScript runner's complexity and the missing
generic instance checks remain follow-ups under proposal 0233; this release
update does not establish inexpensive reuse or complete acceptance coverage.

## Second scenario, 31 October 2026

At revision `76f2dbd2c30c95b696d7b2f95b91aa630e4cc16f` the same CLI
ran both cases with Ontology 0.3.0 and TypeScript 6.0.3. Each passed SDK
generation, type checking, instance validation and the production behavior probe.

| Scenario | Observed production checks | Overall context | Local report SHA-256 |
| --- | --- | --- | --- |
| `SG72-MIXED` | Duplicate selection invalid, required compiler unavailable | `invalid` | `02e0e11e99a26ce734038d0dd78413184169f8788040540aeb631cef84c02df7` |
| `SG72-UNSUPPORTED-CLOSURE` | Member verified, dependency closure unavailable for that member | `unavailable` | `b4cdb91c587964e7ba46636538c186885fea4b48d1b85d00ef8abaa497273ed3` |

The second case executed the compiler in the production capture. Its snapshot
matched the selected source, IR, package identity and compiler digest. The
observed compiler SHA-256 was `1d0128d27f33f04b46c3969e41a04f3ac365afbb748d4c1f7f45645c09839923`.
Each report above includes local run paths, so its digest identifies that run.
A repeat run can compare outcomes, checks, inputs and tool hashes.

The focused suite passed 59 tests with both tool paths configured. Controls
rejected a reversed, type-correct check relation, a diagnostic for another
package and a snapshot from a different compiler. The original self-contained
model from `bcee7569` also passed via the default CLI in a fresh directory.

The 55-line instance consumer serves both cases unchanged. They share a typed
case constructor, the package compiler steps and production capture. The
second case added 27 lines of TypeScript, 9 of Gherkin, a 64-line source map
and one vocabulary relation. Supporting both cost a net 127 Python lines
across the runner and its reviewed case definitions relative to `bcee7569`.
Each map still marks one of four acceptance criteria partial. A third case
could exercise `verified` and measure how much more adapter work it requires.

## Single-package verified probe, 31 October 2026

SG-SPEC-0072 acceptance case 0 requires successful structural checks for a
pinned package. The proposed third example needed a package with zero imports
because the current capture can verify closure only under that condition.
The pinned compiler rejects this prerequisite. The executable pilot still has
two cases. This experiment changed zero lines of runner code, and the cost of
adding a working third case remains unmeasured.

| Imports in the selected package | ontologyc check / compile | Production context CLI |
| --- | --- | --- |
| Empty list | Both exit 1 with `imports.empty`. No IR emitted. | No compiled IR to select |
| Omitted field | Both exit 1 with `spec.required` and `imports.empty`. No IR emitted. | No compiled IR to select |
| One pinned foundation import | Both exit 0. Compilation emits IR. | Exit 1, member verified, closure unavailable, context unavailable |

Removing the import from this fixture also leaves its two `sg:ValueObject` base
references unresolved. Independently of those references, the release schema
sets `minItems: 1` and the compiler unconditionally checks for an empty list.
Every compilable package in this format therefore takes the unsupported-import
branch of the current production capture. The 20 passing context tests include
a positive control using their own compiler fixture. See the
[observations, selected hashes and source revision](verified-single-probe.json),
[release schema](https://github.com/0al-spec/Ontology/blob/d831e25b46095dfea5e17befbc88c5fdcd03e031/SPECS/ontology/domain-ontology-package.schema.yaml),
[compiler validation](https://github.com/0al-spec/Ontology/blob/d831e25b46095dfea5e17befbc88c5fdcd03e031/Sources/OntologyCompiler/PackageValidation.swift#L22-L34)
and [context capture](https://github.com/0al-spec/SpecGraph/blob/a42077cf4ddd8c84e96fc684e0505533dcf906b4/tools/project_ontology_context/capture.py).

To replay from the SpecGraph checkout, set `work` to a fresh scratch directory,
`ONTOLOGY_CHECKOUT` to an Ontology checkout containing the release and
`ONTOLOGYC` to the built release binary. The receipt contains the exact
selection used for the successful package compilation.

```sh
git -C "$ONTOLOGY_CHECKOUT" show d831e25b46095dfea5e17befbc88c5fdcd03e031:SPECS/ontology/fixtures/valid/local-model-omitted-sections.yaml > "$work/upstream.yaml"
.venv/bin/python - "$work" <<'PYTHON'
import json, sys, yaml
from pathlib import Path
work = Path(sys.argv[1])
receipt = Path("docs/reviews/0233_mechanical_specification_authoring/local-model-pilot/verified-single-probe.json")
for variant in ("with-import", "empty-imports", "omitted-imports"):
    case = work / variant
    case.mkdir()
    data = yaml.safe_load((work / "upstream.yaml").read_bytes())
    if variant == "empty-imports":
        data["spec"]["imports"] = []
    elif variant == "omitted-imports":
        del data["spec"]["imports"]
    (case / "member.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
selection = json.loads(receipt.read_bytes())["with_import_control"]["selection"]
(work / "with-import/selection.yaml").write_text(yaml.safe_dump(selection))
PYTHON
for case in with-import empty-imports omitted-imports; do
  "$ONTOLOGYC" check "$work/$case/member.yaml" || printf 'check exit %s\n' "$?"
  "$ONTOLOGYC" compile "$work/$case/member.yaml" --target typescript --out "$work/$case/ir" || printf 'compile exit %s\n' "$?"
done
.venv/bin/python tools/project_ontology_context_cli.py --workspace-root "$work/with-import" \
  --project-id sg72-verified-probe --selection selection.yaml --ontologyc "$ONTOLOGYC" \
  --compiler-sha256 1d0128d27f33f04b46c3969e41a04f3ac365afbb748d4c1f7f45645c09839923
```

The compiler pin in the replay command identifies the observed binary. For a
different build, pin the digest of the executable being tested and record it
with the result. Return through proposal 0233 after SpecGraph can resolve a
pinned import, or after a released package format supports standalone packages.

## One pinned foundation import

The next pilot selected `ontologyc-foundation-v1` and compiled two versions
of the same ten-line member. Each version had a fresh source pin and IR pin.
The public context CLI verified `sg:ValueObject` and rejected `sg:Typo` as
invalid at `/spec/classes/Entry/extends`. Both reports identify the same
foundation glossary digest. Project-local `specgraph-core` also verified.
The [observation](pinned-foundation-observation.json) records the source revision,
binary and input hashes, pointer, result and report digests. The preceding
single-package observation used the original structural profile.

All three typed scenarios passed the SDK, typecheck, instance and production
layers. The original profiles still exercise invalid and unavailable. The
third model adds 27 lines of TypeScript and reuses the same consumer. Relative
to `0cedfcbf` the runner grew by 34 physical Python lines, case definitions
by 33, and the production resolver, capture and result types by 171 combined.
This experiment includes implementing a new product capability. Those counts
do not isolate the cost of declaring a case for an already supported import.

To replay both CLI controls and the production package, set `ONTOLOGYC_BINARY_PATH`
and run `python -m pytest -q tests/test_project_ontology_foundation.py` in the
repository environment. For the four-layer run use the
[model instructions](../../../../specs/models/SG-SPEC-0072/README.md).

## Released compiler control — Ontology 0.4.0

The [0.4.0 release](https://github.com/0al-spec/Ontology/releases/tag/0.4.0) changes the point at which SG72-PINNED-FOUNDATION detects a misspelled base. The compiler rejects the source before generating an IR. SpecGraph records the native diagnostic code, the checked source and compiler digests, and the field as a JSON pointer. The earlier 0.3.0 observation above retains the behavior of that release.

The [release-binary observation](ontology-040-observation.json) pairs the actual SG-SPEC-0072 package with a one-literal edit. It also checks the same rejection with a previously valid IR on disk, a valid source without IR, and the project-local core package. The adapter still reports the existing ClaimCalibration gap.
