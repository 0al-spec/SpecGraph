"""Typed facts for deciding candidate repair-preview readiness."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateRepairReadinessContext:
    has_findings: bool
    applied_action_count: int
    no_op_ready: bool
