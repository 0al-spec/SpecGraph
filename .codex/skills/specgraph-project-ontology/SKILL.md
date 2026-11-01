---
name: specgraph-project-ontology
description: Maintain consistent domain terminology while discussing, drafting, or reviewing specifications for a SpecGraph product. Inspect concepts and relations, identify gaps, and prepare grounded proposals or readable ontology HC/HCS overviews; do not model ordinary UI controls as domain concepts by default.
---

# Project ontology during specification work

Use ontology to preserve a consistent, reviewable domain vocabulary across a
product's specifications, not to model every screen, button or gesture. This
skill does not itself install tools or establish an ontology, policy, or
canonical authority.

## Start from the project's actual context

Identify the product workspace and its existing intent, current specifications,
ontology packages, imports, review decisions and relevant drafts. Discover their
paths and statuses from the workspace rather than assuming they exist. Check
whether the workspace distinguishes project-local terms from imported terms and
whether the available tooling can inspect them. An unavailable or uninitialized
ontology is a limitation, not an empty approved vocabulary.

Trace a relevant term to its defining document, node and field where available.
Record its package/version, scope, source and actual approval status. Separate
the source package from normalized data, fixtures, candidate locks and generated
reports: a fixture's `accepted` label or a passing report does not establish
acceptance outside that fixture. A reference to a vocabulary term is not itself
a binding between particular objects or proof that a test ran.

In the SpecGraph source checkout, `ontology/packages/specgraph-core/` contains
the source package and `ontologyc/` review fixtures; `specs/nodes/` contains
specifications. These are navigation examples, not required paths in a product
workspace or evidence that the package is accepted. A newly initialized product
workspace may have no ontology package. Do not require one before capturing or
developing an idea.

For conversation capture, follow the project's conversational-notes workflow
if available. Recording a person's words must not depend on an ontology lookup;
preserve quotations, agent interpretations and decisions separately.

## Work with meaning before structure

For the bounded topic under discussion:

1. Reuse a matching accepted concept or relation when its actual meaning and
   context fit. Check definitions, aliases, provenance and review status, not
   just spelling. Distinguish similarly named concepts when their meanings differ.
2. Separate a concept's meaning and distinguishing characteristics from its
   properties and its relationships to other entities. Avoid defining an entity
   solely by its membership in a higher-level entity or by a UI's use of it.
3. Describe a relation independently, with meaningful direction and participant
   types; record cardinality, conditions and scope only when justified. A
   relation can exist without the action that created it still occurring.
4. Where useful, distinguish an actor or other participant's role in a specific
   action, the action or command, the resulting event and the resulting state.
   A role is contextual; do not infer an agent's identity, intention or
   responsibility without supporting evidence. Do not create an event model or
   state machine merely because one is possible.
5. Treat UI controls, presentation choices and implementation mechanisms as UX
   or engineering details unless they have a separately justified domain meaning.
   The UX specification may still use domain vocabulary and describe behavior.

Preserve distinctions between observed facts, derived interpretations, unknown
data, and proposals. Do not invent meanings, relations, requirements, decisions,
or source citations to fill gaps. Ask a focused question when the answer matters;
otherwise record the uncertainty and continue independent work. Use a concrete
domain example to make a proposed distinction reviewable, clearly labelled as
an example rather than a decision.

## Reconcile terms in drafts and specifications

When an unfamiliar or conflicting term appears, check whether it is an existing
concept, an appropriate alias, a different concept, or a UI/implementation
detail. If not resolved, record a candidate or ontology gap with the source,
intended meaning, affected context and open question. Do not silently replace it
with a near synonym or silently add it to the accepted vocabulary. Existing
specifications are evidence of usage, not automatic ontology authority.

If the user wants a new concept or changed relation, prepare a small proposal
with its rationale, source, relationships and potential impact on existing
specifications; use the project's existing review and governance process. Do
not equate human agreement to one point with approval of an entire sketch or
package. A draft, preview, generated binding, validation result or candidate
lock does not by itself accept terms or authorize canonical changes.

## Show a readable ontology composition

Use a compact overview when the person asks to see the model's structure, or
when a PR changes an ontology-bound composition whose review would benefit from
an ordinary text diff. Choose one useful scope and short responsibility names.
Label the selected hierarchy and names as authored choices pending review.
This step uses explicit ontology bindings; ordinary SpecDraft note capture
remains independent of ontology availability.

Prepare an HC selection with stable occurrence IDs and HCS with versioned
`ontology_ref` bindings. Use `overview_name` for readable names. Put technical
identity, source properties and optional production bindings in HCS. Nesting
expresses the selected composition, not inferred inheritance, execution order
or every relationship in the ontology. Reuse types for distinct local roles
without collapsing their IDs. The exporter currently accepts ASCII display
names and checks optional top-level Python function/anchor bindings.

For a native runtime whose help lists `ontology-overview`, invoke its actual
launcher path with the product workspace selected explicitly:

```sh
specgraph-runtime --workspace /absolute/product/workspace ontology-overview -- \
  --hc ontology/views/publication.selection.hc \
  --hcs ontology/views/publication.selection.hcs \
  --hypercode /path/to/hypercode --ontologyc /path/to/ontologyc \
  --output-dir /path/to/new-review-directory
```

Paths and names above are examples. HC/HCS and their source paths are relative
to the selected workspace; relative output paths also use that workspace in
native mode. Pass the selected compiler executables explicitly. In a source
checkout, the equivalent entry point is `tools/ontology_overview_cli.py` with
`--workspace-root`. If the runtime or tools are unavailable, keep the authored
draft and state which check could not run. No compiler installation is implied.

Generate into a new directory, inspect the result and compare it with any
tracked review pair before updating that pair. Follow the project's Git and
privacy rules; the overview need not contain raw conversation quotations.
Show the person the short HC first and keep HCS available for definitions,
identities and implementation navigation. Explain important omissions and
unresolved meanings. `exported` confirms structural export and checked
references; ontology meaning and composition acceptance remain review decisions.

## Tool boundary and handoff

Use actual project-supported ontology inspection, validation and review tools
when available, checking their help, selected workspace, inputs and output
authority before running them. Do not assume that a SpecGraph native runtime
provides ontology commands: inspect the installed version. In a SpecGraph
source checkout, `tools/README.md` and
`docs/ontology_spec_validation_roadmap.md` describe existing review-only
package and semantic reports; do not assume those checkout Make targets run in
an unrelated product workspace. Review-only describes their authority, not
necessarily filesystem behavior: some commands write generated reports to
`runs/`. Ontology's `ontologyc` validates its supported
contracts; structural validation or a passing report does not prove domain
truth or owner acceptance.

If tooling or an accepted ontology is unavailable, continue with a clearly
labelled source-attributed draft and report what could not be checked. At a
handoff, identify the workspace and relevant sources, accepted terms used,
new candidates or gaps, unresolved questions, checks actually run and their
limits. Keep product-specific ontology with its owning project, following its
existing storage and review policy; do not change shared Ontology packages or
publish private conversation material as a side effect.
