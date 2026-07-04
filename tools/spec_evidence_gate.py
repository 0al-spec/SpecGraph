#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SPEC_ID_PATTERN = re.compile(r"\bSG-SPEC-\d{4}\b")
PROPOSAL_ID_PATTERN = re.compile(r"\b(?:SG-PROP-|PROP-|PROPOSAL-)?(\d{4})\b")
NO_SPEC_IMPACT = "NO-SPEC-IMPACT"

SPEC_FIELD_PATTERN = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:Spec-ID|Spec-IDs|Spec ID|Spec IDs)\s*:\s*(.+?)\s*$"
)
PROPOSAL_FIELD_PATTERN = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?"
    r"(?:Proposal-ID|Proposal-IDs|Proposal ID|Proposal IDs)\s*:\s*(.+?)\s*$"
)
IMPACT_FIELD_PATTERN = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:Spec-Impact|Spec Impact)\s*:\s*(.+?)\s*$"
)
RATIONALE_FIELD_PATTERN = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:Spec-Rationale|Spec Rationale)\s*:\s*(.+?)\s*$"
)

LOGIC_PATH_PREFIXES = ("src/", "tools/")
LOGIC_WORKFLOW_PREFIX = ".github/workflows/"
LOGIC_EXACT_PATHS = (
    ".mlc_config.json",
    ".pre-commit-config.yaml",
    ".pre-commit-config.yml",
    ".ruff.toml",
    "Makefile",
    "Package.resolved",
    "Package.swift",
    "mypy.ini",
    "pyproject.toml",
    "requirements-dev.txt",
    "requirements.txt",
    "ruff.toml",
    "setup.cfg",
    "setup.py",
    "specgraph.project.yaml",
    "tox.ini",
)
LOGIC_SUFFIXES = (".py", ".json", ".yaml", ".yml", ".sh")


@dataclass(frozen=True)
class Evidence:
    spec_ids: tuple[str, ...]
    proposal_ids: tuple[str, ...]
    no_spec_impact: bool
    rationale: str
    invalid_tokens: tuple[str, ...]


@dataclass(frozen=True)
class GateResult:
    passed: bool
    message: str
    logic_files: tuple[str, ...]
    evidence: Evidence


def is_logic_path(path: str) -> bool:
    if path in LOGIC_EXACT_PATHS:
        return True
    if path.startswith(LOGIC_WORKFLOW_PREFIX) and path.endswith((".yml", ".yaml")):
        return True
    if path.startswith(LOGIC_PATH_PREFIXES) and path.endswith(LOGIC_SUFFIXES):
        return True
    return False


def _split_field_value(value: str) -> list[str]:
    return [token.strip("`[]() \t,;") for token in re.split(r"[\s,;]+", value) if token.strip()]


def _extract_spec_ids(text: str) -> tuple[list[str], list[str], bool]:
    spec_ids: list[str] = []
    invalid_tokens: list[str] = []
    no_spec_impact = False

    for match in SPEC_FIELD_PATTERN.finditer(text):
        for token in _split_field_value(match.group(1)):
            normalized = token.upper()
            if normalized == NO_SPEC_IMPACT:
                no_spec_impact = True
            elif SPEC_ID_PATTERN.fullmatch(normalized):
                spec_ids.append(normalized)
            elif token and token not in {"-", "N/A", "n/a"}:
                invalid_tokens.append(token)

    return spec_ids, invalid_tokens, no_spec_impact


def _extract_proposal_ids(text: str) -> tuple[list[str], list[str]]:
    proposal_ids: list[str] = []
    invalid_tokens: list[str] = []

    for match in PROPOSAL_FIELD_PATTERN.finditer(text):
        for token in _split_field_value(match.group(1)):
            normalized = token.upper()
            id_match = PROPOSAL_ID_PATTERN.fullmatch(normalized)
            if id_match:
                proposal_ids.append(id_match.group(1))
            elif token and token not in {"-", "N/A", "n/a"}:
                invalid_tokens.append(token)

    return proposal_ids, invalid_tokens


def _extract_first_field(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1).strip()


def parse_evidence_texts(texts: list[str]) -> Evidence:
    spec_ids: list[str] = []
    proposal_ids: list[str] = []
    invalid_tokens: list[str] = []
    no_spec_impact = False
    rationale = ""

    for text in texts:
        extracted_specs, invalid_specs, extracted_no_impact = _extract_spec_ids(text)
        extracted_proposals, invalid_proposals = _extract_proposal_ids(text)
        impact = _extract_first_field(IMPACT_FIELD_PATTERN, text).lower()
        text_rationale = _extract_first_field(RATIONALE_FIELD_PATTERN, text)

        spec_ids.extend(extracted_specs)
        proposal_ids.extend(extracted_proposals)
        invalid_tokens.extend(invalid_specs)
        invalid_tokens.extend(invalid_proposals)
        no_spec_impact = no_spec_impact or extracted_no_impact or impact == "no-impact"
        if text_rationale and not rationale:
            rationale = text_rationale

    return Evidence(
        spec_ids=tuple(dict.fromkeys(spec_ids)),
        proposal_ids=tuple(dict.fromkeys(proposal_ids)),
        no_spec_impact=no_spec_impact,
        rationale=rationale,
        invalid_tokens=tuple(dict.fromkeys(invalid_tokens)),
    )


def spec_id_exists(repo_root: Path, spec_id: str) -> bool:
    path = repo_root / "specs" / "nodes" / f"{spec_id}.yaml"
    if not path.exists():
        return False
    return f"id: {spec_id}" in path.read_text(encoding="utf-8")


