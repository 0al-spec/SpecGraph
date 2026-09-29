"""Typed inputs for candidate approval readiness decisions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovalReadinessContext:
    effective_state: str
    has_findings: bool

    @property
    def approval_ready(self) -> bool:
        return self.effective_state == "approved" and not self.has_findings
