"""Pinned public inputs and catalog placement for the projection pilot."""

import hashlib
from pathlib import Path

FIXTURE = Path("Examples/package-visualization/domain-ontology-package.yaml")
FOUNDATION = Path("SPECS/ontology/foundation")
CATALOG = FOUNDATION / "0.1.0/model.json"
DISTRACTOR = FOUNDATION / "0.2.0/model.json"
INPUT_SHA256 = {
    FIXTURE: "7b87c27205c1079b983456f710eb413672724a242a28fdc0ce48ccdd0e75a009",
    CATALOG: "7999a4ce110535c8093f177493532420a04ab7db9ff86492db802580531d7e48",
    DISTRACTOR: "2f43dbd772c8356de107e3ea48cd548405023edb6a641702ddbec52c4942033b",
}
TRACE = Path("output/.ontologyviz-invocations.jsonl")
GRAPH = Path("output/ontology.graph.json")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trial_inputs(repeat: int, two_catalogs: bool) -> dict[Path, Path]:
    paths = {FIXTURE: Path("package.yaml"), CATALOG: Path("catalogs/model.json")}
    if two_catalogs:
        matching, other = ("b", "a") if repeat % 2 else ("a", "b")
        paths[CATALOG] = Path("catalogs") / matching / "model.json"
        paths[DISTRACTOR] = Path("catalogs") / other / "model.json"
    return paths


def inputs_match(root: Path, paths: dict[Path, Path]) -> bool:
    try:
        return all(digest(root / path) == INPUT_SHA256[source] for source, path in paths.items())
    except OSError:
        return False
