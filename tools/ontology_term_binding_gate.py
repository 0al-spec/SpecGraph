"""Review-first gate for ontology term bindings in generated artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY_PATH = ROOT / "tools" / "ontology_term_binding_policy.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "ontology_term_binding_gate_report.json"

ACCEPTED_STATUSES = {"accepted", "canonical", "approved"}
REJECTED_TERM_STATUSES = {"deprecated", "rejected"}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value if isinstance(value, str) and value else default


def _bool(value: Any) -> bool:
    return value is True


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("artifact_kind") != "ontology_term_binding_policy":
        raise ValueError("policy artifact_kind must be ontology_term_binding_policy")
    boundary = _dict(policy.get("authority_boundary"))
    required_false = (
        "may_write_ontology_package",
        "may_write_ontology_lockfile",
        "may_mutate_canonical_specs",
        "may_mark_candidate_accepted",
        "may_execute_prompt_agent",
        "canonical_mutations_allowed",
    )
    expanded = [name for name in required_false if boundary.get(name) is not False]
    if expanded:
        raise ValueError(f"policy authority boundary expanded: {', '.join(expanded)}")


def _source_ref(artifact: dict[str, Any], artifact_path: Path | None) -> str:
    source_ref = _text(artifact.get("source_ref"))
    if source_ref:
        return source_ref
    if artifact_path is not None:
        try:
            return artifact_path.relative_to(ROOT).as_posix()
        except ValueError:
            return artifact_path.as_posix()
    return "generated_artifact"


def _finding(
    *,
    finding_id: str,
    severity: str,
    message: str,
    source_ref: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "message": message,
        "source_ref": source_ref,
        "evidence": evidence or {},
    }


def _has_reviewable_gap(gaps: list[Any], term: str | None = None) -> bool:
    for raw_gap in gaps:
        gap = _dict(raw_gap)
        if gap.get("canonical_mutations_allowed") is not False:
            continue
        if not _text(gap.get("proposed_term")):
            continue
        if term is None or _text(gap.get("proposed_term")).lower() == term.lower():
            return True
    return False


def build_term_binding_gate_report(
    artifact: dict[str, Any],
    *,
    policy: dict[str, Any],
    artifact_path: Path | None = None,
) -> dict[str, Any]:
    validate_policy(policy)
    source_ref = _source_ref(artifact, artifact_path)
    gate = _dict(policy.get("generated_artifact_gate"))
    mode = _text(gate.get("default_mode"), "review_warning")
    gaps = _list(artifact.get("ontology_gaps"))
    findings: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    new_terms = [item for item in _list(artifact.get("new_terms")) if _text(item)]
    if new_terms and not gaps:
        findings.append(
            _finding(
                finding_id="new_term_without_gap",
                severity="review_required",
                message="New generated terms require ontology_gap records.",
                source_ref=source_ref,
                evidence={"new_terms": new_terms},
            )
        )

    for raw_match in _list(artifact.get("accepted_ontology_matches")):
        match = _dict(raw_match)
        binding_state = _text(match.get("binding_state"))
        if binding_state and binding_state != "bound_to_accepted_entity":
            findings.append(
                _finding(
                    finding_id="duplicate_accepted_entity",
                    severity="review_required",
                    message="Accepted ontology match was not bound to the accepted entity.",
                    source_ref=source_ref,
                    evidence=match,
                )
            )

    for raw_term in _list(artifact.get("deprecated_or_rejected_terms")):
        term = _dict(raw_term)
        status = _text(term.get("status"))
        replacement_or_gap = term.get("replacement_or_gap")
        if status in REJECTED_TERM_STATUSES and not replacement_or_gap:
            findings.append(
                _finding(
                    finding_id="deprecated_or_rejected_term_reused",
                    severity="review_required",
                    message="Deprecated or rejected terms require replacement binding or gap.",
                    source_ref=source_ref,
                    evidence=term,
                )
            )

    observation_rows = _list(artifact.get("practical_ontology_observations"))
    observation_rows.extend(
        row
        for row in _list(artifact.get("term_bindings"))
        if _dict(row).get("authority_class") == "practical_ontology_observation"
    )
    for raw_observation in observation_rows:
        observation = _dict(raw_observation)
        if _text(observation.get("status")) in ACCEPTED_STATUSES:
            findings.append(
                _finding(
                    finding_id="observation_marked_accepted",
                    severity="review_required",
                    message="Practical ontology observations cannot mark terms accepted.",
                    source_ref=source_ref,
                    evidence=observation,
                )
            )

    topology_rows = _list(artifact.get("topology_edges"))
    topology_rows.extend(
        row
        for row in _list(artifact.get("term_bindings"))
        if _dict(row).get("authority_class") == "specgraph_topology_edge"
    )
    for raw_edge in topology_rows:
        edge = _dict(raw_edge)
        if _bool(edge.get("semantic_relation")):
            findings.append(
                _finding(
                    finding_id="topology_edge_as_semantic_relation",
                    severity="review_required",
                    message="SpecGraph topology edges are not semantic ontology relations.",
                    source_ref=source_ref,
                    evidence=edge,
                )
            )

    for raw_binding in _list(artifact.get("term_bindings")):
        binding = _dict(raw_binding)
        if not _list(binding.get("domain_refs")):
            warnings.append(
                _finding(
                    finding_id="broad_term_without_domain",
                    severity="warning",
                    message="Term binding should include active domain refs.",
                    source_ref=source_ref,
                    evidence=binding,
                )
            )

    for raw_gap in gaps:
        gap = _dict(raw_gap)
        proposed_term = _text(gap.get("proposed_term"))
        if not _list(gap.get("source_refs")):
            warnings.append(
                _finding(
                    finding_id="candidate_gap_without_evidence",
                    severity="warning",
                    message="Ontology gaps should cite source refs.",
                    source_ref=source_ref,
                    evidence=gap,
                )
            )
        if gap.get("canonical_mutations_allowed") is not False:
            findings.append(
                _finding(
                    finding_id="gap_authority_expanded",
                    severity="review_required",
                    message="Ontology gaps must keep canonical_mutations_allowed false.",
                    source_ref=source_ref,
                    evidence=gap,
                )
            )
        if (
            proposed_term
            and proposed_term in new_terms
            and not _has_reviewable_gap(gaps, proposed_term)
        ):
            findings.append(
                _finding(
                    finding_id="new_term_gap_not_reviewable",
                    severity="review_required",
                    message="New term gap must be reviewable and non-mutating.",
                    source_ref=source_ref,
                    evidence={"proposed_term": proposed_term},
                )
            )

    review_state = "review_required" if findings else "clear"
    would_reject = bool(findings)
    return {
        "artifact_kind": "ontology_term_binding_gate_report",
        "schema_version": 1,
        "generated_at": _now_iso(),
        "policy_ref": "tools/ontology_term_binding_policy.json",
        "policy_proposal_id": policy.get("proposal_id"),
        "source_artifact": {
            "artifact_kind": artifact.get("artifact_kind"),
            "source_ref": source_ref,
        },
        "gate_mode": mode,
        "ok": mode == "review_warning" or not would_reject,
        "review_state": review_state,
        "would_reject_in_hard_gate": would_reject,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "findings": findings,
        "warnings": warnings,
        "summary": {
            "finding_count": len(findings),
            "warning_count": len(warnings),
            "new_term_count": len(new_terms),
            "ontology_gap_count": len(gaps),
            "term_binding_count": len(_list(artifact.get("term_bindings"))),
        },
    }


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--policy", default=DEFAULT_POLICY_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    artifact = load_json(args.artifact)
    policy = load_json(args.policy)
    report = build_term_binding_gate_report(artifact, policy=policy, artifact_path=args.artifact)
    write_report(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and report["would_reject_in_hard_gate"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
