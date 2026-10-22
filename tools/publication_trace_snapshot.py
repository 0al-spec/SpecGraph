#!/usr/bin/env python3
"""Collect a declaration-only trace snapshot from explicitly selected providers."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from intent_decision_review.sources import revision
from traceability.evidence import EvidenceRequest, EvidenceScope
from traceability.providers import EvidenceRegistry
from traceability.publication import PROFILE
from traceability.publication_provider import PublicationEvidenceProvider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True, type=Path)
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--spec-id", action="append", required=True)
    parser.add_argument("--provider", action="append")
    args = parser.parse_args(argv)
    try:
        root = args.repository_root.expanduser().resolve(strict=True)
        scope = EvidenceScope(
            args.repository_id, revision(root, args.revision), tuple(args.spec_id), PROFILE
        )
        request = EvidenceRequest(root, scope)
        registry = EvidenceRegistry((PublicationEvidenceProvider(),))
        snapshot = registry.collect(request, tuple(args.provider or ("publication.declarations",)))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"trace snapshot input error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(snapshot.to_payload(), indent=2, sort_keys=True))
    return 0  # An incomplete observation is a valid diagnostic, not merge readiness.


if __name__ == "__main__":
    raise SystemExit(main())
