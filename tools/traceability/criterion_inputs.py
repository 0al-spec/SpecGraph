"""Adapters for explicit retained inputs and pinned Git blobs."""

import hashlib
import os
import re
import stat
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from intent_decision_review.sources import MAX_BYTES, encoded, git, strict_json
from spec_yaml import load_yaml_text

from .criterion import (
    CriterionBinding,
    CriterionSource,
    ExpectedAssertion,
    FilePin,
    JournalDeclaration,
)
from .publication import mapping, records, text

PROFILE = "specgraph.criterion-observation/cucumber-messages-34.2.1-v1"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def checked_hash(raw: bytes, pin: FilePin) -> None:
    actual = sha256(raw)
    if actual != pin.sha256:
        raise ValueError(f"{pin.path}: SHA-256 mismatch; expected {pin.sha256}, observed {actual}")


def read_regular(path: Path, limit: int = MAX_BYTES) -> bytes:
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW), "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise ValueError("input must be a bounded regular file")
        data = handle.read(limit + 1)
        if len(data) > limit:
            raise ValueError("input exceeds size limit")
        return data


def read_pin(root: Path, pin: FilePin) -> bytes:
    root = root.resolve()
    path = (root / pin.path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"retained path escapes its explicit root: {pin.path}")
    try:
        raw = read_regular(path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"retained input unavailable: {pin.path}") from exc
    checked_hash(raw, pin)
    return raw


def full_revision(value: object) -> str:
    ref = text(value, "source revision")
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", ref):
        raise ValueError("source revision must be a full lowercase Git commit ID")
    return ref


