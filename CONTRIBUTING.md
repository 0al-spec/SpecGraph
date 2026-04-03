# Contributing to SpecGraph

## Python Scaffold

This repository includes a default Python project scaffold with:

- a package in `src/specgraph`
- a simple CLI entry point (`python -m specgraph`)
- a smoke test in `tests/test_smoke.py`
- packaging metadata in `pyproject.toml`

## CI

A minimal GitHub Actions workflow is available at `.github/workflows/python-ci.yml`.
It installs the package with development dependencies and runs `pytest -q`.
