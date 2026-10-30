# Authoring proposal return path

SG-RFC-0233 preserves the human request to use the shared graph as a thinking
and memory system. This packet records the authoring design, not pilot execution.

- [Proposal](../../proposals/0233_mechanical_specification_authoring.md)
- [Exact attributed excerpts and synthesis](../../archive/proposal_sources/0233_mechanical_specification_authoring.md)
- [Draft obligations](../../proposals/0233_mechanical_specification_authoring.intent.yaml)
- [Authored operator packet](operator-request.json)
- [Registration observation](graph-links.json)

## Durable graph route

- [user_intent](../../../intent_layer/nodes/user_intent--0233-mechanical-specification-authoring--f1341ca0.json)
- [operator_request](../../../intent_layer/nodes/operator_request--0233-mechanical-specification-authoring--cafda04f.json)
- [proposal](../../../proposal_lane/nodes/proposal--0233-mechanical-specification-authoring--cf422918.json)

The route is UserIntent -> OperatorRequest -> Proposal -> SG-SPEC-0015.
The proposal remains `under_review`; the request is `proposal_linked`.
These records use existing graph kinds and query contracts. They are not
canonical Requirement/Intent publication and do not add a canonical spec node.
The authored proposal has an empty `proposal_queue_status`: it is not owned by
the derived Supervisor queue, so a queue refresh cannot retire it. Its review
state is recorded independently in `proposal_authority_state`.

The helpers listed in graph-links.json registered the authored packet without
calling an executor. Existing lineage vocabulary calls some authored-file links
`runtime_artifact`; that label is not evidence that a run occurred. There is no
supporting run ID, execution timestamp or canonical application event.

## Resume

Find `proposal::0233-mechanical-specification-authoring` in the existing proposal
lane overlay and follow its source/intent links. Start with review of the scoped
SG-SPEC-0072 outcome-precedence inventory and authoring profile. Its selected
revision is retained in graph-links.json; do not silently use a newer stack head.

Do not execute operator-request.json as a Supervisor CLI request: it is a
registration record, and that CLI path would also launch refinement. A later
bounded execution needs its own explicit request.

The proposal runtime/promotion registries retain the pending realization as
`deferred_until_canonicalized`;
`make proposal-tracking-gate` checks that it is accounted for. Existing derived
surfaces can be refreshed through these existing entrypoints, using the project
Python environment and configured local artifact/cache locations:

```sh
.venv/bin/python tools/supervisor.py --build-intent-layer-overlay
.venv/bin/python tools/supervisor.py --build-proposal-lane-overlay
make pre-spec-semantics proposal-spec-trace PYTHON=.venv/bin/python
```

Refreshing reports does not implement the proposal.

## Evidence and limits

Preparation inspected source at SpecGraph main
`ee8cb62f5acca18e884dcc19cf306ca6708ab7c5`, the SG-SPEC-0072 stack revision,
and the local Ontology/Metrics source checkouts. No fresh ontology compiler run,
behavioral pilot, statistical readiness calibration or deployment was performed.
Source excerpts are agent-attributed; original identity/timestamp is not attested.

Relevant existing sources to recheck before implementing:

- `tools/supervisor.py`: acceptance evidence, atomicity and graph-health functions.
- `tools/metric_packs/legacy_verifiability.py`: legacy denominator behavior.
- `tools/native_bdd/boundary.py`: declaration-only checks and profile selection.
- `ontology/packages/specgraph-core/domain-ontology-package.yaml`: optional links.
- Ontology `Sources/OntologyCompiler/SpecGraphValidation.swift`,
  `GoldenIntentValidation.swift`, `InstanceGraphValidation.swift`.
- Metrics `SIB_FULL/sib_full_metrics.tex` and `METRIC_PACKS.md`.

## Workspace disposition

Prepared in the primary SpecGraph checkout on
`codex/0233-mechanical-spec-authoring`, based on main; no extra worktree created.
The focused PR is the durable review handoff. The primary checkout can return
to main after publication; no service or notebook depends on this branch.
