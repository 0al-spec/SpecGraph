---
name: specgraph-criterion-evidence
description: Look up saved verification evidence for a SpecGraph acceptance criterion. Use when someone asks what supports a criterion, which runs observed it, or whether the retained observation can be rechecked.
---

# Inspect evidence for one criterion

Select the product Git workspace, specification ID, full declaration commit,
and the criterion's `/acceptance/N` pointer. Read the criterion at that commit
to confirm its wording and zero-based position. The commit identifies the
specification declaration, which can differ from the test or execution commit.

Use the project's established directory of retained workflow 0234 runs. It
contains run directories with `terminal.json`. If no directory is known,
report the missing input. Use the project's installed native launcher. Check
`criterion-evidence -- --help` through that launcher if its support is unclear.

```sh
"$SPECGRAPH_RUNTIME" --workspace "$PRODUCT_WORKSPACE" criterion-evidence -- "$SPEC_ID" \
  --revision "$DECLARATION_COMMIT" --criterion "$CRITERION_POINTER" \
  --runs-root "$VERIFICATION_RUNS_ROOT"
```

Supply `--repository-id` if the producer uses a repository identity different
from the workspace's project ID. This lookup reads workflow terminal records.
A standalone archived C2c report is outside its search scope.

Read the JSON even when exit status is zero. `found` means one or more matching
records exist. Show all matching runs and their distinct outcomes unless the
user selects a run. `not_found` applies to this revision and directory.
`incomplete` means unreadable or invalid run entries prevented a definitive
empty answer. Check `findings` and each run's artifacts for details.

For each run, report three separate facts:

- The saved outcome in `recorded_observation` and its run ID. A null observation
  gives no measured result. If a run failed before collection, give its recorded
  workflow outcome.
- The current `recheck_inputs` status. `available` means the selected artifact
  bytes match their pins. If a file is missing or altered, name its role and path
  and retain any readable historical observation as such.
- The recorded evidence scope and `admission`. Describe `local_test` and
  `not_evaluated` as local recorded evidence without an admission decision.

Cite the criterion address, declaration revision, and relevant run or report.
Explain the observed behavior in the user's terms. A fresh test run or an
admission decision uses a separate workflow.
