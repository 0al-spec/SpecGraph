"""Typed facts used to decide whether a clean pre-SIB result can pass through."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepairedHandoffContext:
    pre_sib_ready: bool
    repair_loop_ready: bool
    has_findings: bool
    applied_action_count: object
    context_required_count: object
