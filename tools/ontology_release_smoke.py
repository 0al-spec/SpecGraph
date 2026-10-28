"""Exercise a provided ontologyc and the SpecGraph adapter without canonical writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

from ontology_imports import build_ontology_import_surfaces

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_REVISION = "d07cf5a8cd829b78027dda6d414ab89f4cb4f4e0"
PACKAGE_ROOT = ROOT / "ontology/packages/specgraph-core"


def prepare_work_dir(path: Path) -> Path:
    path = path.expanduser().absolute()
    if path.is_symlink():
        raise ValueError("work directory must not be a symlink")
    if path.exists():
        if not path.is_dir() or any(path.iterdir()):
            raise ValueError("work directory must be new or empty")
    else:
        path.mkdir(parents=True)
    return path.resolve()


def check_ontology_source(source: Path) -> str:
    source = source.expanduser().resolve(strict=True)
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "--show-toplevel", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = result.stdout.splitlines()
    if len(lines) != 2 or Path(lines[0]).resolve() != source:
        raise ValueError("ontology source must be the Git repository root")
    if lines[1] != ONTOLOGY_REVISION:
        raise ValueError(f"ontology source must be at {ONTOLOGY_REVISION}, got {lines[1]}")
    status = subprocess.run(
        ["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"],
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout:
        raise ValueError("ontology source has tracked changes")
    return lines[1]


def observe_authority(package: dict, fixture_package: dict) -> dict:
    """Report source fields without assigning approval or changing governance."""
    return {
        "package_approval_status": package.get("metadata", {}).get("approvalStatus"),
        "fixture_authority_class": fixture_package.get("authority_class"),
        "fixture_lifecycle_state": fixture_package.get("governance", {}).get("lifecycle_state"),
    }


def smoke(ontologyc: Path, ontology_source: Path, work_dir: Path) -> dict:
    source_revision = check_ontology_source(ontology_source)
    binary = ontologyc.expanduser().resolve(strict=True)
    binary_sha256 = hashlib.sha256(binary.read_bytes()).hexdigest()
    work = prepare_work_dir(work_dir)

    def run(*args: str) -> None:
        subprocess.run([str(binary), *args], cwd=work, check=True, capture_output=True, text=True)

    package_file = PACKAGE_ROOT / "domain-ontology-package.yaml"
    package = yaml.safe_load(package_file.read_text())
    fixture = yaml.safe_load((PACKAGE_ROOT / "import-fixture.yaml").read_text())
    fixture_package = fixture["package"]
    authority = observe_authority(package, fixture_package)

    run("check", str(package_file))
    run("compile", str(package_file), "--target", "typescript", "--out", "generated")
    generated_ir = work / "generated/ontology.normalized.json"
    ir = generated_ir.read_bytes()
    reference_ir = (PACKAGE_ROOT / "generated/ontology.normalized.json").read_bytes()
    if ir != reference_ir:
        raise ValueError("compiler normalized IR differs from the tracked project IR")

    # ontologyc's report stores basenames. Stage both inputs beside its report;
    # only the copied fixture's IR location changes, never the project source.
    fixture_package["materialized_ir"] = "ontology.normalized.json"
    fixture_path = work / "import-fixture.yaml"
    fixture_path.write_text(yaml.safe_dump(fixture, sort_keys=False))
    (work / "ontology.normalized.json").write_bytes(ir)
    run(
        "validate-specgraph",
        fixture_path.name,
        "--ontology-ir",
        "ontology.normalized.json",
        "--out",
        ".",
        "--source-uri",
        fixture_package["source_uri"],
        "--source-ref",
        fixture_package["source_ref"],
    )
    surfaces = build_ontology_import_surfaces(
        fixture_path,
        adapter_report_path=work / "ontologyc-adapter-report.yaml",
        semantic_policy_path=None,
    )
    adapter = surfaces["adapter_report_smoke"]
    summary = adapter["summary"]
    if (
        summary["status"] != "passed"
        or adapter["canonical_mutations_allowed"] is not False
        or adapter["tracked_artifacts_written"] is not False
    ):
        raise ValueError("adapter results or authority boundary changed")
    gaps = yaml.safe_load((work / "ontology-gaps.yaml").read_text())
    gap_refs = [gap["spec"]["missingConcept"] for gap in gaps["spec"]["gaps"]]
    if len(gap_refs) != summary["gap_count"]:
        raise ValueError("adapter gap count differs from generated gaps")

    receipt = {
        "artifact_kind": "ontology_release_compatibility_smoke",
        "schema_version": 1,
        "status": "passed",
        "ontology_source_revision": source_revision,
        "ontology_source_tracked_changes": False,
        "ontologyc_sha256": binary_sha256,
        "ontologyc_source_provenance": "not_verified",
        **authority,
        "normalized_ir_sha256": hashlib.sha256(ir).hexdigest(),
        "normalized_ir_matches_tracked": True,
        "resolved_ref_count": summary["resolved_ref_count"],
        "gap_refs": gap_refs,
        "canonical_mutations_allowed": False,
        "semantic_acceptance": "not_evaluated",
        "adapter_checks": adapter["checks"],
    }
    (work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ontologyc", required=True, type=Path)
    parser.add_argument("--ontology-source", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = smoke(args.ontologyc, args.ontology_source, args.work_dir)
    except subprocess.CalledProcessError as error:
        print(f"Ontology release smoke failed: {error}\n{error.stderr}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as error:
        print(f"Ontology release smoke failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
