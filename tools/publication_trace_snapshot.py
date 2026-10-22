#!/usr/bin/env python3
"""Collect a revision-bound trace snapshot from explicitly selected providers."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from intent_decision_review.sources import revision
from publication_evidence.context import ExecutionIdentity
from traceability.evidence import EvidenceRequest, EvidenceScope
from traceability.execution import PublicationExecutionSelection
from traceability.providers import EvidenceRegistry
from traceability.publication import PROFILE
from traceability.publication_execution_provider import PublicationExecutionEvidenceProvider
from traceability.publication_provider import PublicationEvidenceProvider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True, type=Path)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--spec-id", action="append", required=True)
    parser.add_argument("--provider", action="append")
    parser.add_argument("--tests-report", type=Path)
    parser.add_argument("--delivery-report", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--run-attempt")
    args = parser.parse_args(argv)
    try:
        root = args.repository_root.expanduser().resolve(strict=True)
        scope = EvidenceScope(
            args.repository_id, revision(root, args.revision), tuple(args.spec_id), PROFILE
        )
        selected = tuple(args.provider or ("publication.declarations",))
        execution = None
        if any((args.tests_report, args.delivery_report, args.run_id, args.run_attempt)):
            if "publication.execution" not in selected or not args.run_id or not args.run_attempt:
                raise ValueError(
                    "execution reports require --provider publication.execution, "
                    "--run-id and --run-attempt"
                )
            execution = PublicationExecutionSelection(
                ExecutionIdentity(
                    "github_actions",
                    args.run_id,
                    args.run_attempt,
                    f"https://github.com/{args.repository_id}/actions/runs/{args.run_id}",
                ),
                args.tests_report.expanduser().resolve() if args.tests_report else None,
                args.delivery_report.expanduser().resolve() if args.delivery_report else None,
            )
        request = EvidenceRequest(root, scope, execution_selection=execution)
        registry = EvidenceRegistry(
            (PublicationEvidenceProvider(), PublicationExecutionEvidenceProvider())
        )
        snapshot = registry.collect(request, selected)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"trace snapshot input error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(snapshot.to_payload(), indent=2, sort_keys=True))
    return 0  # An incomplete observation is a valid diagnostic, not merge readiness.


if __name__ == "__main__":
    raise SystemExit(main())
