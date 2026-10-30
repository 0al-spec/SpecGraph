# First authoring baseline

This is the first executed observation slice of proposal 0233, following the
operator's instruction to begin the pilot after merging #829–836. It does not
complete the proposed authoring profile or activate a readiness gate.

Selected revision: `a980ba6f3c76153e7990f6fdad6cfd2536a3f1f0`. SG-SPEC-0072 bytes
match the historical pilot revision exactly; selection is explicitly renewed.
The baseline runner is new in this PR. [Provenance](provenance.json) records its
hash separately from the selected source revision.

## Observed results

The unchanged source has four acceptance criteria, six prose acceptance cases,
and no native BDD scenarios. The expected inventory remains four rows in every
mutation experiment; its source-hash/pointer identities are snapshot-local,
not stable intent atom identities across edits.

| Copy-only experiment | Existing check observation |
| --- | --- |
| Remove one evidence row | Acceptance shape mismatch detected |
| Remove a criterion and matching evidence | No acceptance shape error; source inventory still has four rows |
| Remove the mixed-outcome prose case | No finding from the selected declaration checks |
| Contradict outcome precedence in prose | No finding from the selected declaration checks |
| Add a synthetic linked native scenario | Declaration accepted; behavior not executed |
| Remove that referenced scenario | Unresolved local reference detected |

These are results of `validate_acceptance_evidence` and native BDD only, not a
claim that every SpecGraph checker misses these changes. Full semantic checks,
ontology compilation and a new authoring profile were not executed.

[Supervisor graph health](graph-health.json) observed one leaf, zero signals and
no recommended actions. This is graph shape, not a completeness certificate.
Separately, all 20 existing project-context tests passed using fixture compiler
inputs and mocked failures. They verify implementation behavior within their
test scope; they do not establish coverage of every source obligation.

## Reproduction and return task

From repository root, use the repository Python environment:

```sh
.venv/bin/python tools/authoring_pilot_baseline.py specs/nodes/SG-SPEC-0072.yaml
.venv/bin/python tools/supervisor.py --target-spec SG-SPEC-0072 --observe-graph-health
.venv/bin/python -m pytest -q tests/test_authoring_pilot_baseline.py tests/test_project_ontology_context.py
```

[Declaration observations](declaration-observations.json) are reproducible on
the selected bytes. Source hash changes mean a different experiment; this tool
does not admit reports as fresh evidence or produce a readiness score.

Return through `proposal::0233-mechanical-specification-authoring`. Next bounded
slice: review a frozen expected inventory for the four outcome-precedence rows,
link them to scenario IDs and executable checks, and define applicable ontology
bindings. Then probe deletion, contradictory machine-readable expectations and
stale inputs against that inventory. Missing bindings, optional relations,
large-leaf completeness and stale-report admission remain unsupported here.
No source-obligation coverage ratio or SIB readiness claim is calculated.
