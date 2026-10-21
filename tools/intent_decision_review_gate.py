#!/usr/bin/env python3
"""Require a source-bound decision disposition for each changed intent atom."""

import argparse
import subprocess
import sys
from pathlib import Path

from intent_decision_review.report import collect, draft
from intent_decision_review.sources import encoded, strict_json


def event_context(path: Path) -> tuple[str, str, dict]:
    payload = strict_json(path.read_bytes())
    pr = payload["pull_request"]
    base, head = pr["base"]["sha"], pr["head"]["sha"]
    if not all(isinstance(v, str) and len(v) in (40, 64) for v in (base, head)):
        raise ValueError("GitHub event revisions are missing or invalid")
    context = {k: pr.get(k) for k in ("number", "title", "body", "html_url")}
    if context["body"] is None:
        context["body"] = ""  # GitHub represents an absent description as null.
    return base, head, context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--base-ref")
    parser.add_argument("--head-ref", default="HEAD")
    parser.add_argument("--event-path", type=Path)
    parser.add_argument("--pr-body-file", type=Path)
    parser.add_argument("--review-path")
    parser.add_argument(
        "--draft", action="store_true", help="Print an unresolved draft; never approves it"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        base, head, context = args.base_ref, args.head_ref, {}
        if args.event_path:
            if args.base_ref or args.pr_body_file or args.review_path or args.draft:
                raise ValueError(
                    "event mode cannot override its revisions, body or review selection"
                )
            base, head, context = event_context(args.event_path)
        if not base:
            raise ValueError("--base-ref or --event-path is required")
        if args.pr_body_file:
            context["body"] = args.pr_body_file.read_text(encoding="utf-8")
        if args.draft:
            if not args.review_path:
                raise ValueError("draft requires --review-path")
            result = draft(args.repo_root, base, head, args.review_path, pr_context=context)
            code = 0
        else:
            result = collect(
                args.repo_root, base, head, pr_context=context, review_path=args.review_path
            )
            code = 0 if result["gate_passed"] else 2 if result["status"] == "invalid" else 1
    except (
        ValueError,
        KeyError,
        TypeError,
        OSError,
        SyntaxError,
        subprocess.CalledProcessError,
    ) as error:
        result = dict(
            status="invalid",
            gate_passed=False,
            diagnostics=[type(error).__name__],
            semantic_approval=False,
            hosted_requests=0,
        )
        code = 2
    text = encoded(result) + "\n"
    if args.output:
        if (
            not args.draft
            and result.get("review_path")
            and args.output.resolve() == (args.repo_root / result["review_path"]).resolve()
        ):
            parser.error("report output must not overwrite its review input")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return code


if __name__ == "__main__":
    sys.exit(main())
