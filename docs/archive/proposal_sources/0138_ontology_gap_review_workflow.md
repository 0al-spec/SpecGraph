# Source: Ontology Gap Review Workflow

Operator intent:

- Existing ontology gaps are visible, but reviewers need them grouped into a
  stable workflow surface.
- The workflow should show proposed term or relation, source specs, affected
  generated artifacts, source gap/finding references, and recommended owner
  action.
- The surface must stay read-only or acknowledgement-only. It must not accept
  ontology terms, write Ontology packages, import owner decisions, mutate
  canonical specs, or execute prompt agents.

Bounded slice:

- add a deterministic `ontology_gap_review_workflow` artifact;
- group gaps from package gap preview, spec ontology validation findings, and
  optional generated artifacts;
- preserve source specs and generated artifact refs;
- emit recommended owner actions for each group;
- add tests, Makefile target, proposal docs, and proposal tracking.

Deferred:

- owner decision import v2;
- before/after accepted/rejected status;
- legacy spec backfill planning;
- SpecSpace consolidated Ontology Workbench UI;
- ontology package mutation.
