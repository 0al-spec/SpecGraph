# Native SpecGraph runtime

## Status and source

Synchronous runtime slice for review. The [source](../archive/proposal_sources/0231_native_specgraph_runtime.md), [attributed note](../reviews/0231_native_runtime/source-notes.json), [intake](../reviews/0231_native_runtime/intake.json) and [draft obligations](0231_native_specgraph_runtime.intent.yaml) precede canonical acceptance.

See the [installed-runtime observation](../reviews/0231_native_runtime/verification.json)
and [pipeline observation](../reviews/0231_native_runtime/pipeline.json).

An agent needs a stable installed snapshot while the SpecGraph developer
checkout evolves independently. The existing Product Workspace model remains
the project boundary; source snapshots and Python environments are versioned
separately from project-owned graphs, runs and Git history.

## Bounded contract

`tools/native_runtime.py install --source <git-repository> --revision <full-sha>
--destination <new-directory>` fetches that exact commit into temporary bare Git,
archives tracked files without history, creates a separate Python environment,
installs dependencies, and produces a launcher and a completed receipt. It fails
if the destination exists, preserves incomplete installations on error, and
never adds projects or their data to the installed runtime. Python >=3.10, Git,
network access to dependencies and Unix venv layout are prerequisites.
The bootstrap script can be downloaded from the same chosen Git commit; the
consumer does not need an existing developer checkout.

The installed `specgraph-runtime --workspace <workspace> init -- --project-id <id>`
invokes the existing product initializer from the installed engine root.
`next-move`, `supervisor` and `draft` forward arguments with the selected
workspace as current directory. This retains existing CLI output and authority
semantics. Existing source facades remain available. A workspace with existing
Git history keeps it; the installer does not create or overwrite project Git.

The installed snapshot contains tracked source files, not `.git`, uncommitted
changes, credentials, existing worktrees, local notes or generated artifacts.
The launcher is colocated with its Python environment and is not relocatable;
reinstall at a new path. One installation can serve separate workspace roots.
Current supervisor refinement launches a configured `codex exec` child; ASP is
a future integration. An agent invoking the launcher is not itself the child
executor. No package-index release, native Windows support, offline installation,
automatic upgrades, broad integration bundle or Docker image is claimed.

## Verification and limits

Focused tests verify conflict preservation, unsafe archive rejection, full SHA
and incomplete installation rejection. A real isolated install and product
workspace probe must bind to the installed commit and report exactly what ran.
The existing initializer does not create `specs/nodes`, and after supervisor
creates `.worktrees` a repeated initializer may report it as unexpected; these
pre-existing limitations are not silently altered by this distribution slice.
Real provider calls, canonical publication, cross-repository code trace and
hosted evidence admission are outside the technical smoke's claims.
The actual repeat-init probe failed on `.worktrees` after the synthetic
refinement, as expected from proposal 0227; this is an open usability defect.

## Pipeline

Captured user intent → proposal lane → draft obligations → implementation →
tests/observations. SG-SPEC-0007 constrains the attribution boundary; references
are governance context, not a canonical Requirement binding. The named
`RUNTIME_READY_SPEC` checks that a versioned installation receipt identifies a
complete snapshot. CLI forwarding, archive copying and environment creation are
I/O mechanics and do not expand supervisor authority.
