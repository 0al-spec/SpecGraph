# Ontology Viewer skill evaluation

This local pilot compares two versions of `specgraph-project-ontology` on the same public task. The agent generates a JSON Viewer projection for a package that imports `specgraph.foundation@0.1.0` as `sg`. Each condition gets a fresh directory with the same package, catalogs and executable. The order alternates between pairs.

The two-catalog scenario offers the published `0.1.0` and `0.2.0` foundation models in neutral directories, with their placement swapped between pairs. It records two independent outcomes.

| Metric | Evidence |
| --- | --- |
| `first_catalog_correct` | The first projection call received exactly the matching catalog. The instrumented executable records resolved catalog paths, including paths from a saved profile. Help and version probes are excluded. A missing or unreadable first record is unobserved. |
| `projection_complete` | The final JSON contains exactly the expected binding, alias, full catalog contents and byte digest, with `review:Proposal` extending `sg:DomainEntity`. A successful retry can pass this check after a wrong first choice. |

MLflow records the two metrics, input hashes, process result, traces and generated graph. `first_catalog_observed` distinguishes missing evidence from an incorrect first choice. The experiment measures projection generation when the skill instructions are included in the prompt. It uses synthetic task requests and public fixtures. The journal is writable within the trial and provides diagnostic evidence for this experiment.

## Run the two-catalog scenario

Use an isolated Python environment with `mlflow` and a dedicated, authenticated Codex home with a read-restricted profile. The recorded pilot used Codex 0.163.0, Luna 6 Medium, and MLflow 3.18.0. Retain the default project and user profiles in their existing locations.

1. Obtain a clean Ontology source snapshot at `4c5027b7fe075e80d141e77f576eaa58ca0d3679`. The runner verifies the package YAML and both `SPECS/ontology/foundation/<version>/model.json` catalogs against pinned SHA-256 values.
2. From the SpecGraph checkout, apply the two trial patches to that snapshot and build the executable in a separate build directory. Use a single binary for both conditions.

   ```sh
   eval_dir="$PWD/tools/ontology_skill_eval"
   git -C "$ONTOLOGY_SNAPSHOT" apply --unidiff-zero \
     "$eval_dir/GraphvizRenderer.swift.patch" "$eval_dir/main.swift.patch"
   swift build --package-path "$ONTOLOGY_SNAPSHOT" --scratch-path "$SWIFT_BUILD" \
     --product ontologyviz
   ```

   The scratch patch confines temporary files to the trial output. The invocation patch writes `output/.ontologyviz-invocations.jsonl` in the trial working directory. Use the same patched build for both arms, and keep the source commit and executable hash with the results.
3. Configure the dedicated Codex home's `config.toml`. This sample is for macOS. Substitute the actual home path and place the trial root outside the denied directories. Check that the profile blocks reading a file outside the trial, writing the inputs, and command network access. Check that the instrumented binary can write the output and trace inside the trial.

   ```toml
   default_permissions = "eval"
   approval_policy = "never"
   allow_login_shell = false
   web_search = "disabled"

   [analytics]
   enabled = false

   [agents]
   enabled = false

   [shell_environment_policy]
   inherit = "none"

   [shell_environment_policy.set]
   PATH = "/usr/bin:/bin"

   [permissions.eval.filesystem]
   ":minimal" = "read"
   "/path/to/host-home" = "deny"
   "/private/tmp" = "deny"
   "/private/var/folders" = "deny"

   [permissions.eval.filesystem.":workspace_roots"]
   "." = "read"
   "output" = "write"

   [permissions.eval.network]
   enabled = false
   ```
4. Export the two exact skill versions as Markdown files and run the paired evaluation. Point `TRACKING_URI` at a dedicated local SQLite store, for example `sqlite:////absolute/path/to/batch/mlflow.db`. Keep the batch and raw traces local.

   ```sh
   python "$eval_dir/pilot.py" --scenario two-catalogs \
     --ontology "$ONTOLOGY_SNAPSHOT" --viz "$VIZ" \
     --baseline "$BASELINE_SKILL" --treatment "$TREATMENT_SKILL" \
     --codex-home "$PILOT_CODEX_HOME" --output "$BATCH/runs" --repetitions 3 \
     --tracking-uri "$TRACKING_URI"
   ```

Use `--scenario single-catalog` or omit `--scenario` to run the original experiment with a compatible release binary and the original workspace-write sandbox. That mode grades the final graph using the original catalog declaration check. The first-invocation metric belongs to the instrumented two-catalog run. The original single-catalog sandbox allows external filesystem reads.

## Regrade saved artifacts without inference

```sh
python tools/ontology_skill_eval/report.py "$BATCH/runs"
```

The report validates the pinned inputs, pairs the conditions, and evaluates the saved graphs and first invocation records. For a moved batch, also supply `--recorded-root` with the original absolute `runs` path from the journal. This uses Python's standard library and the saved trial files.

### Recorded comparison

The published skill at `6cb46158` was compared with the clarification from [#930](https://github.com/0al-spec/SpecGraph/pull/930) on three pairs. With the published skill, the first choice was correct in 2 of 3 runs. With the clarification, it was correct in 3 of 3. Final projection completeness was 3 of 3 in both arms. All six final graphs matched the official Ontology 0.12.0 control by SHA-256. These counts cover one public fixture.
