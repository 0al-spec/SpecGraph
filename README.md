# SpecGraph

**SpecGraph is the executable product ontology for Intent-Driven Development.**

It turns product intent into a structured, governed, and execution-ready graph that is:

- machine-verifiable
- human-readable
- semantically structured
- execution-connected

SpecGraph makes it possible to move from intent to implementation through specifications that remain understandable to humans, verifiable by machines, and traceable across the full software lifecycle.

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
## Python Scaffold

This repository now includes a default Python project scaffold with:

- a package in `src/specgraph`
- a simple CLI entry point (`python -m specgraph`)
- a smoke test in `tests/test_smoke.py`
- packaging metadata in `pyproject.toml`

## CI

A minimal GitHub Actions workflow is available at `.github/workflows/python-ci.yml`.
It installs the package with development dependencies and runs `pytest -q`.
