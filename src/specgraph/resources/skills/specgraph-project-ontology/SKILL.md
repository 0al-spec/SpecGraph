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

## Check an executable relationship in a project package

For Ontology 0.7.0 with `ontology.foundation@0.2.0`, inspect the authored
`subject`, `action` and `object`. For example, an operator adds a repository
to a project: `User → AddRepository → Project`. The project is the object
whose membership changes. The repository reference can be an action parameter.

If `relation.subject.unresolved` points at `User`, inspect its declaration
in the selected source. A protocol describes a contract. When the project
means a particular operator, use its identified entity class in the subject
slot. Preserve the project's name and review the modeling choice there.
For `relation.action.unresolved`, check the spelling, import and ancestry of
the action class against `ont:Action`.

Use the project's pinned compiler to check and compile the source. Refresh
source and IR digests in the candidate selection. Run the installed runtime
against each selection being claimed, for example:

```sh
specgraph-runtime --workspace "$PROJECT" ontology-context -- \
  --project-id "$PROJECT_ID" --selection "$SELECTION" \
  --ontologyc "$ONTOLOGYC" --compiler-sha256 "$COMPILER_SHA256"
```

In a composition, resolve each reference against the version its own package
imports. Inspect the report's `outcome` and the JSON pointer for each disputed
field. If direct compilation passes but the runtime reports an unsupported
foundation version, record that profile gap separately. Report runtime
execution only when an application or SDK test actually triggers the action
and observes the affected state.

## Show a readable ontology composition

Use a compact overview when the person asks to see the model's structure, or
when a PR changes an ontology-bound composition whose review would benefit from
an ordinary text diff. Choose one useful scope and short responsibility names.
Label the selected hierarchy and names as authored choices pending review.
This step uses explicit ontology bindings; ordinary SpecDraft note capture
remains independent of ontology availability.

Prepare the overview from the project's actual materials:

1. Select the relevant terms from an existing ontology package and specification
   or attributed draft. Record the source revision and draft/accepted status.
   Choose the few concepts needed to review this topic; do not traverse all
   relations to construct a tree or turn ordinary SpecDraft notes into an ontology.
2. Author the composition in HC with stable occurrence IDs. Use short role names
   through HCS `overview_name`. Nesting expresses this selected composition,
   not inferred inheritance, execution order, causality or every ontology edge.
   Reuse a type for distinct local roles without collapsing their IDs.
3. Bind each role in HCS to its versioned `ontology_ref` and exact source package
   with `ontology_source` and `ontology_sha256`. The root source is the exporter's
   default; explicitly override it for a role defined in another package. Reuse
   that package's term instead of inventing a local duplicate. Keep technical
   identity, source properties and optional production bindings in HCS so the
   readable HC contains just names and hierarchy.
4. Export into a new directory using the command below. Inspect the generated
   pair: hierarchy and names in HC, distinct role IDs, type URIs, package versions
   and source hashes in HCS. For a first use in another product, repeat with the
   same inputs/tools into another new directory and compare both files' bytes.
   If implementation is absent, leave production bindings absent and describe
   the result as a model overview. Existing code bindings currently support
   top-level Python functions with an anchor; display names must be ASCII.
5. Show the compact HC for human review with HCS available for inspection.
   Record agreement at its actual scope: approving a view does not accept the
   entire ontology or prove an actor's motive, causality or implemented behavior.
   When saving the view is authorized, preserve the selection inputs and generated
   HC/HCS together in the owning project's version control, following its privacy
   rules. Review changes to both files; labels may change while IDs stay stable.

The exporter checks declarations in each explicitly selected source, not import
closure. If claiming that the packages compose, separately run the project's
supported `ontology-context` check for its selected profile and retain its result.
Keep `exported`, context `verified` and semantic acceptance distinct.

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
to the selected workspace. In native mode, relative `--output-dir`, `--hypercode`
and `--ontologyc` paths also use that workspace, regardless of the caller's
directory. Prefer absolute compiler paths. In a source checkout, the equivalent
entry point is `tools/ontology_overview_cli.py` with `--workspace-root`: HC/HCS
and source bindings still use that root, while relative output and compiler
paths use the caller's current directory. If the runtime or tools are unavailable,
keep the authored draft and state which check could not run. No compiler
installation is implied.

Read the exit code before inspecting an error report. Native launcher validation
errors return code 2 with `{"error": "..."}` and no `status`; dispatched exporter
errors additionally carry `status: invalid` or `status: unavailable`. Argument
usage failures can print ordinary argparse diagnostics. Treat `status` as
optional when handling an arbitrary failed native invocation.

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
