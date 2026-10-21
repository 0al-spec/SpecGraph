"""Join a versioned intent delta to explicit, source-bound review dispositions."""

import hashlib
import re
from pathlib import Path

from intent_atoms import build_snapshot, diff_snapshots

from . import CONTRACT, decide
from .context import DecisionReviewFacts, RecordEvidenceFacts
from .record_rules import inspect_evidence
from .sources import GitSources, digest, encoded, normalized_path, revision, strict_json

REVIEW_PREFIX = "tools/intent_decision_reviews/"
DISPOSITIONS = {
    "new_specification",
    "reuse_specification",
    "mechanics",
    "needs_review",
    "contract_only",
    "retired",
}


MAX_REFS_PER_LIST = 16
MAX_REFS_TOTAL = 256
DECISION_DELTA_PROFILE = "intent-decision-obligations-v1"


def changes_from(diff: dict, before: dict, after: dict) -> list[dict]:
    # The historical counter compares explicit statements only. Decision coverage
    # also observes declared attributes, without changing that published metric.
    def explicit(snapshot):
        return {
            (atom["node_id"], atom["atom_id"]): atom
            for atom in snapshot["atoms"]
            if atom.get("origin") == "explicit_intent" and atom.get("atom_id")
        }

    def obligation(atom):
        return {
            k: v
            for k, v in atom.items()
            if k not in {"source_path", "source_field", "element_index"}
        }

    old, new = explicit(before), explicit(after)
    modified = [
        dict(node_id=key[0], atom_id=key[1], before=old[key], after=new[key])
        for key in sorted(old.keys() & new.keys())
        if obligation(old[key]) != obligation(new[key])
    ]
    return [
        dict(kind=kind, change_sha256=digest(dict(kind=kind, atom=atom)), atom=atom)
        for kind, field in (("added", "added"), ("removed", "removed"), ("modified", "modified"))
        for atom in (modified if kind == "modified" else diff[field])
    ]


def review_path_from(body: str) -> str | None:
    paths = re.findall(r"(?m)^Intent-Decision-Review:[ \t]*(\S+)[ \t]*$", body)
    if len(paths) > 1:
        raise ValueError("only one Intent-Decision-Review field is allowed")
    return paths[0] if paths else None


def validate_review_path(value: str) -> str:
    path = normalized_path(value)
    if not path.startswith(REVIEW_PREFIX) or not path.endswith(".json"):
        raise ValueError("review record must be JSON under tools/intent_decision_reviews/")
    return path


def inspect_records(sources: GitSources, review: dict, changes: list[dict]) -> tuple[list, list]:
    records = review["decisions"]
    if not isinstance(records, list):
        raise ValueError("decisions must be a list")
    wanted = {c["change_sha256"]: c for c in changes}
    seen, inspected = set(), []
    # Preflight every list before any Git/AST reference lookup, including when a
    # late record is oversized. Bounds apply to submitted entries, not uniques.
    total = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("decision must be an object")
        for name in ("implementation_refs", "specification_refs"):
            refs = record.get(name)
            if not isinstance(refs, list) or len(refs) > MAX_REFS_PER_LIST:
                raise ValueError("reference list exceeds v1 bounds or is not a list")
            total += len(refs)
            if total > MAX_REFS_TOTAL:
                raise ValueError("review exceeds total reference bound")
            if len({encoded(ref) for ref in refs}) != len(refs):
                raise ValueError("duplicate declaration reference")
    production_changed = sources.production_changed()
    for record in records:
        if not isinstance(record, dict) or set(record) != {
            "change_sha256",
            "disposition",
            "rationale",
            "implementation_refs",
            "specification_refs",
        }:
            raise ValueError("decision fields differ from the v1 contract")
        key = record["change_sha256"]
        if not isinstance(key, str) or key not in wanted or key in seen:
            raise ValueError("unknown or duplicate intent change reference")
        seen.add(key)
        disposition = record["disposition"]
        if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
            raise ValueError("unknown decision disposition")
        if not isinstance(record["rationale"], str) or not record["rationale"].strip():
            raise ValueError("every disposition requires a rationale")
        if any(
            not isinstance(record[name], list)
            for name in ("implementation_refs", "specification_refs")
        ):
            raise ValueError("references must be lists")
        implementations = [sources.declaration(ref) for ref in record["implementation_refs"]]
        specifications = [sources.declaration(ref) for ref in record["specification_refs"]]
        origins = []
        for reference, observed in zip(record["specification_refs"], specifications, strict=True):
            try:
                old = sources.declaration(reference, ref=sources.base)
            except ValueError:
                old = None
            origins.append(
                (
                    observed["recognized_specification"],
                    old is not None and old["recognized_specification"],
                )
            )
        failed, record_trace = inspect_evidence(
            RecordEvidenceFacts(
                disposition,
                wanted[key]["kind"],
                len(implementations),
                tuple(origins),
                production_changed,
            )
        )
        if failed:
            raise ValueError("record evidence obligations failed: " + ", ".join(failed))
        inspected.append(
            dict(
                record,
                implementation_evidence=implementations,
                specification_evidence=specifications,
                record_trace=record_trace,
            )
        )
    return inspected, sorted(set(wanted) - seen)


