# Native SpecGraph runtime

Proposal 0231 describes a pinned source snapshot for an agent running SpecGraph
from independent product workspaces. The installer ships tracked tools and
policy resources without the engine Git history; it creates a separate Python
environment and a launcher. Python 3.10+, Git and access to dependencies are
prerequisites. The local source commit is recorded in `runtime.json`.

`tools/native_runtime.py install` takes an explicit Git source, full revision
and new destination. It never overwrites an existing destination. Failure leaves
an incomplete installation without the `runtime.json` ready marker.
Before creating the destination it checks the interpreter version and reports
the selected executable and version; Python older than 3.10 is rejected without
creating the installation directory.
To bootstrap without a developer checkout, download that script from the same
trusted full commit on `raw.githubusercontent.com` before invoking it; the
repository README gives the command. The chosen revision must contain the script.
Local Git source paths are resolved against the caller's directory before Git
enters its temporary repository; Git URL and SSH remote syntax stays unchanged.
The installed-runtime smoke uses a relative source to preserve this behavior.

The launcher accepts `--workspace` and `init`, `next-move`, `supervisor` or
`draft`. `init` runs the existing initializer from the installed source root;
other operations run in the selected product workspace. Project-owned Git,
notes, specs and runs are not installed data. Each workspace must be explicitly
selected, and an existing workspace or Git history is not overwritten by setup.

Install the version-matched ontology skill into the product project explicitly:

```sh
<new-runtime-directory>/specgraph-runtime --workspace /absolute/knowledge/workspace \
  draft -- skill install --name specgraph-project-ontology \
  --project /absolute/product/project
```

The outer workspace selects the knowledge workspace used by the launcher;
`--project` selects the product project where the skill is installed under
`.codex/skills/`. They may be different directories. The skill can guide
terminology work even when the workspace has no ontology package or `ontologyc`.
Installing it does not accept ontology terms, publish changes, or change agent
settings. Existing differing skill content is not overwritten. The original
conversation-notes installation with `--destination` remains available.

Current supervisor refinement requires its configured Codex executor. ASP is
future work, and the invoking agent is not automatically the child executor.
The initializer does not create `specs/nodes`. After Supervisor execution it
accepts an existing `.worktrees` directory, preserving its contents, and rejects
a file or symlink at that path.
Unix platforms are the target; relocation, offline installation, Docker and a
full cross-repository evidence binding are not claimed by this slice.

Focused tests cover snapshot safety and installer refusal. An installed-runtime
probe exercises a real snapshot and separate project roots; no canonical
acceptance or live provider inference follows from that observation.
