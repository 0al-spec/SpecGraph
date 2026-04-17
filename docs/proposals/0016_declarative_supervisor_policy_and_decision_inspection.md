# Declarative Supervisor Policy and Decision Inspection

## Status

Draft proposal

## Problem

Supervisor currently mixes three different classes of logic inside Python code:

- hard runtime invariants
- governance policy
- operator-local execution choices

This makes the system harder to inspect and evolve.

Today, many thresholds and heuristics live directly in Python constants:

- atomicity thresholds
- graph-health thresholds
- profile behavior
- selection priorities
- proposal thresholds

At the same time, operators still lack a clear "decision inspector" that can
explain why the runtime chose a spec, raised a gate, emitted a proposal, or
classified a diff as governance-sensitive.

## Goals

- Separate hard runtime logic from changeable governance policy.
- Make supervisor thresholds and profiles inspectable as declarative policy.
- Add a decision-inspection surface for selection, gating, and queue behavior.
- Tighten machine protocol so success requires explicit structured outcome.

## Non-Goals

- Eliminating all Python decision logic
- Finalizing every future governance threshold now
- Replacing human judgment with a fully automatic policy engine

## Core Proposal

Supervisor should be split conceptually into three layers.

### Layer 1. Hard Runtime Invariants

These remain in code and should be treated as non-negotiable runtime contracts.

Examples:

- schema loading rules
- immutable field protection
- artifact integrity requirements
- approval barrier behavior
- lock discipline

### Layer 2. Declarative Governance Policy

Changeable policy should move into an explicit declarative layer that the
runtime reads and applies.

Examples:

- graph-health thresholds
- proposal thresholds
- execution profile definitions
- allowed mutation classes
- selector priorities

### Layer 3. Operator-Local Overrides

Short-lived, reviewable run overrides remain explicit operator inputs.

Examples:

- `--operator-note`
- temporary mutation budget
- temporary run authority
- explicit target selection

## Decision Inspector

Supervisor should emit a machine-readable explanation artifact for each
meaningful run decision.

It should answer questions such as:

- why this spec was selected
- which signals or rules fired
- why a run became `review_pending`, `split_required`, or `blocked`
- why a proposal or queue item appeared or disappeared
- which diff paths made a change governance-sensitive

This is the governance analogue of a configuration inspector.

## Profile Honesty

Execution profiles should be semantically honest.

If `fast`, `standard`, and `materialize` exist as distinct profiles, they should
actually differ in one or more meaningful dimensions such as:

- reasoning effort
- timeout
- disabled features
- retry or strictness policy

## Protocol Hardening

The executor protocol should be stricter than "exit code zero implies done."

Success should require an explicit structured outcome contract such as:

- `RUN_OUTCOME`
- optional `BLOCKER`
- optional machine-readable findings payload

Missing protocol markers should resolve to protocol error, retry, or blocked
state rather than silent success.

## Supervisor Implications

After this proposal:

- policy drift becomes visible and reviewable
- operators can inspect which rules actually shaped a decision
- profile names become trustworthy
- supervisor behavior becomes more explainable without becoming less bounded

## Open Questions

- Should declarative supervisor policy live as canonical spec-backed YAML, a
  dedicated policy artifact, or generated policy from accepted spec nodes?
- Should the decision inspector be a run artifact only, or also feed viewer
  overlays and longitudinal reporting?
