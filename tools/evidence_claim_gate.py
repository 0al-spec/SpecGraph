"""Admission of bounded implementation claims from a live Feature Passport adapter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import selectors
import signal
import subprocess
import tempfile
import time
from pathlib import Path

KINDS = {
    "source_anchored",
    "tests_verified",
    "runtime_verified",
    "effect_committed",
    "outcome_completed",
}
CLAIM_FIELDS = {"id", "kind", "passport_criterion_ids"}
RUNTIME_MAPPING_FIELDS = {
    "feature_id",
    "passport_id",
    "passport_version",
    "claim_id",
    "claim_policy_id",
    "claim_policy_version",
    "claim_policy_digest",
    "predicate_profile",
    "authority_id",
    "key_id",
}
RUNTIME_PIN_FIELDS = {
    "claim_policy_sha256",
    "bundle_sha256",
    "decision_sha256",
    "receipt_trust_store_sha256",
    "decision_trust_store_sha256",
    "feature_passport_cli_sha256",
    "pair_files",
}
POLICY_ID = "specgraph.evidence-claim-admission.local-source.v1"
RUNTIME_POLICY_ID = "specgraph.evidence-claim-admission.local-source-runtime.v1"


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
        if (
            not isinstance(claim, dict)
            or set(claim) - (CLAIM_FIELDS | {"feature_passport_decision"})
            or not CLAIM_FIELDS <= set(claim)
        ):
            errors.append(
                "evidence_claims allow only declaration fields and runtime decision identity; "
                "verdicts are derived"
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
        mapping = claim.get("feature_passport_decision")
        if "feature_passport_decision" in claim:
            if (
                claim["kind"] != "runtime_verified"
                or not isinstance(mapping, dict)
                or set(mapping) != RUNTIME_MAPPING_FIELDS
            ):
                errors.append(
                    "feature_passport_decision is an exact identity mapping allowed only "
                    "for runtime_verified"
                )
            elif (
                not all(nonempty(value) for value in mapping.values())
                or mapping["claim_id"] != claim["id"]
            ):
                errors.append(
                    "feature_passport_decision requires nonempty identities matching the claim ID"
                )
            elif not re.fullmatch(r"sha256:[0-9a-f]{64}", mapping["claim_policy_digest"]):
                errors.append(
                    "feature_passport_decision claim_policy_digest must be a SHA-256 digest"
                )
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


def evaluate_claims(request, passport, resolution, runtime_results=None):
    """Pure interpretation; callers must supply a live trusted adapter result."""
    if not isinstance(request, dict):
        return {"admitted": False, "claims": [], "errors": ["request must be an object"]}
    errors = canonical_claim_errors({"evidence_claims": request.get("claims")})
    if errors:
        return {"admitted": False, "claims": [], "errors": errors}
    results = []
    runtime_results = runtime_results or {}
    for claim in request["claims"]:
        reason = "evidence_evaluator_unavailable"
        if claim["kind"] == "source_anchored":
            try:
                reason = source_claim_reason(claim, passport, resolution)
            except (AttributeError, KeyError, TypeError, ValueError):
                reason = "malformed_evidence_input"
        elif claim["kind"] == "runtime_verified":
            reason = runtime_results.get(claim["id"], "evidence_evaluator_unavailable")
            if reason is None:
                reason = None
        results.append(
            {
                "id": claim["id"],
                "kind": claim["kind"],
                "passport_criterion_ids": claim["passport_criterion_ids"],
                "state": "satisfied" if reason is None else "unknown",
                "reason": reason,
                "scope": "pinned_source_identity_only"
                if claim["kind"] == "source_anchored"
                else "signed_feature_passport_runtime_predicate"
                if claim["kind"] == "runtime_verified" and claim.get("feature_passport_decision")
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


def prefixed_digest(raw):
    return "sha256:" + digest(raw)


def read_bounded(path, limit, label):
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError(f"{label} exceeds {limit}-byte limit")
    return raw


def run_bounded(command, timeout, stdout_limit, stderr_limit):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    selector = selectors.DefaultSelector()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    limits = {"stdout": stdout_limit, "stderr": stderr_limit}
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            for key, _ in selector.select(remaining):
                chunk = os.read(key.fileobj.fileno(), 65_536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                buffer = buffers[key.data]
                if len(buffer) + len(chunk) > limits[key.data]:
                    raise ValueError(f"Feature Passport {key.data} exceeds output limit")
                buffer.extend(chunk)
        return subprocess.CompletedProcess(
            command,
            process.wait(timeout=max(0.01, deadline - time.monotonic())),
            bytes(buffers["stdout"]),
            bytes(buffers["stderr"]),
        )
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        raise
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()


def _runtime_inputs(runtime):
    if not isinstance(runtime, dict) or set(runtime) != RUNTIME_PIN_FIELDS:
        raise ValueError(
            "runtime source requires exact policy, bundle, decision, trust, CLI, and pair pins"
        )
    for name in RUNTIME_PIN_FIELDS - {"pair_files"}:
        if not re.fullmatch(
            r"[0-9a-f]{64}", runtime[name] if isinstance(runtime[name], str) else ""
        ):
            raise ValueError(f"invalid runtime digest pin: {name}")
    if not isinstance(runtime["pair_files"], list):
        raise ValueError("runtime pair_files must be a list")
    return runtime


def _relative_pair_file(root, relative):
    if not nonempty(relative) or "\\" in relative:
        raise ValueError("bundle pair paths must be nonempty relative POSIX paths")
    path = Path(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("bundle pair path escapes its pinned bundle directory")
    root = root.resolve(strict=True)
    resolved = (root / path).resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ValueError("bundle pair file is not a regular file below the bundle directory")
    return resolved


def _validate_pair_file_sizes(pair_sources):
    total = 0
    for _, _, observation, receipt in pair_sources:
        observation_size = observation.stat().st_size
        receipt_size = receipt.stat().st_size
        if observation_size > 10_000_000 or receipt_size > 256_000:
            raise ValueError("runtime pair file exceeds Feature Passport limit")
        total += observation_size + receipt_size
        if total > 64_000_000:
            raise ValueError("runtime pair files exceed Feature Passport aggregate limit")


def _validate_runtime_decision(
    decision, mapping, passport_raw, policy_raw, bundle_raw, receipt_trust_raw, bundle
):
    fields = {
        "artifact_kind",
        "schema_version",
        "decision_profile",
        "decision_digest",
        "decision",
        "feature_id",
        "passport_id",
        "passport_version",
        "claim_id",
        "claim_policy_id",
        "claim_policy_version",
        "claim_policy_digest",
        "predicate_profile",
        "evaluation_time",
        "passport_digest",
        "bundle_digest",
        "receipt_trust_store_digest",
        "pair_digests",
        "issuer",
        "signature",
    }
    if not isinstance(decision, dict) or set(decision) != fields:
        raise ValueError("invalid signed aggregate decision fields")
    if (
        decision["artifact_kind"] != "aggregate_claim_decision"
        or type(decision["schema_version"]) is not int
        or decision["schema_version"] != 1
        or decision["decision_profile"] != "fp-aggregate-decision-v1-fields"
    ):
        raise ValueError("unsupported signed decision profile")
    for field in (
        "decision_digest",
        "passport_digest",
        "bundle_digest",
        "receipt_trust_store_digest",
    ):
        if not isinstance(decision[field], str) or not re.fullmatch(
            r"sha256:[0-9a-f]{64}", decision[field]
        ):
            raise ValueError(f"invalid signed decision digest: {field}")
    if decision["passport_digest"] != prefixed_digest(passport_raw):
        raise ValueError("signed decision passport digest mismatch")
    if decision["bundle_digest"] != prefixed_digest(bundle_raw):
        raise ValueError("signed decision bundle digest mismatch")
    if decision["claim_policy_digest"] != prefixed_digest(policy_raw):
        raise ValueError("signed decision claim policy digest mismatch")
    if decision["receipt_trust_store_digest"] != prefixed_digest(receipt_trust_raw):
        raise ValueError("signed decision receipt trust store digest mismatch")
    identity_fields = {
        "feature_id": "feature_id",
        "passport_id": "passport_id",
        "passport_version": "passport_version",
        "claim_id": "claim_id",
        "claim_policy_id": "claim_policy_id",
        "claim_policy_version": "claim_policy_version",
        "claim_policy_digest": "claim_policy_digest",
        "predicate_profile": "predicate_profile",
    }
    if any(decision[source] != mapping[target] for source, target in identity_fields.items()):
        raise ValueError("signed decision identity does not match canonical declaration")
    issuer = decision["issuer"]
    if (
        not isinstance(issuer, dict)
        or set(issuer) != {"authority_id", "key_id"}
        or any(issuer[field] != mapping[field] for field in ("authority_id", "key_id"))
    ):
        raise ValueError("signed decision authority does not match canonical declaration")
    signature = decision["signature"]
    if (
        not isinstance(signature, dict)
        or set(signature) != {"algorithm", "profile", "value"}
        or not all(nonempty(value) for value in signature.values())
    ):
        raise ValueError("invalid signed decision signature envelope")
    if not nonempty(decision["evaluation_time"]) or decision["decision"] not in {
        "accepted",
        "not_satisfied",
    }:
        raise ValueError("invalid signed decision verdict")
    pairs = bundle.get("pairs") if isinstance(bundle, dict) else None
    pair_digests = decision["pair_digests"]
    if (
        not isinstance(pairs, list)
        or not isinstance(pair_digests, list)
        or len(pairs) != len(pair_digests)
    ):
        raise ValueError("signed decision pair list does not match bundle")
    return decision


def _runtime_decision_result(report_raw, exit_code, mapping):
    try:
        report = read_json(report_raw)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return "invalid_runtime_verification_report"
    report_decision = report.get("decision") if isinstance(report, dict) else None
    report_claim_id = report.get("claim_id") if isinstance(report, dict) else None
    if (
        not isinstance(report, dict)
        or set(report) != {"trusted", "decision", "claim_id", "issues"}
        or type(report.get("trusted")) is not bool
        or not isinstance(report.get("issues"), list)
        or (report.get("trusted") is True and report.get("issues") != [])
        or (
            report_decision is not None
            and (
                not isinstance(report_decision, str)
                or report_decision not in {"accepted", "not_satisfied"}
            )
        )
        or (report_claim_id is not None and not isinstance(report_claim_id, str))
        or (report_claim_id is not None and report_claim_id != mapping["claim_id"])
    ):
        return "invalid_runtime_verification_report"
    if exit_code != 0 or report["trusted"] is not True:
        return "runtime_decision_untrusted"
    if report["claim_id"] != mapping["claim_id"]:
        return "runtime_decision_claim_mismatch"
    if report["decision"] == "not_satisfied":
        return "signed_decision_not_accepted"
    return None if report["decision"] == "accepted" else "runtime_decision_unknown"


def run_admission(
    request_path,
    passport_path,
    spec_path,
    executable,
    expected_executable_digest,
    repositories,
    claim_policy_path=None,
    bundle_path=None,
    decision_path=None,
    receipt_trust_store_path=None,
    decision_trust_store_path=None,
):
    # Inputs are snapshotted once; the resolver receives those exact passport bytes.
    import yaml

    from implementation_contract_pack import UniqueKeyLoader

    request_raw = read_bounded(request_path, 1_000_000, "admission request")
    passport_raw = read_bounded(passport_path, 10_000_000, "passport")
    spec_raw = read_bounded(spec_path, 10_000_000, "source spec")
    request, passport = read_json(request_raw), read_json(passport_raw)
    policy_path = Path(__file__)
    policy_raw = read_bounded(policy_path, 2_000_000, "admission policy")
    policy_digest = digest(policy_raw)
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
    cli_raw = read_bounded(cli, 64_000_000, "Feature Passport executable")
    cli_digest = digest(cli_raw)
    if cli_digest != expected_executable_digest:
        raise ValueError("untrusted Feature Passport executable digest")
    mapped = [
        c
        for c in request["claims"]
        if c["kind"] == "runtime_verified" and c.get("feature_passport_decision")
    ]
    runtime_results, runtime_process = {}, None
    runtime_inputs, pair_originals, normalized_pairs = {}, [], []
    pair_limits = {}
    runtime_paths = {}
    bundle = None
    signed_decision = None
    if mapped:
        if len(mapped) != 1:
            raise ValueError("one runtime decision per admission request is supported")
        required = (
            claim_policy_path,
            bundle_path,
            decision_path,
            receipt_trust_store_path,
            decision_trust_store_path,
        )
        if not all(required):
            raise ValueError(
                "runtime_verified requires claim policy, bundle, decision, and both trust stores"
            )
        pins = _runtime_inputs(source.get("runtime"))
        if pins["feature_passport_cli_sha256"] != expected_executable_digest:
            raise ValueError("runtime request CLI digest pin does not match invocation")
        runtime_paths = {
            "claim_policy": Path(claim_policy_path).expanduser().resolve(strict=True),
            "bundle": Path(bundle_path).expanduser().resolve(strict=True),
            "decision": Path(decision_path).expanduser().resolve(strict=True),
            "receipt_trust": Path(receipt_trust_store_path).expanduser().resolve(strict=True),
            "decision_trust": Path(decision_trust_store_path).expanduser().resolve(strict=True),
        }
        limits = {
            "claim_policy": 256_000,
            "bundle": 256_000,
            "decision": 1_000_000,
            "receipt_trust": 1_000_000,
            "decision_trust": 1_000_000,
        }
        for name, path in runtime_paths.items():
            runtime_inputs[name] = read_bounded(path, limits[name], f"runtime {name}")
        pin_names = {
            "claim_policy": "claim_policy_sha256",
            "bundle": "bundle_sha256",
            "decision": "decision_sha256",
            "receipt_trust": "receipt_trust_store_sha256",
            "decision_trust": "decision_trust_store_sha256",
        }
        for name, pin in pin_names.items():
            if digest(runtime_inputs[name]) != pins[pin]:
                raise ValueError(f"stale runtime input digest: {pin}")
        bundle = read_json(runtime_inputs["bundle"])
        if (
            not isinstance(bundle, dict)
            or set(bundle) != {"artifact_kind", "schema_version", "pairs"}
            or bundle.get("artifact_kind") != "local_aggregate_claim_bundle"
            or type(bundle.get("schema_version")) is not int
            or bundle["schema_version"] != 1
        ):
            raise ValueError("invalid Feature Passport aggregate claim bundle")
        pairs, pair_pins = bundle["pairs"], pins["pair_files"]
        if (
            not isinstance(pairs, list)
            or len(pairs) > 64
            or not isinstance(pair_pins, list)
            or len(pair_pins) != len(pairs)
        ):
            raise ValueError("runtime pair pins must cover the bounded bundle exactly")
        pair_sources = []
        for index in range(len(pairs)):
            pair, pin = pairs[index], pair_pins[index]
            if not isinstance(pair, dict) or set(pair) != {"observation", "receipt"}:
                raise ValueError("invalid aggregate bundle pair")
            if (
                not isinstance(pin, dict)
                or set(pin)
                != {"observation_path", "observation_sha256", "receipt_path", "receipt_sha256"}
                or pair["observation"] != pin["observation_path"]
                or pair["receipt"] != pin["receipt_path"]
            ):
                raise ValueError("runtime pair file pin does not match bundle")
            observed = _relative_pair_file(runtime_paths["bundle"].parent, pair["observation"])
            receipt = _relative_pair_file(runtime_paths["bundle"].parent, pair["receipt"])
            pair_sources.append((pair, pin, observed, receipt))
        _validate_pair_file_sizes(pair_sources)
        aggregate_pair_bytes = 0
        for pair, pin, observed, receipt in pair_sources:
            observed_raw = read_bounded(observed, 10_000_000, "observation")
            receipt_raw = read_bounded(receipt, 256_000, "receipt")
            aggregate_pair_bytes += len(observed_raw) + len(receipt_raw)
            if aggregate_pair_bytes > 64_000_000:
                raise ValueError("runtime pair files exceed Feature Passport aggregate limit")
            for field, raw in (
                ("observation_sha256", observed_raw),
                ("receipt_sha256", receipt_raw),
            ):
                value = pin[field]
                if (
                    not re.fullmatch(r"[0-9a-f]{64}", value if isinstance(value, str) else "")
                    or digest(raw) != value
                ):
                    raise ValueError(f"stale runtime pair file digest: {field}")
            pair_originals.extend([(observed, observed_raw), (receipt, receipt_raw)])
            pair_limits[observed] = max(pair_limits.get(observed, 0), 10_000_000)
            pair_limits[receipt] = max(pair_limits.get(receipt, 0), 256_000)
            normalized_pairs.append(
                (pair["observation"], pair["receipt"], observed_raw, receipt_raw)
            )
        decision = read_json(runtime_inputs["decision"])
        signed_decision = decision
        mapping = mapped[0]["feature_passport_decision"]
        _validate_runtime_decision(
            decision,
            mapping,
            passport_raw,
            runtime_inputs["claim_policy"],
            runtime_inputs["bundle"],
            runtime_inputs["receipt_trust"],
            bundle,
        )
        for index in range(len(normalized_pairs)):
            signed = decision["pair_digests"][index]
            observation, receipt, observation_raw, receipt_raw = normalized_pairs[index]
            if (
                not isinstance(signed, dict)
                or set(signed)
                != {"observation_path", "receipt_path", "observation_digest", "receipt_digest"}
                or signed["observation_path"] != observation
                or signed["receipt_path"] != receipt
                or signed["observation_digest"] != prefixed_digest(observation_raw)
                or signed["receipt_digest"] != prefixed_digest(receipt_raw)
            ):
                raise ValueError("signed decision pair digest mismatch")
    elif "runtime" in source:
        raise ValueError("runtime input pins require a canonical runtime decision declaration")
    with tempfile.TemporaryDirectory(prefix="specgraph-evidence-admission-") as directory:
        root = Path(directory)
        snapshot = root / "passport.json"
        snapshot.write_bytes(passport_raw)
        process = None
        resolution = {"validation_issues": [], "anchors": []}
        if any(c["kind"] == "source_anchored" for c in request["claims"]):
            command = [str(cli), "resolve-sources", str(snapshot)]
            for name, path in sorted(repositories.items()):
                command.extend(["--repository", f"{name}={path}"])
            process = run_bounded(command, 120, 16_000_000, 1_000_000)
            if process.returncode not in {0, 1}:
                raise ValueError("Feature Passport source adapter execution failed")
            resolution = read_json(process.stdout)
            if not isinstance(resolution, dict):
                raise ValueError("invalid Feature Passport source response")
        if mapped:
            copied_cli = root / "feature-passport"
            copied_cli.write_bytes(cli_raw)
            copied_cli.chmod(0o700)
            if (
                digest(read_bounded(copied_cli, 64_000_000, "Feature Passport executable snapshot"))
                != cli_digest
            ):
                raise ValueError("Feature Passport executable snapshot digest mismatch")
            snapshots = {}
            for name in runtime_paths:
                snapshots[name] = root / (name + ".json")
                snapshots[name].write_bytes(runtime_inputs[name])
            snapshots["bundle"].write_bytes(runtime_inputs["bundle"])
            bundle_root = snapshots["bundle"].parent
            for observation, receipt, observation_raw, receipt_raw in normalized_pairs:
                for relative, raw in ((observation, observation_raw), (receipt, receipt_raw)):
                    target = bundle_root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(raw)
            command = [
                str(copied_cli),
                "verify-decision",
                str(snapshot),
                str(snapshots["claim_policy"]),
                str(snapshots["bundle"]),
                str(snapshots["decision"]),
                "--trust-store",
                str(snapshots["receipt_trust"]),
                "--decision-trust",
                str(snapshots["decision_trust"]),
            ]
            runtime_process = run_bounded(command, 120, 1_000_000, 1_000_000)
            if (
                digest(read_bounded(copied_cli, 64_000_000, "Feature Passport executable snapshot"))
                != cli_digest
            ):
                raise ValueError("Feature Passport executable snapshot changed during evaluation")
            runtime_results[mapped[0]["id"]] = _runtime_decision_result(
                runtime_process.stdout,
                runtime_process.returncode,
                mapped[0]["feature_passport_decision"],
            )
            if runtime_results[mapped[0]["id"]] in {
                None,
                "signed_decision_not_accepted",
            }:
                try:
                    report_decision = read_json(runtime_process.stdout)["decision"]
                    if report_decision != signed_decision["decision"]:
                        runtime_results[mapped[0]["id"]] = "runtime_signed_decision_mismatch"
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError, ValueError):
                    runtime_results[mapped[0]["id"]] = "invalid_runtime_verification_report"
            if (
                runtime_results[mapped[0]["id"]] is None
                and signed_decision["decision"] != "accepted"
            ):
                runtime_results[mapped[0]["id"]] = "signed_decision_not_accepted"
    watched = [
        (request_path, request_raw),
        (passport_path, passport_raw),
        (spec_path, spec_raw),
    ]
    watched.extend((path, runtime_inputs[name]) for name, path in runtime_paths.items())
    watched.extend(pair_originals)
    watched_limits = {
        request_path: 1_000_000,
        passport_path: 10_000_000,
        spec_path: 10_000_000,
        **{
            path: {
                "claim_policy": 256_000,
                "bundle": 256_000,
                "decision": 1_000_000,
                "receipt_trust": 1_000_000,
                "decision_trust": 1_000_000,
            }[name]
            for name, path in runtime_paths.items()
        },
        **pair_limits,
    }
    if any(
        read_bounded(path, watched_limits[path], "watched evidence input") != raw
        for path, raw in watched
    ):
        raise ValueError("evidence inputs changed during evaluation")
    if digest(read_bounded(policy_path, 2_000_000, "admission policy")) != policy_digest:
        raise ValueError("admission policy changed during evaluation")
    if digest(read_bounded(cli, 64_000_000, "Feature Passport executable")) != cli_digest:
        raise ValueError("Feature Passport executable changed during evaluation")
    if any(
        read_bounded(p, watched_limits[p], "watched evidence input") != raw for p, raw in watched
    ):
        raise ValueError("evidence inputs changed during evaluation")
    result = evaluate_claims(request, passport, resolution, runtime_results)
    blockers = []
    if process is not None and process.returncode != 0:
        blockers.append("source_adapter_unsuccessful")
    if node.get("gate_state") != "none":
        blockers.append(f"source_gate:{node.get('gate_state', 'missing')}")
    if node.get("status") not in {"linked", "reviewed", "frozen"}:
        blockers.append(f"source_status:{node.get('status', 'missing')}")
    result["admitted"] = result["admitted"] and not blockers
    return {
        "artifact_kind": "evidence_claim_admission",
        "schema_version": 1,
        "policy_id": RUNTIME_POLICY_ID if mapped else POLICY_ID,
        "policy_sha256": policy_digest,
        "subject": source,
        "request_sha256": digest(request_raw),
        "passport_id": passport.get("metadata", {}).get("passport_id"),
        "passport_version": passport.get("metadata", {}).get("version"),
        "adapter": {
            "provider": "feature_passport",
            "executable_sha256": cli_digest,
            "profile": "pinned_swift_source_resolution",
            "exit_code": process.returncode if process is not None else None,
            "report_sha256": digest(process.stdout) if process is not None else None,
        },
        "runtime_verification": {
            "exit_code": runtime_process.returncode,
            "report_sha256": digest(runtime_process.stdout),
            "executable_sha256": cli_digest,
            "status": runtime_results[mapped[0]["id"]],
        }
        if runtime_process is not None
        else None,
        "source_resolution": resolution,
        "blockers": blockers,
        **result,
        "canonical_mutations_allowed": False,
        "runtime_code_mutations_allowed": False,
        "feature_passport_decision_trusted": bool(
            mapped
            and runtime_process is not None
            and runtime_results[mapped[0]["id"]] in {None, "signed_decision_not_accepted"}
        ),
        "environment": "local_source_and_runtime_inspection"
        if mapped
        else "local_source_inspection",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--passport", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--feature-passport-cli", type=Path, required=True)
    parser.add_argument("--feature-passport-cli-sha256", required=True)
    parser.add_argument("--claim-policy", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--receipt-trust-store", type=Path)
    parser.add_argument("--decision-trust-store", type=Path)
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
            args.claim_policy,
            args.bundle,
            args.decision,
            args.receipt_trust_store,
            args.decision_trust_store,
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
