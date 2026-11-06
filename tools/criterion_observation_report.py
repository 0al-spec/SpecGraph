#!/usr/bin/env python3
"""Project a pinned retained-test criterion observation report."""

import argparse
import json
import sys
from pathlib import Path

from intent_decision_review.sources import digest
from traceability.criterion import CriterionSelection, FilePin
from traceability.criterion_inputs import PROFILE
from traceability.criterion_passport import NativePassportValidation
from traceability.criterion_provider import PROVIDER_ID, RetainedCriterionEvidenceProvider
from traceability.evidence import EvidenceRequest, EvidenceScope
from traceability.providers import EvidenceRegistry
from traceability.snapshot import TraceSnapshot


def report_payload(snapshot: TraceSnapshot) -> dict:
    if len(snapshot.reports) != 1 or snapshot.reports[0].criterion is None:
        raise ValueError("criterion projection requires one explicit criterion provider report")
    report = snapshot.reports[0]
    payload = {
        "artifact_kind": "criterion_observation_report",
        "schema_version": 1,
        "report_profile": "criterion_observation_report/v1",
        "scope": "local_test",
        "evidence_scope": snapshot.scope.to_payload(),
        "provider": report.identity.to_payload(),
        "source_lifecycle": report.nodes[0].to_payload()["source_lifecycle"],
        "sources": [source.to_payload() for source in report.sources],
        **report.criterion.to_payload(),
        "collection_sha256": report.collection_digest,
        "execution_source_provenance": "producer_declared",
        "admission": "not_evaluated",
        "receipt": None,
        "canonical_mutations_allowed": False,
    }
    return {**payload, "content_sha256": digest(payload)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--retained-root", type=Path, required=True)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--spec-id", required=True)
    parser.add_argument("--spec", nargs=2, metavar=("PATH", "SHA256"), required=True)
    parser.add_argument("--passport", nargs=2, metavar=("PATH", "SHA256"), required=True)
    parser.add_argument("--binding-plan", nargs=2, metavar=("PATH", "SHA256"), required=True)
    parser.add_argument("--journal", action="append", nargs=3, metavar=("ID", "PATH", "SHA256"))
    parser.add_argument("--validator", type=Path, required=True)
    parser.add_argument("--validator-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        root = args.repository_root.resolve(strict=True)
        selection = CriterionSelection(
            args.workspace,
            FilePin(*args.spec),
            FilePin(*args.passport),
            FilePin(*args.binding_plan),
            args.retained_root.resolve(strict=True),
            tuple((identity, FilePin(path, sha)) for identity, path, sha in args.journal or ()),
        )
        if not root.is_dir() or not selection.retained_root.is_dir():
            raise ValueError("repository and retained roots must be directories")
        scope = EvidenceScope(args.repository_id, args.revision, (args.spec_id,), PROFILE)
        validator = NativePassportValidation(args.validator, args.validator_sha256)
        registry = EvidenceRegistry((RetainedCriterionEvidenceProvider(validator),))
        snapshot = registry.collect(
            EvidenceRequest(root, scope, criterion_selection=selection), (PROVIDER_ID,)
        )
    except (ValueError, OSError) as error:
        print(f"criterion observation request error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report_payload(snapshot), indent=2, ensure_ascii=False, sort_keys=True))
    return 0  # Diagnostic report availability does not imply successful criteria.


if __name__ == "__main__":
    raise SystemExit(main())
