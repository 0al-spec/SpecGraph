from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "ontology_term_binding_gate.py"
POLICY_PATH = ROOT / "tools" / "ontology_term_binding_policy.json"
FIXTURE_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "ontology_term_binding"
    / "generated_artifact_review_required.json"
)


def load_gate_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "ontology_term_binding_gate_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def test_term_binding_gate_reports_review_findings() -> None:
    module = load_gate_module()
    artifact = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    report = module.build_term_binding_gate_report(
        artifact,
        policy=load_policy(),
        artifact_path=FIXTURE_PATH,
    )

    assert report["artifact_kind"] == "ontology_term_binding_gate_report"
    assert report["gate_mode"] == "review_warning"
    assert report["ok"] is True
    assert report["review_state"] == "review_required"
    assert report["would_reject_in_hard_gate"] is True
    assert report["canonical_mutations_allowed"] is False
    ids = finding_ids(report)
    assert "duplicate_accepted_entity" in ids
    assert "deprecated_or_rejected_term_reused" in ids
    assert "observation_marked_accepted" in ids
    assert "topology_edge_as_semantic_relation" in ids


def test_term_binding_gate_reports_clear_artifact() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://clean",
        "new_terms": ["Agent Passport"],
        "term_bindings": [
            {
                "generated_term": "Agent Passport",
                "binding_state": "bound_to_accepted_entity",
                "authority_class": "accepted_ontology_entity",
                "ontology_ref": "ontology.agent_passport.entity",
                "ontology_package_ref": "ontology.agent_passport@0.1.0",
                "term_ref": "AgentPassport",
                "domain_refs": ["domain.agent_layer"],
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
            }
        ],
        "accepted_ontology_matches": [
            {
                "generated_term": "Agent Passport",
                "ontology_ref": "ontology.agent_passport.entity",
                "ontology_package_ref": "ontology.agent_passport@0.1.0",
                "term_ref": "AgentPassport",
                "binding_state": "bound_to_accepted_entity",
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
            }
        ],
        "ontology_gaps": [],
    }

    report = module.build_term_binding_gate_report(artifact, policy=load_policy())

    assert report["review_state"] == "clear"
    assert report["would_reject_in_hard_gate"] is False
    assert report["findings"] == []
    assert report["summary"]["unknown_new_term_count"] == 0


def test_term_binding_gate_allows_justified_candidate_gap_for_accepted_match() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://justified-gap",
        "new_terms": ["Agent Passport Runtime"],
        "accepted_ontology_matches": [
            {
                "generated_term": "Agent Passport Runtime",
                "ontology_ref": "ontology.agent_passport.entity",
                "binding_state": "candidate_gap_required",
            }
        ],
        "ontology_gaps": [
            {
                "proposed_term": "Agent Passport Runtime",
                "proposed_kind": "entity",
                "reason": (
                    "Generated term appears distinct from the accepted Agent Passport entity."
                ),
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
                "candidate_bindings": [
                    {
                        "ontology_ref": "ontology.agent_passport.entity",
                        "reason": (
                            "Name overlaps with Agent Passport but target runtime role differs."
                        ),
                    }
                ],
                "status": "requires_owner_review",
                "canonical_mutations_allowed": False,
            }
        ],
    }

    report = module.build_term_binding_gate_report(artifact, policy=load_policy())

    assert report["review_state"] == "clear"
    assert report["would_reject_in_hard_gate"] is False
    assert report["findings"] == []
    assert report["summary"]["unknown_new_term_count"] == 1


def test_term_binding_gate_preserves_candidate_bindings_in_gap_records() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://missing-candidates",
        "new_terms": ["Agent Passport Runtime"],
        "ontology_gaps": [
            {
                "proposed_term": "Agent Passport Runtime",
                "proposed_kind": "entity",
                "reason": (
                    "Generated term appears distinct from the accepted Agent Passport entity."
                ),
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
                "status": "requires_owner_review",
                "canonical_mutations_allowed": False,
            }
        ],
    }

    report = module.build_term_binding_gate_report(artifact, policy=load_policy())

    assert report["review_state"] == "review_required"
    assert "candidate_gap_without_candidate_bindings" in finding_ids(report)


def test_term_binding_gate_requires_matching_gap_per_new_term() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://unrelated-gap",
        "new_terms": ["A"],
        "ontology_gaps": [
            {
                "proposed_term": "B",
                "proposed_kind": "entity",
                "reason": "Different term.",
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
                "candidate_bindings": [],
                "status": "requires_owner_review",
                "canonical_mutations_allowed": False,
            }
        ],
    }

    report = module.build_term_binding_gate_report(artifact, policy=load_policy())

    assert "new_term_without_gap" in finding_ids(report)


