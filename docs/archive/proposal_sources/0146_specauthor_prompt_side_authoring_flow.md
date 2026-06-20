# Source: SpecAuthor Prompt-Side Authoring Flow

Operator intent: move from standalone SpecAuthor validators to an actual
prompt-side authoring boundary that emits a typed invocation artifact from the
real review flow.

The implementation remains deterministic and review-only. It assembles an
already-produced draft with active ontology/domain/context/layer/applicability
data, runs the generated artifact contract and ontology write gate, then emits
the invocation artifact and invocation contract report.

The slice intentionally avoids prompt execution, raw prompt publication,
canonical spec mutation, ontology package writes, lockfile updates, owner
decision import, and ontology term acceptance.
