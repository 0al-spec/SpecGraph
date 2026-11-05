"""Native FeaturePassport validation and the SpecGraph-owned locator join."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Protocol

from intent_decision_review.sources import strict_json

from .criterion import CriterionBinding, CriterionSource, PassportBindingFacts, PassportIdentity
from .criterion_inputs import read_regular, sha256
from .criterion_passport_binding_spec import CRITERION_PASSPORT_BINDING_SPEC
from .publication import mapping, records, text

FEATURE_PASSPORT_REVISION = "0fe35e9edb1461744ffa89161ec64cc86d44f728"
FEATURE_PASSPORT_SCHEMA_SHA256 = "b672a5523516cf91ddfacbaf2a4e6df622c05edb2ef97306b199313662ef6902"
SCHEMA_NAME = "feature-passport.v1.schema.json"
RESOURCE_DIRS = (
    "FeaturePassport_FeaturePassport.bundle/Contents/Resources",
    "FeaturePassport_FeaturePassport.bundle",
    "FeaturePassport_FeaturePassport.resources",
)


class PassportValidation(Protocol):
    def validate(self, raw: bytes) -> str:
        """Validate with the pinned native contract and return the tool digest."""


@dataclass(frozen=True)
class NativePassportValidation:
    executable: Path
    executable_sha256: str

    def validate(self, raw: bytes) -> str:
        if not self.executable.is_absolute():
            raise ValueError("native FeaturePassport validator requires an absolute path")
        executable = self.executable.resolve(strict=True)
        digest = sha256(read_regular(executable, 128 * 1024 * 1024))
        if digest != self.executable_sha256:
            raise ValueError("native FeaturePassport validator SHA-256 mismatch")
        candidates = [executable.parent / directory / SCHEMA_NAME for directory in RESOURCE_DIRS]
        resources = [path for path in candidates if path.is_file()]
        if len(resources) != 1:
            raise FileNotFoundError("expected one adjacent native FeaturePassport schema resource")
        if sha256(read_regular(resources[0].resolve())) != FEATURE_PASSPORT_SCHEMA_SHA256:
            raise ValueError("native FeaturePassport schema SHA-256 mismatch")
        # Native CLI validates a file. Pass the exact captured bytes in a private temp file.
        with NamedTemporaryFile(suffix=".json") as captured:
            captured.write(raw)
            captured.flush()
            result = subprocess.run(
                [str(executable), "validate", captured.name],
                cwd=executable.parent,
                capture_output=True,
                timeout=30,
                check=False,
            )
        if result.returncode == 1:
            codes = {line.partition(b":")[0] for line in result.stderr.splitlines()}
            labels = sorted(
                c.decode()
                for c in codes
                & {b"schema", b"duplicate_id", b"missing_reference", b"invalid_reference_role"}
            )
            raise ValueError(f"native FeaturePassport rejected passport: {', '.join(labels)}")
        if result.returncode != 0 or result.stdout.strip() != b"valid":
            raise OSError("native FeaturePassport validator did not complete validation")
        return digest


def native_document(raw: bytes, validator: PassportValidation) -> tuple[dict, PassportIdentity]:
    passport = mapping(strict_json(raw), "FeaturePassport")
    digest = validator.validate(raw)
    meta = mapping(passport.get("metadata"), "passport metadata")
    return passport, PassportIdentity(
        text(meta.get("passport_id"), "passport ID"),
        text(meta.get("feature_id"), "feature ID"),
        text(meta.get("version"), "passport version"),
        text(meta.get("status"), "passport lifecycle"),
        digest,
        FEATURE_PASSPORT_REVISION,
        FEATURE_PASSPORT_SCHEMA_SHA256,
    )


def exact_row(value: object, row_id: str, label: str) -> dict:
    candidates = [row for row in records(value, label) if row.get("id") == row_id]
    if len(candidates) != 1:
        raise ValueError(f"{label} does not contain exactly one selected ID: {row_id}")
    return candidates[0]


def scenario_binding(
    passport: dict, source: CriterionSource, binding: CriterionBinding, scope: dict
) -> str:
    spec = mapping(passport.get("spec"), "passport spec")
    intent = mapping(spec.get("intent"), "passport intent")
    criterion = exact_row(intent.get("acceptance_criteria"), binding.criterion_id, "criterion")
    contract = exact_row(spec.get("contract_refs"), binding.contract_ref_id, "contract reference")
    locator = mapping(contract.get("locator"), "contract locator")
    implementation = mapping(spec.get("implementation"), "passport implementation")
    declared = exact_row(
        implementation.get("bindings"), binding.passport_binding_id, "implementation binding"
    )
    expected_locator = {**scope, "pointer": source.pointer}
    facts = PassportBindingFacts(
        source.text,
        criterion.get("text"),
        contract.get("provider"),
        contract.get("relation"),
        tuple(expected_locator.items()),
        tuple((name, locator.get(name)) for name in expected_locator),
        binding.criterion_id,
        binding.contract_ref_id,
        tuple(declared.get("acceptance_criteria_ids", [])),
        tuple(declared.get("contract_ref_ids", [])),
        tuple(declared.get("test_element_ids", [])),
    )
    if not CRITERION_PASSPORT_BINDING_SPEC.is_satisfied_by(facts):
        raise ValueError("selected passport criterion, locator or test binding does not match")
    return text(locator.get("scenario_id"), "scenario ID")
