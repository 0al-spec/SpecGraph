"""Regrade a saved two-catalog batch using only its local artifacts."""

import argparse
import json
import re
from pathlib import Path

from grade import first_catalog_correct, grade
from scenario import CATALOG, GRAPH, TRACE, inputs_match, trial_inputs

TRIAL = re.compile(r"([1-9][0-9]*)-(baseline|treatment)")


def report(runs: Path, recorded_root: Path) -> dict:
    trials = []
    for directory in sorted(runs.iterdir()):
        match = TRIAL.fullmatch(directory.name)
        if match is None or not directory.is_dir():
            continue
        number, condition = match.groups()
        repeat = int(number)
        paths = trial_inputs(repeat, two_catalogs=True)
        if not inputs_match(directory, paths):
            raise ValueError(f"{directory.name}: trial inputs differ from the fixture")
        catalog = paths[CATALOG]
        trials.append(
            {
                "repeat": repeat,
                "condition": condition,
                "projection_complete": grade(
                    directory / GRAPH, directory / catalog, exact_binding=True
                ),
                "first_catalog_correct": first_catalog_correct(
                    directory / TRACE, recorded_root / directory.name / catalog
                ),
            }
        )
    trials.sort(key=lambda row: (row["repeat"], row["condition"]))
    groups = {
        condition: [row for row in trials if row["condition"] == condition]
        for condition in ("baseline", "treatment")
    }
    if not trials or [row["repeat"] for row in groups["baseline"]] != [
        row["repeat"] for row in groups["treatment"]
    ]:
        raise ValueError("Expected a saved batch with both conditions for every repeat")

    return {
        "counts": {
            condition: {
                "trials": len(rows),
                "projection_complete": sum(row["projection_complete"] for row in rows),
                "first_catalog_observed": sum(
                    row["first_catalog_correct"] is not None for row in rows
                ),
                "first_catalog_correct": sum(row["first_catalog_correct"] is True for row in rows),
            }
            for condition, rows in groups.items()
        },
        "trials": trials,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, help="Saved two-catalog trial directory")
    parser.add_argument(
        "--recorded-root", type=Path, help="Original runs path if the batch was moved"
    )
    args = parser.parse_args()
    if args.recorded_root is not None and not args.recorded_root.is_absolute():
        parser.error("--recorded-root must be an absolute path")
    try:
        result = report(args.runs, args.recorded_root or args.runs.resolve())
    except (OSError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
