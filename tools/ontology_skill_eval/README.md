# Ontology skill evaluation pilot

This exploratory pilot compares the existing `specgraph-project-ontology`
instructions with a candidate revision on the same public example. The agent is
asked to build a JSON Viewer projection; the independent grader checks the
expected foundation catalog declaration and its use by `review:Proposal`.
This checks one observable structural outcome, not the meaning of the model,
Viewer rendering, actual skill auto-discovery, or an installation workflow.

Each trial gets a fresh directory with a package, a catalog, and a copy of the
executable. Order alternates between conditions. The runner records input and
skill SHA-256 values, output, raw Codex event stream, process result, and grade
in local MLflow. Confirm that the input package, catalog, skills, and binaries
are appropriate to send to the chosen model provider before running it. The
sandbox restricts writes and network access from the agent; it does not isolate
its filesystem reads. Traces may contain prompts and tool output: use only
non-sensitive fixtures and protect the local tracking store.

Prepare a clean Python environment with `mlflow` and provide explicit paths to
the `Ontology` source snapshot, a compatible `ontologyviz`, both exact skill
versions and a new output directory. For example, obtain each skill version
from the intended Git commit and execute:

```sh
python tools/ontology_skill_eval/pilot.py \
  --ontology /path/to/Ontology --viz /path/to/ontologyviz \
  --baseline /path/to/baseline/SKILL.md --treatment /path/to/candidate/SKILL.md \
  --output /path/to/new-runs --repetitions 3 \
  --tracking-uri sqlite:////absolute/path/to/mlflow.db
```

The fixture bytes are pinned to Ontology commit `4c5027b7fe075e80d141e77f576eaa58ca0d3679`. The fixture imports `specgraph.foundation@0.1.0`; both the package and
`SPECS/ontology/foundation/0.1.0/model.json` must exist in the given snapshot.
Provenance of the compiler binary must be established separately: a hash
identifies bytes, not their origin. The output directory and MLflow database must
be local and durable; use a separate directory for each batch. A passing grade
can be fabricated by an agent and is not a trust or admission receipt. Review
traces and artifacts, and compare per-case results; three repetitions cannot
establish statistical reliability.

This first pilot does not yet cover missing, incorrect, multiple, or stale
catalogs, older executables, or GitView. A `codex` invocation failing or timing
out is recorded as such, not as a successful model evaluation.
