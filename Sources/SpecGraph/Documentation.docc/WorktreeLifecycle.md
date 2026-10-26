# Worktree lifecycle

Use the `worktree-lifecycle` skill when creating, reusing, handing off or retiring
Git worktrees. Reuse an existing task environment when appropriate; retain the
task/PR, exact head, persistent data, disposition and next action in its existing
record. Active, published and archived states account for a directory's purpose
without requiring a new registry or CI gate.

Inspect staged, unstaged, untracked and ignored data, nested trees, Git
reachability and live consumers. A clean status does not cover an ignored
notebook. A squash/rebase merge needs comparison against the actual PR head;
a failed ancestor check alone does not prove lost work. Preserve recoverable
data and references before removal, verify the archive, and retire children
before parents. Use the app archive operation for managed attached worktrees.

The 27 October 2026 recovery compared the remaining candidates with current
SpecGraph. The authored traceability retry files were already retained in main;
the Ontology #548 difference was test order. Later contracts cover most old
refinements. WTR-0021 retains an unpublished Specification Verifiability
candidate for review against proposal 0226. WTR-0043 and WTR-0063 retain
unadopted alternatives with context-specific return triggers.

The existing salvage mechanism from proposal 0048 records WTR-0021 under
`worktree-recovery-20261026t2150z-sg-spec-0021` with
`review_salvaged_worktree_diff` pending. Its blocked recovery status does not
claim a new executor run or infrastructure failure. Archive closure does not
approve canonical mutation, admit evidence, or restore old runtime metadata.

The SpecDraft notebook is preserved in the primary checkout's ignored
`conversation_memory/sketches/hypercode-conversation-poc`; 50 file hashes,
16 history entries and fresh-process recovery matched. Raw notes, patches and
archives stay local. See `docs/worktree_lifecycle.md` for the bounded findings
and return points. No automatic supervisor garbage collector is added.
