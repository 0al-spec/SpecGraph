# SpecGraph

[![Coverage](https://img.shields.io/badge/coverage-pytest--cov-2ea44f)](https://pytest-cov.readthedocs.io/)
[![Ruff](https://img.shields.io/badge/lint-ruff-46aef7?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

**SpecGraph is the executable product ontology for Intent-Driven Development.**

It turns product intent into a structured, governed, and execution-ready graph that is:

- machine-verifiable
- human-readable
- semantically structured
- execution-connected

SpecGraph makes it possible to move from intent to implementation through specifications that remain understandable to humans, verifiable by machines, and traceable across the full software lifecycle.

## Python Environment

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

The Makefile runs `make check-python` before Python-backed targets and fails
fast with a clear message when the selected interpreter is too old.

## Model Layers

SpecGraph is built on four foundational layers:

- **Intent** as the source of truth
- **Specifications** as governed artifacts
- **Graph** as operational memory
- **Code** as the derived and executable layer

## Intent

In SpecGraph, intent is not a vague description.  
It is a precise, governed representation of what a product must be, how it must behave, and how its implementation can be validated.

Intent is defined by:

- completeness
- correctness
- contradiction resistance
- traceability
- bounded execution cost
- human legibility
