"""Check a stable SpecGraph Git tag against the product version in this checkout."""

import argparse
import re
from pathlib import Path
from runpy import run_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    tag = parser.parse_args().tag
    source = Path(__file__).resolve().parents[1] / "src/specgraph/__init__.py"
    version = run_path(str(source))["__version__"]
    component = r"(?:0|[1-9][0-9]*)"
    if not re.fullmatch(rf"{component}\.{component}\.{component}", version):
        parser.error(f"product version {version!r} is not a stable SemVer")
    if tag != f"v{version}":
        parser.error(f"expected tag v{version} for this checkout, got {tag!r}")
    print(f"SpecGraph {version}: release tag {tag} matches")


if __name__ == "__main__":
    main()
