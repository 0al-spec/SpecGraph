#!/usr/bin/env python3
"""Run an exploratory paired ontology projection pilot; no semantic grading."""

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import time

import mlflow
from grade import first_catalog_correct, grade
from scenario import (
    CATALOG,
    DISTRACTOR,
    FIXTURE,
    GRAPH,
    INPUT_SHA256,
    TRACE,
    digest,
    inputs_match,
    trial_inputs,
)


def main():
    P = argparse.ArgumentParser()
    P.add_argument("--ontology", type=pathlib.Path, required=True)
    P.add_argument("--viz", type=pathlib.Path, required=True)
    P.add_argument("--baseline", type=pathlib.Path, required=True)
    P.add_argument("--treatment", type=pathlib.Path, required=True)
    P.add_argument("--output", type=pathlib.Path, required=True)
    P.add_argument("--repetitions", type=int, default=3)
    P.add_argument("--tracking-uri", required=True)
    P.add_argument(
        "--scenario", choices=("single-catalog", "two-catalogs"), default="single-catalog"
    )
    P.add_argument(
        "--codex-home", type=pathlib.Path, help="Dedicated Codex home for two-catalog runs"
    )
    args = P.parse_args()
    if args.repetitions < 1:
        P.error("--repetitions must be positive")
    two_catalogs = args.scenario == "two-catalogs"
    environment = None
    sandbox_args = ["--ignore-user-config", "--sandbox", "workspace-write"]
    if two_catalogs:
        if args.codex_home is None or not (args.codex_home / "config.toml").is_file():
            P.error("--scenario two-catalogs requires --codex-home with a dedicated config.toml")
        environment = {
            "PATH": os.environ.get("PATH", os.defpath),
            "CODEX_HOME": str(args.codex_home.resolve()),
        }
        sandbox_args = ["--ignore-rules"]

    frozen = trial_inputs(1, two_catalogs)
    for source in frozen:
        path = args.ontology / source
        if not path.is_file() or digest(path) != INPUT_SHA256[source]:
            P.error(f"Unexpected bytes for {path}. Use the pinned Ontology snapshot.")
    catalog = args.ontology / CATALOG

    args.output.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(args.tracking_uri)
    experiment_name = (
        "ontology-viewer-skill-two-catalogs" if two_catalogs else "ontology-viewer-skill-pilot"
    )
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment is None:
        experiment_id = mlflow.create_experiment(
            experiment_name,
            artifact_location=(args.output.parent / "artifacts").resolve().as_uri(),
        )
    else:
        experiment_id = experiment.experiment_id
    mlflow.set_experiment(experiment_id=experiment_id)
    for n in range(args.repetitions):
        paths = trial_inputs(n + 1, two_catalogs)
        for condition, skill in (
            [("baseline", args.baseline), ("treatment", args.treatment)]
            if n % 2 == 0
            else [("treatment", args.treatment), ("baseline", args.baseline)]
        ):
            run_dir = args.output / f"{n + 1}-{condition}"
            run_dir.mkdir()
            if two_catalogs:
                (run_dir / GRAPH.parent).mkdir()
            for source, relative in paths.items():
                target = run_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(args.ontology / source, target)
            shutil.copy2(args.viz, run_dir / "ontologyviz")
            task = (
                "Create a JSON ontology viewer projection for package.yaml. "
                "The local ontologyviz executable and catalogs directory are available. "
                "Place the result at output/ontology.graph.json and explain missing definitions. "
                "Do not modify input files.\n\n"
                "The project ontology skill instructions are:\n" + skill.read_text()
            )
            cmd = [
                "codex",
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                *sandbox_args,
                "--json",
                "-m",
                "gpt-6-luna",
                "-c",
                'model_reasoning_effort="medium"',
                task,
            ]
            start = time.monotonic()
            with mlflow.start_run(run_name=f"{condition}-{n + 1}"):
                mlflow.log_params(
                    {
                        "condition": condition,
                        "repeat": n + 1,
                        "model": "gpt-6-luna",
                        "reasoning": "medium",
                        "skill_sha256": digest(skill),
                        "scenario": args.scenario,
                        "package_sha256": INPUT_SHA256[FIXTURE],
                        "catalog_sha256": INPUT_SHA256[CATALOG],
                        "viz_sha256": digest(args.viz),
                    }
                )
                if two_catalogs:
                    mlflow.log_params(
                        {
                            "other_catalog_sha256": INPUT_SHA256[DISTRACTOR],
                            "matching_catalog_path": paths[CATALOG].as_posix(),
                            "other_catalog_path": paths[DISTRACTOR].as_posix(),
                            "sandbox_profile_sha256": digest(args.codex_home / "config.toml"),
                        }
                    )
                try:
                    process = subprocess.run(
                        cmd,
                        cwd=run_dir,
                        stdin=subprocess.DEVNULL,
                        capture_output=True,
                        env=environment,
                        timeout=360,
                    )
                    exit_code = process.returncode
                    stdout, stderr = process.stdout, process.stderr
                except subprocess.TimeoutExpired as exc:
                    exit_code = 124
                    stdout, stderr = exc.stdout or b"", exc.stderr or b""
                (run_dir / "events.jsonl").write_bytes(stdout)
                (run_dir / "stderr.log").write_bytes(stderr)
                graph = run_dir / GRAPH
                good = grade(graph, catalog, exact_binding=two_catalogs)
                inputs_intact = inputs_match(run_dir, paths)
                result = {
                    "run": n + 1,
                    "condition": condition,
                    "complete": good,
                    "inputs_intact": inputs_intact,
                    "exit": exit_code,
                }
                metrics = {
                    "projection_complete": int(good),
                    "inputs_intact": int(inputs_intact),
                    "exit_code": exit_code,
                    "elapsed_seconds": time.monotonic() - start,
                }
                if two_catalogs:
                    trace = run_dir / TRACE
                    first = first_catalog_correct(trace, (run_dir / paths[CATALOG]).resolve())
                    result["first_catalog_correct"] = first
                    metrics["first_catalog_observed"] = int(first is not None)
                    if first is not None:
                        metrics["first_catalog_correct"] = int(first)
                    if trace.is_file():
                        mlflow.log_artifact(str(trace))
                for line in stdout.splitlines():
                    try:
                        event = json.loads(line)
                        if event.get("type") == "turn.completed":
                            for key, value in event.get("usage", {}).items():
                                if isinstance(value, (float, int)):
                                    metrics["tokens_" + key] = value
                    except (ValueError, AttributeError):
                        continue
                mlflow.log_metrics(metrics)
                mlflow.log_artifact(str(run_dir / "events.jsonl"))
                mlflow.log_artifact(str(run_dir / "stderr.log"))
                if graph.is_file():
                    mlflow.log_artifact(str(graph))
                print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
