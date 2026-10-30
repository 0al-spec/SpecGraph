"""Characterize existing declaration checks for RFC 0233; no readiness policy."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

import yaml

from native_bdd.boundary import load_native_bdd
from supervisor import validate_acceptance_evidence


def inspect(node: dict) -> dict:
    """Observe existing validators without assigning authoring readiness."""
    bdd = load_native_bdd(yaml.safe_dump(node), profile="bdd_scenarios_v1")
    return {
        "acceptance_shape_errors": validate_acceptance_evidence(node),
        "bdd_presence": bdd.presence.value,
        "bdd_findings": [asdict(finding) for finding in bdd.findings],
        "bdd_scenario_count": bdd.extracted_count,
        "execution_evidence": "not_evaluated",
    }


def characterize(source: bytes) -> dict:
    node = yaml.safe_load(source)
    if node.get("id") != "SG-SPEC-0072":
        raise ValueError("This experiment is scoped to SG-SPEC-0072")
    # Expected rows come from the unchanged source, never from a mutated copy.
    inventory = [
        {"source_pointer": f"/acceptance/{i}", "text": text}
        for i, text in enumerate(node["acceptance"])
    ]
    cases = []

    def observe(name: str, candidate: dict, changed_paths: list[str]) -> None:
        cases.append(
            {
                "experiment": name,
                "changed_paths": changed_paths,
                "remaining_acceptance_count": len(candidate["acceptance"]),
                "remaining_prose_case_count": len(candidate["specification"]["acceptance_cases"]),
                "observations": inspect(candidate),
            }
        )

    observe("unchanged_source", node, [])
    candidate = deepcopy(node)
    candidate["acceptance_evidence"].pop(2)
    observe("remove_evidence_only", candidate, ["/acceptance_evidence/2"])
    candidate = deepcopy(node)
    candidate["acceptance"].pop(2)
    candidate["acceptance_evidence"].pop(2)
    observe(
        "remove_criterion_and_matching_evidence",
        candidate,
        ["/acceptance/2", "/acceptance_evidence/2"],
    )
    candidate = deepcopy(node)
    candidate["specification"]["acceptance_cases"].pop(4)
    observe("remove_mixed_outcome_prose_case", candidate, ["/specification/acceptance_cases/4"])
    candidate = deepcopy(node)
    candidate["specification"]["verification_contract"]["outcome_precedence"] = (
        "A detected invalidity together with an unavailable check produces verified."
    )
    observe(
        "contradict_outcome_precedence_prose",
        candidate,
        ["/specification/verification_contract/outcome_precedence"],
    )

    # Synthetic declarations probe the existing reference checker, not behavior.
    candidate = deepcopy(node)
    candidate["specification"]["bdd_scenarios"] = [
        {
            "id": "PILOT-MIXED",
            "steps": [
                "Given invalid and unavailable checks",
                "Then the outcome is invalid and both diagnostics remain",
            ],
        }
    ]
    candidate["specification"]["observability"] = {
        "obligations": [{"id": "PILOT-PRECEDENCE", "scenario_ids": ["PILOT-MIXED"]}]
    }
    observe(
        "synthetic_linked_declaration",
        candidate,
        ["/specification/bdd_scenarios", "/specification/observability"],
    )
    candidate["specification"]["bdd_scenarios"] = []
    observe("remove_referenced_synthetic_scenario", candidate, ["/specification/bdd_scenarios"])
    return {
        "artifact_kind": "authoring_pilot_baseline",
        "schema_version": 1,
        "proposal_id": "0233",
        "spec_id": node["id"],
        "source_sha256": sha256(source).hexdigest(),
        "expected_acceptance_inventory": inventory,
        "inventory_identity": (
            "source_sha256 plus source_pointer; snapshot-local, not durable atom IDs"
        ),
        "experiments": cases,
        "unsupported_by_this_baseline": [
            "Required ontology usage bindings: no authoring profile selected",
            "Stale authoring evidence admission: no authoring report contract yet",
            "Semantic contradiction detection in prose",
            "Formal source-obligation discharge and atom-level SVC",
            "Large-leaf completeness and optional ontology relation applicability",
        ],
        "canonical_mutations_allowed": False,
        "runtime_profile_activation_allowed": False,
        "authoring_readiness": "not_evaluated",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    print(json.dumps(characterize(args.source.read_bytes()), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
