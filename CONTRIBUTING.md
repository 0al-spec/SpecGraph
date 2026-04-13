# Contributing to SpecGraph

## Supervisor Guide

For practical supervisor workflow, operator modes, outcome interpretation, and runtime-versus-spec troubleshooting, start with:

- [docs/supervisor_manual.md](/Users/egor/Development/GitHub/0AL/SpecGraph/docs/supervisor_manual.md)
- [tools/README.md](/Users/egor/Development/GitHub/0AL/SpecGraph/tools/README.md)

## Python Scaffold

This repository includes a default Python project scaffold with:

- a package in `src/specgraph`
- a simple CLI entry point (`python -m specgraph`)
- a smoke test in `tests/test_smoke.py`
- packaging metadata in `pyproject.toml`

## CI

A minimal GitHub Actions workflow is available at `.github/workflows/python-ci.yml`.
It installs the package with development dependencies and runs `pytest -q`.
