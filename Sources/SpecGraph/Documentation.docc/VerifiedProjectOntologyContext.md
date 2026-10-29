# Verified Project Ontology Context

## Reviewed selection contract and implementation track

The 0232 selection contract is prepared as SG-SPEC-0072 with parent
SG-SPEC-0064 reconciliation through a fresh Terra 6.1 High Supervisor run and
independent review. `docs/reviews/0232_project_ontology_context/adoption/`
retains its source, byte inventory, normalized sync digests and gate resolution.
Preparation on a PR branch is not a human signature, semantic approval or
production activation. The global legacy smoke findings were preserved.

The seven-layer track in
`docs/reviews/0232_project_ontology_context/marathon.md` proceeds through captured
context, CLI/native routing, advisory reports, explicit freshness assessment,
scoped terminology inventory and a target-specific Supervisor check. It does
not activate a global gate or claim complete prose coverage. Unsupported
dependency closure remains unavailable; draft capture remains available.

Proposal `SG-RFC-0232` is a planning contract for grounding every project
specification in an explicitly selected ontology context. Runtime realization
is `deferred_until_canonicalized`; this proposal activates no new policy.

The review sources are:

- `docs/proposals/0232_verified_project_ontology_context.md`
- `docs/proposals/0232_verified_project_ontology_context.intent.yaml`
- `docs/archive/proposal_sources/0232_verified_project_ontology_context.md`
- `docs/reviews/0232_project_ontology_context/source-notes.json`

## Selected context and scope

The bounded source API `capture_project_context` implements explicit selection
and immutable capture under SG-SPEC-0072. Selection v1 declares pinned members,
`ontologyc-structural-v1` and explicit qualified composition rules. The optional
compiler pin is checked before execution. Named outcome policies preserve
invalid-before-unavailable precedence; errors have typed outcomes.
An ambiguous compiler process failure or undecodable process output is unavailable;
independently detected identity, pin and source/IR mismatches remain invalid.
Imported/composed closure remains unavailable. See
`docs/project_ontology_context.md` for the actual API and manifest shape.

The source CLI `project_ontology_context_cli.py` and native runtime
`ontology-context` route operate on an explicit external workspace. Optional
project configuration supplies defaults without initialization or mutation.
Exit outcomes remain verified/unavailable/invalid; native routing rejects
workspace overrides and abbreviated arguments. Optional report writes are
workspace-contained and atomic. No compiler is installed or discovered implicitly.

`build_context_reports` connects the existing advisory binding and validation
views to one captured context and specification byte set. Its
`specgraph-local-symbol-advisory-v1` profile records exact input hashes and the
`single_member_local_symbols` scope. Invalid/foreign or unsupported joint input
does not fall back to saved IR. Local analysis does not verify imported closure
or semantically accept the legacy `accepted_bindings` field.

A context can select one ontology or a composed package set. Selection records
exact package/source identities, dependencies, compiler and check profile.
Version conflicts, unavailable dependency checks and ambiguous terms stay
visible. Compiler release versions do not change package approval status.

One immutable `OntologySnapshot`, or a composed context of such snapshots,
supplies captured source and IR to an operation. Provenance binds all relevant
inputs. Compiler hashes identify bytes without authenticating the compiler.
`TraceSnapshot` from proposal 0226 remains the separate trace-fact model.

Terminology coverage uses a scoped inventory of definitions, qualified
bindings and source locations. Unassessed prose stays unassessed. Compilation
and spelling matches cannot establish full semantic coverage or acceptance.

## Drafts, gaps and readiness

Valid packages with gaps remain usable for resolved vocabulary. Required gaps
need review before the affected specification can be called fully grounded.
Draft capture stays available when a compiler or ontology is missing.
Ontology-dependent actions require the checks and vocabulary they declare.

Reports bind the selected context, project, specification, binding and policy
inputs. Missing, stale or partial evidence cannot become current success.
An old context remains historical evidence; it cannot silently replace changed
current inputs. Existing specifications migrate through an explicit inventory
that preserves IDs and history while exposing unassessed scope and exceptions.

## SpecSpace surfaces

Reuse `/api/v1/practical-ontology` and `/api/v1/ontology-workbench` for workspace
observation of the selected context, verification, freshness, coverage and gaps.
Graph rendering and artifact presence do not establish approved terminology.
The `/ontology` route remains independent browser-local artifact inspection;
dropping a ZIP does not select or approve the active project context.

## Delivery and evidence boundaries

PR #825 proposes optional checked inputs in two report consumers; it is not the
project-wide guarantee. Subsequent slices define minimal context selection,
migrate candidate graph and Supervisor, assess the legacy corpus, provide a
compiler in the native distribution and update SpecSpace display contracts.
The proposal's acceptance matrix describes future tests, not completed runs.

`canonical_mutations_allowed: false` and
`runtime_profile_activation_allowed: false` describe this preparation slice.
Intent preservation across specification, code and observation is a separate
bounded follow-up using Ontology examples and 0226 facts. An agent skill can
guide that review without substituting for evidence or human acceptance.

## Supervisor contract candidate

The initial review packet at
`docs/reviews/0232_project_ontology_context/supervisor/README.md` preserves a
targeted `split_required` result and a subsequent one-child materialization.
The latter produced the proposed SG-SPEC-0072 selection contract and SG-SPEC-0064
parent reconciliation, with zero validation errors and `review_pending`.
`accepted_canonical_diff: false` remains the recorded result. Exact candidate
files were retained under `docs/reviews/` without canonical graph updates at
that stage.

The first run's quoted-documentation environment finding and the existing soft
ontology gate's unestablished applicability remain in the observations. No gate
is cleared by this packet. The later adoption review prepares the contract and
parent reconciliation on a PR branch, with PR review and merge still separate.
This preparation does not approve ontology meanings or activate global policy;
configuration/runtime implementation follows the contract review boundary.
