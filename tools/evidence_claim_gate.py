"""Admission of bounded implementation claims from a live Feature Passport adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

KINDS = {
    "source_anchored",
    "tests_verified",
    "runtime_verified",
    "effect_committed",
    "outcome_completed",
}
CLAIM_FIELDS = {"id", "kind", "passport_criterion_ids"}
POLICY_ID = "specgraph.evidence-claim-admission.local-source.v1"


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def unique_strings(value):
    return (
        isinstance(value, list)
        and bool(value)
        and all(nonempty(v) for v in value)
        and len(value) == len(set(value))
    )


def canonical_claim_errors(node):
    """Claims are declarations. Verdicts can only be freshly derived by the gate."""
    if "evidence_claims" not in node:
        return []
    claims = node["evidence_claims"]
    if not isinstance(claims, list) or not claims:
        return ["evidence_claims must be a nonempty declaration list"]
    errors, ids = [], set()
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != CLAIM_FIELDS:
            errors.append(
                "evidence_claims allow only id, kind, passport_criterion_ids; verdicts are derived"
            )
            continue
        if not nonempty(claim["id"]) or claim["id"] in ids:
            errors.append("evidence_claims require unique nonempty IDs")
        else:
            ids.add(claim["id"])
        if not isinstance(claim["kind"], str) or claim["kind"] not in KINDS:
            errors.append("unknown evidence claim kind")
        if not unique_strings(claim["passport_criterion_ids"]):
            errors.append("passport_criterion_ids must be a nonempty unique string list")
    return errors


def source_claim_reason(claim, passport, resolution):
    """Interpret only the upstream pinned Swift source-resolution contract."""
    spec = passport["spec"]
    criteria = {item["id"] for item in spec["intent"]["acceptance_criteria"]}
    requested = set(claim["passport_criterion_ids"])
    if not requested <= criteria:
        return "unknown_passport_criterion"
    implementation = spec.get("implementation", {})
    bindings = implementation.get("bindings", [])
    relevant = [b for b in bindings if requested & set(b["acceptance_criteria_ids"])]
    covered = {c for b in relevant for c in b["acceptance_criteria_ids"]}
    if not requested <= covered:
        return "missing_criterion_binding"
    required_elements = {
        e for b in relevant for e in b["element_ids"] + b.get("test_element_ids", [])
    }
    elements = implementation.get("elements", [])
    by_id = {e["id"]: e for e in elements}
    if len(by_id) != len(elements) or not required_elements or not required_elements <= set(by_id):
        return "invalid_element_binding"
    if resolution.get("validation_issues") != []:
        return "passport_validation_failed"
    anchors = resolution.get("anchors")
    if not isinstance(anchors, list) or not anchors:
        return "missing_source_evidence"
    observed = {}
    for anchor in anchors:
        if not isinstance(anchor, dict):
            return "malformed_source_evidence"
        key = (anchor.get("element_id"), anchor.get("anchor_index"))
        if not isinstance(key[0], str) or type(key[1]) is not int or key in observed:
            return "ambiguous_source_evidence"
        observed[key] = anchor
    expected_keys = {(e["id"], i) for e in elements for i, _ in enumerate(e["anchors"])}
    if set(observed) != expected_keys:
        return "incomplete_or_extra_source_evidence"
    for element_id in sorted(required_elements):
        expected = by_id[element_id]["anchors"]
        if not expected:
            return "missing_source_anchors"
        for index, authored in enumerate(expected):
            actual = observed[(element_id, index)]
            fields = ("repository", "revision", "module", "path", "symbol")
            if any(actual.get(field) != authored[field] for field in fields):
                return "source_identity_mismatch"
            if actual.get("status") != "resolved":
                return "source_unresolved"
            if not re.fullmatch(r"[a-fA-F0-9]{40}|[a-fA-F0-9]{64}", actual.get("blob_oid", "")):
                return "missing_blob_identity"
    return None


def evaluate_claims(request, passport, resolution):
    """Pure interpretation; callers must supply a live trusted adapter result."""
    if not isinstance(request, dict):
        return {"admitted": False, "claims": [], "errors": ["request must be an object"]}
    errors = canonical_claim_errors({"evidence_claims": request.get("claims")})
    if errors:
        return {"admitted": False, "claims": [], "errors": errors}
    results = []
    for claim in request["claims"]:
        reason = "evidence_evaluator_unavailable"
        if claim["kind"] == "source_anchored":
            try:
                reason = source_claim_reason(claim, passport, resolution)
            except (AttributeError, KeyError, TypeError, ValueError):
                reason = "malformed_evidence_input"
        results.append(
            {
                "id": claim["id"],
                "kind": claim["kind"],
                "passport_criterion_ids": claim["passport_criterion_ids"],
                "state": "satisfied" if reason is None else "unknown",
                "reason": reason,
                "scope": "pinned_source_identity_only"
                if claim["kind"] == "source_anchored"
                else "unsupported",
            }
        )
    return {
        "admitted": all(item["state"] == "satisfied" for item in results),
        "claims": results,
        "errors": [],
    }


def digest(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(raw):
    def reject_constant(value):
        raise ValueError(f"non-finite JSON number: {value}")

    return json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)


def run_admission(
    request_path, passport_path, spec_path, executable, expected_executable_digest, repositories
):
    # Inputs are snapshotted once; the resolver receives those exact passport bytes.
    import yaml

    from implementation_contract_pack import UniqueKeyLoader

    request_raw, passport_raw, spec_raw = (
        p.read_bytes() for p in (request_path, passport_path, spec_path)
    )
    request, passport = read_json(request_raw), read_json(passport_raw)
    policy_digest = digest(Path(__file__).read_bytes())
    try:
        node = yaml.load(spec_raw, Loader=UniqueKeyLoader)
    except yaml.YAMLError as error:
        raise ValueError("invalid source YAML") from error
    if (
        not isinstance(request, dict)
        or type(request.get("schema_version")) is not int
        or request.get("schema_version") != 1
    ):
        raise ValueError("request requires schema_version 1")
    if request.get("artifact_kind") != "evidence_claim_admission_request":
        raise ValueError("invalid request artifact kind")
    if not isinstance(passport, dict) or not isinstance(node, dict):
        raise ValueError("passport and spec must be objects")
    source = request.get("source", {})
    if not isinstance(source, dict) or not isinstance(passport.get("metadata"), dict):
        raise ValueError("source and passport metadata must be objects")
    if source.get("spec_sha256") != digest(spec_raw) or source.get("passport_sha256") != digest(
        passport_raw
    ):
        raise ValueError("stale spec or passport digest")
    if (
        not nonempty(source.get("spec_id"))
        or source.get("spec_id") != node.get("id")
        or node.get("kind") != "spec"
    ):
        raise ValueError("source spec identity mismatch")
    if canonical_claim_errors(node):
        raise ValueError("canonical spec contains invalid claim declarations or asserted verdicts")
    if canonical_claim_errors({"evidence_claims": request.get("claims")}):
        raise ValueError("invalid requested claim declarations")
    if "evidence_claims" in node and request["claims"] != node["evidence_claims"]:
        raise ValueError("request must cover the exact canonical claim declarations")
    cli = executable.expanduser().resolve(strict=True)
    cli_digest = digest(cli.read_bytes())
    if cli_digest != expected_executable_digest:
        raise ValueError("untrusted Feature Passport executable digest")
    with tempfile.TemporaryDirectory(prefix="specgraph-evidence-admission-") as directory:
        snapshot = Path(directory) / "passport.json"
        snapshot.write_bytes(passport_raw)
        command = [str(cli), "resolve-sources", str(snapshot)]
        for name, path in sorted(repositories.items()):
            command.extend(["--repository", f"{name}={path}"])
        process = subprocess.run(command, capture_output=True, timeout=120)
    if any(
        p.read_bytes() != raw
        for p, raw in (
            (request_path, request_raw),
            (passport_path, passport_raw),
            (spec_path, spec_raw),
        )
    ):
        raise ValueError("evidence inputs changed during evaluation")
    if digest(Path(__file__).read_bytes()) != policy_digest:
        raise ValueError("admission policy changed during evaluation")
    if digest(cli.read_bytes()) != cli_digest:
        raise ValueError("Feature Passport executable changed during evaluation")
    if process.returncode not in {0, 1}:
        raise ValueError("Feature Passport adapter execution failed")
    resolution = read_json(process.stdout)
    if not isinstance(resolution, dict):
        raise ValueError("invalid Feature Passport response")
    result = evaluate_claims(request, passport, resolution)
    blockers = []
    if process.returncode != 0:
        blockers.append("source_adapter_unsuccessful")
    if node.get("gate_state") != "none":
        blockers.append(f"source_gate:{node.get('gate_state', 'missing')}")
    if node.get("status") not in {"linked", "reviewed", "frozen"}:
        blockers.append(f"source_status:{node.get('status', 'missing')}")
    result["admitted"] = result["admitted"] and not blockers
    return {
        "artifact_kind": "evidence_claim_admission",
        "schema_version": 1,
        "policy_id": POLICY_ID,
        "policy_sha256": policy_digest,
        "subject": source,
        "request_sha256": digest(request_raw),
        "passport_id": passport.get("metadata", {}).get("passport_id"),
        "passport_version": passport.get("metadata", {}).get("version"),
        "adapter": {
            "provider": "feature_passport",
            "executable_sha256": cli_digest,
            "profile": "pinned_swift_source_resolution",
            "exit_code": process.returncode,
            "report_sha256": digest(process.stdout),
        },
        "source_resolution": resolution,
        "blockers": blockers,
        **result,
        "canonical_mutations_allowed": False,
        "runtime_code_mutations_allowed": False,
        "receipt_signature_verified": False,
        "environment": "local_source_inspection",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--passport", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--feature-passport-cli", type=Path, required=True)
    parser.add_argument("--feature-passport-cli-sha256", required=True)
    parser.add_argument("--repository", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        repositories = {}
        for item in args.repository:
            name, separator, path = item.partition("=")
            if not separator or not name or name in repositories or not Path(path).is_absolute():
                raise ValueError("repository must be a unique name=absolute-checkout")
            repositories[name] = path
        result = run_admission(
            args.request,
            args.passport,
            args.spec,
            args.feature_passport_cli,
            args.feature_passport_cli_sha256,
            repositories,
        )
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
        return 0 if result["admitted"] else 2
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print(
            json.dumps(
                {
                    "artifact_kind": "evidence_claim_admission_error",
                    "admitted": False,
                    "error": str(error),
                },
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
