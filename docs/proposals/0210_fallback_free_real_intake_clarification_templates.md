# 0210 Fallback-Free Real Intake Clarification Templates

## Status

Draft / producer-side real-intake clarification contract slice.

## Summary

The UI-started product demo currently falls back to deterministic clarification
fixtures when SpecGraph's real-intake artifacts are not usable in a non-demo
workspace. The underlying request and answer-template tools already produce
typed targets, but the artifacts do not carry enough workspace identity to be
selected safely, policy context is not part of the mandatory intake questions,
and an empty or unsupported template is not distinguished from a legitimate
"no clarification required" outcome.

This slice makes the existing answer-template contract authoritative enough for
browser consumers without adding a second clarification protocol.

## Decision

The existing `idea_to_spec_clarification_requests` and
`real_idea_answer_template` artifacts carry:

- `workspace_id`, `candidate_id`, and a sanitized `workspace` identity;
- a stable digest binding the template to its clarification request source;
- one explicit `clarification_outcome`:
  - `answers_required`;
  - `clarification_not_required`;
  - `clarification_blocked`;
- typed browser-answerable targets for every mandatory request;
- public-safe findings when a mandatory request cannot be represented.

Real intake requires policy context alongside actors, commands, domain events,
and constraints. Missing policy context therefore becomes an ordinary
`event_storming_hints.policies` clarification target.

A ready complete intake emits `clarification_not_required` with no answer
targets. A mandatory request with an unsupported action or value shape emits
`clarification_blocked` and fails strict template generation. A blocked
generation does not overwrite an existing ready template.

## Authority Boundary

This slice does not:

- execute a prompt agent or infer product answers;
- auto-fill clarification answers;
- mutate canonical specs or accepted candidate artifacts;
- write Ontology packages or lockfiles;
- accept Ontology terms;
- approve candidates or change promotion gates;
- create Git branches, commits, or pull requests;
- publish a read model;
- publish raw idea text, prompts, model output, or operator notes.

SpecSpace remains an operator-answer surface. Platform remains the controlled
execution boundary.

## Acceptance Criteria

- Incomplete real ideas produce workspace-bound browser-answerable answer
  templates without deterministic fixture fallback.
- Complete real ideas produce an explicit `clarification_not_required`
  outcome and can continue safely without an answer set.
- Unsupported mandatory clarification requests produce
  `clarification_blocked`, strict failure, and public-safe findings.
- Template source refs and digests bind to the current workspace/session.
- Stale or cross-workspace artifacts cannot be selected as current intake
  evidence.
- Failed generation does not clobber a pre-existing ready template.
- Raw idea text does not appear in request, template, report, or public bundle
  artifacts.
- The standard SpecSpace product demo completes with
  `clarification_fallback_used=false`.

