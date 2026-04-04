# TODO

1. Implement worktree cleanup to prevent `.worktrees/*` accumulation over time.
2. Add branch/worktree freshness validation in gate resolution (do not blindly trust `last_worktree_path`).
3. Add a command to list and clean stale gate states and stale worktrees.
4. Upgrade `search_kg_json.py` from plain keyword matching to structured requirement extraction.
5. Add integration tests that exercise real `git worktree` commands (beyond monkeypatched fake worktrees).
