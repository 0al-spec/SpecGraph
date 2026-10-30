# Verified ontology context: seven-PR implementation track

Source: the operator's direction in the active conversation on 2026-10-30
(Europe/Moscow): review SG-SPEC-0072, then prepare 5–7 stacked ontology PRs;
use Terra 6.1 High agents. This is attributed task direction, not authenticated
approval of every package meaning or a global enforcement policy.

The stack contains seven bounded slices, each targeting its predecessor. Root
owns integration and publication; agents own disjoint source/test paths. Runtime
layers depend on review of the selection contract. Preparing this stack does
not merge it or activate a production policy.

| Layer | Behavior | Boundary |
| --- | --- | --- |
| 1 | Reviewed SG-SPEC-0072 and parent reconciliation through Supervisor | Contract preparation; no implementation or semantic acceptance |
| 2 | Explicit selection, captured source/IR/compiler identity and scoped outcomes | Reuse OntologySnapshot; invalid > unavailable > verified |
| 3 | Workspace CLI and native runtime route | Explicit operator-provided compiler; no install, download or automatic init |
| 4 | Existing binding/validation reports consume one captured context/spec set | Local-symbol advisory scope; no legacy IR fallback or semantic approval |
| 5 | Explicit freshness assessment for saved advisory reports | Match actual project/context/spec/binding/profile inputs; no automatic cache or new merge gate |
| 6 | Explicit-term inventory and attributable gaps | Declared fields/references only; normative prose remains unassessed |
| 7 | Target-scoped Supervisor context-check operation | Opt-in report generation; preserve existing refinement/approval authority |

Layers 4–7 extend the existing report-only 0134/0135/0138/0140 and 0109/0117
surfaces in the direction of 0232. They do not treat those draft proposals or
the SG-SPEC-0072 selection contract as approval of whole-prose coverage,
cross-operation cache admission or a global Supervisor readiness policy.
Technical report profiles must describe their exact input scope. Any later
governance activation requires its own bounded review.

The single no-import package path may establish its declared structural scope.
The current specgraph-core package imports specgraph.foundation; compiling the
root alone does not prove closure. Unsupported dependency/composition checks
remain unavailable, and compiler hashes identify bytes without attesting their
origin. Structurally usable local vocabulary and semantic acceptance remain
separate. Draft capture stays available throughout.

Verification uses focused behavioral tests, existing quality/DocC/tracking
checks and immutable source inventories. Each SpecificationMetrics report
receives a revision-bound explanation. No S/U, complexity or duplication gain
is assumed before measurement. Native installation, real compiler execution,
hosted CI and visual/runtime product evidence are reported separately.

The implementation source and hardening return path is registered through native
intent/operator-request/proposal lanes; concrete paths are in
`marathon/graph-links.json`. `marathon/defects.json` records the compiler-pin,
abbreviated-workspace, hosted-test-environment, legacy CLI abbreviation and
output/input collision defects with repair/test refs.
These are prepared fixes under review, not merged closure. The registration-only
packet does not claim another model run or signed human approval. No new
canonical Defect kind or new gate is introduced.

## Prepared stack and verification

| PR | Slice |
| --- | --- |
| [829](https://github.com/0al-spec/SpecGraph/pull/829) | Supervisor-reviewed selection contract |
| [830](https://github.com/0al-spec/SpecGraph/pull/830) | Captured context and scoped outcome policies |
| [831](https://github.com/0al-spec/SpecGraph/pull/831) | External-workspace CLI and native route |
| [832](https://github.com/0al-spec/SpecGraph/pull/832) | Captured binding/validation bundle |
| [833](https://github.com/0al-spec/SpecGraph/pull/833) | Explicit saved-bundle freshness |
| [834](https://github.com/0al-spec/SpecGraph/pull/834) | Explicit-term inventory and attributable gaps |
| [835](https://github.com/0al-spec/SpecGraph/pull/835) | Target-scoped Supervisor operation and graph return path |

`marathon/verification.json` records the exact tested revision, attributed local
compiler bytes, actual Supervisor smoke, gates and test boundaries. The full
local run passed 3382 tests and failed two history-dependent live assertions;
those tests now use a controlled commit clock, and all four targeted live/drift
regressions passed. This does not claim a repeated green full local suite or
hosted CI. Production freshness is unchanged. Counts from overlapping focused
runs must not be added together.

Ten concrete hardening observations have repair/test references in the linked
native proposal return path. Source-level and hosted reviews remain separate
from final merge, semantic acceptance and production policy activation. The
next ontology slice is explicit imported dependency closure for specgraph-core;
current local advisory reports cannot prove it. Revision-bound execution evidence
for legacy trace freshness is also retained as a follow-up, not silently solved
by the test fixture.
