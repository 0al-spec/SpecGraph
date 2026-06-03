# Getting Started

Use SpecGraph to keep specification work tied to explicit artifacts and runtime
evidence.

## Operator Surface

The repository keeps the following surfaces separate:

- `docs/` contains source documentation, proposal records, and operator notes.
- `tools/` contains Python tooling for derived surfaces and validation gates.
- `runs/` contains local runtime artifacts and is not published directly.
- GitHub Pages publishes the technical entrypoint and DocC documentation.
- The specgraph.tech static host publishes product-facing landing content and
  generated public artifacts.

## Routine Validation

SpecGraph tooling requires Python 3.10 or newer. CI currently runs Python 3.10,
and `pyproject.toml` declares `requires-python = ">=3.10"`.

On macOS, `python3` may still point to the Xcode/system Python 3.9 runtime. In
that case, pass `PYTHON` explicitly or create a local virtual environment:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'

make test PYTHON="$PWD/.venv/bin/python"
make test-supervisor PYTHON="$PWD/.venv/bin/python"
```

Common local checks are exposed through Make targets:

```bash
make check-python
make publish-bundle
make proposal-tracking-gate
make test
```

The Makefile runs `make check-python` before Python-backed targets and fails
fast with a clear message when the selected interpreter is too old.

Use narrower tests when changing a focused workflow or documentation surface.
