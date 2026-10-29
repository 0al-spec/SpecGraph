# Verified Project Ontology Context: source draft

## Attributed operator direction

Conversation on 2026-10-29. The excerpt references below are local names for
messages available to the authoring agent, not native conversation identifiers,
authenticated identities or independently recovered timestamps. The excerpts
are the source of the proposed product direction; the detailed design is the
agent's interpretation for review.

`operator-excerpt:2026-10-29/project-ontology-context`:

> Встроить точно надо. Все спеки проекта должны опираться в терминологии на верифицированные онтологии или одну большую онтологию.

The operator also requested reuse of existing SpecSpace work:

`operator-excerpt:2026-10-29/specspace-ontology-graph`:

> Кстати в SpecSpace мы уже делали Ontology graph представление
> Поищи для контекста

After the agent proposed including the two existing SpecSpace surfaces in the
project-context proposal, the operator answered:

`operator-excerpt:2026-10-29/proposal-preparation`:

> Да, всё верно. Давай сделаем.

The earlier choice about structurally valid packages with unknown terms was:

> Разрешать использование, а gaps явно отправлять на review (рекомендую)

That choice allows use of the valid package while preserving gaps; it does not
resolve a particular unknown term or justify marking every specification as
fully grounded. Requiring a resolved term for a specific normative decision is
the bounded interpretation proposed here, not an already active global gate.

## Captured note and observed sources

- [Selected source-attributed note](../../reviews/0232_project_ontology_context/source-notes.json)
  was written using the existing conversation notes CLI. It remains
  `canonical: false`. Its original local sketch is ignored; this selected
  export is retained in Git. No approval operation was inferred for the sketch.
- SpecGraph inspected base: `a8d316bec2f8ac0ce3ea926f6f8675966f5ebad8`.
  `tools/ontology_snapshot.py` checks captured source and IR with a selected
  compiler. At this base only the release smoke consumes it.
- SpecGraph PR #825 at `e468aeaa` proposes optional checked inputs for the
  binding index and validation report. It is a dependency under review, not
  implemented behavior on this base and not the global guarantee.
- SpecSpace inspected commit: `bd3de6137ebe5c2fa2c53079b699f6d9d18f89da`.
  `docs/SPECSPACE_BOUNDARY.md`, `docs/ONTOLOGY_GRAPH_VIEWER_PRD.md`,
  `viewer/ontology_workbench.py` and the `graphspace/src/pages/ontology-viewer/`
  code distinguish workspace panels from local artifact inspection at
  `/ontology`. These observations are from source inspection, not a browser test.
- Ontology tooling release `0.2.0` pins
  `1a47f7058228efb412cbdeaabbaf27bca25e9846`. The source release version is
  separate from each ontology package's version and draft/approval status.
  Its `skills/ontology-action-model/`, `Examples/intent-preservation/`,
  `Examples/edit-cancellation/` and `SPECS/intent-preservation/0.1/` are related
  modeling/review resources, not an existing universal semantic checker.

## Agent interpretation and unresolved choices

The operator's direction motivates a project-selected context with one or more
pinned packages, checked dependency closure, explicit term bindings, honest
coverage, and review for unknown or ambiguous terms. Compilation correctness,
semantic review, input freshness and human acceptance remain distinct.

Existing specs should migrate without losing IDs or historical revisions.
Draft capture stays available before terminology is resolved. A missing compiler
should prevent a claim of checked ontology, not prevent writing a note.
The manifest layout, compiler installation method, resolver, lexical extraction
profile and canonical migration target require implementation/review; this
source does not invent their availability.

## Process observation

The existing Supervisor's targeted dry-run is used only to inspect the current
bounded target. SG-SPEC-0010 provides vocabulary context, SG-SPEC-0064 the
governance/vocabulary cluster, and SG-SPEC-0007 the pre-canonical boundary.
They are related anchors, not evidence that the proposed project-wide policy
already exists. No nested executor or canonical writer is invoked.
