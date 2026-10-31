#!/usr/bin/env python3
"""Check retained root HTTP observations offline against the build and deploy artifacts."""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit


def _rows(rows):
    if not isinstance(rows, list):
        raise ValueError("expected a list of path/digest records")
    pairs = Counter()
    for row in rows:
        path, digest = row["path"], row["sha256"]
        if not isinstance(path, str) or not path:
            raise ValueError("invalid path in evidence")
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            raise ValueError(f"invalid SHA-256 for {path}")
        pairs[path, digest] += 1
    return pairs


def coverage(
    bundle: Path, receipt_path: Path, observations_path: Path, run_id: str | None = None
) -> dict:
    manifest = (bundle / "artifact_manifest.json").read_bytes()
    metadata = {
        "artifact_manifest.json": hashlib.sha256(manifest).hexdigest(),
        "checksums.sha256": hashlib.sha256((bundle / "checksums.sha256").read_bytes()).hexdigest(),
    }
    payloads = _rows(json.loads(manifest)["files"])
    expected = payloads + Counter(metadata.items())
    if len({path for path, _ in expected}) != expected.total():
        raise ValueError("duplicate expected path in the retained bundle")
    receipt = json.loads(receipt_path.read_bytes())
    raw = observations_path.read_bytes()
    witness = json.loads(raw)
    if (
        receipt["artifact_kind"] != "specgraph_static_artifact_remote_verification_report"
        or witness["artifact_kind"] != "specgraph_publication_path_observations"
        or receipt["schema_version"] != 1
        or witness["schema_version"] != 1
    ):
        raise ValueError("unrecognized receipt or observations format")
    actual = _rows(witness["observations"])
    errors = []
    origin = urlsplit(receipt["remote_base_url"])
    if origin.scheme != "https" or not origin.netloc:
        errors.append("expected an absolute HTTPS origin")
    execution = receipt["execution_context"]
    if run_id is not None and (execution["provider"], execution["run_id"]) != (
        "github_actions",
        run_id,
    ):
        errors.append("receipt is not from the requested GitHub run")
    if receipt["status"] != "verified" or receipt["summary"] != {
        "verified_file_count": payloads.total(),
        "verified_metadata_file_count": len(metadata),
        "failure_count": 0,
    }:
        errors.append("receipt status or counts differ from the expected bundle")
    if receipt["bundle_identity"] != {
        "manifest_sha256": metadata["artifact_manifest.json"],
        "checksums_sha256": metadata["checksums.sha256"],
    }:
        errors.append("retained metadata differs from the receipt")
    if receipt["path_observations_sha256"] != hashlib.sha256(raw).hexdigest():
        errors.append("observations digest differs from the receipt")
    if any(
        receipt[key] != witness[key] for key in ("execution_context", "remote_base_url", "attempt")
    ):
        errors.append(
            "observations belong to a different execution, origin or verification attempt"
        )
    missing = sorted(path for path, _ in (expected - actual).elements())
    extra = sorted(path for path, _ in (actual - expected).elements())
    return {
        "status": "verified" if not (errors or missing or extra) else "unverified",
        "expected_payloads": payloads.total(),
        "expected_metadata_files": len(metadata),
        "observed_records": actual.total(),
        "execution_context": execution,
        "remote_base_url": receipt["remote_base_url"],
        "missing_path_digest_pairs": missing,
        "unexpected_path_digest_pairs": extra,
        "errors": errors,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--run-id", help="Require the receipt to identify this GitHub Actions run")
    args = parser.parse_args(argv)
    try:
        result = coverage(args.bundle_dir, args.receipt, args.observations, args.run_id)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        print(f"cannot verify publication coverage: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "verified" else 1


if __name__ == "__main__":
    raise SystemExit(main())