def collect(
    root: Path,
    base_ref: str,
    head_ref: str,
    *,
    pr_context: dict | None = None,
    review_path: str | None = None,
) -> dict:
    base, head = revision(root, base_ref), revision(root, head_ref)
    context = dict(pr_context or {})
    body = context.get("body", "")
    if not isinstance(body, str):
        raise ValueError("PR description must be text")
    before = build_snapshot(repo=str(root), revision=base)
    after = build_snapshot(repo=str(root), revision=head)
    diff = diff_snapshots(before, after)
    changes = changes_from(diff, before, after)
    delta_sha = digest(
        dict(
            profile=diff["profile"],
            analyzer_sha256=diff["analyzer_sha256"],
            decision_delta_profile=DECISION_DELTA_PROFILE,
            changes=changes,
        )
    )
    sources = GitSources(root, base, head)
    errors, inspected, missing = [], [], []
    ledger_sha, scope, path = None, {}, None
    if diff["completeness"] != "complete":
        errors.append("intent_delta_incomplete")
    elif changes:
        try:
            path = review_path or review_path_from(body)
            if path:
                path = validate_review_path(path)
                scope = sources.scope(path)
                raw = sources.blob(head, path)
                ledger_sha = hashlib.sha256(raw).hexdigest()
                review = strict_json(raw)
                if not isinstance(review, dict) or set(review) != {
                    "artifact_kind",
                    "schema_version",
                    "base_sha",
                    "intent_delta_sha256",
                    "source_scope_sha256",
                    "pr_body_sha256",
                    "decisions",
                }:
                    raise ValueError("review fields differ from the v1 contract")
                if (
                    review["artifact_kind"] != CONTRACT
                    or type(review["schema_version"]) is not int
                    or review["schema_version"] != 1
                    or review["base_sha"] != base
                    or review["intent_delta_sha256"] != delta_sha
                    or review["pr_body_sha256"] != hashlib.sha256(body.encode()).hexdigest()
                    or review["source_scope_sha256"] != digest(scope)
                ):
                    raise ValueError("review snapshot binding is stale or incompatible")
                inspected, missing = inspect_records(sources, review, changes)
            else:
                missing = [c["change_sha256"] for c in changes]
        except (ValueError, SyntaxError, UnicodeError) as error:
            errors.append(str(error))
    facts = DecisionReviewFacts(
        len(changes),
        invalid=bool(errors),
        unresolved=bool(missing or any(row["disposition"] == "needs_review" for row in inspected)),
    )
    status, trace = decide(facts)
    return dict(
        artifact_kind=CONTRACT,
        schema_version=1,
        status=status,
        gate_passed=status in {"covered", "not_required"},
        base_sha=base,
        head_sha=head,
        intent_delta_sha256=delta_sha,
        decision_delta_profile=DECISION_DELTA_PROFILE,
        source_scope_sha256=digest(scope),
        source_scope=scope,
        review_path=path,
        review_blob_sha256=ledger_sha,
        changed_atoms=len(changes),
        changes=changes,
        decisions=inspected,
        missing_changes=missing,
        diagnostics=errors,
        trace=trace,
        intent_completeness=diff["completeness"],
        intent_diagnostics=diff["diagnostics"],
        intent_summary=diff["summary"],
        reviewer_context=dict(
            pull_request=context,
            description_authority="author_context_not_approval",
            architecture_goal=(
                "Uniform named, composable and observable domain decisions; "
                "reuse existing Specifications."
            ),
            instruction=(
                "Review intent/proposal/spec context before deciding policy versus mechanics."
            ),
            code_scope=(
                "Python declaration references are structural witnesses, "
                "not proof of semantic equivalence."
            ),
        ),
        semantic_approval=False,
        human_approval_attested=False,
        metric_effect="none",
        hosted_requests=0,
    )


def draft(
    root: Path, base_ref: str, head_ref: str, review_path: str, *, pr_context: dict | None = None
) -> dict:
    path = validate_review_path(review_path)
    report = collect(root, base_ref, head_ref, pr_context=pr_context)
    if report["intent_completeness"] != "complete":
        raise ValueError("cannot draft an incomplete intent delta")
    sources = GitSources(root, report["base_sha"], report["head_sha"])
    return dict(
        artifact_kind=CONTRACT,
        schema_version=1,
        base_sha=report["base_sha"],
        intent_delta_sha256=report["intent_delta_sha256"],
        source_scope_sha256=digest(sources.scope(path)),
        pr_body_sha256=hashlib.sha256((pr_context or {}).get("body", "").encode()).hexdigest(),
        decisions=[
            dict(
                change_sha256=c["change_sha256"],
                disposition="needs_review",
                rationale="Pending source and intent review.",
                implementation_refs=[],
                specification_refs=[],
            )
            for c in report["changes"]
        ],
    )
