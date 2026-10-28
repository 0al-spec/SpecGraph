"""Reject PR event identities that differ from the live GitHub comparison."""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def verify_pull_request(payload, base, head, merge):
    if not isinstance(payload, dict) or payload.get("state") != "open":
        raise ValueError("pull request is unavailable or not open")
    actual_base = payload.get("base")
    actual_head = payload.get("head")
    if not isinstance(actual_base, dict) or not isinstance(actual_head, dict):
        raise ValueError("pull request base/head identities are unavailable")
    if (
        actual_base.get("sha") != base
        or actual_head.get("sha") != head
        or payload.get("merge_commit_sha") != merge
    ):
        raise ValueError("PR base, head or merge snapshot changed since this CI event")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--merge", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        repo = os.environ["GITHUB_REPOSITORY"]
        number = os.environ["RULE_PR_NUMBER"]
        token = os.environ["GH_TOKEN"]
        api_url = os.environ["GITHUB_API_URL"].rstrip("/")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("invalid repository identity")
        if not re.fullmatch(r"[1-9][0-9]*", number) or not token:
            raise ValueError("missing PR number or GitHub token")
        request = Request(
            f"{api_url}/repos/{repo}/pulls/{number}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
        verify_pull_request(payload, args.base, args.head, args.merge)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {"status": "matched", "base": args.base, "head": args.head, "merge": args.merge}
            )
            + "\n"
        )
    except (KeyError, OSError, URLError, ValueError) as error:
        print(f"rule reuse freshness check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
