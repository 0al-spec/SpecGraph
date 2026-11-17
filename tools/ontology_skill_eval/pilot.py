#!/usr/bin/env python3
"""Run an exploratory paired ontology projection pilot; no semantic grading."""

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import time

import mlflow
from grade import grade


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    P = argparse.ArgumentParser()
    P.add_argument("--ontology", type=pathlib.Path, required=True)
    P.add_argument("--viz", type=pathlib.Path, required=True)
    P.add_argument("--baseline", type=pathlib.Path, required=True)
    P.add_argument("--treatment", type=pathlib.Path, required=True)
    P.add_argument("--output", type=pathlib.Path, required=True)
    P.add_argument("--repetitions", type=int, default=3)
    P.add_argument("--tracking-uri", required=True)
    args = P.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(args.tracking_uri)
    experiment = mlflow.get_experiment_by_name("ontology-viewer-skill-pilot")
    if experiment is None:
        experiment_id = mlflow.create_experiment(
            "ontology-viewer-skill-pilot",
            artifact_location=(args.output.parent / "artifacts").resolve().as_uri(),
        )
    else:
        experiment_id = experiment.experiment_id
    mlflow.set_experiment(experiment_id=experiment_id)
    fixture = args.ontology / "Examples/package-visualization/domain-ontology-package.yaml"
    catalog = args.ontology / "SPECS/ontology/foundation/0.1.0/model.json"
    if digest(fixture) != "7b87c27205c1079b983456f710eb413672724a242a28fdc0ce48ccdd0e75a009":
        raise SystemExit("Unexpected fixture bytes; use the pinned Ontology snapshot")
    if digest(catalog) != "7999a4ce110535c8093f177493532420a04ab7db9ff86492db802580531d7e48":
        raise SystemExit("Unexpected foundation catalog bytes")
    for n in range(args.repetitions):
        for condition, skill in (
            [("baseline", args.baseline), ("treatment", args.treatment)]
            if n % 2 == 0
            else [("treatment", args.treatment), ("baseline", args.baseline)]
        ):
            run_dir = args.output / f"{n + 1}-{condition}"
            run_dir.mkdir(exist_ok=False)
            shutil.copy2(fixture, run_dir / "package.yaml")
            (run_dir / "catalogs").mkdir()
            shutil.copy2(catalog, run_dir / "catalogs/model.json")
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
                "--ignore-user-config",
                "--skip-git-repo-check",
                "--sandbox",
                "workspace-write",
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
                        "package_sha256": digest(fixture),
                        "catalog_sha256": digest(catalog),
                        "viz_sha256": digest(args.viz),
                    }
                )
                try:
                    process = subprocess.run(
                        cmd,
                        cwd=run_dir,
                        stdin=subprocess.DEVNULL,
                        capture_output=True,
                        timeout=360,
                    )
                    exit_code = process.returncode
                    stdout, stderr = process.stdout, process.stderr
                except subprocess.TimeoutExpired as exc:
                    exit_code = 124
                    stdout, stderr = exc.stdout or b"", exc.stderr or b""
                (run_dir / "events.jsonl").write_bytes(stdout)
                (run_dir / "stderr.log").write_bytes(stderr)
                good = grade(run_dir / "output/ontology.graph.json", catalog)
                inputs_intact = digest(run_dir / "package.yaml") == digest(fixture) and digest(
                    run_dir / "catalogs/model.json"
                ) == digest(catalog)
                metrics = {
                    "projection_complete": int(good),
                    "inputs_intact": int(inputs_intact),
                    "exit_code": exit_code,
                    "elapsed_seconds": time.monotonic() - start,
                }
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
                graph = run_dir / "output/ontology.graph.json"
                if graph.is_file():
                    mlflow.log_artifact(str(graph))
                print(
                    json.dumps(
                        {
                            "run": n + 1,
                            "condition": condition,
                            "complete": good,
                            "inputs_intact": inputs_intact,
                            "exit": exit_code,
                        }
                    ),
                    flush=True,
                )


if __name__ == "__main__":
    main()
