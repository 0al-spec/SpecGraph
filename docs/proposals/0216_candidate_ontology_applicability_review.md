# 0216 Candidate Ontology Applicability Review

## Status

Implemented read-only candidate review projection.

## Problem

Ontology ONT-040 and SpecGraph proposal `0144` already provide compiler-backed
model applicability profiles and compatibility change classification. SpecSpace
can inspect those artifacts in the Ontology Workbench, but Product Workspace
Candidate Overview does not carry the same evidence. Operators therefore need
to leave the product lifecycle surface to understand where the imported
ontology model applies, which assumptions were authored, and what changes
require review.

## Decision

Extend `runs/candidate_overview.json` with an additive
`sections.ontology_applicability` projection. The projection consumes:

- `runs/ontology_package_index.json`;
- `runs/ontology_compatibility_diff_preview.json`.

Only the existing ONT-040 vocabulary is copied:

- applies-to and exclusion scopes across domains, lifecycle phases, agent
  types, subsystems, runtimes, platforms, and contexts;
- authored assumptions;
- invalidation triggers;
- structural, annotation, and applicability change classifications, including
  compiler-published target kind, before/after, and compatibility detail;
- package refs and public-safe source refs.

Missing applicability remains `not_published`. It is not converted to zero,
failure, or a readiness blocker. Classified changes produce
`change_review_required` review telemetry, but do not change candidate,
approval, promotion, or publication gates.

Compatibility classification is projected only when the diff package refs
correlate with a declared package profile. A foreign or stale diff becomes
`change_evidence_stale`; its changes are not attached to the candidate.
Custom-run smoke targets scope both ontology inputs to the current run
directory rather than falling back to shared `runs/*`.

Malformed, wrong-kind, or write-capable source artifacts fail Candidate
Overview readiness through source-contract checks. Any truthy `may_*` field is
an authority expansion even when a newer producer field is not in the legacy
allowlist. Free text is passed through the existing public-safe redaction
boundary.

## Authority Boundary

This proposal does not:

- infer applicability from candidate prose;
- turn applicability into a score or runtime policy;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve or promote candidates;
- execute Platform, Git, or prompt agents.

## Acceptance Criteria

- Candidate Overview publishes compiler-backed applicability scopes,
  assumptions, exclusions, and invalidation triggers when available.
- Candidate Overview publishes compiler-backed structural, annotation, and
  applicability change classifications with compiler detail when available.
- Compatibility diff evidence is correlated with declared package refs; stale
  or foreign classifications are not mixed into the candidate.
- Missing optional artifacts remain `not_published`.
- Applicability review does not alter Candidate Overview readiness unless the
  source artifact is malformed, wrong-kind, or authority-expanding.
- The existing Candidate Overview CLI and Make target accept explicit source
  paths for both artifacts.
- Focused tests cover declared profiles, missing profiles, classified changes,
  package correlation, run-dir scoping, and write-capable source rejection.