def pinned_blob(root: Path, ref: str, path: str) -> bytes:
    full_revision(ref)
    try:
        actual = git(root, "--no-replace-objects", "rev-parse", "--verify", f"{ref}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise FileNotFoundError(f"pinned Git commit unavailable: {ref}") from exc
    if actual.decode().strip() != ref:
        raise ValueError("source revision does not name a commit directly")
    entry = git(
        root, "--no-replace-objects", "--literal-pathspecs", "ls-tree", "-z", ref, "--", path
    )
    if not entry:
        raise FileNotFoundError(f"pinned Git blob unavailable: {ref}:{path}")
    header, name = entry.removesuffix(b"\0").split(b"\t", 1)
    mode, kind, oid = header.split()
    if name.decode() != path or mode not in (b"100644", b"100755") or kind != b"blob":
        raise ValueError("pinned source must be a regular Git blob at the exact path")
    blob = oid.decode()
    if int(git(root, "--no-replace-objects", "cat-file", "-s", blob)) > MAX_BYTES:
        raise ValueError("pinned source exceeds size limit")
    return git(root, "--no-replace-objects", "cat-file", "blob", blob)


@dataclass(frozen=True)
class CriterionInventory:
    sources: tuple[CriterionSource, ...]
    status: str | None
    gate_state: str | None


def parse_inventory(raw: bytes, spec_id: str, revision: str, path: str) -> CriterionInventory:
    document = load_yaml_text(raw.decode())
    if document.get("id") != spec_id:
        raise ValueError("pinned source node ID differs from selection")
    criteria = document.get("acceptance")
    if not isinstance(criteria, list) or not all(
        isinstance(c, str) and c.strip() for c in criteria
    ):
        raise ValueError("criterion profile requires an explicit acceptance string list")
    status, gate_state = document.get("status"), document.get("gate_state")
    if any(item is not None and not isinstance(item, str) for item in (status, gate_state)):
        raise ValueError("source lifecycle values must be text or null")
    for criterion in criteria:
        criterion.encode("utf-8")
    sha = sha256(raw)
    return CriterionInventory(
        tuple(
            CriterionSource(path, revision, sha, f"/acceptance/{i}", c)
            for i, c in enumerate(criteria)
        ),
        status,
        gate_state,
    )


def fields(raw: object, names: str, label: str) -> dict:
    row = mapping(raw, label)
    if set(row) != set(names.split()):
        raise ValueError(f"{label} fields differ from the v1 profile")
    return row


def pin(raw: object) -> FilePin:
    row = fields(raw, "path sha256", "file pin")
    return FilePin(text(row["path"], "file path"), text(row["sha256"], "SHA-256"))


def journal_declaration(raw: dict) -> JournalDeclaration:
    row = fields(
        raw,
        "artifact_id sha256 run_id test_source_revision execution_source_revision feature",
        "journal declaration",
    )
    digest = FilePin("journal", text(row["sha256"], "journal SHA-256")).sha256
    return JournalDeclaration(
        text(row["artifact_id"], "artifact ID"),
        digest,
        text(row["run_id"], "run ID"),
        full_revision(row["test_source_revision"]),
        full_revision(row["execution_source_revision"]),
        pin(row["feature"]),
    )


def canonical_json(value: object) -> str:
    rendered = encoded(value)
    rendered.encode("utf-8")  # Reject isolated surrogate escapes from JSON.
    return rendered


def assertion(raw: dict) -> ExpectedAssertion:
    row = fields(raw, "id step_id media_type expected_measurement", "assertion")
    media = text(row["media_type"], "media type")
    if media != "application/json" and not re.fullmatch(r"application/[a-z0-9.+-]+\+json", media):
        raise ValueError("assertion media type must be a supported JSON type")
    return ExpectedAssertion(
        text(row["id"], "assertion ID"),
        text(row["step_id"], "step ID"),
        media,
        canonical_json(mapping(row["expected_measurement"], "expected measurement")),
    )


def criterion_binding(raw: dict) -> CriterionBinding:
    row = fields(
        raw,
        "pointer criterion_id contract_ref_id passport_binding_id artifact_id case_id "
        "case_started_id attempt assertions",
        "criterion binding",
    )
    attempt = row["attempt"]
    if type(attempt) is not int or attempt < 0:
        raise ValueError("selected attempt must be a nonnegative integer")
    assertions = tuple(
        sorted(
            set(map(assertion, records(row["assertions"], "assertions"))),
            key=lambda item: (item.id, item.step_id, item.media_type, item.expected_json),
        )
    )
    if not assertions or len(assertions) != len({a.id for a in assertions}):
        raise ValueError("binding requires nonempty, unambiguous assertion IDs")
    if len(assertions) != len({(a.step_id, a.media_type) for a in assertions}):
        raise ValueError("binding requires unambiguous step/attachment selections")
    return CriterionBinding(
        text(row["pointer"], "criterion pointer"),
        text(row["criterion_id"], "passport criterion ID"),
        text(row["contract_ref_id"], "passport contract reference ID"),
        text(row["passport_binding_id"], "passport binding ID"),
        text(row["artifact_id"], "journal artifact ID"),
        text(row["case_id"], "test case ID"),
        text(row["case_started_id"], "test case start ID"),
        attempt,
        assertions,
    )


@dataclass(frozen=True)
class BindingPlan:
    journals: tuple[JournalDeclaration, ...]
    bindings: tuple[CriterionBinding, ...]


def parse_plan(raw: bytes, *, scope: dict, passport_sha256: str) -> BindingPlan:
    plan = fields(
        strict_json(raw),
        "artifact_kind schema_version scope profile passport_sha256 journals bindings",
        "binding plan",
    )
    if (
        plan["artifact_kind"] != "criterion_observation_binding_plan"
        or type(plan["schema_version"]) is not int
        or plan["schema_version"] != 1
        or plan["profile"] != PROFILE
    ):
        raise ValueError("unsupported criterion binding plan/profile")
    if plan["scope"] != scope or plan["passport_sha256"] != passport_sha256:
        raise ValueError("binding plan scope or passport fingerprint differs from selection")
    journals = set(map(journal_declaration, records(plan["journals"], "journals")))
    bindings = set(map(criterion_binding, records(plan["bindings"], "bindings")))
    return BindingPlan(
        tuple(sorted(journals, key=lambda j: encoded(asdict(j)))),
        tuple(sorted(bindings, key=lambda b: encoded(b.to_payload()))),
    )