def test_term_binding_gate_treats_missing_accepted_match_state_as_unbound() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://missing-state",
        "accepted_ontology_matches": [
            {
                "generated_term": "Agent Passport",
                "ontology_ref": "ontology.agent_passport.entity",
            }
        ],
    }

    report = module.build_term_binding_gate_report(artifact, policy=load_policy())

    assert "duplicate_accepted_entity" in finding_ids(report)


def test_term_binding_gate_does_not_mutate_artifact_lists() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://no-mutation",
        "practical_ontology_observations": [],
        "topology_edges": [],
        "term_bindings": [
            {
                "generated_term": "ObservedUsage",
                "binding_state": "observed",
                "authority_class": "practical_ontology_observation",
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
            },
            {
                "generated_term": "SG-SPEC-0041 refines SG-SPEC-0034",
                "binding_state": "observed",
                "authority_class": "specgraph_topology_edge",
                "semantic_relation": True,
                "source_refs": ["specs/nodes/SG-SPEC-0041.yaml"],
            },
        ],
    }

    module.build_term_binding_gate_report(artifact, policy=load_policy())
    module.build_term_binding_gate_report(artifact, policy=load_policy())

    assert artifact["practical_ontology_observations"] == []
    assert artifact["topology_edges"] == []


def test_term_binding_gate_checks_accepted_binding_state_on_observations() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://accepted-observation",
        "term_bindings": [
            {
                "generated_term": "PracticalOntologyObservation",
                "binding_state": "accepted",
                "authority_class": "practical_ontology_observation",
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
            }
        ],
    }

    report = module.build_term_binding_gate_report(artifact, policy=load_policy())

    assert "observation_marked_accepted" in finding_ids(report)


def test_term_binding_gate_requires_refs_for_accepted_entity_bindings() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://accepted-stub",
        "new_terms": ["Agent Passport"],
        "term_bindings": [
            {
                "generated_term": "Agent Passport",
                "binding_state": "bound_to_accepted_entity",
                "authority_class": "accepted_ontology_entity",
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
            }
        ],
    }

    report = module.build_term_binding_gate_report(artifact, policy=load_policy())

    ids = finding_ids(report)
    assert "accepted_entity_binding_missing_refs" in ids
    assert "new_term_without_gap" in ids


def test_term_binding_gate_rejects_non_review_gap_statuses() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://accepted-gap",
        "new_terms": ["Agent Passport Runtime"],
        "ontology_gaps": [
            {
                "proposed_term": "Agent Passport Runtime",
                "proposed_kind": "entity",
                "reason": "Generated term appears distinct.",
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
                "candidate_bindings": [],
                "status": "accepted",
                "canonical_mutations_allowed": False,
            }
        ],
    }

    report = module.build_term_binding_gate_report(artifact, policy=load_policy())

    ids = finding_ids(report)
    assert "ontology_gap_invalid_status" in ids
    assert "new_term_without_gap" in ids


def test_term_binding_gate_requires_candidate_binding_before_duplicate_waiver() -> None:
    module = load_gate_module()
    artifact = {
        "artifact_kind": "generated_spec_artifact",
        "source_ref": "memory://candidate-gap-without-binding",
        "new_terms": ["Agent Passport Runtime"],
        "accepted_ontology_matches": [
            {
                "generated_term": "Agent Passport Runtime",
                "ontology_ref": "ontology.agent_passport.entity",
                "binding_state": "candidate_gap_required",
            }
        ],
        "ontology_gaps": [
            {
                "proposed_term": "Agent Passport Runtime",
                "proposed_kind": "entity",
                "reason": "Generated term appears distinct.",
                "source_refs": ["docs/proposals/0128_ontology_term_binding_policy.md"],
                "candidate_bindings": [],
                "status": "requires_owner_review",
                "canonical_mutations_allowed": False,
            }
        ],
    }

    report = module.build_term_binding_gate_report(artifact, policy=load_policy())

    assert "duplicate_accepted_entity" in finding_ids(report)


def test_term_binding_gate_cli_strict_exits_nonzero(tmp_path: Path) -> None:
    output_path = tmp_path / "gate-report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--artifact",
            str(FIXTURE_PATH),
            "--output",
            str(output_path),
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["would_reject_in_hard_gate"] is True
    assert "topology_edge_as_semantic_relation" in finding_ids(report)