def proposal_id_exists(repo_root: Path, proposal_id: str) -> bool:
    return bool(list((repo_root / "docs" / "proposals").glob(f"{proposal_id}_*.md")))


def _invalid_existing_ids(repo_root: Path, evidence: Evidence) -> list[str]:
    invalid_ids: list[str] = []
    for spec_id in evidence.spec_ids:
        if not spec_id_exists(repo_root, spec_id):
            invalid_ids.append(spec_id)
    for proposal_id in evidence.proposal_ids:
        if not proposal_id_exists(repo_root, proposal_id):
            invalid_ids.append(proposal_id)
    return invalid_ids


def evaluate_gate(repo_root: Path, changed_files: list[str], texts: list[str]) -> GateResult:
    logic_files = tuple(path for path in changed_files if is_logic_path(path))
    evidence = parse_evidence_texts(texts)

    if not logic_files:
        return GateResult(
            passed=True,
            message="Spec evidence gate skipped: no SpecGraph logic files changed.",
            logic_files=logic_files,
            evidence=evidence,
        )

    if evidence.invalid_tokens:
        return GateResult(
            passed=False,
            message=(
                "Spec evidence gate failed: unrecognized values in Spec-ID/Proposal-ID "
                f"fields: {', '.join(evidence.invalid_tokens)}."
            ),
            logic_files=logic_files,
            evidence=evidence,
        )

    invalid_ids = _invalid_existing_ids(repo_root, evidence)
    if invalid_ids:
        return GateResult(
            passed=False,
            message=(
                "Spec evidence gate failed: referenced Spec-ID/Proposal-ID values do not "
                f"exist in this checkout: {', '.join(invalid_ids)}."
            ),
            logic_files=logic_files,
            evidence=evidence,
        )

    if evidence.spec_ids or evidence.proposal_ids:
        cited = [*evidence.spec_ids, *evidence.proposal_ids]
        return GateResult(
            passed=True,
            message=f"Spec evidence gate passed: logic change cites {', '.join(cited)}.",
            logic_files=logic_files,
            evidence=evidence,
        )

    if evidence.no_spec_impact and evidence.rationale:
        return GateResult(
            passed=True,
            message="Spec evidence gate passed: no-impact rationale provided.",
            logic_files=logic_files,
            evidence=evidence,
        )

    if evidence.no_spec_impact:
        return GateResult(
            passed=False,
            message=(
                "Spec evidence gate failed: no-impact evidence requires a non-empty "
                "Spec-Rationale field."
            ),
            logic_files=logic_files,
            evidence=evidence,
        )

    return GateResult(
        passed=False,
        message=(
            "Spec evidence gate failed: SpecGraph logic changed without Spec-ID, "
            "Proposal-ID, or justified NO-SPEC-IMPACT evidence."
        ),
        logic_files=logic_files,
        evidence=evidence,
    )


def run_git(repo_root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout


def changed_files_from_git(repo_root: Path, base_ref: str, head_ref: str) -> list[str]:
    output = run_git(repo_root, ["diff", "--name-only", f"{base_ref}...{head_ref}"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def commit_messages_from_git(repo_root: Path, base_ref: str, head_ref: str) -> list[str]:
    output = run_git(repo_root, ["log", "--format=%B%x1e", f"{base_ref}..{head_ref}"])
    return [message.strip() for message in output.split("\x1e") if message.strip()]


def pr_body_from_event(event_path: Path | None) -> str:
    if event_path is None or not event_path.exists():
        return ""
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict):
        return ""
    body = pull_request.get("body")
    return body if isinstance(body, str) else ""


def read_texts(paths: list[Path]) -> list[str]:
    return [path.read_text(encoding="utf-8") for path in paths]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Require Spec-ID/Proposal-ID evidence for SpecGraph logic changes."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--base-ref",
        default=os.environ.get("SPEC_EVIDENCE_BASE_REF", "origin/main"),
    )
    parser.add_argument("--head-ref", default=os.environ.get("SPEC_EVIDENCE_HEAD_REF", "HEAD"))
    parser.add_argument("--event-path", type=Path, default=_default_event_path())
    parser.add_argument("--pr-body-file", type=Path, action="append", default=[])
    parser.add_argument("--commit-message-file", type=Path, action="append", default=[])
    parser.add_argument("--changed-file", action="append", default=[])
    return parser


def _default_event_path() -> Path | None:
    raw_path = os.environ.get("GITHUB_EVENT_PATH")
    return Path(raw_path) if raw_path else None


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()

    changed_files = list(args.changed_file)
    if not changed_files:
        changed_files = changed_files_from_git(repo_root, args.base_ref, args.head_ref)

    texts: list[str] = []
    event_body = pr_body_from_event(args.event_path)
    if event_body:
        texts.append(event_body)
    texts.extend(read_texts(args.pr_body_file))
    texts.extend(read_texts(args.commit_message_file))

    if not args.commit_message_file:
        try:
            texts.extend(commit_messages_from_git(repo_root, args.base_ref, args.head_ref))
        except subprocess.CalledProcessError as error:
            print(
                f"warning: could not read commit messages for {args.base_ref}..{args.head_ref}: "
                f"{error.stderr.strip()}",
                file=sys.stderr,
            )

    result = evaluate_gate(repo_root, changed_files, texts)
    print(result.message)
    if result.logic_files:
        print("Logic files:")
        for path in result.logic_files:
            print(f"  - {path}")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
